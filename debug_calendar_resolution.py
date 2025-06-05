#!/usr/bin/env python3
"""
Debug script to check calendar URI resolution
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.utilities.calendar_resolver import CalendarResolver
from core.utilities.auth_utility import get_cached_access_token
from core.services.user_service import UserService

def main():
    # Get user
    user_service = UserService()
    user = user_service.get_by_email("bruce.cherrington@outlook.com")
    if not user:
        print("User not found!")
        return
    
    # Get access token
    access_token = get_cached_access_token()
    if not access_token:
        print("No access token found!")
        return
    
    # Create resolver
    resolver = CalendarResolver(user, access_token)
    
    # Test URIs from the default configuration
    source_uri = "msgraph://calendars/primary"
    dest_uri = 'msgraph://calendars/"Activity Archive"'
    
    print("=== Calendar URI Resolution Debug ===")
    print(f"User: {user.email}")
    print()
    
    print(f"Source URI: {source_uri}")
    try:
        source_id = resolver.resolve_calendar_uri(source_uri)
        print(f"Resolved Source ID: '{source_id}'")
        print(f"Source ID type: {type(source_id)}")
        print(f"Source ID length: {len(source_id) if source_id else 0}")
    except Exception as e:
        print(f"Source resolution error: {e}")
    
    print()
    print(f"Destination URI: {dest_uri}")
    try:
        dest_id = resolver.resolve_calendar_uri(dest_uri)
        print(f"Resolved Dest ID: '{dest_id}'")
        print(f"Dest ID type: {type(dest_id)}")
        print(f"Dest ID length: {len(dest_id) if dest_id else 0}")
    except Exception as e:
        print(f"Destination resolution error: {e}")
    
    print()
    print("=== Available Calendars ===")
    try:
        calendars = resolver._get_msgraph_calendars()
        for i, cal in enumerate(calendars):
            name = cal.get('name', 'Unknown')
            cal_id = cal.get('id', 'Unknown')
            is_default = cal.get('isDefaultCalendar', False)
            print(f"{i+1}. Name: '{name}'")
            print(f"   ID: '{cal_id}'")
            print(f"   Is Default: {is_default}")
            print()
    except Exception as e:
        print(f"Error listing calendars: {e}")

if __name__ == "__main__":
    main()
