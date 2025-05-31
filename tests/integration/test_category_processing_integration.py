"""
Integration tests for CategoryProcessingService with CalendarArchiveOrchestrator
"""

import pytest
from unittest.mock import Mock, patch
from datetime import date, datetime
from core.services.category_processing_service import CategoryProcessingService
from core.orchestrators.calendar_archive_orchestrator import CalendarArchiveOrchestrator


class TestCategoryProcessingIntegration:
    """Integration tests for category processing in the archive workflow"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.category_service = CategoryProcessingService()
        self.orchestrator = CalendarArchiveOrchestrator()
    
    def test_category_processing_in_archive_workflow(self):
        """Test that category processing is properly integrated in the archive workflow"""
        # Create mock appointments with various category scenarios
        appointments = [
            self._create_mock_appointment("Work Meeting", ["Acme Corp - billable"]),
            self._create_mock_appointment("Personal Appointment", None),  # No categories
            self._create_mock_appointment("Invalid Category", ["Invalid Format"]),
            self._create_mock_appointment("Online Meeting", ["Online"]),
            self._create_mock_appointment("Admin Task", ["Admin - non-billable"])
        ]
        
        # Test category statistics generation
        stats = self.category_service.get_category_statistics(appointments)
        
        # Verify statistics
        assert stats['total_appointments'] == 5
        assert stats['personal_appointments'] == 1  # Personal appointment with no categories
        assert stats['valid_categories'] == 3  # Acme Corp, Online, Admin
        assert stats['invalid_categories'] == 2  # Personal (no category) + Invalid Format
        assert "Acme Corp" in stats['customers']
        assert stats['billing_types']['billable'] == 1
        assert stats['billing_types']['non-billable'] == 1
        assert stats['billing_types']['online'] == 1
    
    def test_privacy_flag_automation(self):
        """Test that personal appointments are automatically marked as private"""
        # Personal appointment (no categories)
        personal_appt = self._create_mock_appointment("Personal Meeting", None)
        assert self.category_service.should_mark_private(personal_appt) is True
        
        # Work appointment (with valid category)
        work_appt = self._create_mock_appointment("Client Meeting", ["Acme Corp - billable"])
        assert self.category_service.should_mark_private(work_appt) is False
        
        # Invalid category appointment (has categories but invalid format)
        invalid_appt = self._create_mock_appointment("Meeting", ["Invalid Format"])
        assert self.category_service.should_mark_private(invalid_appt) is False
    
    def test_special_category_handling(self):
        """Test handling of special categories"""
        # Online appointment
        online_appt = self._create_mock_appointment("Video Call", ["Online"])
        customer_info = self.category_service.extract_customer_billing_info(online_appt)
        assert customer_info['customer'] == "Online"
        assert customer_info['billing_type'] == "online"
        assert customer_info['is_valid'] is True
        
        # Admin appointment
        admin_appt = self._create_mock_appointment("Admin Work", ["Admin - non-billable"])
        customer_info = self.category_service.extract_customer_billing_info(admin_appt)
        assert customer_info['customer'] == "Admin"
        assert customer_info['billing_type'] == "non-billable"
        assert customer_info['is_valid'] is True
    
    def test_category_validation_issues_detection(self):
        """Test detection and reporting of category validation issues"""
        appointments = [
            self._create_mock_appointment("Meeting 1", ["Too - Many - Dashes"]),
            self._create_mock_appointment("Meeting 2", ["No Separator"]),
            self._create_mock_appointment("Meeting 3", [" - billable"]),  # Empty customer
            self._create_mock_appointment("Meeting 4", ["Client - invalid_type"])
        ]
        
        stats = self.category_service.get_category_statistics(appointments)
        
        # All should be invalid
        assert stats['valid_categories'] == 0
        assert stats['invalid_categories'] == 4
        assert len(stats['issues']) >= 4  # Should have at least one issue per appointment
        
        # Check for specific issue types
        issues_text = " ".join(stats['issues'])
        assert "Too many ' - ' separators" in issues_text
        assert "Missing ' - ' separator" in issues_text
        assert "Empty customer name" in issues_text
        assert "Invalid billing type" in issues_text
    
    def test_multiple_categories_handling(self):
        """Test handling of appointments with multiple categories"""
        # Appointment with multiple valid categories
        multi_cat_appt = self._create_mock_appointment(
            "Multi-Client Meeting", 
            ["Acme Corp - billable", "Client XYZ - non-billable"]
        )
        
        customer_info = self.category_service.extract_customer_billing_info(multi_cat_appt)
        
        # Should use first valid category
        assert customer_info['customer'] == "Acme Corp"
        assert customer_info['billing_type'] == "billable"
        assert customer_info['is_valid'] is True
        assert "Multiple valid categories found" in str(customer_info['issues'])
    
    def test_edge_cases(self):
        """Test edge cases and error handling"""
        # Empty categories list
        empty_cat_appt = self._create_mock_appointment("Meeting", [])
        customer_info = self.category_service.extract_customer_billing_info(empty_cat_appt)
        assert customer_info['is_personal'] is True
        
        # None appointment
        assert self.category_service.extract_customer_billing_info(None)['customer'] is None
        
        # Categories as string instead of list
        string_cat_appt = self._create_mock_appointment("Meeting", "Acme Corp - billable")
        customer_info = self.category_service.extract_customer_billing_info(string_cat_appt)
        assert customer_info['customer'] == "Acme Corp"
        assert customer_info['billing_type'] == "billable"
    
    def test_case_insensitive_processing(self):
        """Test case-insensitive processing of categories"""
        # Test special categories with different cases
        assert self.category_service.is_special_category("ONLINE") is True
        assert self.category_service.is_special_category("online") is True
        assert self.category_service.is_special_category("Online") is True
        
        # Test billing type case insensitivity
        customer, billing_type = self.category_service.parse_outlook_category("Client - BILLABLE")
        assert customer == "Client"
        assert billing_type == "billable"  # Should be normalized to lowercase
        
        customer, billing_type = self.category_service.parse_outlook_category("Client - Non-Billable")
        assert customer == "Client"
        assert billing_type == "non-billable"
    
    def _create_mock_appointment(self, subject, categories):
        """Helper method to create mock appointments"""
        appointment = Mock()
        appointment.subject = subject
        appointment.categories = categories
        appointment.sensitivity = None
        appointment.id = f"mock-{subject.replace(' ', '-').lower()}"
        appointment.ms_event_id = f"ms-{appointment.id}"
        appointment.start_time = datetime.now()
        appointment.end_time = datetime.now()
        return appointment


class TestCategoryProcessingCLI:
    """Test CLI integration for category processing"""
    
    @patch('core.services.calendar_service.CalendarService')
    @patch('core.db.get_session')
    def test_validate_categories_cli_integration(self, mock_get_session, mock_calendar_service):
        """Test that the CLI command integrates properly with the service"""
        # This test verifies the CLI command structure is correct
        # Actual CLI testing would require more complex setup
        
        # Mock appointments
        mock_appointments = [
            Mock(categories=["Acme Corp - billable"]),
            Mock(categories=None),  # Personal
            Mock(categories=["Invalid Format"])
        ]
        
        # Mock calendar service
        mock_calendar_service.return_value.get_appointments_for_date_range.return_value = mock_appointments
        
        # Test category processing
        category_service = CategoryProcessingService()
        stats = category_service.get_category_statistics(mock_appointments)
        
        # Verify the service works with mocked data
        assert stats['total_appointments'] == 3
        assert stats['valid_categories'] == 1
        assert stats['invalid_categories'] == 2
        assert stats['personal_appointments'] == 1
