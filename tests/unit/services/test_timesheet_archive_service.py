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
