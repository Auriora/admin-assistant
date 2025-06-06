#!/usr/bin/env python3
"""
Verify that all appointment modification types are covered in the test generation.
This script analyzes the appointment generator code to ensure complete coverage.
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.utils.appointment_generator import AppointmentGenerator
from core.services.meeting_modification_service import MeetingModificationService


def verify_modification_coverage():
    """Verify that all modification types are covered in test generation."""
    print("🔍 Verifying Appointment Modification Coverage")
    print("=" * 50)
    
    # Create a generator instance to get test cases
    generator = AppointmentGenerator(
        user_email="test@example.com",
        days_back=30,
        days_forward=30
    )
    
    # Get all test case templates
    test_cases = generator._create_specific_test_cases()
    
    # Initialize modification service for pattern detection
    mod_service = MeetingModificationService()
    
    # Track modification types found
    modification_stats = {
        'extension': [],
        'shortened': [],
        'early_start': [],
        'late_start': [],
        'regular': [],
        'orphaned': []
    }
    
    # Analyze all test cases
    for case in test_cases:
        subject = case.get('subject', '')
        mod_type = case.get('modification_type')
        edge_type = case.get('edge_type', '')
        
        # Detect modification type from subject
        detected_type = mod_service.detect_modification_type(subject)
        
        if detected_type:
            modification_stats[detected_type].append({
                'subject': subject,
                'declared_type': mod_type,
                'edge_type': edge_type
            })
            
            # Check for orphaned modifications
            if 'orphaned' in edge_type.lower():
                modification_stats['orphaned'].append({
                    'subject': subject,
                    'type': detected_type,
                    'edge_type': edge_type
                })
        else:
            modification_stats['regular'].append({
                'subject': subject,
                'declared_type': mod_type,
                'edge_type': edge_type
            })
    
    # Display results
    print(f"📊 Analysis Results:")
    print(f"   Total test cases: {len(test_cases)}")
    print()
    
    print("🔧 Modification Type Coverage:")
    required_types = ['extension', 'shortened', 'early_start', 'late_start']
    
    for mod_type in required_types:
        count = len(modification_stats[mod_type])
        status = "✅" if count > 0 else "❌"
        print(f"   {status} {mod_type.replace('_', ' ').title()}: {count} appointments")
        
        if count > 0:
            # Show examples
            for i, appt in enumerate(modification_stats[mod_type][:3]):
                print(f"      {i+1}. {appt['subject']} ({appt.get('edge_type', 'basic')})")
            if count > 3:
                print(f"      ... and {count - 3} more")
        print()
    
    # Check for orphaned modifications
    orphaned_count = len(modification_stats['orphaned'])
    if orphaned_count > 0:
        print(f"🔄 Orphaned Modifications: {orphaned_count} appointments")
        for appt in modification_stats['orphaned']:
            print(f"   - {appt['subject']} ({appt['type']})")
        print()
    
    # Check for Extended/Extension subjects
    extended_subjects = [case for case in test_cases 
                        if 'Extended' in case.get('subject', '') or 'Extension' in case.get('subject', '')]
    
    print(f"📈 Extended/Extension Appointments: {len(extended_subjects)}")
    for i, case in enumerate(extended_subjects[:10]):
        print(f"   {i+1}. {case['subject']}")
    if len(extended_subjects) > 10:
        print(f"   ... and {len(extended_subjects) - 10} more")
    print()
    
    # Coverage assessment
    missing_types = [t for t in required_types if len(modification_stats[t]) == 0]
    
    if missing_types:
        print(f"⚠️  Missing modification types: {', '.join(missing_types)}")
        return False
    else:
        print("✅ All modification types are covered!")
        
        # Additional checks
        edge_cases = sum(1 for case in test_cases if case.get('is_edge_case'))
        boundary_cases = sum(1 for case in test_cases if case.get('is_boundary_case'))
        
        print(f"⚡ Edge cases: {edge_cases}")
        print(f"🎯 Boundary cases: {boundary_cases}")
        print(f"🔧 Total modification appointments: {sum(len(modification_stats[t]) for t in required_types)}")
        
        return True


if __name__ == "__main__":
    success = verify_modification_coverage()
    sys.exit(0 if success else 1)
