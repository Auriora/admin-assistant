"""
Unit tests for CategoryProcessingService

Tests the parsing and validation of Outlook categories according to the
documented workflow format: '<customer name> - <billing type>'
"""

import pytest
from unittest.mock import Mock
from core.services.category_processing_service import CategoryProcessingService
from core.models.appointment import Appointment


class TestCategoryProcessingService:
    """Test suite for CategoryProcessingService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = CategoryProcessingService()
    
    def test_parse_outlook_category_valid_formats(self):
        """Test parsing of valid category formats"""
        # Standard billable format
        customer, billing_type = self.service.parse_outlook_category("Acme Corp - billable")
        assert customer == "Acme Corp"
        assert billing_type == "billable"
        
        # Standard non-billable format
        customer, billing_type = self.service.parse_outlook_category("Client XYZ - non-billable")
        assert customer == "Client XYZ"
        assert billing_type == "non-billable"
        
        # With extra spaces
        customer, billing_type = self.service.parse_outlook_category("  Big Company  -  billable  ")
        assert customer == "Big Company"
        assert billing_type == "billable"
    
    def test_parse_outlook_category_special_categories(self):
        """Test parsing of special categories"""
        # Online category
        customer, billing_type = self.service.parse_outlook_category("Online")
        assert customer == "Online"
        assert billing_type == "online"
        
        # Admin category
        customer, billing_type = self.service.parse_outlook_category("Admin - non-billable")
        assert customer == "Admin"
        assert billing_type == "non-billable"
        
        # Case insensitive special categories
        customer, billing_type = self.service.parse_outlook_category("ONLINE")
        assert customer == "Online"
        assert billing_type == "online"
    
    def test_parse_outlook_category_invalid_formats(self):
        """Test parsing of invalid category formats"""
        # No separator
        customer, billing_type = self.service.parse_outlook_category("Invalid Category")
        assert customer is None
        assert billing_type is None
        
        # Too many separators
        customer, billing_type = self.service.parse_outlook_category("Too - Many - Dashes")
        assert customer is None
        assert billing_type is None
        
        # Empty customer name
        customer, billing_type = self.service.parse_outlook_category(" - billable")
        assert customer is None
        assert billing_type is None
        
        # Invalid billing type
        customer, billing_type = self.service.parse_outlook_category("Client - invalid")
        assert customer is None
        assert billing_type is None
        
        # Empty string
        customer, billing_type = self.service.parse_outlook_category("")
        assert customer is None
        assert billing_type is None
        
        # None input
        customer, billing_type = self.service.parse_outlook_category(None)
        assert customer is None
        assert billing_type is None
    
    def test_validate_category_format_valid_categories(self):
        """Test validation of valid category lists"""
        categories = [
            "Acme Corp - billable",
            "Client XYZ - non-billable", 
            "Online",
            "Admin - non-billable"
        ]
        
        result = self.service.validate_category_format(categories)
        
        assert len(result['valid']) == 4
        assert len(result['invalid']) == 0
        assert len(result['issues']) == 0
        assert "Acme Corp - billable" in result['valid']
        assert "Online" in result['valid']
    
    def test_validate_category_format_invalid_categories(self):
        """Test validation of invalid category lists"""
        categories = [
            "Invalid Category",
            "Too - Many - Dashes",
            " - billable",
            "Client - invalid",
            ""
        ]
        
        result = self.service.validate_category_format(categories)
        
        assert len(result['valid']) == 0
        assert len(result['invalid']) == 5
        assert len(result['issues']) == 5
        
        # Check specific issue messages
        issues = result['issues']
        assert any("Missing ' - ' separator" in issue for issue in issues)
        assert any("Too many ' - ' separators" in issue for issue in issues)
        assert any("Empty customer name" in issue for issue in issues)
        assert any("Invalid billing type" in issue for issue in issues)
    
    def test_extract_customer_billing_info_valid_appointment(self):
        """Test extracting customer info from appointment with valid categories"""
        # Mock appointment with valid category
        appointment = Mock(spec=Appointment)
        appointment.categories = ["Acme Corp - billable"]
        
        result = self.service.extract_customer_billing_info(appointment)
        
        assert result['customer'] == "Acme Corp"
        assert result['billing_type'] == "billable"
        assert result['is_valid'] is True
        assert result['is_personal'] is False
        assert result['categories_found'] == ["Acme Corp - billable"]
    
    def test_extract_customer_billing_info_personal_appointment(self):
        """Test extracting info from personal appointment (no categories)"""
        # Mock appointment with no categories
        appointment = Mock(spec=Appointment)
        appointment.categories = None
        
        result = self.service.extract_customer_billing_info(appointment)
        
        assert result['customer'] is None
        assert result['billing_type'] is None
        assert result['is_valid'] is False
        assert result['is_personal'] is True
        assert result['categories_found'] == []
        assert "No categories found - treating as personal appointment" in result['issues']
    
    def test_extract_customer_billing_info_multiple_categories(self):
        """Test extracting info from appointment with multiple categories"""
        # Mock appointment with multiple valid categories
        appointment = Mock(spec=Appointment)
        appointment.categories = ["Acme Corp - billable", "Client XYZ - non-billable"]
        
        result = self.service.extract_customer_billing_info(appointment)
        
        # Should use first valid category
        assert result['customer'] == "Acme Corp"
        assert result['billing_type'] == "billable"
        assert result['is_valid'] is True
        assert "Multiple valid categories found" in str(result['issues'])
    
    def test_is_special_category(self):
        """Test special category detection"""
        assert self.service.is_special_category("Online") is True
        assert self.service.is_special_category("ONLINE") is True
        assert self.service.is_special_category("Admin - non-billable") is True
        assert self.service.is_special_category("Break - non-billable") is True
        assert self.service.is_special_category("Regular Category") is False
        assert self.service.is_special_category("") is False
        assert self.service.is_special_category(None) is False
    
    def test_should_mark_private(self):
        """Test privacy flag determination"""
        # Personal appointment (no categories) should be private
        personal_appointment = Mock(spec=Appointment)
        personal_appointment.categories = None
        assert self.service.should_mark_private(personal_appointment) is True
        
        # Work appointment (valid categories) should not be private
        work_appointment = Mock(spec=Appointment)
        work_appointment.categories = ["Acme Corp - billable"]
        assert self.service.should_mark_private(work_appointment) is False
    
    def test_get_category_statistics(self):
        """Test category statistics generation"""
        # Create mock appointments
        appointments = []
        
        # Personal appointment
        personal = Mock(spec=Appointment)
        personal.categories = None
        appointments.append(personal)
        
        # Valid work appointment
        work = Mock(spec=Appointment)
        work.categories = ["Acme Corp - billable"]
        appointments.append(work)
        
        # Invalid category appointment
        invalid = Mock(spec=Appointment)
        invalid.categories = ["Invalid Format"]
        appointments.append(invalid)
        
        stats = self.service.get_category_statistics(appointments)
        
        assert stats['total_appointments'] == 3
        assert stats['personal_appointments'] == 1
        assert stats['valid_categories'] == 1
        assert stats['invalid_categories'] == 2
        assert "Acme Corp" in stats['customers']
        assert stats['billing_types']['billable'] == 1
