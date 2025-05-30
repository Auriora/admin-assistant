import os
from core.db import get_session
from core.models.user import User
from core.models.archive_configuration import ArchiveConfiguration
from core.services.archive_configuration_service import ArchiveConfigurationService
from core.repositories.calendar_repository_msgraph import MSGraphCalendarRepository
from core.utilities import get_graph_client
from core.services import UserService

# --- DB SETUP ---
session = get_session()
user_service = UserService()

# --- Get user by ID ---
user = user_service.get_by_id(1)
if not user:
    print("No user found in user DB.")
    exit(1)
print(f"Using user: {user.email}")
user_id = int(getattr(user, 'id', 0))

# --- Check required env vars ---
if not os.getenv('MS_CLIENT_ID') or not os.getenv('MS_TENANT_ID'):
    print("Error: MS_CLIENT_ID and MS_TENANT_ID must be set as environment variables.")
    exit(1)

# --- MS Graph Auth & Client ---
graph_client = get_graph_client(user, session)

# --- List calendars from Graph ---
cal_repo = MSGraphCalendarRepository(graph_client, user)
calendars = cal_repo.list()
if not calendars:
    print("No calendars found for user in Graph API.")
    exit(1)
print("Available calendars:")
for idx, cal in enumerate(calendars):
    print(f"  [{idx}] {cal.name} (id={cal.ms_calendar_id})")

# --- Prompt user to select archive calendar ---
sel = input(f"Select the calendar to use as the ARCHIVE calendar [0-{len(calendars)-1}]: ")
try:
    sel_idx = int(sel)
    archive_cal = calendars[sel_idx]
except Exception:
    print("Invalid selection.")
    exit(1)

# --- Create ArchiveConfiguration ---
archive_config = ArchiveConfiguration(
    user_id=user_id,
    name=f"Archive: {archive_cal.name}",
    source_calendar_uri=archive_cal.ms_calendar_id,  # For demo, use as both source and dest
    destination_calendar_uri=archive_cal.ms_calendar_id,
    is_active=True,
    timezone="Europe/London"
)

# --- Store configuration ---
service = ArchiveConfigurationService()
service.create(archive_config)
print(f"Created archive configuration: {archive_config}") 