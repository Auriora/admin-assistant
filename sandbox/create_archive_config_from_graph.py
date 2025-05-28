import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.models.user import User
from core.models.archive_configuration import ArchiveConfiguration
from core.services.archive_configuration_service import ArchiveConfigurationService
from core.repositories.calendar_repository_msgraph import MSGraphCalendarRepository
from msgraph.graph_service_client import GraphServiceClient
from azure.identity import DeviceCodeCredential, TokenCachePersistenceOptions

# --- CONFIGURATION ---
CORE_DB_URL = 'sqlite:///instance/admin_assistant_core_dev.db'
MS_CLIENT_ID = os.getenv('MS_CLIENT_ID')
MS_TENANT_ID = os.getenv('MS_TENANT_ID')

# --- DB SETUP ---
engine = create_engine(CORE_DB_URL, echo=False, future=True)
Session = sessionmaker(bind=engine)
session = Session()

# --- Get first user ---
user = session.query(User).first()
if not user:
    print("No user found in user DB.")
    exit(1)
print(f"Using user: {user.email}")
user_id = int(getattr(user, 'id', 0))

# --- Check required env vars ---
if not MS_CLIENT_ID or not MS_TENANT_ID:
    print("Error: MS_CLIENT_ID and MS_TENANT_ID must be set as environment variables.")
    exit(1)

# --- MS Graph Auth ---
cache_path = os.path.join(os.path.dirname(__file__), '.msgraph_token_cache.bin')
cache_opts = TokenCachePersistenceOptions(
    name="msgraph_token_cache",
    allow_unencrypted_storage=True,
    path=cache_path
)
credential = DeviceCodeCredential(
    client_id=MS_CLIENT_ID,
    tenant_id=MS_TENANT_ID,
    cache_persistence_options=cache_opts
)
scopes = ["https://graph.microsoft.com/.default"]
graph_client = GraphServiceClient(credentials=credential, scopes=scopes)

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
    source_calendar_id=archive_cal.ms_calendar_id,  # For demo, use as both source and dest
    destination_calendar_id=archive_cal.ms_calendar_id,
    is_active=True,
    timezone="Europe/London"
)

# --- Store configuration ---
service = ArchiveConfigurationService()
service.create(archive_config)
print(f"Created archive configuration: {archive_config}") 