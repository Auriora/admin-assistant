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
from datetime import datetime, UTC
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
from azure.identity import DeviceCodeCredential

# --- CONFIGURATION ---
USER_DB_URL = 'sqlite:///instance/admin_assistant_flask_dev.db'
CORE_DB_URL = 'sqlite:///instance/admin_assistant_core_dev.db'
MS_CLIENT_ID = os.getenv('MS_CLIENT_ID')
MS_TENANT_ID = os.getenv('MS_TENANT_ID')
MS_SCOPES = ['Calendars.ReadWrite', 'User.Read']
TOKEN_FILE = 'ms_token.json'
LOCAL_EVENTS_FILE = 'tests/data/ms365_calendar_20250521_to_20250527.json'

# --- CLI FLAG ---
USE_LIVE = '--live' in sys.argv

# --- STEP 1: Get first user from user DB ---
user_engine = create_engine(USER_DB_URL, echo=False, future=True)
UserSession = sessionmaker(bind=user_engine)
user_session = UserSession()
user = user_session.query(User).first()
if not user:
    print("No user found in user DB.")
    sys.exit(1)
print(f"Using user: {user.email}")

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
class MockMSGraphClient:
    """
    Mock MS Graph client that returns events loaded from a local JSON file.
    """
    def __init__(self, events):
        self._events = events

    def list_events(self, filters=None, page=1, page_size=100):
        # For simplicity, ignore filters/pagination
        return self._events, None

def main():
    today = datetime.now(UTC).date()  # Used for archiving range

    if not USE_LIVE:
        print(f"[INFO] Loading events from local file: {LOCAL_EVENTS_FILE}")
        with open(LOCAL_EVENTS_FILE) as f:
            raw_events = json.load(f)
        mock_client = MockMSGraphClient(raw_events)
        repo = MSGraphAppointmentRepository(mock_client, user)  # type: ignore  # Mock client for testing
    else:
        if not MS_CLIENT_ID or not MS_TENANT_ID:
            print("Error: MS_CLIENT_ID and MS_TENANT_ID must be set as environment variables.")
            sys.exit(1)
        # Use DeviceCodeCredential for interactive login
        credential = DeviceCodeCredential(client_id=MS_CLIENT_ID, tenant_id=MS_TENANT_ID)
        scopes = ["https://graph.microsoft.com/.default"]
        graph_client = GraphServiceClient(credentials=credential, scopes=scopes)
        repo = MSGraphAppointmentRepository(graph_client, user)

    # --- STEP 3: Archive appointments into core DB ---
    core_engine = create_engine(CORE_DB_URL, echo=False, future=True)
    CoreSession = sessionmaker(bind=core_engine)
    core_session = CoreSession()
    from core.models.user import User as CoreUser  # For foreign key

    # Set up repositories for orchestrator
    fetch_repo = repo  # MSGraphAppointmentRepository instance from above
    write_repo = SQLAlchemyAppointmentRepository(core_session)

    orchestrator = CalendarArchiveOrchestrator()
    result = orchestrator.archive_user_appointments(
        user=user,
        start_date=today,
        end_date=today,
        fetch_repo=fetch_repo,
        write_repo=write_repo
    )
    print("Archive result:")
    print(result) 


if __name__ == "__main__":
    main()
