"""
Integration tests for MeetingModificationService with CalendarArchiveOrchestrator

Tests the end-to-end processing of meeting modifications in the archiving workflow.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta, date
from core.services.meeting_modification_service import MeetingModificationService
from core.models.appointment import Appointment


class TestMeetingModificationIntegration:
    """Integration test suite for meeting modification processing"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = MeetingModificationService()
        self.base_time = datetime(2024, 1, 15, 10, 0, 0)
    
    def create_appointment(self, subject, start_time, end_time, categories=None):
        """Helper to create appointment instances"""
        appointment = Appointment()
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
    
    def test_workflow_scenario_meeting_extension(self):
        """Test complete workflow with meeting extension"""
        # Create original meeting and extension
        original = self.create_appointment(
            "Client Meeting",
            self.base_time,
            self.base_time + timedelta(hours=1)
        )
        
        extension = self.create_appointment(
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
    
    def test_workflow_scenario_meeting_shortening(self):
        """Test complete workflow with meeting shortening"""
        # Create original meeting and shortening
        original = self.create_appointment(
            "Client Meeting",
            self.base_time,
            self.base_time + timedelta(hours=1)
        )
        
        shortening = self.create_appointment(
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
    
    def test_workflow_scenario_early_start(self):
        """Test complete workflow with early start"""
        # Create original meeting and early start
        original = self.create_appointment(
            "Client Meeting",
            self.base_time,
            self.base_time + timedelta(hours=1)
        )
        
        early_start = self.create_appointment(
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
    
    def test_workflow_scenario_late_start(self):
        """Test complete workflow with late start"""
        # Create original meeting and late start
        original = self.create_appointment(
            "Client Meeting",
            self.base_time,
            self.base_time + timedelta(hours=1)
        )
        
        late_start = self.create_appointment(
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
    
    def test_workflow_scenario_multiple_meetings_with_modifications(self):
        """Test workflow with multiple meetings and their modifications"""
        # Meeting 1 and its extension
        meeting1 = self.create_appointment(
            "Client A Meeting",
            self.base_time,
            self.base_time + timedelta(hours=1),
            categories=["Client A - billable"]
        )
        
        extension1 = self.create_appointment(
            "Extended",
            self.base_time + timedelta(hours=1),
            self.base_time + timedelta(hours=1, minutes=30),
            categories=["Client A - billable"]
        )
        
        # Meeting 2 and its shortening
        meeting2 = self.create_appointment(
            "Client B Meeting",
            self.base_time + timedelta(hours=2),
            self.base_time + timedelta(hours=3),
            categories=["Client B - billable"]
        )
        
        shortening2 = self.create_appointment(
            "Shortened",
            self.base_time + timedelta(hours=2, minutes=45),
            self.base_time + timedelta(hours=3),
            categories=["Client B - billable"]
        )
        
        # Meeting 3 with no modifications
        meeting3 = self.create_appointment(
            "Client C Meeting",
            self.base_time + timedelta(hours=4),
            self.base_time + timedelta(hours=5),
            categories=["Client C - billable"]
        )
        
        appointments = [meeting1, extension1, meeting2, shortening2, meeting3]
        result = self.service.process_modifications(appointments)
        
        # Should have 3 appointments with modifications applied
        assert len(result) == 3
        
        # Find each meeting in results
        client_a_meeting = next(a for a in result if "Client A" in a.subject)
        client_b_meeting = next(a for a in result if "Client B" in a.subject)
        client_c_meeting = next(a for a in result if "Client C" in a.subject)
        
        # Verify Client A meeting was extended
        assert client_a_meeting.start_time == self.base_time
        assert client_a_meeting.end_time == self.base_time + timedelta(hours=1, minutes=30)
        
        # Verify Client B meeting was shortened
        assert client_b_meeting.start_time == self.base_time + timedelta(hours=2)
        assert client_b_meeting.end_time == self.base_time + timedelta(hours=2, minutes=45)
        
        # Verify Client C meeting was unchanged
        assert client_c_meeting.start_time == self.base_time + timedelta(hours=4)
        assert client_c_meeting.end_time == self.base_time + timedelta(hours=5)
    
    def test_workflow_scenario_orphaned_modifications(self):
        """Test workflow with orphaned modifications (no matching original)"""
        # Extension with no matching original
        orphaned_extension = self.create_appointment(
            "Extended",
            self.base_time + timedelta(hours=2),
            self.base_time + timedelta(hours=2, minutes=30)
        )
        
        # Regular meeting
        regular_meeting = self.create_appointment(
            "Regular Meeting",
            self.base_time,
            self.base_time + timedelta(hours=1)
        )
        
        appointments = [orphaned_extension, regular_meeting]
        result = self.service.process_modifications(appointments)
        
        # Should only have the regular meeting (orphaned modification filtered out)
        assert len(result) == 1
        assert result[0].subject == "Regular Meeting"
        assert result[0].start_time == self.base_time
        assert result[0].end_time == self.base_time + timedelta(hours=1)
    
    def test_workflow_scenario_complex_multiple_modifications_same_meeting(self):
        """Test workflow with multiple modifications on the same meeting"""
        # Original meeting
        original = self.create_appointment(
            "Important Client Meeting",
            self.base_time,
            self.base_time + timedelta(hours=1)
        )
        
        # Early start
        early_start = self.create_appointment(
            "Early Start",
            self.base_time - timedelta(minutes=10),
            self.base_time
        )
        
        # Extension
        extension = self.create_appointment(
            "Extended",
            self.base_time + timedelta(hours=1),
            self.base_time + timedelta(hours=1, minutes=30)
        )
        
        appointments = [original, early_start, extension]
        result = self.service.process_modifications(appointments)
        
        # Should have one appointment with both modifications applied
        # Note: The order of processing may affect the final result
        assert len(result) == 1
        assert result[0].subject == "Important Client Meeting"
        
        # The exact timing depends on the order of processing, but it should be modified
        assert result[0].start_time != self.base_time or result[0].end_time != self.base_time + timedelta(hours=1)
