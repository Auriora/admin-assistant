#!/usr/bin/env python3
"""
Find and list Extension/Extended appointments in the calendar.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.models.user import User
from core.repositories.user_repository import UserRepository
from core.repositories.appointment_repository_msgraph import MSGraphAppointmentRepository
from core.db import SessionLocal
from core.utilities.auth_utility import get_cached_access_token
from core.utilities.graph_utility import get_graph_client


async def find_extension_appointments(user_email: str):
    """Find Extension/Extended appointments in the calendar."""
    session = SessionLocal()
    try:
        user_repo = UserRepository(session)
        user = user_repo.get_by_email(user_email)
        
        if not user:
            raise ValueError(f"User not found: {user_email}")
        
        # Get MS Graph access token and create client
        access_token = get_cached_access_token()
        if not access_token:
            raise ValueError("No valid MS Graph token found. Please login with 'admin-assistant login msgraph'.")
        
        graph_client = get_graph_client(user, access_token)
        appointment_repo = MSGraphAppointmentRepository(graph_client, user)
        
        # Get appointments from a wide date range (focus on August 2025)
        start_date = datetime(2025, 8, 1).date()
        end_date = datetime(2025, 8, 31).date()
        
        print(f"🔍 Searching for appointments from {start_date} to {end_date}")
        print(f"📧 User: {user_email}")
        print("=" * 60)
        
        appointments = await appointment_repo.alist_for_user(start_date, end_date)
        
        print(f"📊 Found {len(appointments)} total appointments in August 2025")
        print()
        
        # Filter for Extension/Extended appointments
        extension_appointments = []
        for appt in appointments:
            subject = getattr(appt, 'subject', '')
            if 'Extension' in subject or 'Extended' in subject:
                extension_appointments.append(appt)
        
        if extension_appointments:
            print(f"📈 Found {len(extension_appointments)} Extension/Extended appointments:")
            print()
            
            for i, appt in enumerate(extension_appointments, 1):
                subject = getattr(appt, 'subject', 'Unknown')
                start_time = getattr(appt, 'start_time', 'Unknown')
                end_time = getattr(appt, 'end_time', 'Unknown')
                location = getattr(appt, 'location', 'No location')
                categories = getattr(appt, 'categories', [])
                
                print(f"   {i}. {subject}")
                print(f"      📅 {start_time} - {end_time}")
                print(f"      📍 {location}")
                print(f"      🏷️  {categories}")
                print()
        else:
            print("❌ No Extension/Extended appointments found in August 2025")
            print()
            print("🔍 Let's check what appointments DO exist:")
            for i, appt in enumerate(appointments[:10], 1):
                subject = getattr(appt, 'subject', 'Unknown')
                start_time = getattr(appt, 'start_time', 'Unknown')
                print(f"   {i}. {subject} - {start_time}")
            if len(appointments) > 10:
                print(f"   ... and {len(appointments) - 10} more")
        
        return extension_appointments
        
    finally:
        session.close()


if __name__ == "__main__":
    user_email = "bcherrington.993834@outlook.com"
    try:
        extension_appts = asyncio.run(find_extension_appointments(user_email))
        print(f"✅ Search complete. Found {len(extension_appts)} Extension/Extended appointments.")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
