#!/usr/bin/env python3
"""
Demonstration script for TimesheetArchiveService

This script shows how to use the TimesheetArchiveService to filter appointments
for timesheet and billing purposes.
"""

import sys
import os
from datetime import datetime, timezone
from unittest.mock import Mock

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.services.timesheet_archive_service import TimesheetArchiveService
from core.models.appointment import Appointment


def create_sample_appointment(subject, categories=None, show_as="busy", start_hour=9):
    """Create a sample appointment for demonstration"""
    appointment = Mock(spec=Appointment)
    appointment.subject = subject
    appointment.categories = categories or []
    appointment.show_as = show_as
    appointment.start_time = datetime(2024, 1, 15, start_hour, 0, tzinfo=timezone.utc)
    appointment.end_time = datetime(2024, 1, 15, start_hour + 1, 0, tzinfo=timezone.utc)
    return appointment


def main():
    """Demonstrate TimesheetArchiveService functionality"""
    print("=== TimesheetArchiveService Demonstration ===\n")
    
    # Create the service
    service = TimesheetArchiveService()
    
    # Create sample appointments
    appointments = [
        create_sample_appointment("Client Strategy Meeting", ["Acme Corp - billable"], start_hour=9),
        create_sample_appointment("Team Standup", ["Internal - non-billable"], start_hour=10),
        create_sample_appointment("Travel to Client Site", [], start_hour=11),
        create_sample_appointment("Personal Doctor Appointment", [], start_hour=12),
        create_sample_appointment("Free Time Block", [], show_as="free", start_hour=13),
        create_sample_appointment("Project Review", ["TechCorp - billable"], start_hour=14),
        create_sample_appointment("Drive to Conference", [], start_hour=15),
    ]
    
    print(f"Total appointments: {len(appointments)}")
    print("\nAppointment details:")
    for i, appt in enumerate(appointments, 1):
        print(f"  {i}. {appt.subject} (Status: {appt.show_as}, Categories: {appt.categories})")
    
    # Mock the category service to provide realistic responses
    def mock_category_extract(appointment):
        if "Acme Corp - billable" in appointment.categories:
            return {"customer": "Acme Corp", "billing_type": "billable", "is_personal": False, "is_valid": True}
        elif "Internal - non-billable" in appointment.categories:
            return {"customer": "Internal", "billing_type": "non-billable", "is_personal": False, "is_valid": True}
        elif "TechCorp - billable" in appointment.categories:
            return {"customer": "TechCorp", "billing_type": "billable", "is_personal": False, "is_valid": True}
        else:
            return {"customer": None, "billing_type": None, "is_personal": True, "is_valid": False}
    
    # Apply the mock
    service.category_service.extract_customer_billing_info = mock_category_extract
    
    # Filter appointments for timesheet
    print("\n=== Filtering Appointments for Timesheet ===")
    result = service.filter_appointments_for_timesheet(appointments, include_travel=True)
    
    print(f"\nFiltered appointments (business + travel): {len(result['filtered_appointments'])}")
    for i, appt in enumerate(result['filtered_appointments'], 1):
        print(f"  {i}. {appt.subject}")
    
    print(f"\nExcluded appointments: {len(result['excluded_appointments'])}")
    for i, appt in enumerate(result['excluded_appointments'], 1):
        print(f"  {i}. {appt.subject}")
    
    # Show statistics
    print("\n=== Statistics ===")
    stats = result['statistics']
    print(f"Total appointments processed: {stats['total_appointments']}")
    print(f"Business appointments: {stats['business_appointments']}")
    print(f"Excluded appointments: {stats['excluded_appointments']}")
    print(f"Overlap groups processed: {stats['overlap_groups_processed']}")
    
    print("\nExclusion reasons:")
    for reason, count in stats['exclusion_reasons'].items():
        if count > 0:
            print(f"  {reason}: {count}")
    
    print("\nCategory breakdown:")
    for category, count in stats['category_breakdown'].items():
        print(f"  {category}: {count}")
    
    # Test travel detection
    print("\n=== Travel Detection Test ===")
    travel_subjects = [
        "Travel to Client Site",
        "Drive to Conference", 
        "Flight to Meeting",
        "Regular Team Meeting"
    ]
    
    for subject in travel_subjects:
        test_appt = create_sample_appointment(subject)
        is_travel = service._detect_travel_appointment(test_appt)
        print(f"'{subject}' -> Travel: {is_travel}")
    
    # Test without travel appointments
    print("\n=== Filtering Without Travel Appointments ===")
    result_no_travel = service.filter_appointments_for_timesheet(appointments, include_travel=False)
    print(f"Business appointments (no travel): {len(result_no_travel['filtered_appointments'])}")
    for i, appt in enumerate(result_no_travel['filtered_appointments'], 1):
        print(f"  {i}. {appt.subject}")
    
    print("\n=== Demonstration Complete ===")


if __name__ == "__main__":
    main()
