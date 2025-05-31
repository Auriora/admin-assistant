"""
Integration tests for PrivacyAutomationService

Tests the privacy automation service with realistic appointment scenarios
and integration with the category processing service.
"""

import pytest
from unittest.mock import Mock
from core.services.privacy_automation_service import PrivacyAutomationService
from core.services.category_processing_service import CategoryProcessingService
from core.models.appointment import Appointment


class TestPrivacyAutomationIntegration:
    """Integration test suite for PrivacyAutomationService"""
    
    def setup_method(self):
        """Set up test fixtures with real service integration"""
        self.category_service = CategoryProcessingService()
        self.privacy_service = PrivacyAutomationService(category_service=self.category_service)
    
    def _create_mock_appointment(self, subject: str, categories: list = None, sensitivity: str = 'normal'):
        """Create a mock appointment with specified properties"""
        appointment = Mock(spec=Appointment)
        appointment.subject = subject
        appointment.categories = categories
        appointment.sensitivity = sensitivity
        appointment.is_private = (sensitivity == 'private')
        return appointment
    
    def test_personal_appointment_privacy_workflow(self):
        """Test complete workflow for personal appointments"""
        # Create personal appointment (no categories)
        personal_meeting = self._create_mock_appointment("Doctor Appointment", None)
        
        # Test privacy detection
        assert self.privacy_service.should_mark_private(personal_meeting) is True
        assert self.privacy_service.is_personal_appointment(personal_meeting) is True
        
        # Apply privacy rules
        processed = self.privacy_service.apply_privacy_rules([personal_meeting])
        assert len(processed) == 1
        assert processed[0].sensitivity == 'private'
    
    def test_work_appointment_privacy_workflow(self):
        """Test complete workflow for work appointments"""
        # Create work appointment with valid category
        client_meeting = self._create_mock_appointment(
            "Client Strategy Meeting", 
            ["Acme Corp - billable"]
        )
        
        # Test privacy detection
        assert self.privacy_service.should_mark_private(client_meeting) is False
        assert self.privacy_service.is_personal_appointment(client_meeting) is False
        
        # Apply privacy rules
        processed = self.privacy_service.apply_privacy_rules([client_meeting])
        assert len(processed) == 1
        assert processed[0].sensitivity == 'normal'  # Should remain unchanged
    
    def test_mixed_appointment_batch_processing(self):
        """Test batch processing of mixed appointment types"""
        appointments = [
            # Personal appointments
            self._create_mock_appointment("Personal Call", None),
            self._create_mock_appointment("Family Dinner", []),
            
            # Work appointments
            self._create_mock_appointment("Team Meeting", ["Acme Corp - billable"]),
            self._create_mock_appointment("Project Review", ["Client XYZ - non-billable"]),
            
            # Special categories
            self._create_mock_appointment("Admin Tasks", ["Admin - non-billable"]),
            self._create_mock_appointment("Online Training", ["Online"]),
            
            # Already private appointment
            self._create_mock_appointment("Private Meeting", ["Acme Corp - billable"], 'private'),
            
            # Invalid category (should remain public as it has categories)
            self._create_mock_appointment("Invalid Meeting", ["Invalid Format"])
        ]
        
        # Process all appointments
        stats = self.privacy_service.update_privacy_flags(appointments)
        
        # Verify statistics
        assert stats['total_appointments'] == 8
        assert stats['personal_appointments'] == 2  # 2 personal (None and empty categories)
        assert stats['work_appointments'] == 6      # 6 with categories (valid, special, invalid, already private)
        assert stats['already_private'] == 1        # One was already private
        assert stats['marked_private'] == 2         # 2 personal appointments marked private
    
    def test_privacy_statistics_comprehensive_scenario(self):
        """Test comprehensive privacy statistics with various appointment types"""
        appointments = [
            # Different sensitivity levels
            self._create_mock_appointment("Private Meeting", ["Acme Corp - billable"], 'private'),
            self._create_mock_appointment("Personal Meeting", None, 'personal'),
            self._create_mock_appointment("Confidential Meeting", ["Client XYZ - billable"], 'confidential'),
            self._create_mock_appointment("Normal Meeting", ["Acme Corp - non-billable"], 'normal'),
            
            # Personal appointments that should be marked private
            self._create_mock_appointment("Doctor Visit", None),
            self._create_mock_appointment("Personal Call", []),
        ]
        
        # Get comprehensive statistics
        stats = self.privacy_service.get_privacy_statistics(appointments)
        
        # Verify comprehensive statistics
        assert stats['total_appointments'] == 6
        assert stats['private_appointments'] == 1  # Only the explicitly private one
        assert stats['public_appointments'] == 5   # All others
        assert stats['personal_appointments'] == 3 # 2 with None/empty categories + 1 with personal sensitivity
        assert stats['work_appointments'] == 3     # 3 with valid categories
        
        # Verify privacy breakdown
        assert stats['privacy_breakdown']['private'] == 1
        assert stats['privacy_breakdown']['personal'] == 1
        assert stats['privacy_breakdown']['confidential'] == 1
        assert stats['privacy_breakdown']['normal'] == 3  # 1 explicit + 2 default
    
    def test_special_categories_privacy_handling(self):
        """Test privacy handling for special categories"""
        special_appointments = [
            self._create_mock_appointment("Admin Work", ["Admin - non-billable"]),
            self._create_mock_appointment("Coffee Break", ["Break - non-billable"]),
            self._create_mock_appointment("Online Training", ["Online"]),
        ]
        
        # All special categories should be treated as work appointments
        for appointment in special_appointments:
            assert self.privacy_service.is_personal_appointment(appointment) is False
            assert self.privacy_service.should_mark_private(appointment) is False
        
        # Apply privacy rules
        processed = self.privacy_service.apply_privacy_rules(special_appointments)
        
        # All should remain with normal sensitivity
        for appointment in processed:
            assert appointment.sensitivity == 'normal'
    
    def test_invalid_categories_privacy_handling(self):
        """Test privacy handling for appointments with invalid categories"""
        invalid_appointments = [
            self._create_mock_appointment("Meeting 1", ["Invalid Format"]),
            self._create_mock_appointment("Meeting 2", ["Too - Many - Dashes"]),
            self._create_mock_appointment("Meeting 3", [" - billable"]),  # Empty customer
        ]
        
        # Invalid categories should NOT be treated as personal
        # (they have categories, just invalid format)
        for appointment in invalid_appointments:
            assert self.privacy_service.is_personal_appointment(appointment) is False
            assert self.privacy_service.should_mark_private(appointment) is False
    
    def test_privacy_preservation_workflow(self):
        """Test that existing privacy settings are preserved"""
        appointments = [
            # Already private work appointment (should stay private)
            self._create_mock_appointment("Private Work", ["Acme Corp - billable"], 'private'),
            
            # Already private personal appointment (should stay private)
            self._create_mock_appointment("Private Personal", None, 'private'),
            
            # Public personal appointment (should become private)
            self._create_mock_appointment("Public Personal", None, 'normal'),
            
            # Public work appointment (should stay public)
            self._create_mock_appointment("Public Work", ["Client XYZ - billable"], 'normal'),
        ]
        
        # Apply privacy rules
        processed = self.privacy_service.apply_privacy_rules(appointments)
        
        # Verify privacy preservation and application
        assert processed[0].sensitivity == 'private'  # Already private work - preserved
        assert processed[1].sensitivity == 'private'  # Already private personal - preserved
        assert processed[2].sensitivity == 'private'  # Public personal - made private
        assert processed[3].sensitivity == 'normal'   # Public work - stays public
    
    def test_empty_and_edge_cases(self):
        """Test edge cases and empty scenarios"""
        # Empty list
        assert self.privacy_service.apply_privacy_rules([]) == []
        assert self.privacy_service.update_privacy_flags([])['total_appointments'] == 0
        assert self.privacy_service.get_privacy_statistics([])['total_appointments'] == 0
        
        # Appointment with None sensitivity
        none_sensitivity = self._create_mock_appointment("Test", ["Acme Corp - billable"], None)
        none_sensitivity.sensitivity = None
        none_sensitivity.is_private = False
        
        stats = self.privacy_service.get_privacy_statistics([none_sensitivity])
        assert stats['privacy_breakdown']['normal'] == 1  # None treated as normal
