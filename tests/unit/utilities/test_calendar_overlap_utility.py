import pytest
from datetime import datetime, timezone
from unittest.mock import Mock
from core.utilities.calendar_overlap_utility import (
    merge_duplicates,
    detect_overlaps,
    detect_overlaps_with_metadata
)
from core.models.appointment import Appointment


class MockAppointment:
    """Simple mock appointment class for testing"""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
            # Also set in __dict__ for the utility functions that access it directly
            self.__dict__[key] = value


class TestCalendarOverlapUtility:
    """Test suite for calendar overlap utility functions"""

    def test_merge_duplicates_removes_exact_duplicates(self):
        """Test that merge_duplicates removes appointments with identical subject, start_time, and end_time"""
        # Arrange
        start_time = datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
        
        appt1 = Mock(spec=Appointment)
        appt1.subject = "Team Meeting"
        appt1.start_time = start_time
        appt1.end_time = end_time
        
        appt2 = Mock(spec=Appointment)
        appt2.subject = "Team Meeting"
        appt2.start_time = start_time
        appt2.end_time = end_time
        
        appointments = [appt1, appt2]
        
        # Act
        result = merge_duplicates(appointments)
        
        # Assert
        assert len(result) == 1
        assert result[0] in [appt1, appt2]

    def test_merge_duplicates_keeps_different_appointments(self):
        """Test that merge_duplicates keeps appointments with different details"""
        # Arrange
        start_time1 = datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)
        end_time1 = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
        start_time2 = datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc)
        end_time2 = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        
        appt1 = Mock(spec=Appointment)
        appt1.subject = "Team Meeting"
        appt1.start_time = start_time1
        appt1.end_time = end_time1
        
        appt2 = Mock(spec=Appointment)
        appt2.subject = "Client Call"
        appt2.start_time = start_time2
        appt2.end_time = end_time2
        
        appointments = [appt1, appt2]
        
        # Act
        result = merge_duplicates(appointments)
        
        # Assert
        assert len(result) == 2
        assert appt1 in result
        assert appt2 in result

    def test_merge_duplicates_handles_missing_attributes(self):
        """Test that merge_duplicates handles appointments with missing attributes"""
        # Arrange
        appt1 = Mock(spec=Appointment)
        appt1.subject = None
        appt1.start_time = None
        appt1.end_time = None
        
        appt2 = Mock(spec=Appointment)
        appt2.subject = "Meeting"
        appt2.start_time = datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)
        appt2.end_time = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
        
        appointments = [appt1, appt2]
        
        # Act
        result = merge_duplicates(appointments)
        
        # Assert
        assert len(result) == 2

    def test_detect_overlaps_finds_overlapping_appointments(self):
        """Test that detect_overlaps identifies overlapping appointments"""
        # Arrange
        appt1 = MockAppointment(
            start_time=datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 10, 30, tzinfo=timezone.utc)
        )

        appt2 = MockAppointment(
            start_time=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc)
        )

        appointments = [appt1, appt2]

        # Act
        result = detect_overlaps(appointments)

        # Assert
        assert len(result) == 1
        assert len(result[0]) == 2
        assert appt1 in result[0]
        assert appt2 in result[0]

    def test_detect_overlaps_no_overlaps(self):
        """Test that detect_overlaps returns empty list when no overlaps exist"""
        # Arrange
        appt1 = MockAppointment(
            start_time=datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
        )

        appt2 = MockAppointment(
            start_time=datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        )

        appointments = [appt1, appt2]

        # Act
        result = detect_overlaps(appointments)

        # Assert
        assert len(result) == 0

    def test_detect_overlaps_filters_invalid_appointments(self):
        """Test that detect_overlaps filters out appointments with missing or invalid time fields"""
        # Arrange
        valid_appt = MockAppointment(
            start_time=datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
        )

        invalid_appt1 = MockAppointment(start_time=None, end_time=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc))
        invalid_appt2 = MockAppointment(start_time="not a datetime", end_time=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc))

        appointments = [valid_appt, invalid_appt1, invalid_appt2]

        # Act
        result = detect_overlaps(appointments)

        # Assert
        assert len(result) == 0  # No overlaps since only one valid appointment

    def test_detect_overlaps_with_metadata_includes_metadata(self):
        """Test that detect_overlaps_with_metadata includes resolution metadata"""
        # Arrange
        appt1 = MockAppointment(
            start_time=datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 10, 30, tzinfo=timezone.utc),
            show_as='busy',
            importance='high',
            sensitivity='normal',
            subject='Important Meeting'
        )

        appt2 = MockAppointment(
            start_time=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc),
            show_as='tentative',
            importance='normal',
            sensitivity='private',
            subject='Regular Meeting'
        )
        
        appointments = [appt1, appt2]
        
        # Act
        result = detect_overlaps_with_metadata(appointments)
        
        # Assert
        assert len(result) == 1
        overlap_group = result[0]
        
        assert 'appointments' in overlap_group
        assert 'metadata' in overlap_group
        assert len(overlap_group['appointments']) == 2
        
        metadata = overlap_group['metadata']
        assert metadata['show_as_values'] == ['busy', 'tentative']
        assert metadata['importance_values'] == ['high', 'normal']
        assert metadata['sensitivity_values'] == ['normal', 'private']
        assert metadata['subjects'] == ['Important Meeting', 'Regular Meeting']
        assert metadata['group_size'] == 2

    def test_detect_overlaps_with_metadata_no_overlaps(self):
        """Test that detect_overlaps_with_metadata returns empty list when no overlaps exist"""
        # Arrange
        appt1 = MockAppointment(
            start_time=datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
        )

        appt2 = MockAppointment(
            start_time=datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        )

        appointments = [appt1, appt2]

        # Act
        result = detect_overlaps_with_metadata(appointments)

        # Assert
        assert len(result) == 0
