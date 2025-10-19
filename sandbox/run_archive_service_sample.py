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
from core.db import get_session
from core.utilities import get_graph_client
from core.services import UserService
from support.calendar_utils import load_events_from_file, get_event_date_range
# Import MS Graph mocks for test/sample use
from tests.mocks.msgraph_mocks import (
    MockEventObj, MockEvents, MockCalendarView, MockCalendar, MockUser, MockUsers, MockMSGraphClient
)
from core.repositories.factory import get_appointment_repository
from core.orchestrators.archive_job_runner import ArchiveJobRunner
import logging

# --- CONFIGURATION ---
CORE_DB_URL = 'sqlite:///instance/admin_assistant_core_dev.db'
MS_CLIENT_ID = os.getenv('MS_CLIENT_ID')
MS_TENANT_ID = os.getenv('MS_TENANT_ID')
MS_SCOPES = ['Calendars.ReadWrite', 'User.Read']
TOKEN_FILE = 'ms_token.json'
LOCAL_EVENTS_FILE = 'tests/data/ms365_calendar_20250521_to_20250527.json'

# --- CLI FLAG ---
USE_LIVE = '--live' in sys.argv

# --- STEP 1: Get user by ID ---
user_service = UserService()
user = user_service.get_by_id(1)
if not user:
    print("No user found in user DB.")
    sys.exit(1)
print(f"Using user: {user.email}")

# --- Load ArchiveConfiguration for user ---
archive_config_service = ArchiveConfigurationService()
user_id = int(getattr(user, 'id', 0))
archive_config = archive_config_service.get_active_for_user(user_id)
if not archive_config:
    print(f"No active archive configuration found for user {user.email}.")
    sys.exit(1)
print(f"Using archive configuration: {archive_config}")

# Use configured calendar IDs
source_calendar_uri = str(getattr(archive_config, 'source_calendar_uri', ''))
archive_calendar_uri = str(getattr(archive_config, 'destination_calendar_uri', ''))


# --- STEP 2: Get events ---
# Import MS Graph mocks for test/sample use
from tests.mocks.msgraph_mocks import (
    MockEventObj, MockEvents, MockCalendarView, MockCalendar, MockUser, MockUsers, MockMSGraphClient
)

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def main():
    # Parse CLI flag and user ID (default to 1)
    import argparse
    parser = argparse.ArgumentParser(description="Run archive service sample.")
    parser.add_argument('--live', action='store_true', help='Use live MS Graph API')
    parser.add_argument('--user-id', type=int, default=1, help='User ID to archive for')
    parser.add_argument('--events-file', type=str, default=LOCAL_EVENTS_FILE, help='Path to local events file (mock mode)')
    args = parser.parse_args()

    runner = ArchiveJobRunner()
    archive_config_id = getattr(archive_config, 'id', None)
    if archive_config_id is None:
        logging.error("Archive configuration does not have an ID.")
        sys.exit(1)
    archive_config_id = int(archive_config_id)
    if args.live:
        # Live mode: get session and graph client
        session = get_session()
        from core.services import UserService
        user_service = UserService()
        user = user_service.get_by_id(args.user_id)
        if not user:
            logging.error(f"No user found in user DB for user_id={args.user_id}.")
            sys.exit(1)
        graph_client = get_graph_client(user=user, session=session)
        result = runner.run_archive_job(
            user_id=args.user_id,
            archive_config_id=archive_config_id,
            # start_date and end_date can be added if needed
        )
    else:
        result = runner.run_archive_job(
            user_id=args.user_id,
            archive_config_id=archive_config_id,
            # start_date and end_date can be added if needed
        )
    print("[ARCHIVE RESULT]")
    print(result)

# === ArchiveConfigurationRepository/Service Usage Example ===
# (This block has been removed for clarity and maintainability. See tests or samples for CRUD usage.)

if __name__ == "__main__":
    main()
