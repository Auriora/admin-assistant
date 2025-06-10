"""
Unit tests for CalendarResolver account validation functionality.

Tests the account validation logic in CalendarResolver to ensure URIs with
account context are properly validated against the user.
"""

import pytest
from unittest.mock import Mock, patch

from core.utilities.calendar_resolver import CalendarResolver, CalendarResolutionError
from core.utilities.uri_utility import ParsedURI


class TestCalendarResolverAccountValidation:
    """Test suite for CalendarResolver account validation"""

    def setup_method(self):
        """Set up test fixtures"""
        # Create a mock user
        self.mock_user = Mock()
        self.mock_user.id = 123
        self.mock_user.email = "bruce@company.com"
        self.mock_user.username = "bruce"
        
        # Create resolver instance
        self.resolver = CalendarResolver(self.mock_user, "fake_token")

    def test_validate_account_context_email_match(self):
        """Test successful validation with matching email"""
        # Should not raise any exception
        self.resolver._validate_account_context("bruce@company.com")
        
        # Test case-insensitive matching
        self.resolver._validate_account_context("BRUCE@COMPANY.COM")
        self.resolver._validate_account_context("Bruce@Company.Com")

    def test_validate_account_context_username_match(self):
        """Test successful validation with matching username"""
        # Should not raise any exception
        self.resolver._validate_account_context("bruce")

    def test_validate_account_context_id_match(self):
        """Test successful validation with matching user ID"""
        # Should not raise any exception
        self.resolver._validate_account_context("123")

    def test_validate_account_context_empty_account(self):
        """Test validation with empty account (should pass)"""
        # Should not raise any exception
        self.resolver._validate_account_context("")
        self.resolver._validate_account_context("   ")
        self.resolver._validate_account_context(None)

    def test_validate_account_context_mismatch_email(self):
        """Test validation failure with mismatched email"""
        with pytest.raises(CalendarResolutionError) as exc_info:
            self.resolver._validate_account_context("jane@company.com")
        
        error_msg = str(exc_info.value)
        assert "Account context mismatch" in error_msg
        assert "jane@company.com" in error_msg
        assert "bruce@company.com" in error_msg

    def test_validate_account_context_mismatch_username(self):
        """Test validation failure with mismatched username"""
        with pytest.raises(CalendarResolutionError) as exc_info:
            self.resolver._validate_account_context("jane")
        
        error_msg = str(exc_info.value)
        assert "Account context mismatch" in error_msg
        assert "jane" in error_msg
        assert "bruce" in error_msg

    def test_validate_account_context_mismatch_id(self):
        """Test validation failure with mismatched ID"""
        with pytest.raises(CalendarResolutionError) as exc_info:
            self.resolver._validate_account_context("456")
        
        error_msg = str(exc_info.value)
        assert "Account context mismatch" in error_msg
        assert "456" in error_msg
        assert "123" in error_msg

    def test_validate_account_context_user_without_username(self):
        """Test validation when user has no username"""
        # Create user without username
        user_no_username = Mock()
        user_no_username.id = 123
        user_no_username.email = "bruce@company.com"
        user_no_username.username = None
        
        resolver = CalendarResolver(user_no_username, "fake_token")
        
        # Email should still work
        resolver._validate_account_context("bruce@company.com")
        
        # ID should still work
        resolver._validate_account_context("123")
        
        # Username should fail since user has no username
        with pytest.raises(CalendarResolutionError):
            resolver._validate_account_context("bruce")

    def test_validate_account_context_user_without_email(self):
        """Test validation when user has no email"""
        # Create user without email
        user_no_email = Mock()
        user_no_email.id = 123
        user_no_email.email = None
        user_no_email.username = "bruce"
        
        resolver = CalendarResolver(user_no_email, "fake_token")
        
        # Username should still work
        resolver._validate_account_context("bruce")
        
        # ID should still work
        resolver._validate_account_context("123")
        
        # Email should fail since user has no email
        with pytest.raises(CalendarResolutionError):
            resolver._validate_account_context("bruce@company.com")

    @patch('core.utilities.calendar_resolver.parse_resource_uri')
    def test_resolve_calendar_uri_with_account_validation(self, mock_parse):
        """Test that resolve_calendar_uri calls account validation when account is present"""
        # Mock parsed URI with account context
        mock_parsed = Mock(spec=ParsedURI)
        mock_parsed.account = "bruce@company.com"
        mock_parsed.namespace = "calendars"
        mock_parsed.scheme = "msgraph"
        mock_parsed.identifier = "primary"
        mock_parsed.is_friendly_name = False
        
        mock_parse.return_value = mock_parsed
        
        # Should succeed with matching account
        result = self.resolver.resolve_calendar_uri("msgraph://bruce@company.com/calendars/primary")
        assert result == ""  # Primary calendar returns empty string

    @patch('core.utilities.calendar_resolver.parse_resource_uri')
    def test_resolve_calendar_uri_account_validation_failure(self, mock_parse):
        """Test that resolve_calendar_uri raises error for account mismatch"""
        # Mock parsed URI with mismatched account context
        mock_parsed = Mock(spec=ParsedURI)
        mock_parsed.account = "jane@company.com"
        mock_parsed.namespace = "calendars"
        mock_parsed.scheme = "msgraph"
        mock_parsed.identifier = "primary"
        
        mock_parse.return_value = mock_parsed
        
        # Should fail with mismatched account
        with pytest.raises(CalendarResolutionError) as exc_info:
            self.resolver.resolve_calendar_uri("msgraph://jane@company.com/calendars/primary")
        
        assert "Account context mismatch" in str(exc_info.value)

    @patch('core.utilities.calendar_resolver.parse_resource_uri')
    def test_resolve_calendar_uri_without_account_context(self, mock_parse):
        """Test that resolve_calendar_uri works without account context (backward compatibility)"""
        # Mock parsed URI without account context
        mock_parsed = Mock(spec=ParsedURI)
        mock_parsed.account = None
        mock_parsed.namespace = "calendars"
        mock_parsed.scheme = "msgraph"
        mock_parsed.identifier = "primary"
        mock_parsed.is_friendly_name = False
        
        mock_parse.return_value = mock_parsed
        
        # Should succeed without account validation
        result = self.resolver.resolve_calendar_uri("msgraph://calendars/primary")
        assert result == ""  # Primary calendar returns empty string
