#!/usr/bin/env python3
"""
Privacy Automation Service Demonstration

This script demonstrates the functionality of the PrivacyAutomationService
with realistic appointment scenarios.
"""

import hashlib
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import Mock
from core.models.appointment import Appointment
from core.services.privacy_automation_service import PrivacyAutomationService


def mask_subject(subject: str) -> str:
    """Return a non-sensitive representation of an appointment subject."""
    if not subject:
        return "[no-subject]"
    digest = hashlib.sha256(subject.encode("utf-8")).hexdigest()[:8]
    return f"[redacted:{digest}]"


def create_mock_appointment(subject: str, categories: list = None, sensitivity: str = 'normal'):
    """Create a mock appointment for demonstration purposes"""
    appointment = Mock(spec=Appointment)
    appointment.subject = subject
    appointment.categories = categories
    appointment.sensitivity = sensitivity
    appointment.is_private = (sensitivity == 'private')
    return appointment


def main():
    """Demonstrate Privacy Automation Service functionality"""
    print("=" * 60)
    print("Privacy Automation Service Demonstration")
    print("=" * 60)
    
    # Initialize the service
    privacy_service = PrivacyAutomationService()
    
    # Create sample appointments
    appointments = [
        # Personal appointments (should be marked private)
        create_mock_appointment("Doctor Appointment", None),
        create_mock_appointment("Family Dinner", []),
        create_mock_appointment("Personal Call", None),
        
        # Work appointments (should remain public)
        create_mock_appointment("Client Meeting", ["Acme Corp - billable"]),
        create_mock_appointment("Project Review", ["Client XYZ - non-billable"]),
        create_mock_appointment("Team Standup", ["Internal Project - billable"]),
        
        # Special categories (should remain public)
        create_mock_appointment("Admin Tasks", ["Admin - non-billable"]),
        create_mock_appointment("Coffee Break", ["Break - non-billable"]),
        create_mock_appointment("Online Training", ["Online"]),
        
        # Already private appointment (should be preserved)
        create_mock_appointment("Private Work Meeting", ["Acme Corp - billable"], 'private'),
        
        # Invalid category format (should remain public)
        create_mock_appointment("Meeting with Invalid Category", ["Invalid Format"]),
    ]
    
    print(f"\nProcessing {len(appointments)} appointments...")
    print("\nBefore Privacy Processing:")
    print("-" * 40)
    for i, appt in enumerate(appointments, 1):
        categories_str = str(appt.categories) if appt.categories else "None"
        subject_str = mask_subject(getattr(appt, "subject", ""))
        print(f"{i:2d}. {subject_str:<30} | Categories: {categories_str:<25} | Sensitivity: {appt.sensitivity}")
    
    # Apply privacy rules
    processed_appointments = privacy_service.apply_privacy_rules(appointments)
    
    print("\nAfter Privacy Processing:")
    print("-" * 40)
    for i, appt in enumerate(processed_appointments, 1):
        categories_str = str(appt.categories) if appt.categories else "None"
        privacy_status = "PRIVATE" if appt.sensitivity == 'private' else "PUBLIC"
        subject_str = mask_subject(getattr(appt, "subject", ""))
        print(f"{i:2d}. {subject_str:<30} | Categories: {categories_str:<25} | Status: {privacy_status}")
    
    # Get detailed statistics
    stats = privacy_service.update_privacy_flags(appointments)
    
    print("\nPrivacy Processing Statistics:")
    print("-" * 40)
    print(f"Total appointments processed: {stats['total_appointments']}")
    print(f"Personal appointments found: {stats['personal_appointments']}")
    print(f"Work appointments found: {stats['work_appointments']}")
    print(f"Already private: {stats['already_private']}")
    print(f"Newly marked private: {stats['marked_private']}")
    
    # Get comprehensive privacy statistics
    privacy_stats = privacy_service.get_privacy_statistics(appointments)
    
    print("\nComprehensive Privacy Statistics:")
    print("-" * 40)
    print(f"Private appointments: {privacy_stats['private_appointments']}")
    print(f"Public appointments: {privacy_stats['public_appointments']}")
    print(f"Personal appointments: {privacy_stats['personal_appointments']}")
    print(f"Work appointments: {privacy_stats['work_appointments']}")
    
    print("\nPrivacy Breakdown by Sensitivity Level:")
    for level, count in privacy_stats['privacy_breakdown'].items():
        if count > 0:
            print(f"  {level.capitalize()}: {count}")
    
    # Demonstrate individual appointment analysis
    print("\nIndividual Appointment Analysis:")
    print("-" * 40)
    
    sample_appointments = [
        create_mock_appointment("Personal Meeting", None),
        create_mock_appointment("Client Call", ["Acme Corp - billable"]),
        create_mock_appointment("Admin Work", ["Admin - non-billable"]),
    ]
    
    for appt in sample_appointments:
        is_personal = privacy_service.is_personal_appointment(appt)
        should_be_private = privacy_service.should_mark_private(appt)
        
        print(f"{mask_subject(getattr(appt, 'subject', ''))}:")
        print(f"  Categories: {appt.categories}")
        print(f"  Is personal: {is_personal}")
        print(f"  Should be private: {should_be_private}")
        print()
    
    print("=" * 60)
    print("Privacy Automation Service demonstration completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
