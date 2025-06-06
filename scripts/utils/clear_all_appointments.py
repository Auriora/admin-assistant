#!/usr/bin/env python3
"""
Clear all appointments from a test calendar.
"""
import asyncio
from datetime import datetime, timedelta, timezone
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


async def clear_all_appointments(user_email: str):
    """Clear all appointments from the calendar."""
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
        
        # Delete appointments in a very wide date range (2 years back to 2 years forward)
        start_date = (datetime.now(timezone.utc) - timedelta(days=730)).date()
        end_date = (datetime.now(timezone.utc) + timedelta(days=730)).date()
        
        print(f"Deleting all appointments from {start_date} to {end_date}...")
        
        deleted_appointments = await appointment_repo.adelete_for_period(start_date, end_date)
        
        print(f"Successfully deleted {len(deleted_appointments)} appointments!")
        
        return len(deleted_appointments)
        
    finally:
        session.close()


if __name__ == "__main__":
    user_email = "bcherrington.993834@outlook.com"
    deleted_count = asyncio.run(clear_all_appointments(user_email))
    print(f"Cleared {deleted_count} appointments from {user_email}")
