"""
Unit tests for PrivacyAutomationService

Tests the automated privacy flag management functionality including:
- Privacy detection for personal appointments
- Bulk privacy rule application
- Privacy statistics generation
- Integration with category processing
"""

import pytest
from unittest.mock import Mock, MagicMock
from core.services.privacy_automation_service import PrivacyAutomationService
from core.services.category_processing_service import CategoryProcessingService
from core.models.appointment import Appointment


class TestPrivacyAutomationService:
    """Test suite for PrivacyAutomationService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_category_service = Mock(spec=CategoryProcessingService)
        self.service = PrivacyAutomationService(category_service=self.mock_category_service)
        self.service_with_default = PrivacyAutomationService()
    
    def test_init_with_category_service(self):
        """Test initialization with provided category service"""
        assert self.service.category_service == self.mock_category_service
    
    def test_init_with_default_category_service(self):
        """Test initialization with default category service"""
        assert isinstance(self.service_with_default.category_service, CategoryProcessingService)
    
    def test_should_mark_private_delegates_to_category_service(self):
        """Test that should_mark_private delegates to category service"""
        # Setup
        appointment = Mock(spec=Appointment)
        self.mock_category_service.should_mark_private.return_value = True
        
        # Execute
        result = self.service.should_mark_private(appointment)
        
        # Verify
        assert result is True
        self.mock_category_service.should_mark_private.assert_called_once_with(appointment)
    
    def test_is_personal_appointment_personal(self):
        """Test personal appointment detection"""
        # Setup
        appointment = Mock(spec=Appointment)
        self.mock_category_service.extract_customer_billing_info.return_value = {
            'is_personal': True
        }
        
        # Execute
        result = self.service.is_personal_appointment(appointment)
        
        # Verify
        assert result is True
        self.mock_category_service.extract_customer_billing_info.assert_called_once_with(appointment)
    
    def test_is_personal_appointment_work(self):
        """Test work appointment detection"""
        # Setup
        appointment = Mock(spec=Appointment)
        self.mock_category_service.extract_customer_billing_info.return_value = {
            'is_personal': False
        }
        
        # Execute
        result = self.service.is_personal_appointment(appointment)
        
        # Verify
        assert result is False
    
    def test_apply_privacy_rules_marks_personal_appointments(self):
        """Test that personal appointments are marked as private"""
        # Setup
        personal_appointment = Mock(spec=Appointment)
        personal_appointment.is_private = False
        personal_appointment.sensitivity = 'normal'
        
        work_appointment = Mock(spec=Appointment)
        work_appointment.is_private = False
        work_appointment.sensitivity = 'normal'
        
        appointments = [personal_appointment, work_appointment]
        
        # Mock category service responses
        self.mock_category_service.should_mark_private.side_effect = [True, False]
        
        # Execute
        result = self.service.apply_privacy_rules(appointments)
        
        # Verify
        assert len(result) == 2
        assert result[0].sensitivity == 'private'  # Personal appointment marked private
        assert result[1].sensitivity == 'normal'   # Work appointment unchanged
    
    def test_apply_privacy_rules_preserves_existing_private(self):
        """Test that existing private appointments are preserved"""
        # Setup
        already_private = Mock(spec=Appointment)
        already_private.is_private = True
        already_private.sensitivity = 'private'
        
        appointments = [already_private]
        
        # Execute
        result = self.service.apply_privacy_rules(appointments)
        
        # Verify
        assert len(result) == 1
        assert result[0].sensitivity == 'private'
        # should_mark_private should not be called for already private appointments
        self.mock_category_service.should_mark_private.assert_not_called()
    
    def test_update_privacy_flags_statistics(self):
        """Test privacy flag updates with statistics"""
        # Setup appointments
        personal_new = Mock(spec=Appointment)
        personal_new.is_private = False
        personal_new.sensitivity = 'normal'
        
        personal_existing = Mock(spec=Appointment)
        personal_existing.is_private = True
        personal_existing.sensitivity = 'private'
        
        work_appointment = Mock(spec=Appointment)
        work_appointment.is_private = False
        work_appointment.sensitivity = 'normal'
        
        appointments = [personal_new, personal_existing, work_appointment]
        
        # Mock category service responses
        self.mock_category_service.extract_customer_billing_info.side_effect = [
            {'is_personal': True},   # personal_new
            {'is_personal': True},   # personal_existing
            {'is_personal': False}   # work_appointment
        ]
        
        # Execute
        stats = self.service.update_privacy_flags(appointments)
        
        # Verify statistics
        assert stats['total_appointments'] == 3
        assert stats['already_private'] == 1
        assert stats['marked_private'] == 1
        assert stats['personal_appointments'] == 2
        assert stats['work_appointments'] == 1
        
        # Verify appointment was marked private
        assert personal_new.sensitivity == 'private'
    
    def test_get_privacy_statistics_comprehensive(self):
        """Test comprehensive privacy statistics generation"""
        # Setup appointments with different privacy levels
        private_appt = Mock(spec=Appointment)
        private_appt.is_private = True
        private_appt.sensitivity = 'private'
        
        personal_appt = Mock(spec=Appointment)
        personal_appt.is_private = False
        personal_appt.sensitivity = 'personal'
        
        normal_appt = Mock(spec=Appointment)
        normal_appt.is_private = False
        normal_appt.sensitivity = 'normal'
        
        confidential_appt = Mock(spec=Appointment)
        confidential_appt.is_private = False
        confidential_appt.sensitivity = 'confidential'
        
        appointments = [private_appt, personal_appt, normal_appt, confidential_appt]
        
        # Mock category service responses for personal vs work classification
        self.mock_category_service.extract_customer_billing_info.side_effect = [
            {'is_personal': True},   # private_appt (personal)
            {'is_personal': True},   # personal_appt (personal)
            {'is_personal': False},  # normal_appt (work)
            {'is_personal': False}   # confidential_appt (work)
        ]
        
        # Execute
        stats = self.service.get_privacy_statistics(appointments)
        
        # Verify
        assert stats['total_appointments'] == 4
        assert stats['private_appointments'] == 1
        assert stats['public_appointments'] == 3
        assert stats['personal_appointments'] == 2
        assert stats['work_appointments'] == 2
        assert stats['privacy_breakdown']['private'] == 1
        assert stats['privacy_breakdown']['personal'] == 1
        assert stats['privacy_breakdown']['normal'] == 1
        assert stats['privacy_breakdown']['confidential'] == 1
    
    def test_get_privacy_statistics_handles_none_sensitivity(self):
        """Test privacy statistics with None sensitivity values"""
        # Setup appointment with None sensitivity
        appointment = Mock(spec=Appointment)
        appointment.is_private = False
        appointment.sensitivity = None
        
        appointments = [appointment]
        
        # Mock category service response
        self.mock_category_service.extract_customer_billing_info.return_value = {
            'is_personal': False
        }
        
        # Execute
        stats = self.service.get_privacy_statistics(appointments)
        
        # Verify None sensitivity is treated as 'normal'
        assert stats['privacy_breakdown']['normal'] == 1
    
    def test_apply_privacy_rules_empty_list(self):
        """Test applying privacy rules to empty appointment list"""
        result = self.service.apply_privacy_rules([])
        assert result == []
    
    def test_update_privacy_flags_empty_list(self):
        """Test updating privacy flags for empty appointment list"""
        stats = self.service.update_privacy_flags([])
        assert stats['total_appointments'] == 0
        assert stats['already_private'] == 0
        assert stats['marked_private'] == 0
        assert stats['personal_appointments'] == 0
        assert stats['work_appointments'] == 0
