"""
Unit tests for TimesheetArchiveService

Tests the category-filtered archiving functionality for timesheet and billing purposes.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from core.services.timesheet_archive_service import TimesheetArchiveService
from core.models.appointment import Appointment


class TestTimesheetArchiveService:
    """Test suite for TimesheetArchiveService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = TimesheetArchiveService()

    def create_mock_appointment(
        self, 
        subject="Test Meeting", 
        categories=None, 
        show_as="busy",
        start_time=None,
        end_time=None
    ):
        """Create a mock appointment for testing"""
        appointment = Mock(spec=Appointment)
        appointment.subject = subject
        appointment.categories = categories or []
        appointment.show_as = show_as
        appointment.start_time = start_time or datetime(2024, 1, 15, 9, 0, tzinfo=timezone.utc)
        appointment.end_time = end_time or datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)
        return appointment

    def test_timesheet_categories_constant(self):
        """Test that TIMESHEET_CATEGORIES contains expected values"""
        expected_categories = {"billable", "non-billable", "travel"}
        assert self.service.TIMESHEET_CATEGORIES == expected_categories

    def test_travel_keywords_constant(self):
        """Test that TRAVEL_KEYWORDS contains expected travel-related terms"""
        assert "travel" in self.service.TRAVEL_KEYWORDS
        assert "drive" in self.service.TRAVEL_KEYWORDS
        assert "flight" in self.service.TRAVEL_KEYWORDS
        assert "commute" in self.service.TRAVEL_KEYWORDS

    def test_filter_appointments_for_timesheet_empty_list(self):
        """Test filtering with empty appointment list"""
        result = self.service.filter_appointments_for_timesheet([])
        
        assert result["filtered_appointments"] == []
        assert result["excluded_appointments"] == []
        assert result["overlap_resolutions"] == []
        assert result["statistics"]["total_appointments"] == 0
        assert result["issues"] == []

    def test_filter_business_appointments_billable(self):
        """Test filtering includes billable appointments"""
        # Mock the category service instance
        with patch.object(self.service.category_service, 'extract_customer_billing_info') as mock_extract:
            mock_extract.return_value = {
                "customer": "Acme Corp",
                "billing_type": "billable",
                "is_personal": False,
                "is_valid": True
            }

            # Create test appointment
            appointment = self.create_mock_appointment(
                subject="Client Meeting",
                categories=["Acme Corp - billable"]
            )

            # Test filtering
            business_appts, excluded_appts = self.service._filter_business_appointments([appointment])

            assert len(business_appts) == 1
            assert len(excluded_appts) == 0
            assert business_appts[0] == appointment

    def test_filter_business_appointments_personal(self):
        """Test filtering excludes personal appointments"""
        # Mock the category service instance
        with patch.object(self.service.category_service, 'extract_customer_billing_info') as mock_extract:
            mock_extract.return_value = {
                "customer": None,
                "billing_type": None,
                "is_personal": True,
                "is_valid": False
            }

            # Create test appointment
            appointment = self.create_mock_appointment(
                subject="Personal Appointment",
                categories=[]
            )

            # Test filtering
            business_appts, excluded_appts = self.service._filter_business_appointments([appointment])

            assert len(business_appts) == 0
            assert len(excluded_appts) == 1
            assert excluded_appts[0] == appointment

    def test_filter_business_appointments_free_status(self):
        """Test filtering excludes 'Free' status appointments"""
        appointment = self.create_mock_appointment(
            subject="Free Time Block",
            show_as="free"
        )
        
        business_appts, excluded_appts = self.service._filter_business_appointments([appointment])
        
        assert len(business_appts) == 0
        assert len(excluded_appts) == 1
        assert excluded_appts[0] == appointment

    def test_detect_travel_appointment_by_subject(self):
        """Test travel appointment detection by subject keywords"""
        travel_subjects = [
            "Travel to Client Site",
            "Drive to Office",
            "Flight to Conference",
            "Commute Time",
            "Airport Departure"
        ]
        
        for subject in travel_subjects:
            appointment = self.create_mock_appointment(subject=subject)
            assert self.service._detect_travel_appointment(appointment), f"Failed to detect travel in: {subject}"

    def test_detect_travel_appointment_non_travel(self):
        """Test that non-travel appointments are not detected as travel"""
        non_travel_subjects = [
            "Team Meeting",
            "Project Review",
            "Client Call",
            "Development Work"
        ]
        
        for subject in non_travel_subjects:
            appointment = self.create_mock_appointment(subject=subject)
            assert not self.service._detect_travel_appointment(appointment), f"Incorrectly detected travel in: {subject}"

    def test_is_free_status_appointment(self):
        """Test Free status detection"""
        free_appointment = self.create_mock_appointment(show_as="free")
        busy_appointment = self.create_mock_appointment(show_as="busy")
        tentative_appointment = self.create_mock_appointment(show_as="tentative")
        
        assert self.service._is_free_status_appointment(free_appointment)
        assert not self.service._is_free_status_appointment(busy_appointment)
        assert not self.service._is_free_status_appointment(tentative_appointment)

    @patch('core.services.timesheet_archive_service.detect_overlaps')
    @patch('core.services.timesheet_archive_service.EnhancedOverlapResolutionService')
    def test_resolve_overlaps_automatically_no_overlaps(self, mock_overlap_service, mock_detect_overlaps):
        """Test overlap resolution when no overlaps exist"""
        mock_detect_overlaps.return_value = []
        
        appointments = [
            self.create_mock_appointment(subject="Meeting 1"),
            self.create_mock_appointment(subject="Meeting 2")
        ]
        
        resolved_appts, resolutions = self.service._resolve_overlaps_automatically(appointments)
        
        assert len(resolved_appts) == 2
        assert len(resolutions) == 0

    @patch('core.services.timesheet_archive_service.detect_overlaps')
    def test_resolve_overlaps_automatically_with_overlaps(self, mock_detect_overlaps):
        """Test overlap resolution when overlaps exist"""
        appointment1 = self.create_mock_appointment(subject="Meeting 1")
        appointment2 = self.create_mock_appointment(subject="Meeting 2")

        # Mock overlap detection
        mock_detect_overlaps.return_value = [[appointment1, appointment2]]

        # Mock the overlap service instance
        with patch.object(self.service.overlap_service, 'apply_automatic_resolution_rules') as mock_resolution:
            mock_resolution.return_value = {
                "resolved": [appointment1],
                "conflicts": [],
                "filtered": [appointment2],
                "resolution_log": ["Filtered out 1 'Free' appointment"]
            }

            resolved_appts, resolutions = self.service._resolve_overlaps_automatically([appointment1, appointment2])

            assert len(resolved_appts) == 1
            assert len(resolutions) == 1
            assert resolved_appts[0] == appointment1

    def test_generate_statistics(self):
        """Test statistics generation"""
        original_appointments = [
            self.create_mock_appointment(subject="Business Meeting"),
            self.create_mock_appointment(subject="Personal Appointment"),
            self.create_mock_appointment(subject="Free Time", show_as="free")
        ]
        
        business_appointments = [original_appointments[0]]
        excluded_appointments = original_appointments[1:]
        overlap_resolutions = []
        
        stats = self.service._generate_statistics(
            original_appointments,
            business_appointments,
            excluded_appointments,
            overlap_resolutions
        )
        
        assert stats["total_appointments"] == 3
        assert stats["business_appointments"] == 1
        assert stats["excluded_appointments"] == 2
        assert stats["overlap_groups_processed"] == 0

    def test_get_empty_statistics(self):
        """Test empty statistics structure"""
        stats = self.service._get_empty_statistics()
        
        assert stats["total_appointments"] == 0
        assert stats["business_appointments"] == 0
        assert stats["excluded_appointments"] == 0
        assert "exclusion_reasons" in stats
        assert "category_breakdown" in stats

    def test_get_timesheet_statistics(self):
        """Test getting timesheet statistics"""
        # Mock the category service instance
        with patch.object(self.service.category_service, 'extract_customer_billing_info') as mock_extract:
            mock_extract.return_value = {
                "customer": "Test Corp",
                "billing_type": "billable",
                "is_personal": False,
                "is_valid": True
            }

            appointments = [
                self.create_mock_appointment(subject="Business Meeting", categories=["Test Corp - billable"])
            ]

            stats = self.service.get_timesheet_statistics(appointments)

            assert "total_appointments" in stats
            assert "business_appointments" in stats
            assert "category_breakdown" in stats


class TestTimesheetArchiveServiceAdvanced:
    """Advanced test suite for TimesheetArchiveService edge cases and integration"""

    def setup_method(self):
        """Set up test fixtures"""
        self.service = TimesheetArchiveService()

    def create_mock_appointment(
        self,
        subject="Test Meeting",
        categories=None,
        show_as="busy",
        start_time=None,
        end_time=None,
        importance="normal",
        response_status="accepted"
    ):
        """Create a mock appointment for testing"""
        appointment = Mock(spec=Appointment)
        appointment.subject = subject
        appointment.categories = categories or []
        appointment.show_as = show_as
        appointment.start_time = start_time or datetime(2024, 1, 15, 9, 0, tzinfo=timezone.utc)
        appointment.end_time = end_time or datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)
        appointment.importance = importance
        appointment.response_status = response_status
        return appointment

    def test_filter_business_appointments_comprehensive(self):
        """Test comprehensive business appointment filtering"""
        appointments = [
            # Billable appointments
            self.create_mock_appointment(subject="Client Meeting", categories=["Acme Corp - billable"]),
            self.create_mock_appointment(subject="Project Work", categories=["TechCorp - billable"]),

            # Non-billable appointments
            self.create_mock_appointment(subject="Internal Meeting", categories=["Admin - non-billable"]),
            self.create_mock_appointment(subject="Training", categories=["Learning - non-billable"]),

            # Travel appointments (by category)
            self.create_mock_appointment(subject="Client Visit", categories=["Travel - billable"]),

            # Travel appointments (by subject)
            self.create_mock_appointment(subject="Drive to Office"),
            self.create_mock_appointment(subject="Flight to Conference"),

            # Personal appointments (should be excluded)
            self.create_mock_appointment(subject="Doctor Appointment"),
            self.create_mock_appointment(subject="Personal Meeting", categories=["Personal"]),

            # Free appointments (should be excluded)
            self.create_mock_appointment(subject="Free Time", show_as="free"),

            # Mixed categories
            self.create_mock_appointment(subject="Mixed Meeting", categories=["Acme Corp - billable", "Personal"]),
        ]

        business_appointments, excluded_appointments = self.service._filter_business_appointments(
            appointments, include_travel=True
        )

        # Should include: 2 billable + 2 non-billable + 1 travel category + 2 travel subjects + 1 mixed = 8
        assert len(business_appointments) == 8
        # Should exclude: 2 personal + 1 free = 3
        assert len(excluded_appointments) == 3

        # Verify specific inclusions
        business_subjects = [apt.subject for apt in business_appointments]
        assert "Client Meeting" in business_subjects
        assert "Internal Meeting" in business_subjects
        assert "Client Visit" in business_subjects
        assert "Drive to Office" in business_subjects
        assert "Mixed Meeting" in business_subjects

        # Verify specific exclusions
        excluded_subjects = [apt.subject for apt in excluded_appointments]
        assert "Doctor Appointment" in excluded_subjects
        assert "Personal Meeting" in excluded_subjects
        assert "Free Time" in excluded_subjects

    def test_filter_business_appointments_without_travel(self):
        """Test business appointment filtering excluding travel"""
        # Mock the category service to return appropriate responses
        def mock_extract_side_effect(appointment):
            if appointment.categories and "billable" in appointment.categories[0]:
                if "Travel" in appointment.categories[0]:
                    return {
                        "customer": "Travel Corp",
                        "billing_type": "billable",
                        "is_personal": False,
                        "is_valid": True
                    }
                else:
                    return {
                        "customer": "Acme Corp",
                        "billing_type": "billable",
                        "is_personal": False,
                        "is_valid": True
                    }
            else:
                return {
                    "customer": None,
                    "billing_type": None,
                    "is_personal": True,
                    "is_valid": False
                }

        with patch.object(self.service.category_service, 'extract_customer_billing_info', side_effect=mock_extract_side_effect):
            appointments = [
                self.create_mock_appointment(subject="Client Meeting", categories=["Acme Corp - billable"]),
                self.create_mock_appointment(subject="Drive to Office", categories=[]),  # Travel by subject
                self.create_mock_appointment(subject="Client Visit", categories=["Travel - billable"]),  # Travel by category
            ]

            business_appointments, excluded_appointments = self.service._filter_business_appointments(
                appointments, include_travel=False
            )

            # Should include billable appointments (including travel with valid billing categories)
            # but exclude travel detected by subject when include_travel=False
            assert len(business_appointments) == 2  # "Client Meeting" + "Client Visit" (both billable)
            business_subjects = [apt.subject for apt in business_appointments]
            assert "Client Meeting" in business_subjects
            assert "Client Visit" in business_subjects  # Has billable category, so included

            # Should exclude travel detected by subject only
            assert len(excluded_appointments) == 1
            excluded_subjects = [apt.subject for apt in excluded_appointments]
            assert "Drive to Office" in excluded_subjects  # Travel by subject, no valid category

    def test_resolve_overlaps_automatically_comprehensive(self):
        """Test comprehensive automatic overlap resolution"""
        # Create overlapping appointments with different priorities
        overlapping_appointments = [
            # High importance, confirmed
            self.create_mock_appointment(
                subject="Important Meeting",
                start_time=datetime(2024, 1, 15, 9, 0, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),
                importance="high",
                response_status="accepted"
            ),
            # Normal importance, tentative
            self.create_mock_appointment(
                subject="Tentative Meeting",
                start_time=datetime(2024, 1, 15, 9, 30, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc),
                importance="normal",
                response_status="tentative"
            ),
            # Free appointment (should be filtered out)
            self.create_mock_appointment(
                subject="Free Time",
                start_time=datetime(2024, 1, 15, 9, 15, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 15, 10, 15, tzinfo=timezone.utc),
                show_as="free"
            ),
            # Non-overlapping appointment
            self.create_mock_appointment(
                subject="Separate Meeting",
                start_time=datetime(2024, 1, 15, 11, 0, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc)
            ),
        ]

        with patch('core.utilities.calendar_overlap_utility.detect_overlaps') as mock_detect:
            # Mock overlap detection to return the first three appointments as overlapping
            mock_detect.return_value = [overlapping_appointments[:3]]

            with patch.object(self.service.overlap_service, 'apply_automatic_resolution_rules') as mock_resolve:
                mock_resolve.return_value = {
                    "resolved": [overlapping_appointments[0]],  # Keep the important one
                    "conflicts": [],
                    "filtered": [overlapping_appointments[2]],  # Free appointment filtered
                    "resolution_log": ["Filtered out 1 'Free' appointment", "Resolved by importance"]
                }

                resolved_appointments, overlap_resolutions = self.service._resolve_overlaps_automatically(
                    overlapping_appointments
                )

                # Should have 2 appointments: 1 resolved from overlap + 1 non-overlapping
                assert len(resolved_appointments) == 2

                # Should have 1 overlap resolution
                assert len(overlap_resolutions) == 1
                assert len(overlap_resolutions[0]["resolved"]) == 1
                assert len(overlap_resolutions[0]["filtered"]) == 1

    def test_process_appointments_for_timesheet_complete_workflow(self):
        """Test complete workflow with realistic appointment data"""
        appointments = [
            # Billable work
            self.create_mock_appointment(
                subject="Client Consultation",
                categories=["Acme Corp - billable"],
                start_time=datetime(2024, 1, 15, 9, 0, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)
            ),
            # Non-billable admin work
            self.create_mock_appointment(
                subject="Team Standup",
                categories=["Admin - non-billable"],
                start_time=datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
            ),
            # Travel
            self.create_mock_appointment(
                subject="Drive to Client Site",
                start_time=datetime(2024, 1, 15, 8, 0, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 15, 9, 0, tzinfo=timezone.utc)
            ),
            # Personal (should be excluded)
            self.create_mock_appointment(
                subject="Lunch with Friend",
                start_time=datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 15, 13, 0, tzinfo=timezone.utc)
            ),
            # Free time (should be excluded)
            self.create_mock_appointment(
                subject="Available",
                show_as="free",
                start_time=datetime(2024, 1, 15, 14, 0, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 15, 15, 0, tzinfo=timezone.utc)
            ),
        ]

        result = self.service.process_appointments_for_timesheet(
            appointments, include_travel=True
        )

        # Verify structure
        assert "filtered_appointments" in result
        assert "excluded_appointments" in result
        assert "overlap_resolutions" in result
        assert "statistics" in result
        assert "issues" in result

        # Verify filtering results
        assert len(result["filtered_appointments"]) == 3  # billable + non-billable + travel
        assert len(result["excluded_appointments"]) == 2  # personal + free

        # Verify statistics
        stats = result["statistics"]
        assert stats["total_appointments"] == 5
        assert stats["business_appointments"] == 3
        assert stats["excluded_appointments"] == 2
        assert stats["overlap_groups_processed"] == 0  # No overlaps in this test

        # Verify no issues
        assert len(result["issues"]) == 0

    def test_process_appointments_empty_input(self):
        """Test processing with empty appointment list"""
        result = self.service.process_appointments_for_timesheet([])

        assert result["filtered_appointments"] == []
        assert result["excluded_appointments"] == []
        assert result["overlap_resolutions"] == []
        assert result["statistics"]["total_appointments"] == 0
        assert result["issues"] == []

    def test_process_appointments_with_errors(self):
        """Test processing with appointments that cause errors"""
        # Create appointment with missing attributes
        problematic_appointment = Mock()
        problematic_appointment.subject = "Test Meeting"
        # Missing categories, show_as, etc.

        appointments = [problematic_appointment]

        # Should handle gracefully and not crash
        result = self.service.process_appointments_for_timesheet(appointments)

        # Should still return valid structure
        assert "filtered_appointments" in result
        assert "excluded_appointments" in result
        assert "statistics" in result

    def test_travel_detection_comprehensive(self):
        """Test comprehensive travel appointment detection"""
        travel_keywords = [
            "travel", "drive", "flight", "commute", "airport",
            "departure", "arrival", "transit", "journey", "trip"
        ]

        for keyword in travel_keywords:
            # Test various formats
            test_subjects = [
                f"{keyword.title()} to Office",
                f"Client {keyword}",
                f"{keyword.upper()} TIME",
                f"Morning {keyword}"
            ]

            for subject in test_subjects:
                appointment = self.create_mock_appointment(subject=subject)
                assert self.service._detect_travel_appointment(appointment), \
                    f"Failed to detect travel in: {subject}"

    def test_travel_detection_false_positives(self):
        """Test that travel detection doesn't have false positives"""
        non_travel_subjects = [
            "Team Meeting",
            "Client Consultation",
            "Project Review",
            "Training Session",
            "Lunch Break",
            "Doctor Appointment"
        ]

        for subject in non_travel_subjects:
            appointment = self.create_mock_appointment(subject=subject)
            assert not self.service._detect_travel_appointment(appointment), \
                f"False positive travel detection for: {subject}"

    def test_category_processing_integration(self):
        """Test integration with CategoryProcessingService"""
        appointments = [
            self.create_mock_appointment(
                subject="Business Meeting",
                categories=["Acme Corp - billable"]
            ),
            self.create_mock_appointment(
                subject="Admin Work",
                categories=["Admin - non-billable"]
            ),
            self.create_mock_appointment(
                subject="Personal Meeting",
                categories=["Personal"]
            ),
        ]

        with patch.object(self.service.category_service, 'extract_customer_billing_info') as mock_extract:
            # Mock different responses for different appointments
            def mock_extract_side_effect(appointment):
                if "Acme Corp" in str(appointment.categories):
                    return {
                        "customer": "Acme Corp",
                        "billing_type": "billable",
                        "is_personal": False,
                        "is_valid": True
                    }
                elif "Admin" in str(appointment.categories):
                    return {
                        "customer": "Admin",
                        "billing_type": "non-billable",
                        "is_personal": False,
                        "is_valid": True
                    }
                else:
                    return {
                        "customer": None,
                        "billing_type": None,
                        "is_personal": True,
                        "is_valid": False
                    }

            mock_extract.side_effect = mock_extract_side_effect

            business_appointments, excluded_appointments = self.service._filter_business_appointments(
                appointments, include_travel=False
            )

            # Should include business appointments, exclude personal
            assert len(business_appointments) == 2
            assert len(excluded_appointments) == 1

            # Verify category service was called for each appointment
            assert mock_extract.call_count == 3

    def test_overlap_resolution_service_integration(self):
        """Test integration with EnhancedOverlapResolutionService"""
        overlapping_appointments = [
            self.create_mock_appointment(
                subject="Meeting 1",
                start_time=datetime(2024, 1, 15, 9, 0, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)
            ),
            self.create_mock_appointment(
                subject="Meeting 2",
                start_time=datetime(2024, 1, 15, 9, 30, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
            ),
        ]

        with patch('core.utilities.calendar_overlap_utility.detect_overlaps') as mock_detect:
            mock_detect.return_value = [overlapping_appointments]

            with patch.object(self.service.overlap_service, 'apply_automatic_resolution_rules') as mock_resolve:
                mock_resolve.return_value = {
                    "resolved": [overlapping_appointments[0]],
                    "conflicts": [],
                    "filtered": [],
                    "resolution_log": ["Resolved by priority"]
                }

                resolved_appointments, overlap_resolutions = self.service._resolve_overlaps_automatically(
                    overlapping_appointments
                )

                # Verify overlap service was called
                mock_resolve.assert_called_once_with(overlapping_appointments)

                # Verify results
                assert len(resolved_appointments) == 1
                assert len(overlap_resolutions) == 1
                assert len(overlap_resolutions[0]["resolved"]) == 1

    def test_statistics_generation_comprehensive(self):
        """Test comprehensive statistics generation"""
        original_appointments = [
            self.create_mock_appointment(subject="Business 1"),
            self.create_mock_appointment(subject="Business 2"),
            self.create_mock_appointment(subject="Personal 1"),
            self.create_mock_appointment(subject="Personal 2"),
        ]

        business_appointments = original_appointments[:2]
        excluded_appointments = original_appointments[2:]

        overlap_resolutions = [
            {
                "overlap_group": [original_appointments[0]],
                "resolved": [original_appointments[0]],
                "filtered": [],
                "conflicts": []
            }
        ]

        stats = self.service._generate_statistics(
            original_appointments,
            business_appointments,
            excluded_appointments,
            overlap_resolutions
        )

        # Verify all expected statistics (matching actual implementation)
        assert stats["total_appointments"] == 4
        assert stats["business_appointments"] == 2
        assert stats["excluded_appointments"] == 2
        assert stats["overlap_groups_processed"] == 1
        assert stats["appointments_resolved_by_overlap"] == 1
        assert stats["appointments_filtered_by_overlap"] == 0
        assert stats["appointments_still_conflicted"] == 0
        assert "exclusion_reasons" in stats
        assert "category_breakdown" in stats

    def test_filter_appointments_for_timesheet_integration(self):
        """Test full integration of filtering process"""
        # Create a simple test that doesn't rely on complex mocking
        appointments = [
            self.create_mock_appointment(subject="Travel to Client", categories=[]),
            self.create_mock_appointment(subject="Free Time", show_as="free")
        ]

        # Mock the category service to return personal for non-travel appointments
        with patch.object(self.service.category_service, 'extract_customer_billing_info') as mock_extract:
            mock_extract.return_value = {"customer": None, "billing_type": None, "is_personal": True, "is_valid": False}

            result = self.service.filter_appointments_for_timesheet(appointments)

            # Should have 1 travel appointment and 1 excluded (free status)
            assert len(result["filtered_appointments"]) == 1  # Travel only
            assert len(result["excluded_appointments"]) == 1  # Free status
            assert result["statistics"]["total_appointments"] == 2
            assert len(result["issues"]) == 0
