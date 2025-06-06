#!/usr/bin/env python3
"""
Test data cleanup utility for removing generated test appointments and categories.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any
import sys
from pathlib import Path
import os
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv(project_root / '.env')

from core.models.user import User
from core.repositories.user_repository import UserRepository
from core.repositories.appointment_repository_msgraph import MSGraphAppointmentRepository
from core.db import SessionLocal
from core.utilities.auth_utility import get_cached_access_token
from core.utilities.graph_utility import get_graph_client


class TestDataCleanup:
    """Cleans up test appointments and categories."""
    
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.stats = {
            'appointments_deleted': 0,
            'categories_deleted': 0
        }
    
    def cleanup_test_data(self, dry_run: bool = False) -> Dict[str, Any]:
        """Clean up test appointments and categories."""
        return asyncio.run(self._cleanup_test_data_async(dry_run))
    
    async def _cleanup_test_data_async(self, dry_run: bool = False) -> Dict[str, Any]:
        """Async implementation of test data cleanup."""
        # Get user and repository
        session = SessionLocal()
        try:
            user_repo = UserRepository(session)
            user = user_repo.get_by_email(self.user_email)

            if not user:
                raise ValueError(f"User not found: {self.user_email}")

            # Get MS Graph access token and create client
            access_token = get_cached_access_token()
            if not access_token:
                raise ValueError("No valid MS Graph token found. Please login with 'admin-assistant login msgraph'.")

            graph_client = get_graph_client(user, access_token)
            appointment_repo = MSGraphAppointmentRepository(graph_client, user)
            
            # Get date range for test appointments (last 60 days to next 60 days)
            start_date = datetime.now(timezone.utc) - timedelta(days=60)
            end_date = datetime.now(timezone.utc) + timedelta(days=60)
            
            # Get all appointments in the range
            appointments = await appointment_repo.alist_for_user(
                start_date=start_date.date(),
                end_date=end_date.date()
            )
            
            # Filter for test appointments (those with test patterns in subject)
            test_appointments = self._identify_test_appointments(appointments)
            
            if dry_run:
                print(f"Would delete {len(test_appointments)} test appointments:")
                for appt in test_appointments[:10]:  # Show first 10
                    print(f"  • {appt.subject} - {appt.start_time}")
                if len(test_appointments) > 10:
                    print(f"  ... and {len(test_appointments) - 10} more")
                
                self.stats['appointments_deleted'] = len(test_appointments)
                return self.stats
            
            # Delete test appointments
            for appointment in test_appointments:
                try:
                    if appointment.ms_event_id:
                        await appointment_repo.adelete(appointment.ms_event_id)
                        self.stats['appointments_deleted'] += 1
                except Exception as e:
                    print(f"Failed to delete appointment '{appointment.subject}': {e}")
                    continue
            
            # TODO: Implement category cleanup when MSGraph category management is available
            
            return self.stats
            
        finally:
            session.close()
    
    def _identify_test_appointments(self, appointments: List[Any]) -> List[Any]:
        """Identify appointments that appear to be test data."""
        test_appointments = []
        
        # Patterns that indicate test appointments
        test_patterns = [
            '#',  # Appointments with numbers (from generator)
            'Test',
            'Mock',
            'Demo',
            'Sample',
            'Overlapping Meeting',
            'Daily Standup (Recurring)',
            'All-Day Conference',
            'Meeting with Invalid Category',
            'Test Invalid Format',
            'Wrong Category Format'
        ]
        
        for appointment in appointments:
            subject = getattr(appointment, 'subject', '') or ''
            
            # Check if subject contains test patterns
            for pattern in test_patterns:
                if pattern.lower() in subject.lower():
                    test_appointments.append(appointment)
                    break
            
            # Check for test categories
            categories = getattr(appointment, 'categories', []) or []
            if isinstance(categories, list):
                for category in categories:
                    if isinstance(category, str):
                        if any(test_word in category.lower() for test_word in ['test', 'invalid', 'wrong']):
                            test_appointments.append(appointment)
                            break
        
        return test_appointments


if __name__ == "__main__":
    # Test the cleanup utility
    cleanup = TestDataCleanup("test@example.com")
    result = cleanup.cleanup_test_data(dry_run=True)
    print(f"Would delete {result['appointments_deleted']} appointments")
