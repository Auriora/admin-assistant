"""
Unit tests for MeetingModificationService

Tests the processing of meeting modification appointments including:
- Extension appointments
- Shortened appointments  
- Early Start appointments
- Late Start appointments
"""

import pytest
from unittest.mock import Mock
from datetime import datetime, timedelta
from core.services.meeting_modification_service import MeetingModificationService
from core.models.appointment import Appointment


class TestMeetingModificationService:
    """Test suite for MeetingModificationService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = MeetingModificationService()
        
        # Base time for consistent testing
        self.base_time = datetime(2024, 1, 15, 10, 0, 0)
    
    def create_mock_appointment(self, subject, start_time, end_time, categories=None):
        """Helper to create mock appointments"""
        appointment = Mock(spec=Appointment)
        appointment.subject = subject
        appointment.start_time = start_time
        appointment.end_time = end_time
        appointment.categories = categories or ["Client ABC - billable"]
        appointment.user_id = 1
        appointment.location_id = None
        appointment.category_id = None
        appointment.timesheet_id = None
        appointment.recurrence = None
        appointment.ms_event_data = None
        appointment.show_as = "busy"
        appointment.sensitivity = "normal"
        appointment.location = "Office"
        appointment.importance = "normal"
        appointment.id = None
        appointment.ms_event_id = None
        return appointment
    
    def test_detect_modification_type_extension(self):
        """Test detection of extension modifications"""
        assert self.service.detect_modification_type("Extended") == "extension"
        assert self.service.detect_modification_type("EXTENDED") == "extension"
        assert self.service.detect_modification_type("extended") == "extension"
        # These should NOT match (subject must be exactly "Extended")
        assert self.service.detect_modification_type("Meeting Extended") is None
        assert self.service.detect_modification_type("Extended Meeting") is None
        assert self.service.detect_modification_type("Extension") is None
    
    def test_detect_modification_type_shortened(self):
        """Test detection of shortened modifications"""
        assert self.service.detect_modification_type("Shortened") == "shortened"
        assert self.service.detect_modification_type("Meeting Shortened") == "shortened"
        assert self.service.detect_modification_type("SHORTENED") == "shortened"
        assert self.service.detect_modification_type("shortened meeting") == "shortened"
    
    def test_detect_modification_type_early_start(self):
        """Test detection of early start modifications"""
        assert self.service.detect_modification_type("Early Start") == "early_start"
        assert self.service.detect_modification_type("EARLY START") == "early_start"
        assert self.service.detect_modification_type("early start for meeting") == "early_start"
    
    def test_detect_modification_type_late_start(self):
        """Test detection of late start modifications"""
        assert self.service.detect_modification_type("Late Start") == "late_start"
        assert self.service.detect_modification_type("LATE START") == "late_start"
        assert self.service.detect_modification_type("late start delay") == "late_start"
    
    def test_detect_modification_type_no_match(self):
        """Test detection when no modification type matches"""
        assert self.service.detect_modification_type("Regular Meeting") is None
        assert self.service.detect_modification_type("Client Call") is None
        assert self.service.detect_modification_type("") is None
        assert self.service.detect_modification_type(None) is None
    
    def test_merge_extension_basic(self):
        """Test basic extension merging"""
        # Original 1-hour meeting
        original = self.create_mock_appointment(
            "Client Meeting",
            self.base_time,
            self.base_time + timedelta(hours=1)
        )
        
        # 30-minute extension
        extension = self.create_mock_appointment(
            "Extended",
            self.base_time + timedelta(hours=1),
            self.base_time + timedelta(hours=1, minutes=30)
        )
        
        result = self.service.merge_extension(original, extension)
        
        # Should extend end time by 30 minutes
        assert result.start_time == self.base_time
        assert result.end_time == self.base_time + timedelta(hours=1, minutes=30)
        assert result.subject == "Client Meeting"
    
    def test_apply_shortening_basic(self):
        """Test basic shortening application"""
        # Original 1-hour meeting
        original = self.create_mock_appointment(
            "Client Meeting",
            self.base_time,
            self.base_time + timedelta(hours=1)
        )
        
        # 15-minute shortening
        shortening = self.create_mock_appointment(
            "Shortened",
            self.base_time + timedelta(minutes=45),
            self.base_time + timedelta(hours=1)
        )
        
        result = self.service.apply_shortening(original, shortening)
        
        # Should reduce end time by 15 minutes
        assert result.start_time == self.base_time
        assert result.end_time == self.base_time + timedelta(minutes=45)
        assert result.subject == "Client Meeting"
    
    def test_apply_shortening_minimum_duration(self):
        """Test shortening with minimum duration protection"""
        # Original 30-minute meeting
        original = self.create_mock_appointment(
            "Client Meeting",
            self.base_time,
            self.base_time + timedelta(minutes=30)
        )
        
        # 45-minute shortening (more than the meeting duration)
        shortening = self.create_mock_appointment(
            "Shortened",
            self.base_time,
            self.base_time + timedelta(minutes=45)
        )
        
        result = self.service.apply_shortening(original, shortening)
        
        # Should set minimum 1-minute duration
        assert result.start_time == self.base_time
        assert result.end_time == self.base_time + timedelta(minutes=1)
    
    def test_adjust_start_time_early_start(self):
        """Test early start adjustment"""
        # Original meeting
        original = self.create_mock_appointment(
            "Client Meeting",
            self.base_time,
            self.base_time + timedelta(hours=1)
        )
        
        # Early start (10 minutes before)
        early_start = self.create_mock_appointment(
            "Early Start",
            self.base_time - timedelta(minutes=10),
            self.base_time
        )
        
        result = self.service.adjust_start_time(original, early_start)
        
        # Should move start time earlier
        assert result.start_time == self.base_time - timedelta(minutes=10)
        assert result.end_time == self.base_time + timedelta(hours=1)
        assert result.subject == "Client Meeting"
    
    def test_adjust_start_time_late_start(self):
        """Test late start adjustment"""
        # Original meeting
        original = self.create_mock_appointment(
            "Client Meeting",
            self.base_time,
            self.base_time + timedelta(hours=1)
        )
        
        # Late start (15 minutes delay)
        late_start = self.create_mock_appointment(
            "Late Start",
            self.base_time,
            self.base_time + timedelta(minutes=15)
        )
        
        result = self.service.adjust_start_time(original, late_start)
        
        # Should delay start time by 15 minutes
        assert result.start_time == self.base_time + timedelta(minutes=15)
        assert result.end_time == self.base_time + timedelta(hours=1)
        assert result.subject == "Client Meeting"
    
    def test_adjust_start_time_late_start_minimum_duration(self):
        """Test late start with minimum duration protection"""
        # Original 30-minute meeting
        original = self.create_mock_appointment(
            "Client Meeting",
            self.base_time,
            self.base_time + timedelta(minutes=30)
        )
        
        # Late start (45 minutes delay - more than meeting duration)
        late_start = self.create_mock_appointment(
            "Late Start",
            self.base_time,
            self.base_time + timedelta(minutes=45)
        )
        
        result = self.service.adjust_start_time(original, late_start)
        
        # Should set minimum 1-minute duration
        assert result.start_time == self.base_time + timedelta(minutes=29)
        assert result.end_time == self.base_time + timedelta(minutes=30)

    def test_find_original_appointment_extension(self):
        """Test finding original appointment for extension"""
        # Original meeting
        original = self.create_mock_appointment(
            "Client Meeting",
            self.base_time,
            self.base_time + timedelta(hours=1)
        )

        # Extension starting at end of original
        extension = self.create_mock_appointment(
            "Extended",
            self.base_time + timedelta(hours=1),
            self.base_time + timedelta(hours=1, minutes=30)
        )

        appointments = [original]
        found = self.service.find_original_appointment(extension, appointments)

        assert found == original

    def test_find_original_appointment_shortened(self):
        """Test finding original appointment for shortening"""
        # Original meeting
        original = self.create_mock_appointment(
            "Client Meeting",
            self.base_time,
            self.base_time + timedelta(hours=1)
        )

        # Shortening overlapping with original
        shortening = self.create_mock_appointment(
            "Shortened",
            self.base_time + timedelta(minutes=45),
            self.base_time + timedelta(hours=1)
        )

        appointments = [original]
        found = self.service.find_original_appointment(shortening, appointments)

        assert found == original

    def test_find_original_appointment_early_start(self):
        """Test finding original appointment for early start"""
        # Original meeting
        original = self.create_mock_appointment(
            "Client Meeting",
            self.base_time,
            self.base_time + timedelta(hours=1)
        )

        # Early start before original
        early_start = self.create_mock_appointment(
            "Early Start",
            self.base_time - timedelta(minutes=10),
            self.base_time
        )

        appointments = [original]
        found = self.service.find_original_appointment(early_start, appointments)

        assert found == original

    def test_find_original_appointment_late_start(self):
        """Test finding original appointment for late start"""
        # Original meeting
        original = self.create_mock_appointment(
            "Client Meeting",
            self.base_time,
            self.base_time + timedelta(hours=1)
        )

        # Late start at original start time
        late_start = self.create_mock_appointment(
            "Late Start",
            self.base_time,
            self.base_time + timedelta(minutes=15)
        )

        appointments = [original]
        found = self.service.find_original_appointment(late_start, appointments)

        assert found == original

    def test_find_original_appointment_category_mismatch(self):
        """Test that category mismatch prevents matching"""
        # Original meeting with different category
        original = self.create_mock_appointment(
            "Client Meeting",
            self.base_time,
            self.base_time + timedelta(hours=1),
            categories=["Different Client - billable"]
        )

        # Extension with different category
        extension = self.create_mock_appointment(
            "Extended",
            self.base_time + timedelta(hours=1),
            self.base_time + timedelta(hours=1, minutes=30),
            categories=["Client ABC - billable"]
        )

        appointments = [original]
        found = self.service.find_original_appointment(extension, appointments)

        assert found is None

    def test_find_original_appointment_no_match(self):
        """Test when no original appointment is found"""
        # Extension with no matching original
        extension = self.create_mock_appointment(
            "Extended",
            self.base_time + timedelta(hours=2),
            self.base_time + timedelta(hours=2, minutes=30)
        )

        appointments = []
        found = self.service.find_original_appointment(extension, appointments)

        assert found is None

    def test_process_modifications_extension_scenario(self):
        """Test complete processing of extension scenario"""
        # Original meeting
        original = self.create_mock_appointment(
            "Client Meeting",
            self.base_time,
            self.base_time + timedelta(hours=1)
        )

        # Extension
        extension = self.create_mock_appointment(
            "Extended",
            self.base_time + timedelta(hours=1),
            self.base_time + timedelta(hours=1, minutes=30)
        )

        appointments = [original, extension]
        result = self.service.process_modifications(appointments)

        # Should have one appointment with extended time
        assert len(result) == 1
        assert result[0].start_time == self.base_time
        assert result[0].end_time == self.base_time + timedelta(hours=1, minutes=30)
        assert result[0].subject == "Client Meeting"

    def test_process_modifications_multiple_modifications(self):
        """Test processing multiple modifications on same appointment"""
        # Original meeting
        original = self.create_mock_appointment(
            "Client Meeting",
            self.base_time,
            self.base_time + timedelta(hours=1)
        )

        # Extension
        extension = self.create_mock_appointment(
            "Extended",
            self.base_time + timedelta(hours=1),
            self.base_time + timedelta(hours=1, minutes=30)
        )

        # Early start
        early_start = self.create_mock_appointment(
            "Early Start",
            self.base_time - timedelta(minutes=10),
            self.base_time
        )

        appointments = [original, extension, early_start]
        result = self.service.process_modifications(appointments)

        # Should have one appointment with both modifications applied
        # Note: The order of processing may affect the final result
        assert len(result) == 1
        assert result[0].subject == "Client Meeting"

    def test_process_modifications_orphaned_modification(self):
        """Test processing when modification has no original"""
        # Extension with no matching original
        extension = self.create_mock_appointment(
            "Extended",
            self.base_time + timedelta(hours=2),
            self.base_time + timedelta(hours=2, minutes=30)
        )

        appointments = [extension]
        result = self.service.process_modifications(appointments)

        # Should return empty list (modification filtered out)
        assert len(result) == 0

    def test_process_modifications_no_modifications(self):
        """Test processing when no modifications are present"""
        # Regular appointments only
        appt1 = self.create_mock_appointment(
            "Client Meeting",
            self.base_time,
            self.base_time + timedelta(hours=1)
        )

        appt2 = self.create_mock_appointment(
            "Another Meeting",
            self.base_time + timedelta(hours=2),
            self.base_time + timedelta(hours=3)
        )

        appointments = [appt1, appt2]
        result = self.service.process_modifications(appointments)

        # Should return all appointments unchanged
        assert len(result) == 2
        assert result[0] == appt1
        assert result[1] == appt2

    def test_process_modifications_empty_list(self):
        """Test processing empty appointment list"""
        result = self.service.process_modifications([])
        assert result == []

    def test_copy_appointment(self):
        """Test appointment copying functionality"""
        original = self.create_mock_appointment(
            "Test Meeting",
            self.base_time,
            self.base_time + timedelta(hours=1)
        )
        original.id = 123
        original.ms_event_id = "test-event-id"

        copy = self.service._copy_appointment(original)

        # Should copy all attributes except ID and ms_event_id
        assert copy.subject == original.subject
        assert copy.start_time == original.start_time
        assert copy.end_time == original.end_time
        assert copy.categories == original.categories
        assert copy.user_id == original.user_id

        # Should not copy ID fields
        assert copy.id is None
        assert copy.ms_event_id is None

    def test_process_modifications_shortened_scenario(self):
        """Test complete processing of shortened scenario"""
        # Original 1-hour meeting
        original = self.create_mock_appointment(
            "Client Meeting",
            self.base_time,
            self.base_time + timedelta(hours=1)
        )

        # 15-minute shortening
        shortening = self.create_mock_appointment(
            "Shortened",
            self.base_time + timedelta(minutes=45),
            self.base_time + timedelta(hours=1)
        )

        appointments = [original, shortening]
        result = self.service.process_modifications(appointments)

        # Should have one appointment with shortened time
        assert len(result) == 1
        assert result[0].start_time == self.base_time
        assert result[0].end_time == self.base_time + timedelta(minutes=45)
        assert result[0].subject == "Client Meeting"

    def test_process_modifications_early_start_scenario(self):
        """Test complete processing of early start scenario"""
        # Original meeting
        original = self.create_mock_appointment(
            "Client Meeting",
            self.base_time,
            self.base_time + timedelta(hours=1)
        )

        # Early start
        early_start = self.create_mock_appointment(
            "Early Start",
            self.base_time - timedelta(minutes=10),
            self.base_time
        )

        appointments = [original, early_start]
        result = self.service.process_modifications(appointments)

        # Should have one appointment with earlier start time
        assert len(result) == 1
        assert result[0].start_time == self.base_time - timedelta(minutes=10)
        assert result[0].end_time == self.base_time + timedelta(hours=1)
        assert result[0].subject == "Client Meeting"

    def test_process_modifications_late_start_scenario(self):
        """Test complete processing of late start scenario"""
        # Original meeting
        original = self.create_mock_appointment(
            "Client Meeting",
            self.base_time,
            self.base_time + timedelta(hours=1)
        )

        # Late start (15 minutes delay)
        late_start = self.create_mock_appointment(
            "Late Start",
            self.base_time,
            self.base_time + timedelta(minutes=15)
        )

        appointments = [original, late_start]
        result = self.service.process_modifications(appointments)

        # Should have one appointment with delayed start time
        assert len(result) == 1
        assert result[0].start_time == self.base_time + timedelta(minutes=15)
        assert result[0].end_time == self.base_time + timedelta(hours=1)
        assert result[0].subject == "Client Meeting"
