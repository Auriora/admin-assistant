"""
Sample script to run the archive service independently of Flask.
- By default, loads events from a local MS Graph API JSON file for testing.
- With '--live', fetches events from Microsoft Graph API (with token persistence).
- Archives events into the core DB using the archive_appointments service.
- Prints the result.

Requirements: msal, requests, sqlalchemy, pytz, dateutil
"""
import os
import sys
import json
from datetime import datetime, UTC, timedelta
import pytz
import msal
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.models.user import User
from core.repositories.appointment_repository_msgraph import MSGraphAppointmentRepository
from core.orchestrators.calendar_archive_orchestrator import CalendarArchiveOrchestrator
from core.repositories.appointment_repository_sqlalchemy import SQLAlchemyAppointmentRepository
from msgraph.graph_service_client import GraphServiceClient
from azure.identity import DeviceCodeCredential, TokenCachePersistenceOptions
import re
from core.models.archive_configuration import ArchiveConfiguration
from core.services.archive_configuration_service import ArchiveConfigurationService
from sqlalchemy.exc import SQLAlchemyError

# --- CONFIGURATION ---
CORE_DB_URL = 'sqlite:///instance/admin_assistant_core_dev.db'
MS_CLIENT_ID = os.getenv('MS_CLIENT_ID')
MS_TENANT_ID = os.getenv('MS_TENANT_ID')
MS_SCOPES = ['Calendars.ReadWrite', 'User.Read']
TOKEN_FILE = 'ms_token.json'
LOCAL_EVENTS_FILE = 'tests/data/ms365_calendar_20250521_to_20250527.json'

# --- CLI FLAG ---
USE_LIVE = '--live' in sys.argv

# --- STEP 1: Get first user from user DB ---
user_engine = create_engine(CORE_DB_URL, echo=False, future=True)
UserSession = sessionmaker(bind=user_engine)
user_session = UserSession()
user = user_session.query(User).first()
if not user:
    print("No user found in user DB.")
    sys.exit(1)
print(f"Using user: {user.email}")

# --- Load ArchiveConfiguration for user ---
archive_config_service = ArchiveConfigurationService()
user_id = int(getattr(user, 'id', 0))
archive_configs = archive_config_service.list_for_user(user_id)
archive_config = next((c for c in archive_configs if getattr(c, 'is_active', False)), None)
if not archive_config:
    print(f"No active archive configuration found for user {user.email}.")
    sys.exit(1)
print(f"Using archive configuration: {archive_config}")

# Use configured calendar IDs
source_calendar_id = str(getattr(archive_config, 'source_calendar_id', ''))
archive_calendar_id = str(getattr(archive_config, 'destination_calendar_id', ''))

def get_token(msal_app):
    """
    Load token from file if available, else use device code flow.
    Persist token for future runs.
    """
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            token_data = json.load(f)
        # Try to use refresh token
        result = msal_app.acquire_token_by_refresh_token(
            token_data.get("refresh_token"),
            scopes=MS_SCOPES
        )
        if "access_token" in result:
            return result
        print("Refresh token expired or invalid, falling back to device code flow.")
    # Device code flow
    flow = msal_app.initiate_device_flow(scopes=MS_SCOPES)
    if 'user_code' not in flow:
        print("Failed to create device flow. Response:", flow)
        sys.exit(1)
    print(f"To authenticate, visit {flow['verification_uri']} and enter code: {flow['user_code']}")
    result = msal_app.acquire_token_by_device_flow(flow)
    if "access_token" in result:
        with open(TOKEN_FILE, "w") as f:
            json.dump(result, f)
    return result

# --- STEP 2: Get events ---
# Mock Graph client that mimics the msgraph-sdk interface for repository compatibility
class MockEventObj:
    def __init__(self, data):
        self.__dict__.update(data)

class MockEvents:
    def __init__(self, events, odata_next_link=None):
        # Wrap each event dict in a MockEventObj for compatibility with vars(e)
        self.value = [MockEventObj(e) if isinstance(e, dict) else e for e in events]
        self.odata_next_link = odata_next_link
        print(f"[MOCK DEBUG] MockEvents initialized with {len(self.value)} events. odata_next_link={self.odata_next_link}")
    async def get(self, *args, **kwargs):
        print(f"[MOCK DEBUG] MockEvents.get() called. Returning {len(self.value)} events. odata_next_link={self.odata_next_link}")
        return self

class MockCalendarView:
    def __init__(self, events):
        self._all_events = events
        self._url = None
        self._page_size = 5
        self._page_index = 0
        print(f"[MOCK DEBUG] MockCalendarView initialized.")
    def with_url(self, url):
        self._url = url
        print(f"[MOCK DEBUG] MockCalendarView.with_url({url}) called.")
        # Parse page index from url if present
        if url and "mock://next_page/" in url:
            match = re.search(r"mock://next_page/(\d+)", url)
            if match:
                self._page_index = int(match.group(1))
            else:
                self._page_index = 0
        else:
            # Any other url (the initial calendarView url) is page 0
            self._page_index = 0
        return self
    async def get(self, *args, **kwargs):
        print(f"[MOCK DEBUG] MockCalendarView.get() called for url={self._url} page_index={self._page_index}")
        page_size = self._page_size
        start = self._page_index * page_size
        end = start + page_size
        page_events = self._all_events[start:end]
        next_link = None
        if end < len(self._all_events):
            next_link = f"mock://next_page/{self._page_index+1}"
        return MockEvents(page_events, odata_next_link=next_link)

class MockCalendar:
    def __init__(self, events):
        print(f"[MOCK DEBUG] MockCalendar initialized.")
        self.events = MockEvents(events)
        self.calendar_view = MockCalendarView(events)

class MockUser:
    def __init__(self, events):
        print(f"[MOCK DEBUG] MockUser initialized.")
        self.calendar = MockCalendar(events)

class MockUsers:
    def __init__(self, events):
        self._events = events
        print(f"[MOCK DEBUG] MockUsers initialized.")
    def by_user_id(self, user_email):
        print(f"[MOCK DEBUG] MockUsers.by_user_id({user_email}) called.")
        return MockUser(self._events)

class MockMSGraphClient:
    def __init__(self, events):
        print(f"[MOCK DEBUG] MockMSGraphClient initialized.")
        self.users = MockUsers(events)

def main():
    end_date = datetime.now().date()  # Uses local timezone by default
    start_date = end_date - timedelta(days=7)  # Used for archiving range

    if not USE_LIVE:
        print(f"[INFO] Loading events from local file: {LOCAL_EVENTS_FILE}")
        with open(LOCAL_EVENTS_FILE) as f:
            raw_events = json.load(f)
        print(f"Loaded {len(raw_events)} events from file.")
        event_dates = []
        for e in raw_events:
            start = e.get('start', {}).get('dateTime')
            end = e.get('end', {}).get('dateTime')
            print(f"Event start: {start}, end: {end}")
            if start:
                try:
                    event_dates.append(datetime.fromisoformat(start.replace('Z', '+00:00')).date())
                except Exception:
                    pass
            if end:
                try:
                    event_dates.append(datetime.fromisoformat(end.replace('Z', '+00:00')).date())
                except Exception:
                    pass
        if event_dates:
            start_date = min(event_dates)
            end_date = max(event_dates)
            print(f"Auto archive range: {start_date} to {end_date}")
        else:
            print("No valid event dates found; using today for archive range.")
        mock_client = MockMSGraphClient(raw_events)
        repo = MSGraphAppointmentRepository(mock_client, user, source_calendar_id)  # type: ignore  # Mock client for testing
        print(f"[DEBUG] Calling repo.list_for_user...")
        appointments = repo.list_for_user(start_date=start_date, end_date=end_date)
        print(f"[DEBUG] repo.list_for_user returned {len(appointments)} appointments.")
        for appt in appointments:
            print(f"  Appointment: subject={getattr(appt, 'subject', None)}, start={getattr(appt, 'start_time', None)}, end={getattr(appt, 'end_time', None)}")
    else:
        if not MS_CLIENT_ID or not MS_TENANT_ID:
            print("Error: MS_CLIENT_ID and MS_TENANT_ID must be set as environment variables.")
            sys.exit(1)
        # Use DeviceCodeCredential with persistent token cache
        cache_path = os.path.join(os.path.dirname(__file__), '.msgraph_token_cache.bin')
        cache_opts = TokenCachePersistenceOptions(
            name="msgraph_token_cache",
            allow_unencrypted_storage=True,
            path=cache_path
        )
        print(f"[INFO] Using persistent token cache at: {cache_path}")
        credential = DeviceCodeCredential(
            client_id=MS_CLIENT_ID,
            tenant_id=MS_TENANT_ID,
            cache_persistence_options=cache_opts
        )
        scopes = ["https://graph.microsoft.com/.default"]
        graph_client = GraphServiceClient(credentials=credential, scopes=scopes)
        repo = MSGraphAppointmentRepository(graph_client, user, source_calendar_id)
        print("[INFO] DeviceCodeCredential is now using a persistent token cache. You should only be prompted to authenticate once unless the token expires or is revoked.")
        print(f"[DEBUG] User email: {getattr(user, 'email', None)}")
        print(f"[DEBUG] Querying appointments from {start_date} to {end_date}")
        try:
            appointments = repo.list_for_user(start_date=start_date, end_date=end_date)
            print(f"[DEBUG] repo.list_for_user (live) returned {len(appointments)} appointments.")
            if not appointments:
                print("[WARN] No appointments found for the given user and date range.")
            for appt in appointments:
                print(f"  Appointment: subject={getattr(appt, 'subject', None)}, start={getattr(appt, 'start_time', None)}, end={getattr(appt, 'end_time', None)}")
        except Exception as e:
            print(f"[ERROR] Exception when calling repo.list_for_user (live): {e}")

    # --- STEP 3: Archive appointments into core DB ---
    core_engine = create_engine(CORE_DB_URL, echo=False, future=True)
    CoreSession = sessionmaker(bind=core_engine)
    core_session = CoreSession()
    from core.models.user import User as CoreUser  # For foreign key

    # Set up repositories for orchestrator
    fetch_repo = repo  # MSGraphAppointmentRepository instance from above
    write_repo = SQLAlchemyAppointmentRepository(user, archive_calendar_id, core_session)

    orchestrator = CalendarArchiveOrchestrator()
    print("[DEBUG] Calling orchestrator.archive_user_appointments...")
    result = orchestrator.archive_user_appointments(
        user=user,
        start_date=start_date,
        end_date=end_date,
        fetch_repo=fetch_repo,
        write_repo=write_repo
    )
    print("[DEBUG] Archive result:")
    print(result) 

# === ArchiveConfigurationRepository/Service Usage Example ===
service = ArchiveConfigurationService()

try:
    # Create a new configuration
    config = ArchiveConfiguration(
        user_id=1,
        name="Test Archive Config",
        source_calendar_id="source-calendar-id",
        destination_calendar_id="dest-calendar-id",
        is_active=True,
        timezone="Europe/London"
    )
    service.create(config)
    print(f"Created: {config}")

    # List all configurations for the user
    configs = service.list_for_user(1)
    print(f"Configs for user 1: {configs}")

    # Update the configuration's name
    if configs:
        config_to_update = configs[0]
        setattr(config_to_update, 'name', "Updated Archive Config Name")
        service.update(config_to_update)
        print(f"Updated: {config_to_update}")

    # Delete the configuration
    if configs:
        config_id = getattr(configs[0], 'id', None)
        if isinstance(config_id, int):
            service.delete(config_id)
            print(f"Deleted config with id {config_id}")
        else:
            print(f"Could not delete: invalid config_id {config_id}")

except (ValueError, SQLAlchemyError) as e:
    print(f"Error: {e}")

if __name__ == "__main__":
    main()
