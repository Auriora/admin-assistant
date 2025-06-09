#!/usr/bin/env python3
"""
Archive calendar cleanup utility for removing duplicate appointments from archive calendars.
"""
import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    # python-dotenv not available, continue without loading .env files
    pass

from core.models.user import User
from core.repositories.user_repository import UserRepository
from core.repositories.appointment_repository_msgraph import MSGraphAppointmentRepository
from core.repositories.calendar_repository_msgraph import MSGraphCalendarRepository
from core.db import SessionLocal
from core.utilities.auth_utility import get_cached_access_token
from core.utilities.graph_utility import get_graph_client
from core.utilities.async_runner import run_async


class ArchiveCalendarCleanup:
    """Cleans up duplicate appointments from archive calendars."""
    
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.stats = {
            'appointments_deleted': 0,
            'calendars_processed': 0
        }
    
    def cleanup_archive_calendar(self, calendar_name: str = "Activity Archive", dry_run: bool = False) -> Dict[str, Any]:
        """Clean up all appointments from the specified archive calendar."""
        return run_async(self._cleanup_archive_calendar_async(calendar_name, dry_run))
    
    async def _cleanup_archive_calendar_async(self, calendar_name: str, dry_run: bool) -> Dict[str, Any]:
        """Async implementation of archive calendar cleanup."""
        session = SessionLocal()
        try:
            # Get user
            user_repo = UserRepository(session)
            user = user_repo.get_by_email(self.user_email)
            
            if not user:
                raise ValueError(f"User not found: {self.user_email}")
            
            # Get MS Graph access token and create client
            access_token = get_cached_access_token()
            if not access_token:
                raise ValueError("No valid MS Graph token found. Please login with 'python src/cli/main.py login msgraph'.")
            
            graph_client = get_graph_client(user, access_token)
            
            # Get calendar repository to find the archive calendar
            calendar_repo = MSGraphCalendarRepository(graph_client, user)
            calendars = await calendar_repo.list_async()
            
            # Find the archive calendar
            archive_calendar = None
            for calendar in calendars:
                if calendar.name == calendar_name:
                    archive_calendar = calendar
                    break
            
            if not archive_calendar:
                print(f"Archive calendar '{calendar_name}' not found.")
                print("Available calendars:")
                for calendar in calendars:
                    print(f"  • {calendar.name}")
                return self.stats
            
            print(f"Found archive calendar: {archive_calendar.name} (ID: {archive_calendar.ms_calendar_id})")
            
            # Create appointment repository for the archive calendar
            appointment_repo = MSGraphAppointmentRepository(graph_client, user, archive_calendar.ms_calendar_id)
            
            # Get a wide date range to capture all appointments (2.5 years back to 2.5 years forward = 1825 days total)
            start_date = (datetime.now(timezone.utc) - timedelta(days=912)).date()
            end_date = (datetime.now(timezone.utc) + timedelta(days=912)).date()
            
            print(f"Scanning for appointments from {start_date} to {end_date}...")
            
            # Get all appointments in the archive calendar
            appointments = await appointment_repo.alist_for_user(
                start_date=start_date,
                end_date=end_date
            )
            
            print(f"Found {len(appointments)} appointments in '{calendar_name}' calendar")
            
            if len(appointments) == 0:
                print("No appointments to delete.")
                return self.stats
            
            if dry_run:
                print(f"DRY RUN: Would delete {len(appointments)} appointments:")
                for appt in appointments[:10]:  # Show first 10
                    print(f"  • {appt.subject} - {appt.start_time}")
                if len(appointments) > 10:
                    print(f"  ... and {len(appointments) - 10} more")
                
                self.stats['appointments_deleted'] = len(appointments)
                self.stats['calendars_processed'] = 1
                return self.stats
            
            # Confirm deletion (unless --yes flag is used)
            if not getattr(self, '_skip_confirmation', False):
                print(f"\nThis will delete ALL {len(appointments)} appointments from the '{calendar_name}' calendar.")
                print("This action cannot be undone!")
                response = input("Are you sure you want to continue? (yes/no): ").lower().strip()

                if response not in ['yes', 'y']:
                    print("Operation cancelled.")
                    return self.stats
            
            # Delete all appointments using the bulk delete method
            print(f"Deleting {len(appointments)} appointments...")
            deleted_appointments = await appointment_repo.adelete_for_period(start_date, end_date)
            
            self.stats['appointments_deleted'] = len(deleted_appointments)
            self.stats['calendars_processed'] = 1
            
            print(f"Successfully deleted {len(deleted_appointments)} appointments from '{calendar_name}' calendar!")
            
            return self.stats
            
        finally:
            session.close()
    
    def list_archive_calendars(self) -> List[Dict[str, Any]]:
        """List all calendars to help identify archive calendars."""
        return run_async(self._list_archive_calendars_async())
    
    async def _list_archive_calendars_async(self) -> List[Dict[str, Any]]:
        """Async implementation of calendar listing."""
        session = SessionLocal()
        try:
            # Get user
            user_repo = UserRepository(session)
            user = user_repo.get_by_email(self.user_email)
            
            if not user:
                raise ValueError(f"User not found: {self.user_email}")
            
            # Get MS Graph access token and create client
            access_token = get_cached_access_token()
            if not access_token:
                raise ValueError("No valid MS Graph token found. Please login with 'python src/cli/main.py login msgraph'.")
            
            graph_client = get_graph_client(user, access_token)
            
            # Get calendar repository
            calendar_repo = MSGraphCalendarRepository(graph_client, user)
            calendars = await calendar_repo.list_async()
            
            calendar_info = []
            for calendar in calendars:
                # Get appointment count for each calendar
                appointment_repo = MSGraphAppointmentRepository(graph_client, user, calendar.ms_calendar_id)
                
                # Get appointments in a reasonable range (last year to next year)
                start_date = (datetime.now(timezone.utc) - timedelta(days=365)).date()
                end_date = (datetime.now(timezone.utc) + timedelta(days=365)).date()
                
                try:
                    appointments = await appointment_repo.alist_for_user(
                        start_date=start_date,
                        end_date=end_date
                    )
                    appointment_count = len(appointments)
                except Exception as e:
                    appointment_count = f"Error: {e}"
                
                calendar_info.append({
                    'name': calendar.name,
                    'id': calendar.ms_calendar_id,
                    'appointment_count': appointment_count
                })
            
            return calendar_info
            
        finally:
            session.close()


def main():
    """Main function for command line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up archive calendar duplicates")
    parser.add_argument(
        "--user-email", 
        default="bcherrington.993834@outlook.com",
        help="User email for the Outlook account"
    )
    parser.add_argument(
        "--calendar-name",
        default="Activity Archive",
        help="Name of the archive calendar to clean up"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    parser.add_argument(
        "--list-calendars",
        action="store_true",
        help="List all calendars and their appointment counts"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt"
    )
    
    args = parser.parse_args()
    
    cleanup = ArchiveCalendarCleanup(args.user_email)
    cleanup._skip_confirmation = args.yes

    if args.list_calendars:
        print(f"Listing calendars for {args.user_email}...")
        calendars = cleanup.list_archive_calendars()
        print("\nAvailable calendars:")
        for cal in calendars:
            print(f"  • {cal['name']} (ID: {cal['id']}) - {cal['appointment_count']} appointments")
    else:
        print(f"Cleaning up '{args.calendar_name}' calendar for {args.user_email}...")
        result = cleanup.cleanup_archive_calendar(args.calendar_name, args.dry_run)
        print(f"\nCleanup complete:")
        print(f"  • Calendars processed: {result['calendars_processed']}")
        print(f"  • Appointments deleted: {result['appointments_deleted']}")


if __name__ == "__main__":
    main()
