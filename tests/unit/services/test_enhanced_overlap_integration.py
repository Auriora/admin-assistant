import pytest
from datetime import datetime, timezone, timedelta
from core.services.enhanced_overlap_resolution_service import EnhancedOverlapResolutionService
from core.utilities.calendar_overlap_utility import detect_overlaps
from core.models.appointment import Appointment


class TestEnhancedOverlapIntegration:
    """Integration tests for enhanced overlap resolution with real overlap scenarios."""
    
    @pytest.fixture
    def service(self):
        return EnhancedOverlapResolutionService()
    
    @pytest.fixture
    def base_time(self):
        return datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)
    
    def create_appointment(self, subject, start_time, end_time, show_as=None, importance=None):
        """Helper to create test appointments."""
        appt = Appointment(
            user_id=1,
            subject=subject,
            start_time=start_time,
            end_time=end_time,
            calendar_id='test-calendar'
        )
        if show_as:
            appt.show_as = show_as
        if importance:
            appt.importance = importance
        return appt
    
    def test_workflow_scenario_free_appointments_filtered(self, service, base_time):
        """Test workflow scenario: Free appointments should be filtered out during archiving."""
        # Create overlapping appointments with one marked as 'Free'
        meeting = self.create_appointment("Important Meeting", base_time, base_time + timedelta(hours=1), 
                                        show_as='busy', importance='high')
        free_time = self.create_appointment("Free Time", base_time + timedelta(minutes=30), 
                                          base_time + timedelta(hours=1, minutes=30), show_as='free')
        
        # Detect overlaps first
        overlap_groups = detect_overlaps([meeting, free_time])
        assert len(overlap_groups) == 1  # Should detect overlap
        
        # Apply enhanced resolution
        result = service.apply_automatic_resolution_rules(overlap_groups[0])
        
        # Free appointment should be filtered, meeting should be resolved
        assert len(result['resolved']) == 1
        assert result['resolved'][0] == meeting
        assert free_time in result['filtered']
        assert 'Free' in result['resolution_log'][0]
    
    def test_workflow_scenario_tentative_vs_confirmed(self, service, base_time):
        """Test workflow scenario: Tentative appointments discarded in favor of confirmed."""
        confirmed_meeting = self.create_appointment("Confirmed Meeting", base_time, base_time + timedelta(hours=1), 
                                                   show_as='busy', importance='normal')
        tentative_meeting = self.create_appointment("Tentative Meeting", base_time + timedelta(minutes=15), 
                                                   base_time + timedelta(hours=1, minutes=15), 
                                                   show_as='tentative', importance='normal')
        
        # Detect overlaps
        overlap_groups = detect_overlaps([confirmed_meeting, tentative_meeting])
        assert len(overlap_groups) == 1
        
        # Apply resolution
        result = service.apply_automatic_resolution_rules(overlap_groups[0])
        
        # Confirmed should win, tentative should be filtered
        assert len(result['resolved']) == 1
        assert result['resolved'][0] == confirmed_meeting
        assert tentative_meeting in result['filtered']
        assert 'Tentative' in result['resolution_log'][-1]
    
    def test_workflow_scenario_priority_resolution(self, service, base_time):
        """Test workflow scenario: High priority appointment wins over normal priority."""
        normal_meeting = self.create_appointment("Normal Meeting", base_time, base_time + timedelta(hours=1), 
                                                show_as='busy', importance='normal')
        high_priority_meeting = self.create_appointment("High Priority Meeting", 
                                                       base_time + timedelta(minutes=30), 
                                                       base_time + timedelta(hours=1, minutes=30), 
                                                       show_as='busy', importance='high')
        
        # Detect overlaps
        overlap_groups = detect_overlaps([normal_meeting, high_priority_meeting])
        assert len(overlap_groups) == 1
        
        # Apply resolution
        result = service.apply_automatic_resolution_rules(overlap_groups[0])
        
        # High priority should win
        assert len(result['resolved']) == 1
        assert result['resolved'][0] == high_priority_meeting
        assert normal_meeting in result['filtered']
        assert 'highest priority' in result['resolution_log'][-1]
    
    def test_workflow_scenario_complex_multi_step(self, service, base_time):
        """Test complex workflow scenario with multiple resolution steps."""
        # Create a complex overlap scenario
        free_block = self.create_appointment("Free Time Block", base_time, base_time + timedelta(hours=2), 
                                           show_as='free')
        tentative_call = self.create_appointment("Tentative Call", base_time + timedelta(minutes=30), 
                                               base_time + timedelta(hours=1, minutes=30), 
                                               show_as='tentative', importance='normal')
        low_priority_meeting = self.create_appointment("Low Priority Meeting", 
                                                     base_time + timedelta(minutes=45), 
                                                     base_time + timedelta(hours=1, minutes=45), 
                                                     show_as='busy', importance='low')
        high_priority_meeting = self.create_appointment("High Priority Meeting", 
                                                       base_time + timedelta(hours=1), 
                                                       base_time + timedelta(hours=2), 
                                                       show_as='busy', importance='high')
        
        # Detect overlaps
        overlap_groups = detect_overlaps([free_block, tentative_call, low_priority_meeting, high_priority_meeting])
        assert len(overlap_groups) == 1  # All should overlap
        
        # Apply resolution
        result = service.apply_automatic_resolution_rules(overlap_groups[0])
        
        # High priority meeting should win, others should be filtered
        assert len(result['resolved']) == 1
        assert result['resolved'][0] == high_priority_meeting
        assert len(result['filtered']) == 3
        assert free_block in result['filtered']
        assert tentative_call in result['filtered']
        assert low_priority_meeting in result['filtered']
        
        # Should have multiple resolution steps
        assert len(result['resolution_log']) == 3
        assert any('Free' in log for log in result['resolution_log'])
        assert any('Tentative' in log for log in result['resolution_log'])
        assert any('highest priority' in log for log in result['resolution_log'])
    
    def test_workflow_scenario_unresolvable_conflict(self, service, base_time):
        """Test scenario where automatic resolution fails and manual intervention is needed."""
        meeting1 = self.create_appointment("Meeting 1", base_time, base_time + timedelta(hours=1), 
                                         show_as='busy', importance='high')
        meeting2 = self.create_appointment("Meeting 2", base_time + timedelta(minutes=30), 
                                         base_time + timedelta(hours=1, minutes=30), 
                                         show_as='busy', importance='high')
        
        # Detect overlaps
        overlap_groups = detect_overlaps([meeting1, meeting2])
        assert len(overlap_groups) == 1
        
        # Apply resolution
        result = service.apply_automatic_resolution_rules(overlap_groups[0])
        
        # Should not be able to auto-resolve - both have same priority
        assert len(result['resolved']) == 0
        assert len(result['conflicts']) == 2
        assert meeting1 in result['conflicts']
        assert meeting2 in result['conflicts']
        assert 'Unable to resolve by priority' in result['resolution_log'][-1]
    
    def test_workflow_scenario_no_overlaps(self, service, base_time):
        """Test scenario with no overlapping appointments."""
        meeting1 = self.create_appointment("Meeting 1", base_time, base_time + timedelta(hours=1))
        meeting2 = self.create_appointment("Meeting 2", base_time + timedelta(hours=2), 
                                         base_time + timedelta(hours=3))
        
        # Should detect no overlaps
        overlap_groups = detect_overlaps([meeting1, meeting2])
        assert len(overlap_groups) == 0
        
        # No resolution needed
        result = service.apply_automatic_resolution_rules([])
        assert result['resolved'] == []
        assert result['conflicts'] == []
        assert result['filtered'] == []
        assert result['resolution_log'] == []
    
    def test_workflow_scenario_single_appointment(self, service, base_time):
        """Test scenario with single appointment (no conflicts)."""
        meeting = self.create_appointment("Solo Meeting", base_time, base_time + timedelta(hours=1))
        
        # Apply resolution to single appointment
        result = service.apply_automatic_resolution_rules([meeting])
        
        # Should be resolved immediately
        assert len(result['resolved']) == 1
        assert result['resolved'][0] == meeting
        assert result['conflicts'] == []
        assert result['filtered'] == []
