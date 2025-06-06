#!/usr/bin/env python3
"""
Comprehensive appointment generator for testing admin-assistant functionality.
"""
import asyncio
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
import sys
from pathlib import Path
import os
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv(project_root / '.env')

from core.models.appointment import Appointment
from core.models.user import User
from core.repositories.appointment_repository_msgraph import MSGraphAppointmentRepository
from core.repositories.user_repository import UserRepository
from core.db import SessionLocal
from core.utilities.auth_utility import get_cached_access_token
from core.utilities.graph_utility import get_graph_client


class AppointmentGenerator:
    """Generates comprehensive test appointments for system testing."""
    
    def __init__(
        self,
        user_email: str,
        days_back: int = 30,
        days_forward: int = 30,
        include_overlaps: bool = True,
        include_recurring: bool = True,
        include_private: bool = True,
        include_invalid_categories: bool = True
    ):
        self.user_email = user_email
        self.days_back = days_back
        self.days_forward = days_forward
        self.include_overlaps = include_overlaps
        self.include_recurring = include_recurring
        self.include_private = include_private
        self.include_invalid_categories = include_invalid_categories
        
        # Date range for appointments
        self.start_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        self.end_date = datetime.now(timezone.utc) + timedelta(days=days_forward)
        
        # Initialize counters
        self.stats = {
            'created': 0,
            'overlaps': 0,
            'recurring': 0,
            'private': 0,
            'invalid_categories': 0,
            'categories_created': 0,
            'edge_cases': 0,
            'multi_overlaps': 0,
            'special_categories': 0,
            'boundary_cases': 0,
            'extensions': 0,
            'shortenings': 0,
            'early_starts': 0,
            'late_starts': 0,
            'modifications': 0
        }
    
    def generate_appointments(self, count: int, dry_run: bool = False) -> Dict[str, Any]:
        """Generate the specified number of test appointments."""
        return asyncio.run(self._generate_appointments_async(count, dry_run))
    
    async def _generate_appointments_async(self, count: int, dry_run: bool = False) -> Dict[str, Any]:
        """Async implementation of appointment generation."""
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
            
            # Generate appointment templates
            appointment_templates = self._create_appointment_templates(count)
            
            if dry_run:
                print(f"Would create {len(appointment_templates)} appointments:")

                # Show first 10 random appointments
                print("\n  Random appointments (first 10):")
                for i, template in enumerate(appointment_templates[:10]):
                    print(f"    {i+1}. {template['subject']} - {template['start_time']} ({template.get('categories', ['No category'])})")

                # Show specific test cases with "Extended" in the subject
                extended_appointments = [t for t in appointment_templates if 'Extended' in t['subject'] or 'Extension' in t['subject']]
                if extended_appointments:
                    print(f"\n  Extension/Extended appointments ({len(extended_appointments)} total):")
                    for i, template in enumerate(extended_appointments[:10]):  # Show first 10 extension appointments
                        print(f"    {i+1}. {template['subject']} - {template['start_time']} ({template.get('categories', ['No category'])})")
                    if len(extended_appointments) > 10:
                        print(f"    ... and {len(extended_appointments) - 10} more extension appointments")

                # Show summary of other test cases
                other_test_cases = len(appointment_templates) - count
                if other_test_cases > 0:
                    print(f"\n  Additional test cases: {other_test_cases} appointments")
                    print("    (includes overlaps, recurring, boundary cases, modifications, etc.)")

                return self.stats
            
            # Create appointments
            for template in appointment_templates:
                try:
                    appointment = self._create_appointment_from_template(template, user.id)
                    await appointment_repo.aadd(appointment)
                    self.stats['created'] += 1
                    
                    # Update specific stats
                    if template.get('is_overlap'):
                        self.stats['overlaps'] += 1
                    if template.get('is_multi_overlap'):
                        self.stats['multi_overlaps'] += 1
                    if template.get('is_recurring'):
                        self.stats['recurring'] += 1
                    if template.get('is_private'):
                        self.stats['private'] += 1
                    if template.get('has_invalid_category'):
                        self.stats['invalid_categories'] += 1
                    if template.get('is_edge_case'):
                        self.stats['edge_cases'] += 1
                    if template.get('is_special_category'):
                        self.stats['special_categories'] += 1
                    if template.get('is_boundary_case'):
                        self.stats['boundary_cases'] += 1

                    # Track specific edge case types
                    edge_type = template.get('edge_type')
                    boundary_type = template.get('boundary_type')
                    modification_type = template.get('modification_type')

                    if edge_type or boundary_type:
                        self.stats['edge_cases'] += 1

                    # Track modification types
                    if modification_type:
                        self.stats['modifications'] += 1
                        if modification_type == 'extension':
                            self.stats['extensions'] += 1
                        elif modification_type == 'shortened':
                            self.stats['shortenings'] += 1
                        elif modification_type == 'early_start':
                            self.stats['early_starts'] += 1
                        elif modification_type == 'late_start':
                            self.stats['late_starts'] += 1
                        
                except Exception as e:
                    print(f"Failed to create appointment '{template['subject']}': {e}")
                    continue
            
            return self.stats
            
        finally:
            session.close()
    
    def _create_appointment_templates(self, count: int) -> List[Dict[str, Any]]:
        """Create templates for all appointments to be generated."""
        templates = []
        
        # Define appointment scenarios
        scenarios = self._get_appointment_scenarios()
        
        # Generate appointments distributed across scenarios
        for i in range(count):
            scenario = random.choice(scenarios)
            template = self._create_template_from_scenario(scenario, i)
            templates.append(template)
        
        # Add specific test cases
        templates.extend(self._create_specific_test_cases())
        
        return templates
    
    def _get_appointment_scenarios(self) -> List[Dict[str, Any]]:
        """Define different types of appointment scenarios."""
        scenarios = [
            # Regular business meetings
            {
                'type': 'business_meeting',
                'subjects': [
                    'Client Strategy Meeting', 'Project Review', 'Weekly Standup',
                    'Budget Planning', 'Team Sync', 'Quarterly Review',
                    'Product Demo', 'Requirements Gathering', 'Sprint Planning'
                ],
                'categories': [
                    # Standard valid formats
                    'Billable - Acme Corp', 'Non-billable - Acme Corp',
                    'Billable - TechStart Inc', 'Non-billable - TechStart Inc',
                    'Billable - Global Solutions', 'Non-billable - Global Solutions',
                    'Billable - Microsoft', 'Non-billable - Microsoft',
                    'Billable - Amazon Web Services', 'Non-billable - Amazon Web Services',
                    # Alternative valid formats (reversed)
                    'Acme Corp - billable', 'Acme Corp - non-billable',
                    'TechStart Inc - billable', 'TechStart Inc - non-billable'
                ],
                'durations': [30, 60, 90, 120],
                'locations': ['Conference Room A', 'Conference Room B', 'Client Office', 'Online'],
                'times': ['09:00', '10:00', '11:00', '13:00', '14:00', '15:00', '16:00']
            },
            
            # Administrative tasks
            {
                'type': 'admin',
                'subjects': [
                    'Email Processing', 'Document Review', 'Invoice Processing',
                    'Timesheet Preparation', 'File Organization', 'System Updates'
                ],
                'categories': ['Admin - non-billable'],
                'durations': [30, 45, 60],
                'locations': ['Office', 'Home Office'],
                'times': ['08:00', '08:30', '17:00', '17:30']
            },
            
            # Breaks and personal time
            {
                'type': 'break',
                'subjects': [
                    'Lunch Break', 'Coffee Break', 'Team Lunch', 'Walking Meeting'
                ],
                'categories': ['Break - non-billable'],
                'durations': [15, 30, 60],
                'locations': ['Cafeteria', 'Coffee Shop', 'Park'],
                'times': ['10:30', '12:00', '12:30', '15:30']
            },
            
            # Online meetings (special category)
            {
                'type': 'online',
                'subjects': [
                    'Remote Client Call', 'Virtual Team Meeting', 'Online Training',
                    'Webinar', 'Video Conference', 'Screen Share Session'
                ],
                'categories': ['Online'],
                'durations': [30, 60, 90],
                'locations': ['Online', 'Microsoft Teams', 'Zoom', 'Google Meet'],
                'times': ['09:00', '10:00', '11:00', '14:00', '15:00'],
                'is_special_category': True
            },

            # Special categories testing
            {
                'type': 'special_categories',
                'subjects': [
                    'System Administration', 'Email Management', 'File Organization',
                    'Coffee with Team', 'Lunch Meeting', 'Team Building'
                ],
                'categories': ['Admin - non-billable', 'Break - non-billable'],
                'durations': [30, 45, 60],
                'locations': ['Office', 'Cafeteria', 'Break Room'],
                'times': ['08:30', '12:00', '15:30', '17:00'],
                'is_special_category': True
            }
        ]
        
        # Add private appointments if enabled
        if self.include_private:
            scenarios.append({
                'type': 'private',
                'subjects': [
                    'Doctor Appointment', 'Personal Call', 'Family Time',
                    'Dentist Visit', 'Personal Errands', 'Private Meeting'
                ],
                'categories': [None],  # No categories for private
                'durations': [30, 60, 90],
                'locations': ['Personal', 'Medical Center', 'Home'],
                'times': ['08:00', '12:00', '17:00', '18:00'],
                'is_private': True
            })
        
        # Add comprehensive invalid category scenarios if enabled
        if self.include_invalid_categories:
            scenarios.extend([
                # Missing separator
                {
                    'type': 'invalid_no_separator',
                    'subjects': ['Meeting Missing Separator', 'Invalid Format Test'],
                    'categories': ['ClientName', 'JustText', 'NoSeparatorHere'],
                    'durations': [60],
                    'locations': ['Office'],
                    'times': ['14:00'],
                    'has_invalid_category': True
                },
                # Too many separators
                {
                    'type': 'invalid_too_many_separators',
                    'subjects': ['Meeting Too Many Dashes', 'Multiple Separator Test'],
                    'categories': ['Client - Name - billable', 'Too - Many - Dashes - Here'],
                    'durations': [60],
                    'locations': ['Office'],
                    'times': ['14:30'],
                    'has_invalid_category': True
                },
                # Empty customer name
                {
                    'type': 'invalid_empty_customer',
                    'subjects': ['Meeting Empty Customer', 'Missing Customer Name'],
                    'categories': [' - billable', '- non-billable', ' - billable'],
                    'durations': [60],
                    'locations': ['Office'],
                    'times': ['15:00'],
                    'has_invalid_category': True
                },
                # Invalid billing type
                {
                    'type': 'invalid_billing_type',
                    'subjects': ['Meeting Invalid Billing', 'Wrong Billing Type'],
                    'categories': [
                        'Client - invalid', 'Customer - wrong', 'Company - maybe',
                        'Client - billing', 'Customer - charged', 'Company - paid'
                    ],
                    'durations': [60],
                    'locations': ['Office'],
                    'times': ['15:30'],
                    'has_invalid_category': True
                },
                # Case sensitivity tests
                {
                    'type': 'invalid_case_sensitivity',
                    'subjects': ['Case Sensitivity Test', 'Mixed Case Category'],
                    'categories': [
                        'Client - BILLABLE', 'Customer - NON-BILLABLE',
                        'Company - Billable', 'Firm - Non-Billable'
                    ],
                    'durations': [60],
                    'locations': ['Office'],
                    'times': ['16:00'],
                    'has_invalid_category': True
                },
                # Empty and null categories
                {
                    'type': 'invalid_empty_null',
                    'subjects': ['Empty Category Test', 'Null Category Test'],
                    'categories': ['', '   ', None],
                    'durations': [60],
                    'locations': ['Office'],
                    'times': ['16:30'],
                    'has_invalid_category': True
                }
            ])
        
        return scenarios
    
    def _create_template_from_scenario(self, scenario: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Create an appointment template from a scenario."""
        # Random selections from scenario
        subject = random.choice(scenario['subjects'])
        duration = random.choice(scenario['durations'])
        location = random.choice(scenario['locations'])
        time_str = random.choice(scenario['times'])
        
        # Random date within range
        days_offset = random.randint(0, (self.end_date - self.start_date).days)
        appointment_date = self.start_date + timedelta(days=days_offset)
        
        # Parse time and create datetime
        hour, minute = map(int, time_str.split(':'))
        start_time = appointment_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        end_time = start_time + timedelta(minutes=duration)
        
        # Select category
        category = None
        if scenario['categories'] and scenario['categories'][0] is not None:
            category = random.choice(scenario['categories'])
        
        template = {
            'subject': f"{subject} #{index + 1}",
            'start_time': start_time,
            'end_time': end_time,
            'location': location,
            'categories': [category] if category else [],
            'scenario_type': scenario['type'],
            'is_private': scenario.get('is_private', False),
            'has_invalid_category': scenario.get('has_invalid_category', False),
            'is_special_category': scenario.get('is_special_category', False),
            'show_as': scenario.get('show_as', 'busy'),
            'importance': scenario.get('importance', 'normal'),
            'modification_type': scenario.get('modification_type'),
            'edge_type': scenario.get('edge_type'),
            'boundary_type': scenario.get('boundary_type')
        }
        
        return template
    
    def _create_specific_test_cases(self) -> List[Dict[str, Any]]:
        """Create specific test cases for edge scenarios."""
        test_cases = []
        base_time = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0)

        # Comprehensive overlapping scenarios (if enabled)
        if self.include_overlaps:
            overlap_day = base_time + timedelta(days=1)

            # Simple 2-way overlap
            test_cases.extend([
                {
                    'subject': 'Simple Overlap 1',
                    'start_time': overlap_day,
                    'end_time': overlap_day + timedelta(hours=1),
                    'location': 'Conference Room A',
                    'categories': ['Billable - TestClient'],
                    'show_as': 'busy',
                    'importance': 'normal',
                    'is_overlap': True
                },
                {
                    'subject': 'Simple Overlap 2',
                    'start_time': overlap_day + timedelta(minutes=30),
                    'end_time': overlap_day + timedelta(hours=1, minutes=30),
                    'location': 'Conference Room A',
                    'categories': ['Non-billable - TestClient'],
                    'show_as': 'busy',
                    'importance': 'normal',
                    'is_overlap': True
                }
            ])

            # 3-way overlap with different priorities
            triple_overlap_time = overlap_day + timedelta(hours=2)
            test_cases.extend([
                {
                    'subject': 'Triple Overlap - High Priority',
                    'start_time': triple_overlap_time,
                    'end_time': triple_overlap_time + timedelta(hours=1),
                    'location': 'Conference Room B',
                    'categories': ['Billable - HighPriorityClient'],
                    'show_as': 'busy',
                    'importance': 'high',
                    'is_multi_overlap': True
                },
                {
                    'subject': 'Triple Overlap - Normal Priority',
                    'start_time': triple_overlap_time + timedelta(minutes=15),
                    'end_time': triple_overlap_time + timedelta(hours=1, minutes=15),
                    'location': 'Conference Room B',
                    'categories': ['Billable - NormalClient'],
                    'show_as': 'busy',
                    'importance': 'normal',
                    'is_multi_overlap': True
                },
                {
                    'subject': 'Triple Overlap - Low Priority',
                    'start_time': triple_overlap_time + timedelta(minutes=30),
                    'end_time': triple_overlap_time + timedelta(hours=1, minutes=30),
                    'location': 'Conference Room B',
                    'categories': ['Non-billable - LowPriorityClient'],
                    'show_as': 'busy',
                    'importance': 'low',
                    'is_multi_overlap': True
                }
            ])

            # Tentative vs Confirmed overlap
            tentative_time = overlap_day + timedelta(hours=4)
            test_cases.extend([
                {
                    'subject': 'Confirmed Meeting',
                    'start_time': tentative_time,
                    'end_time': tentative_time + timedelta(hours=1),
                    'location': 'Conference Room C',
                    'categories': ['Billable - ConfirmedClient'],
                    'show_as': 'busy',
                    'importance': 'normal',
                    'is_overlap': True
                },
                {
                    'subject': 'Tentative Meeting',
                    'start_time': tentative_time + timedelta(minutes=30),
                    'end_time': tentative_time + timedelta(hours=1, minutes=30),
                    'location': 'Conference Room C',
                    'categories': ['Billable - TentativeClient'],
                    'show_as': 'tentative',
                    'importance': 'normal',
                    'is_overlap': True
                }
            ])

            # Free vs Busy overlap
            free_time = overlap_day + timedelta(hours=6)
            test_cases.extend([
                {
                    'subject': 'Busy Meeting',
                    'start_time': free_time,
                    'end_time': free_time + timedelta(hours=1),
                    'location': 'Conference Room D',
                    'categories': ['Billable - BusyClient'],
                    'show_as': 'busy',
                    'importance': 'normal',
                    'is_overlap': True
                },
                {
                    'subject': 'Free Time Block',
                    'start_time': free_time + timedelta(minutes=30),
                    'end_time': free_time + timedelta(hours=1, minutes=30),
                    'location': 'Available',
                    'categories': ['Break - non-billable'],
                    'show_as': 'free',
                    'importance': 'low',
                    'is_overlap': True
                }
            ])
        
        # Edge case: Boundary time appointments
        boundary_day = base_time + timedelta(days=2)
        test_cases.extend([
            # Midnight boundary
            {
                'subject': 'Midnight Boundary Start',
                'start_time': boundary_day.replace(hour=0, minute=0),
                'end_time': boundary_day.replace(hour=1, minute=0),
                'location': 'Office',
                'categories': ['Billable - MidnightClient'],
                'is_boundary_case': True
            },
            # End of day boundary
            {
                'subject': 'End of Day Boundary',
                'start_time': boundary_day.replace(hour=23, minute=0),
                'end_time': boundary_day.replace(hour=23, minute=59),
                'location': 'Office',
                'categories': ['Non-billable - LateClient'],
                'is_boundary_case': True
            },
            # Very short appointment (1 minute)
            {
                'subject': 'Very Short Meeting',
                'start_time': boundary_day.replace(hour=12, minute=0),
                'end_time': boundary_day.replace(hour=12, minute=1),
                'location': 'Quick Chat',
                'categories': ['Billable - QuickClient'],
                'is_edge_case': True
            },
            # Very long appointment (8 hours)
            {
                'subject': 'All Day Workshop',
                'start_time': boundary_day.replace(hour=9, minute=0),
                'end_time': boundary_day.replace(hour=17, minute=0),
                'location': 'Training Center',
                'categories': ['Billable - WorkshopClient'],
                'is_edge_case': True
            }
        ])

        # All-day events (fixed for MS Graph compatibility)
        all_day_date = base_time + timedelta(days=3)
        test_cases.append({
            'subject': 'All-Day Conference',
            'start_time': all_day_date.replace(hour=0, minute=0),
            'end_time': (all_day_date + timedelta(days=1)).replace(hour=0, minute=0),
            'location': 'Convention Center',
            'categories': ['Billable - Conference Org'],
            'is_all_day': True,
            'is_edge_case': True
        })
        
        # Comprehensive recurring appointments (if enabled)
        if self.include_recurring:
            recurring_start = base_time + timedelta(days=4)

            # Daily recurring series
            for i in range(5):
                test_cases.append({
                    'subject': 'Daily Standup (Recurring)',
                    'start_time': recurring_start + timedelta(days=i),
                    'end_time': recurring_start + timedelta(days=i, minutes=30),
                    'location': 'Team Room',
                    'categories': ['Non-billable - Internal'],
                    'is_recurring': True
                })

            # Weekly recurring series
            weekly_start = recurring_start + timedelta(days=7)
            for i in range(3):
                test_cases.append({
                    'subject': 'Weekly Client Review (Recurring)',
                    'start_time': weekly_start + timedelta(weeks=i),
                    'end_time': weekly_start + timedelta(weeks=i, hours=1),
                    'location': 'Client Office',
                    'categories': ['Billable - RecurringClient'],
                    'is_recurring': True
                })

            # Overlapping recurring appointments
            overlap_recurring_start = recurring_start + timedelta(days=10)
            for i in range(3):
                test_cases.extend([
                    {
                        'subject': 'Recurring Meeting A',
                        'start_time': overlap_recurring_start + timedelta(days=i),
                        'end_time': overlap_recurring_start + timedelta(days=i, hours=1),
                        'location': 'Room A',
                        'categories': ['Billable - RecurringA'],
                        'is_recurring': True,
                        'is_overlap': True
                    },
                    {
                        'subject': 'Recurring Meeting B',
                        'start_time': overlap_recurring_start + timedelta(days=i, minutes=30),
                        'end_time': overlap_recurring_start + timedelta(days=i, hours=1, minutes=30),
                        'location': 'Room B',
                        'categories': ['Billable - RecurringB'],
                        'is_recurring': True,
                        'is_overlap': True
                    }
                ])

        # Category validation comprehensive tests
        category_test_day = base_time + timedelta(days=15)
        test_cases.extend([
            # Valid category formats
            {
                'subject': 'Valid Standard Format',
                'start_time': category_test_day.replace(hour=9, minute=0),
                'end_time': category_test_day.replace(hour=10, minute=0),
                'location': 'Office',
                'categories': ['Billable - ValidClient'],
                'is_edge_case': True
            },
            {
                'subject': 'Valid Alternative Format',
                'start_time': category_test_day.replace(hour=10, minute=0),
                'end_time': category_test_day.replace(hour=11, minute=0),
                'location': 'Office',
                'categories': ['ValidClient - billable'],
                'is_edge_case': True
            },
            {
                'subject': 'Valid Special Category Admin',
                'start_time': category_test_day.replace(hour=11, minute=0),
                'end_time': category_test_day.replace(hour=12, minute=0),
                'location': 'Office',
                'categories': ['Admin - non-billable'],
                'is_special_category': True
            },
            {
                'subject': 'Valid Special Category Break',
                'start_time': category_test_day.replace(hour=12, minute=0),
                'end_time': category_test_day.replace(hour=13, minute=0),
                'location': 'Cafeteria',
                'categories': ['Break - non-billable'],
                'is_special_category': True
            },
            {
                'subject': 'Valid Special Category Online',
                'start_time': category_test_day.replace(hour=13, minute=0),
                'end_time': category_test_day.replace(hour=14, minute=0),
                'location': 'Virtual',
                'categories': ['Online'],
                'is_special_category': True
            },
            # Multiple categories (first valid should be used)
            {
                'subject': 'Multiple Categories Test',
                'start_time': category_test_day.replace(hour=14, minute=0),
                'end_time': category_test_day.replace(hour=15, minute=0),
                'location': 'Office',
                'categories': ['Invalid Format', 'Billable - ValidClient', 'Another - billable'],
                'is_edge_case': True
            }
        ])

        # Timezone and date edge cases
        timezone_test_day = base_time + timedelta(days=20)
        test_cases.extend([
            # Cross-day appointment
            {
                'subject': 'Cross-Day Appointment',
                'start_time': timezone_test_day.replace(hour=23, minute=30),
                'end_time': (timezone_test_day + timedelta(days=1)).replace(hour=0, minute=30),
                'location': 'Office',
                'categories': ['Billable - CrossDayClient'],
                'is_boundary_case': True
            },
            # Weekend appointments
            {
                'subject': 'Weekend Work',
                'start_time': (timezone_test_day + timedelta(days=6)).replace(hour=10, minute=0),  # Saturday
                'end_time': (timezone_test_day + timedelta(days=6)).replace(hour=12, minute=0),
                'location': 'Home Office',
                'categories': ['Billable - WeekendClient'],
                'is_edge_case': True
            }
        ])

        # Sensitivity and privacy edge cases
        if self.include_private:
            privacy_test_day = base_time + timedelta(days=25)
            test_cases.extend([
                # Private with categories (should be ignored)
                {
                    'subject': 'Private with Categories',
                    'start_time': privacy_test_day.replace(hour=10, minute=0),
                    'end_time': privacy_test_day.replace(hour=11, minute=0),
                    'location': 'Personal',
                    'categories': ['Billable - ShouldBeIgnored'],
                    'is_private': True,
                    'is_edge_case': True
                },
                # Private overlapping with business
                {
                    'subject': 'Business Meeting',
                    'start_time': privacy_test_day.replace(hour=14, minute=0),
                    'end_time': privacy_test_day.replace(hour=15, minute=0),
                    'location': 'Office',
                    'categories': ['Billable - BusinessClient'],
                    'is_overlap': True
                },
                {
                    'subject': 'Private Appointment',
                    'start_time': privacy_test_day.replace(hour=14, minute=30),
                    'end_time': privacy_test_day.replace(hour=15, minute=30),
                    'location': 'Personal',
                    'categories': [],
                    'is_private': True,
                    'is_overlap': True
                }
            ])

        # Date range boundary edge cases - critical for archive logic
        boundary_test_day = base_time + timedelta(days=30)  # Near end of range
        test_cases.extend([
            # Appointment starts before range, ends within range
            {
                'subject': 'Starts Before Range',
                'start_time': (boundary_test_day - timedelta(days=35)).replace(hour=14, minute=0),  # Before start_date
                'end_time': (boundary_test_day - timedelta(days=32)).replace(hour=16, minute=0),    # Within range
                'location': 'Office',
                'categories': ['Billable - BoundaryClient'],
                'is_boundary_case': True,
                'boundary_type': 'starts_before_ends_within'
            },
            # Appointment starts within range, ends after range
            {
                'subject': 'Ends After Range',
                'start_time': (boundary_test_day + timedelta(days=25)).replace(hour=14, minute=0),  # Within range
                'end_time': (boundary_test_day + timedelta(days=35)).replace(hour=16, minute=0),    # After end_date
                'location': 'Office',
                'categories': ['Billable - BoundaryClient'],
                'is_boundary_case': True,
                'boundary_type': 'starts_within_ends_after'
            },
            # Appointment spans entire range (starts before, ends after)
            {
                'subject': 'Spans Entire Range',
                'start_time': (boundary_test_day - timedelta(days=35)).replace(hour=9, minute=0),   # Before start_date
                'end_time': (boundary_test_day + timedelta(days=35)).replace(hour=17, minute=0),   # After end_date
                'location': 'Office',
                'categories': ['Billable - SpanningClient'],
                'is_boundary_case': True,
                'boundary_type': 'spans_entire_range'
            },
            # Appointment exactly on start date boundary
            {
                'subject': 'Exactly on Start Date',
                'start_time': (boundary_test_day - timedelta(days=30)).replace(hour=0, minute=0),   # Exactly start_date
                'end_time': (boundary_test_day - timedelta(days=30)).replace(hour=2, minute=0),
                'location': 'Office',
                'categories': ['Billable - StartBoundary'],
                'is_boundary_case': True,
                'boundary_type': 'on_start_boundary'
            },
            # Appointment exactly on end date boundary
            {
                'subject': 'Exactly on End Date',
                'start_time': (boundary_test_day + timedelta(days=30)).replace(hour=22, minute=0),  # Exactly end_date
                'end_time': (boundary_test_day + timedelta(days=30)).replace(hour=23, minute=59),
                'location': 'Office',
                'categories': ['Billable - EndBoundary'],
                'is_boundary_case': True,
                'boundary_type': 'on_end_boundary'
            }
        ])

        # Timezone edge cases for archive processing
        timezone_edge_day = base_time + timedelta(days=35)
        test_cases.extend([
            # Naive datetime (no timezone info)
            {
                'subject': 'Naive DateTime Test',
                'start_time': timezone_edge_day.replace(hour=10, minute=0, tzinfo=None),  # Naive
                'end_time': timezone_edge_day.replace(hour=11, minute=0, tzinfo=None),    # Naive
                'location': 'Office',
                'categories': ['Billable - NaiveTimezone'],
                'is_edge_case': True,
                'edge_type': 'naive_timezone'
            },
            # Different timezone (will be converted to UTC)
            {
                'subject': 'Different Timezone Test',
                'start_time': timezone_edge_day.replace(hour=10, minute=0),  # UTC
                'end_time': timezone_edge_day.replace(hour=11, minute=0),    # UTC
                'location': 'Office',
                'categories': ['Billable - TimezoneClient'],
                'is_edge_case': True,
                'edge_type': 'timezone_conversion'
            }
        ])

        # Invalid datetime edge cases that should be caught by archive logic
        invalid_time_day = base_time + timedelta(days=40)
        test_cases.extend([
            # Missing start time (will be caught by validation)
            {
                'subject': 'Missing Start Time',
                'start_time': None,
                'end_time': invalid_time_day.replace(hour=11, minute=0),
                'location': 'Office',
                'categories': ['Billable - InvalidTime'],
                'is_edge_case': True,
                'edge_type': 'missing_start_time'
            },
            # Missing end time (will be caught by validation)
            {
                'subject': 'Missing End Time',
                'start_time': invalid_time_day.replace(hour=10, minute=0),
                'end_time': None,
                'location': 'Office',
                'categories': ['Billable - InvalidTime'],
                'is_edge_case': True,
                'edge_type': 'missing_end_time'
            },
            # End time before start time (invalid duration)
            {
                'subject': 'Negative Duration',
                'start_time': invalid_time_day.replace(hour=11, minute=0),
                'end_time': invalid_time_day.replace(hour=10, minute=0),  # Before start
                'location': 'Office',
                'categories': ['Billable - NegativeDuration'],
                'is_edge_case': True,
                'edge_type': 'negative_duration'
            }
        ])

        # Immutability and archive state edge cases
        immutable_test_day = base_time + timedelta(days=45)
        test_cases.extend([
            # Already archived appointment (should be immutable)
            {
                'subject': 'Already Archived',
                'start_time': immutable_test_day.replace(hour=10, minute=0),
                'end_time': immutable_test_day.replace(hour=11, minute=0),
                'location': 'Office',
                'categories': ['Billable - ArchivedClient'],
                'is_archived': True,
                'is_edge_case': True,
                'edge_type': 'already_archived'
            },
            # Appointment with missing MS Graph ID
            {
                'subject': 'Missing MS Event ID',
                'start_time': immutable_test_day.replace(hour=12, minute=0),
                'end_time': immutable_test_day.replace(hour=13, minute=0),
                'location': 'Office',
                'categories': ['Billable - NoMSID'],
                'ms_event_id': None,
                'is_edge_case': True,
                'edge_type': 'missing_ms_event_id'
            }
        ])

        # Duplicate detection edge cases
        duplicate_test_day = base_time + timedelta(days=50)
        duplicate_time = duplicate_test_day.replace(hour=14, minute=0)
        test_cases.extend([
            # Exact duplicates (same subject, start, end)
            {
                'subject': 'Duplicate Meeting',
                'start_time': duplicate_time,
                'end_time': duplicate_time + timedelta(hours=1),
                'location': 'Conference Room A',
                'categories': ['Billable - DuplicateClient'],
                'is_edge_case': True,
                'edge_type': 'exact_duplicate_1'
            },
            {
                'subject': 'Duplicate Meeting',  # Same subject
                'start_time': duplicate_time,    # Same start
                'end_time': duplicate_time + timedelta(hours=1),  # Same end
                'location': 'Conference Room B',  # Different location (should still be duplicate)
                'categories': ['Non-billable - DuplicateClient'],  # Different category
                'is_edge_case': True,
                'edge_type': 'exact_duplicate_2'
            },
            # Near duplicates (slightly different times)
            {
                'subject': 'Near Duplicate Meeting',
                'start_time': duplicate_time + timedelta(minutes=1),  # 1 minute later
                'end_time': duplicate_time + timedelta(hours=1, minutes=1),
                'location': 'Conference Room C',
                'categories': ['Billable - NearDuplicateClient'],
                'is_edge_case': True,
                'edge_type': 'near_duplicate'
            }
        ])

        # Recurring appointment edge cases for expand_recurring_events_range
        if self.include_recurring:
            recurring_edge_day = base_time + timedelta(days=55)
            test_cases.extend([
                # Recurring appointment that starts before range
                {
                    'subject': 'Recurring Starts Before Range',
                    'start_time': (recurring_edge_day - timedelta(days=40)).replace(hour=9, minute=0),
                    'end_time': (recurring_edge_day - timedelta(days=40)).replace(hour=10, minute=0),
                    'location': 'Team Room',
                    'categories': ['Non-billable - RecurringEdge'],
                    'recurrence': 'FREQ=DAILY;COUNT=10',  # Daily for 10 days
                    'is_recurring': True,
                    'is_boundary_case': True,
                    'boundary_type': 'recurring_starts_before'
                },
                # Recurring appointment that extends beyond range
                {
                    'subject': 'Recurring Extends Beyond Range',
                    'start_time': (recurring_edge_day + timedelta(days=25)).replace(hour=15, minute=0),
                    'end_time': (recurring_edge_day + timedelta(days=25)).replace(hour=16, minute=0),
                    'location': 'Team Room',
                    'categories': ['Non-billable - RecurringEdge'],
                    'recurrence': 'FREQ=DAILY;COUNT=20',  # Daily for 20 days (extends beyond)
                    'is_recurring': True,
                    'is_boundary_case': True,
                    'boundary_type': 'recurring_extends_beyond'
                }
            ])

        # Meeting modification scenarios - Extensions, Shortenings, Early/Late Starts
        # Spread appointments across the LAST 2 weeks (14 days in the past)

        # Calculate spread across the last 2 weeks
        week2_end = base_time - timedelta(days=1)  # Yesterday (end of last 2 weeks)
        week2_start = week2_end - timedelta(days=6)  # Start of last week (7 days ago)
        week1_start = week2_start - timedelta(days=7)  # Start of 2 weeks ago (14 days ago)

        # Day distribution for better spread across the past 2 weeks
        modification_test_day = week1_start  # Monday of 2 weeks ago
        complex_mod_day = week1_start + timedelta(days=3)  # Thursday of 2 weeks ago
        edge_mod_day = week2_start + timedelta(days=1)  # Tuesday of last week
        final_test_day = week2_start + timedelta(days=4)  # Friday of last week
        test_cases.extend([
            # Extension scenarios - Original meeting + Extension
            {
                'subject': 'Extended Client Meeting',
                'start_time': modification_test_day.replace(hour=10, minute=0),
                'end_time': modification_test_day.replace(hour=11, minute=0),  # 1 hour original
                'location': 'Conference Room A',
                'categories': ['Billable - ExtensionClient'],
                'is_edge_case': True,
                'edge_type': 'extension_original',
                'modification_type': 'original'
            },
            {
                'subject': 'Extended',  # Extension appointment - subject must be exactly "Extended"
                'start_time': modification_test_day.replace(hour=11, minute=0),  # Starts at original end
                'end_time': modification_test_day.replace(hour=11, minute=30),   # 30 min extension
                'location': 'Conference Room A',
                'categories': ['Billable - ExtensionClient'],
                'is_edge_case': True,
                'edge_type': 'extension_modifier',
                'modification_type': 'extension'
            },

            # Shortening scenarios - Original meeting + Shortening marker
            {
                'subject': 'Shortened Client Meeting',
                'start_time': modification_test_day.replace(hour=14, minute=0),
                'end_time': modification_test_day.replace(hour=15, minute=0),  # 1 hour original
                'location': 'Conference Room B',
                'categories': ['Billable - ShorteningClient'],
                'is_edge_case': True,
                'edge_type': 'shortening_original',
                'modification_type': 'original'
            },
            {
                'subject': 'Shortened',  # Shortening marker
                'start_time': modification_test_day.replace(hour=14, minute=45),  # Overlaps with original
                'end_time': modification_test_day.replace(hour=15, minute=0),     # Ends at original end
                'location': 'Conference Room B',
                'categories': ['Billable - ShorteningClient'],
                'is_edge_case': True,
                'edge_type': 'shortening_modifier',
                'modification_type': 'shortened'
            },

            # Early start scenarios - Original meeting + Early start marker
            {
                'subject': 'Early Start Meeting',
                'start_time': modification_test_day.replace(hour=16, minute=0),
                'end_time': modification_test_day.replace(hour=17, minute=0),  # 1 hour original
                'location': 'Conference Room C',
                'categories': ['Billable - EarlyStartClient'],
                'is_edge_case': True,
                'edge_type': 'early_start_original',
                'modification_type': 'original'
            },
            {
                'subject': 'Early Start',  # Early start marker
                'start_time': modification_test_day.replace(hour=15, minute=50),  # 10 min before original
                'end_time': modification_test_day.replace(hour=16, minute=0),     # Ends at original start
                'location': 'Conference Room C',
                'categories': ['Billable - EarlyStartClient'],
                'is_edge_case': True,
                'edge_type': 'early_start_modifier',
                'modification_type': 'early_start'
            },

            # Late start scenarios - Original meeting + Late start marker
            {
                'subject': 'Late Start Meeting',
                'start_time': modification_test_day.replace(hour=18, minute=0),
                'end_time': modification_test_day.replace(hour=19, minute=0),  # 1 hour original
                'location': 'Conference Room D',
                'categories': ['Billable - LateStartClient'],
                'is_edge_case': True,
                'edge_type': 'late_start_original',
                'modification_type': 'original'
            },
            {
                'subject': 'Late Start',  # Late start marker
                'start_time': modification_test_day.replace(hour=18, minute=0),   # Starts at original start
                'end_time': modification_test_day.replace(hour=18, minute=15),   # 15 min into original
                'location': 'Conference Room D',
                'categories': ['Billable - LateStartClient'],
                'is_edge_case': True,
                'edge_type': 'late_start_modifier',
                'modification_type': 'late_start'
            }
        ])

        # Complex modification scenarios (already defined above)
        test_cases.extend([
            # Multiple extensions on same meeting
            {
                'subject': 'Multi-Extended Meeting',
                'start_time': complex_mod_day.replace(hour=9, minute=0),
                'end_time': complex_mod_day.replace(hour=10, minute=0),  # Original 1 hour
                'location': 'Conference Room E',
                'categories': ['Billable - MultiExtendClient'],
                'is_edge_case': True,
                'edge_type': 'multi_extension_original',
                'modification_type': 'original'
            },
            {
                'subject': 'Extended',  # First extension - subject must be exactly "Extended"
                'start_time': complex_mod_day.replace(hour=10, minute=0),
                'end_time': complex_mod_day.replace(hour=10, minute=30),  # 30 min extension
                'location': 'Conference Room E',
                'categories': ['Billable - MultiExtendClient'],
                'is_edge_case': True,
                'edge_type': 'multi_extension_1',
                'modification_type': 'extension'
            },
            {
                'subject': 'Extended',  # Second extension - subject must be exactly "Extended"
                'start_time': complex_mod_day.replace(hour=10, minute=30),
                'end_time': complex_mod_day.replace(hour=11, minute=0),   # Another 30 min
                'location': 'Conference Room E',
                'categories': ['Billable - MultiExtendClient'],
                'is_edge_case': True,
                'edge_type': 'multi_extension_2',
                'modification_type': 'extension'
            },

            # Combined early start + extension
            {
                'subject': 'Combined Modification Meeting',
                'start_time': complex_mod_day.replace(hour=13, minute=0),
                'end_time': complex_mod_day.replace(hour=14, minute=0),  # Original 1 hour
                'location': 'Conference Room F',
                'categories': ['Billable - CombinedModClient'],
                'is_edge_case': True,
                'edge_type': 'combined_mod_original',
                'modification_type': 'original'
            },
            {
                'subject': 'Early Start',  # Early start
                'start_time': complex_mod_day.replace(hour=12, minute=45),  # 15 min early
                'end_time': complex_mod_day.replace(hour=13, minute=0),
                'location': 'Conference Room F',
                'categories': ['Billable - CombinedModClient'],
                'is_edge_case': True,
                'edge_type': 'combined_mod_early',
                'modification_type': 'early_start'
            },
            {
                'subject': 'Extended',  # Extension - subject must be exactly "Extended"
                'start_time': complex_mod_day.replace(hour=14, minute=0),
                'end_time': complex_mod_day.replace(hour=14, minute=45),   # 45 min extension
                'location': 'Conference Room F',
                'categories': ['Billable - CombinedModClient'],
                'is_edge_case': True,
                'edge_type': 'combined_mod_extension',
                'modification_type': 'extension'
            }
        ])

        # Edge cases for modification detection (already defined above)
        test_cases.extend([
            # Extension with gap (should not be detected as extension)
            {
                'subject': 'Gapped Meeting',
                'start_time': edge_mod_day.replace(hour=10, minute=0),
                'end_time': edge_mod_day.replace(hour=11, minute=0),
                'location': 'Conference Room G',
                'categories': ['Billable - GappedClient'],
                'is_edge_case': True,
                'edge_type': 'gapped_original',
                'modification_type': 'original'
            },
            {
                'subject': 'Not Extension',  # Starts 10 minutes after original ends (gap > 5 min)
                'start_time': edge_mod_day.replace(hour=11, minute=10),
                'end_time': edge_mod_day.replace(hour=11, minute=40),
                'location': 'Conference Room G',
                'categories': ['Billable - GappedClient'],
                'is_edge_case': True,
                'edge_type': 'gapped_not_extension',
                'modification_type': 'separate'
            },

            # Minimal extension (within 5-minute tolerance)
            {
                'subject': 'Minimal Extension Meeting',
                'start_time': edge_mod_day.replace(hour=14, minute=0),
                'end_time': edge_mod_day.replace(hour=15, minute=0),
                'location': 'Conference Room H',
                'categories': ['Billable - MinimalExtClient'],
                'is_edge_case': True,
                'edge_type': 'minimal_extension_original',
                'modification_type': 'original'
            },
            {
                'subject': 'Extended',  # Starts 3 minutes after original ends (within tolerance) - subject must be exactly "Extended"
                'start_time': edge_mod_day.replace(hour=15, minute=3),
                'end_time': edge_mod_day.replace(hour=15, minute=15),
                'location': 'Conference Room H',
                'categories': ['Billable - MinimalExtClient'],
                'is_edge_case': True,
                'edge_type': 'minimal_extension_modifier',
                'modification_type': 'extension'
            },

            # Negative duration after shortening (edge case)
            {
                'subject': 'Over-Shortened Meeting',
                'start_time': edge_mod_day.replace(hour=16, minute=0),
                'end_time': edge_mod_day.replace(hour=16, minute=30),  # 30 min original
                'location': 'Conference Room I',
                'categories': ['Billable - OverShortenClient'],
                'is_edge_case': True,
                'edge_type': 'over_shortened_original',
                'modification_type': 'original'
            },
            {
                'subject': 'Shortened',  # Would shorten to negative duration
                'start_time': edge_mod_day.replace(hour=16, minute=25),  # Only 5 min left
                'end_time': edge_mod_day.replace(hour=16, minute=30),
                'location': 'Conference Room I',
                'categories': ['Billable - OverShortenClient'],
                'is_edge_case': True,
                'edge_type': 'over_shortened_modifier',
                'modification_type': 'shortened'
            },

            # Orphaned modifications (no matching original)
            {
                'subject': 'Extended',  # Extension with no matching original - subject must be exactly "Extended"
                'start_time': edge_mod_day.replace(hour=20, minute=0),
                'end_time': edge_mod_day.replace(hour=20, minute=30),
                'location': 'Conference Room J',
                'categories': ['Billable - OrphanedClient'],
                'is_edge_case': True,
                'edge_type': 'orphaned_extension',
                'modification_type': 'extension'
            },
            {
                'subject': 'Orphaned Shortened',  # Shortening with no matching original
                'start_time': edge_mod_day.replace(hour=21, minute=0),
                'end_time': edge_mod_day.replace(hour=21, minute=15),
                'location': 'Conference Room J',
                'categories': ['Billable - OrphanedClient'],
                'is_edge_case': True,
                'edge_type': 'orphaned_shortened',
                'modification_type': 'shortened'
            },
            {
                'subject': 'Orphaned Early Start',  # Early start with no matching original
                'start_time': edge_mod_day.replace(hour=22, minute=0),
                'end_time': edge_mod_day.replace(hour=22, minute=10),
                'location': 'Conference Room J',
                'categories': ['Billable - OrphanedClient'],
                'is_edge_case': True,
                'edge_type': 'orphaned_early_start',
                'modification_type': 'early_start'
            },
            {
                'subject': 'Orphaned Late Start',  # Late start with no matching original
                'start_time': edge_mod_day.replace(hour=23, minute=0),
                'end_time': edge_mod_day.replace(hour=23, minute=5),
                'location': 'Conference Room J',
                'categories': ['Billable - OrphanedClient'],
                'is_edge_case': True,
                'edge_type': 'orphaned_late_start',
                'modification_type': 'late_start'
            },

            # Case sensitivity tests for modification detection
            {
                'subject': 'Case Test Meeting',
                'start_time': edge_mod_day.replace(hour=8, minute=0),
                'end_time': edge_mod_day.replace(hour=9, minute=0),
                'location': 'Conference Room K',
                'categories': ['Billable - CaseTestClient'],
                'is_edge_case': True,
                'edge_type': 'case_test_original',
                'modification_type': 'original'
            },
            {
                'subject': 'EXTENDED',  # Uppercase extension - subject must be exactly "Extended" (case insensitive)
                'start_time': edge_mod_day.replace(hour=9, minute=0),
                'end_time': edge_mod_day.replace(hour=9, minute=30),
                'location': 'Conference Room K',
                'categories': ['Billable - CaseTestClient'],
                'is_edge_case': True,
                'edge_type': 'case_test_extension_upper',
                'modification_type': 'extension'
            },
            {
                'subject': 'Meeting SHORTENED',  # Mixed case shortening
                'start_time': edge_mod_day.replace(hour=8, minute=45),
                'end_time': edge_mod_day.replace(hour=9, minute=0),
                'location': 'Conference Room K',
                'categories': ['Billable - CaseTestClient'],
                'is_edge_case': True,
                'edge_type': 'case_test_shortened_mixed',
                'modification_type': 'shortened'
            }
        ])

        # Additional appointments spread across the 2 weeks for better distribution
        test_cases.extend([
            # Week 1 - Tuesday
            {
                'subject': 'Week 1 Tuesday Meeting',
                'start_time': (week1_start + timedelta(days=1)).replace(hour=9, minute=0),
                'end_time': (week1_start + timedelta(days=1)).replace(hour=10, minute=0),
                'location': 'Conference Room L',
                'categories': ['Billable - Week1Client'],
                'is_edge_case': False,
                'modification_type': 'original'
            },
            # Week 1 - Wednesday
            {
                'subject': 'Mid-Week Extended Meeting',
                'start_time': (week1_start + timedelta(days=2)).replace(hour=14, minute=0),
                'end_time': (week1_start + timedelta(days=2)).replace(hour=15, minute=0),
                'location': 'Conference Room M',
                'categories': ['Billable - MidWeekClient'],
                'is_edge_case': True,
                'modification_type': 'original'
            },
            {
                'subject': 'Extended',
                'start_time': (week1_start + timedelta(days=2)).replace(hour=15, minute=0),
                'end_time': (week1_start + timedelta(days=2)).replace(hour=15, minute=45),
                'location': 'Conference Room M',
                'categories': ['Billable - MidWeekClient'],
                'is_edge_case': True,
                'modification_type': 'extension'
            },
            # Week 1 - Friday
            {
                'subject': 'Friday Afternoon Meeting',
                'start_time': (week1_start + timedelta(days=4)).replace(hour=16, minute=0),
                'end_time': (week1_start + timedelta(days=4)).replace(hour=17, minute=0),
                'location': 'Conference Room N',
                'categories': ['Non-billable - FridayClient'],
                'is_edge_case': False,
                'modification_type': 'original'
            },
            # Week 2 - Monday
            {
                'subject': 'Week 2 Monday Start',
                'start_time': week2_start.replace(hour=8, minute=0),
                'end_time': week2_start.replace(hour=9, minute=0),
                'location': 'Conference Room O',
                'categories': ['Billable - Week2Client'],
                'is_edge_case': False,
                'modification_type': 'original'
            },
            # Week 2 - Wednesday
            {
                'subject': 'Midweek Extension Test',
                'start_time': (week2_start + timedelta(days=2)).replace(hour=11, minute=0),
                'end_time': (week2_start + timedelta(days=2)).replace(hour=12, minute=0),
                'location': 'Conference Room P',
                'categories': ['Billable - ExtensionTestClient'],
                'is_edge_case': True,
                'modification_type': 'original'
            },
            {
                'subject': 'Extended',
                'start_time': (week2_start + timedelta(days=2)).replace(hour=12, minute=0),
                'end_time': (week2_start + timedelta(days=2)).replace(hour=12, minute=30),
                'location': 'Conference Room P',
                'categories': ['Billable - ExtensionTestClient'],
                'is_edge_case': True,
                'modification_type': 'extension'
            },
            # Week 2 - Friday (final_test_day)
            {
                'subject': 'End of Week 2 Meeting',
                'start_time': final_test_day.replace(hour=15, minute=0),
                'end_time': final_test_day.replace(hour=16, minute=0),
                'location': 'Conference Room Q',
                'categories': ['Billable - FinalTestClient'],
                'is_edge_case': True,
                'modification_type': 'original'
            },
            {
                'subject': 'Extended',
                'start_time': final_test_day.replace(hour=16, minute=0),
                'end_time': final_test_day.replace(hour=16, minute=20),
                'location': 'Conference Room Q',
                'categories': ['Billable - FinalTestClient'],
                'is_edge_case': True,
                'modification_type': 'extension'
            }
        ])

        return test_cases
    
    def _create_appointment_from_template(self, template: Dict[str, Any], user_id: int) -> Appointment:
        """Create an Appointment object from a template."""
        # Filter out None categories
        categories = [cat for cat in template.get('categories', []) if cat is not None]

        # Handle edge cases for invalid times
        start_time = template.get('start_time')
        end_time = template.get('end_time')

        # Skip appointments with None times (they will be caught by validation)
        if start_time is None or end_time is None:
            # Create a minimal appointment that will fail validation
            appointment = Appointment(
                user_id=user_id,
                subject=template['subject'],
                start_time=start_time,
                end_time=end_time,
                location=template.get('location'),
                categories=categories
            )
            return appointment

        appointment = Appointment(
            user_id=user_id,
            subject=template['subject'],
            start_time=start_time,
            end_time=end_time,
            location=template.get('location'),
            categories=categories,
            is_all_day=template.get('is_all_day', False),
            sensitivity='private' if template.get('is_private') else 'normal',
            show_as=template.get('show_as', 'busy'),
            importance=template.get('importance', 'normal'),
            reminder_minutes_before_start=15,
            is_archived=template.get('is_archived', False),
            ms_event_id=template.get('ms_event_id'),
            recurrence=template.get('recurrence')
        )

        return appointment
