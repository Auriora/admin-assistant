import pytest
from datetime import datetime, timezone, timedelta
from core.services.enhanced_overlap_resolution_service import EnhancedOverlapResolutionService
from core.models.appointment import Appointment


class TestEnhancedOverlapResolutionService:
    
    @pytest.fixture
    def service(self):
        return EnhancedOverlapResolutionService()
    
    @pytest.fixture
    def base_time(self):
        return datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)
    
    def create_appointment(self, subject, start_time, end_time, show_as=None, importance=None, sensitivity=None):
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
        if sensitivity:
            appt.sensitivity = sensitivity
        return appt
    
    def test_empty_appointments_list(self, service):
        """Test handling of empty appointments list."""
        result = service.apply_automatic_resolution_rules([])
        
        assert result['resolved'] == []
        assert result['conflicts'] == []
        assert result['filtered'] == []
        assert result['resolution_log'] == []
    
    def test_single_appointment(self, service, base_time):
        """Test handling of single appointment (no conflicts)."""
        appt = self.create_appointment("Meeting", base_time, base_time + timedelta(hours=1))
        
        result = service.apply_automatic_resolution_rules([appt])
        
        assert len(result['resolved']) == 1
        assert result['resolved'][0] == appt
        assert result['conflicts'] == []
        assert result['filtered'] == []
    
    def test_filter_free_appointments(self, service, base_time):
        """Test filtering out 'Free' appointments."""
        appt1 = self.create_appointment("Meeting", base_time, base_time + timedelta(hours=1), show_as='busy')
        appt2 = self.create_appointment("Free Time", base_time, base_time + timedelta(hours=1), show_as='free')
        appt3 = self.create_appointment("Another Meeting", base_time, base_time + timedelta(hours=1), show_as='tentative')
        
        result = service.apply_automatic_resolution_rules([appt1, appt2, appt3])
        
        # Should filter out the free appointment and resolve tentative vs busy
        assert len(result['filtered']) >= 1
        assert appt2 in result['filtered']  # Free appointment should be filtered
        assert 'Free' in result['resolution_log'][0]
    
    def test_resolve_tentative_vs_confirmed(self, service, base_time):
        """Test discarding tentative in favor of confirmed appointments."""
        confirmed_appt = self.create_appointment("Confirmed Meeting", base_time, base_time + timedelta(hours=1), show_as='busy')
        tentative_appt = self.create_appointment("Tentative Meeting", base_time, base_time + timedelta(hours=1), show_as='tentative')
        
        result = service.apply_automatic_resolution_rules([confirmed_appt, tentative_appt])
        
        assert len(result['resolved']) == 1
        assert result['resolved'][0] == confirmed_appt
        assert tentative_appt in result['filtered']
        assert 'Tentative' in result['resolution_log'][-1]
    
    def test_resolve_by_priority_high_wins(self, service, base_time):
        """Test priority resolution - high priority wins."""
        high_priority = self.create_appointment("High Priority", base_time, base_time + timedelta(hours=1), 
                                               show_as='busy', importance='high')
        normal_priority = self.create_appointment("Normal Priority", base_time, base_time + timedelta(hours=1), 
                                                 show_as='busy', importance='normal')
        low_priority = self.create_appointment("Low Priority", base_time, base_time + timedelta(hours=1), 
                                              show_as='busy', importance='low')
        
        result = service.apply_automatic_resolution_rules([normal_priority, high_priority, low_priority])
        
        assert len(result['resolved']) == 1
        assert result['resolved'][0] == high_priority
        assert normal_priority in result['filtered']
        assert low_priority in result['filtered']
        assert 'highest priority' in result['resolution_log'][-1]
    
    def test_resolve_by_priority_same_priority_conflict(self, service, base_time):
        """Test priority resolution when multiple appointments have same priority."""
        appt1 = self.create_appointment("Meeting 1", base_time, base_time + timedelta(hours=1), 
                                       show_as='busy', importance='high')
        appt2 = self.create_appointment("Meeting 2", base_time, base_time + timedelta(hours=1), 
                                       show_as='busy', importance='high')
        
        result = service.apply_automatic_resolution_rules([appt1, appt2])
        
        # Should not be able to auto-resolve - return as conflicts
        assert len(result['conflicts']) == 2
        assert result['resolved'] == []
        assert 'Unable to resolve by priority' in result['resolution_log'][-1]
    
    def test_complex_multi_step_resolution(self, service, base_time):
        """Test complex scenario with multiple resolution steps."""
        free_appt = self.create_appointment("Free Time", base_time, base_time + timedelta(hours=1), show_as='free')
        tentative_appt = self.create_appointment("Tentative", base_time, base_time + timedelta(hours=1), show_as='tentative')
        low_priority = self.create_appointment("Low Priority", base_time, base_time + timedelta(hours=1), 
                                              show_as='busy', importance='low')
        high_priority = self.create_appointment("High Priority", base_time, base_time + timedelta(hours=1), 
                                               show_as='busy', importance='high')
        
        result = service.apply_automatic_resolution_rules([free_appt, tentative_appt, low_priority, high_priority])
        
        assert len(result['resolved']) == 1
        assert result['resolved'][0] == high_priority
        assert len(result['filtered']) == 3
        assert free_appt in result['filtered']
        assert tentative_appt in result['filtered']
        assert low_priority in result['filtered']
        assert len(result['resolution_log']) == 3  # Free filter, tentative resolution, priority resolution
    
    def test_filter_free_appointments_method(self, service, base_time):
        """Test the filter_free_appointments method directly."""
        free_appt = self.create_appointment("Free", base_time, base_time + timedelta(hours=1), show_as='free')
        busy_appt = self.create_appointment("Busy", base_time, base_time + timedelta(hours=1), show_as='busy')
        no_show_as = self.create_appointment("No ShowAs", base_time, base_time + timedelta(hours=1))
        
        non_free, free = service.filter_free_appointments([free_appt, busy_appt, no_show_as])
        
        assert len(free) == 1
        assert free[0] == free_appt
        assert len(non_free) == 2
        assert busy_appt in non_free
        assert no_show_as in non_free
    
    def test_resolve_tentative_conflicts_method(self, service, base_time):
        """Test the resolve_tentative_conflicts method directly."""
        tentative = self.create_appointment("Tentative", base_time, base_time + timedelta(hours=1), show_as='tentative')
        confirmed = self.create_appointment("Confirmed", base_time, base_time + timedelta(hours=1), show_as='busy')
        
        remaining, discarded = service.resolve_tentative_conflicts([tentative, confirmed])
        
        assert len(remaining) == 1
        assert remaining[0] == confirmed
        assert len(discarded) == 1
        assert discarded[0] == tentative
    
    def test_resolve_tentative_conflicts_all_tentative(self, service, base_time):
        """Test tentative resolution when all appointments are tentative."""
        tentative1 = self.create_appointment("Tentative 1", base_time, base_time + timedelta(hours=1), show_as='tentative')
        tentative2 = self.create_appointment("Tentative 2", base_time, base_time + timedelta(hours=1), show_as='tentative')
        
        remaining, discarded = service.resolve_tentative_conflicts([tentative1, tentative2])
        
        assert len(remaining) == 2  # Keep all if all are tentative
        assert len(discarded) == 0
    
    def test_get_appointment_priority_score(self, service, base_time):
        """Test priority score calculation."""
        high_appt = self.create_appointment("High", base_time, base_time + timedelta(hours=1), importance='high')
        normal_appt = self.create_appointment("Normal", base_time, base_time + timedelta(hours=1), importance='normal')
        low_appt = self.create_appointment("Low", base_time, base_time + timedelta(hours=1), importance='low')
        no_importance = self.create_appointment("None", base_time, base_time + timedelta(hours=1))
        
        assert service.get_appointment_priority_score(high_appt) == 3
        assert service.get_appointment_priority_score(normal_appt) == 2
        assert service.get_appointment_priority_score(low_appt) == 1
        assert service.get_appointment_priority_score(no_importance) == 2  # Default to normal
    
    def test_resolve_by_priority_single_appointment(self, service, base_time):
        """Test priority resolution with single appointment."""
        appt = self.create_appointment("Single", base_time, base_time + timedelta(hours=1))
        
        primary, secondary = service.resolve_by_priority([appt])
        
        assert primary == appt
        assert secondary == []
    
    def test_resolve_by_priority_empty_list(self, service):
        """Test priority resolution with empty list."""
        with pytest.raises(ValueError, match="No appointments to resolve"):
            service.resolve_by_priority([])
    
    def test_edge_case_missing_fields(self, service, base_time):
        """Test handling of appointments with missing show_as and importance fields."""
        appt1 = self.create_appointment("Meeting 1", base_time, base_time + timedelta(hours=1))
        appt2 = self.create_appointment("Meeting 2", base_time, base_time + timedelta(hours=1))

        # Should treat both as normal priority and not be able to auto-resolve
        result = service.apply_automatic_resolution_rules([appt1, appt2])

        assert len(result['conflicts']) == 2
        assert result['resolved'] == []

    def test_case_insensitive_show_as(self, service, base_time):
        """Test that show_as values are handled case-insensitively."""
        free_upper = self.create_appointment("Free Upper", base_time, base_time + timedelta(hours=1), show_as='FREE')
        tentative_mixed = self.create_appointment("Tentative Mixed", base_time, base_time + timedelta(hours=1), show_as='Tentative')
        busy_lower = self.create_appointment("Busy Lower", base_time, base_time + timedelta(hours=1), show_as='busy')

        result = service.apply_automatic_resolution_rules([free_upper, tentative_mixed, busy_lower])

        assert len(result['resolved']) == 1
        assert result['resolved'][0] == busy_lower
        assert free_upper in result['filtered']
        assert tentative_mixed in result['filtered']

    def test_case_insensitive_importance(self, service, base_time):
        """Test that importance values are handled case-insensitively."""
        high_upper = self.create_appointment("High Upper", base_time, base_time + timedelta(hours=1),
                                           show_as='busy', importance='HIGH')
        normal_mixed = self.create_appointment("Normal Mixed", base_time, base_time + timedelta(hours=1),
                                             show_as='busy', importance='Normal')

        result = service.apply_automatic_resolution_rules([normal_mixed, high_upper])

        assert len(result['resolved']) == 1
        assert result['resolved'][0] == high_upper
        assert normal_mixed in result['filtered']

    def test_unknown_importance_treated_as_normal(self, service, base_time):
        """Test that unknown importance values are treated as normal priority."""
        unknown_importance = self.create_appointment("Unknown", base_time, base_time + timedelta(hours=1),
                                                    show_as='busy', importance='unknown')
        high_importance = self.create_appointment("High", base_time, base_time + timedelta(hours=1),
                                                 show_as='busy', importance='high')

        result = service.apply_automatic_resolution_rules([unknown_importance, high_importance])

        assert len(result['resolved']) == 1
        assert result['resolved'][0] == high_importance
        assert unknown_importance in result['filtered']

        # Verify the unknown importance gets score 2 (normal)
        assert service.get_appointment_priority_score(unknown_importance) == 2

    def test_only_free_appointments(self, service, base_time):
        """Test scenario where all appointments are 'Free'."""
        free1 = self.create_appointment("Free 1", base_time, base_time + timedelta(hours=1), show_as='free')
        free2 = self.create_appointment("Free 2", base_time, base_time + timedelta(hours=1), show_as='free')

        result = service.apply_automatic_resolution_rules([free1, free2])

        assert len(result['resolved']) == 0
        assert len(result['filtered']) == 2
        assert free1 in result['filtered']
        assert free2 in result['filtered']
        assert 'Free' in result['resolution_log'][0]

    def test_only_tentative_appointments(self, service, base_time):
        """Test scenario where all appointments are 'Tentative'."""
        tentative1 = self.create_appointment("Tentative 1", base_time, base_time + timedelta(hours=1),
                                           show_as='tentative', importance='high')
        tentative2 = self.create_appointment("Tentative 2", base_time, base_time + timedelta(hours=1),
                                           show_as='tentative', importance='low')

        result = service.apply_automatic_resolution_rules([tentative1, tentative2])

        # Should resolve by priority since all are tentative
        assert len(result['resolved']) == 1
        assert result['resolved'][0] == tentative1  # Higher priority
        assert tentative2 in result['filtered']
