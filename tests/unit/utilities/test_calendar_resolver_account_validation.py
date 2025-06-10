"""
Unit tests for CalendarResolver account validation functionality.

Tests the new account validation methods in CalendarResolver that validate
URI account context against user information.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from core.utilities.calendar_resolver import CalendarResolver, CalendarResolutionError
from core.utilities.uri_utility import parse_resource_uri


class TestCalendarResolverAccountValidation:
    """Test suite for CalendarResolver account validation"""

    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing"""
        user = Mock()
        user.id = 123
        user.email = "test@example.com"
        user.username = "testuser"
        return user

    @pytest.fixture
    def mock_msgraph_client(self):
        """Create a mock MS Graph client"""
        return Mock()

    @pytest.fixture
    def resolver(self, mock_user, mock_msgraph_client):
        """Create CalendarResolver instance"""
        return CalendarResolver(mock_user, mock_msgraph_client)

    def test_validate_account_context_with_email_match(self, resolver, mock_user):
        """Test account validation with matching email"""
        # Test exact email match (case-insensitive)
        resolver._validate_account_context("test@example.com")  # Should not raise
        resolver._validate_account_context("TEST@EXAMPLE.COM")  # Should not raise
        resolver._validate_account_context("Test@Example.Com")  # Should not raise

    def test_validate_account_context_with_username_match(self, resolver, mock_user):
        """Test account validation with matching username"""
        # Test exact username match (case-sensitive)
        resolver._validate_account_context("testuser")  # Should not raise

    def test_validate_account_context_with_user_id_match(self, resolver, mock_user):
        """Test account validation with matching user ID"""
        # Test user ID match
        resolver._validate_account_context("123")  # Should not raise

    def test_validate_account_context_with_invalid_account(self, resolver, mock_user):
        """Test account validation with invalid account"""
        # Test non-matching accounts
        with pytest.raises(CalendarResolutionError, match="Account context.*does not match"):
            resolver._validate_account_context("wrong@example.com")
        
        with pytest.raises(CalendarResolutionError, match="Account context.*does not match"):
            resolver._validate_account_context("wronguser")
        
        with pytest.raises(CalendarResolutionError, match="Account context.*does not match"):
            resolver._validate_account_context("999")

    def test_validate_account_context_with_empty_account(self, resolver):
        """Test account validation with empty account"""
        # Empty account should be allowed (skips validation)
        resolver._validate_account_context("")  # Should not raise
        resolver._validate_account_context("   ")  # Should not raise
        resolver._validate_account_context(None)  # Should not raise

    def test_validate_account_context_with_missing_user_info(self, mock_msgraph_client):
        """Test account validation with missing user information"""
        # User with no email
        user_no_email = Mock()
        user_no_email.id = 123
        user_no_email.email = None
        user_no_email.username = "testuser"
        
        resolver = CalendarResolver(user_no_email, mock_msgraph_client)
        
        # Should still validate against username and ID
        resolver._validate_account_context("testuser")  # Should not raise
        resolver._validate_account_context("123")  # Should not raise
        
        with pytest.raises(CalendarResolutionError):
            resolver._validate_account_context("test@example.com")

    def test_validate_account_context_with_no_username(self, mock_msgraph_client):
        """Test account validation with no username"""
        # User with no username
        user_no_username = Mock()
        user_no_username.id = 123
        user_no_username.email = "test@example.com"
        user_no_username.username = None
        
        resolver = CalendarResolver(user_no_username, mock_msgraph_client)
        
        # Should still validate against email and ID
        resolver._validate_account_context("test@example.com")  # Should not raise
        resolver._validate_account_context("123")  # Should not raise
        
        with pytest.raises(CalendarResolutionError):
            resolver._validate_account_context("testuser")

    def test_resolve_calendar_with_account_validation(self, resolver, mock_user):
        """Test calendar resolution with account validation"""
        # Mock the _get_msgraph_calendars method
        mock_calendars = [
            {"id": "cal-123", "name": "primary"},
            {"id": "cal-456", "name": "archive"}
        ]
        
        with patch.object(resolver, '_get_msgraph_calendars', return_value=mock_calendars):
            # Test with valid account context
            uri = f"msgraph://{mock_user.email}/calendars/primary"
            result = resolver.resolve_calendar(uri)
            assert result == "cal-123"

    def test_resolve_calendar_with_invalid_account_context(self, resolver, mock_user):
        """Test calendar resolution with invalid account context"""
        # Mock the _get_msgraph_calendars method
        mock_calendars = [
            {"id": "cal-123", "name": "primary"}
        ]
        
        with patch.object(resolver, '_get_msgraph_calendars', return_value=mock_calendars):
            # Test with invalid account context
            uri = "msgraph://wrong@example.com/calendars/primary"
            
            with pytest.raises(CalendarResolutionError, match="Account context.*does not match"):
                resolver.resolve_calendar(uri)

    def test_resolve_calendar_without_account_context(self, resolver):
        """Test calendar resolution without account context (legacy format)"""
        # Mock the _get_msgraph_calendars method
        mock_calendars = [
            {"id": "cal-123", "name": "primary"}
        ]
        
        with patch.object(resolver, '_get_msgraph_calendars', return_value=mock_calendars):
            # Test legacy URI format (no account context)
            uri = "msgraph://calendars/primary"
            result = resolver.resolve_calendar(uri)
            assert result == "cal-123"

    def test_account_validation_error_message_content(self, resolver, mock_user):
        """Test that account validation error messages contain helpful information"""
        try:
            resolver._validate_account_context("wrong@example.com")
            pytest.fail("Expected CalendarResolutionError")
        except CalendarResolutionError as e:
            error_msg = str(e)
            # Should contain the invalid account
            assert "wrong@example.com" in error_msg
            # Should contain valid user identifiers
            assert mock_user.email in error_msg
            assert mock_user.username in error_msg
            assert str(mock_user.id) in error_msg

    def test_account_validation_with_special_characters(self, mock_msgraph_client):
        """Test account validation with special characters in email/username"""
        # User with special characters in email
        user = Mock()
        user.id = 123
        user.email = "test+tag@sub-domain.example.com"
        user.username = "test_user-123"
        
        resolver = CalendarResolver(user, mock_msgraph_client)
        
        # Should validate correctly
        resolver._validate_account_context("test+tag@sub-domain.example.com")
        resolver._validate_account_context("test_user-123")

    def test_account_validation_case_sensitivity(self, resolver, mock_user):
        """Test case sensitivity in account validation"""
        # Email should be case-insensitive
        resolver._validate_account_context("TEST@EXAMPLE.COM")
        resolver._validate_account_context("test@EXAMPLE.com")
        
        # Username should be case-sensitive
        with pytest.raises(CalendarResolutionError):
            resolver._validate_account_context("TESTUSER")
        
        with pytest.raises(CalendarResolutionError):
            resolver._validate_account_context("TestUser")

    def test_account_validation_with_whitespace(self, resolver, mock_user):
        """Test account validation with whitespace handling"""
        # Should trim whitespace
        resolver._validate_account_context("  test@example.com  ")
        resolver._validate_account_context("\ttestuser\n")
        resolver._validate_account_context("  123  ")

    def test_resolve_calendar_integration_with_account_validation(self, resolver, mock_user):
        """Test full integration of calendar resolution with account validation"""
        mock_calendars = [
            {"id": "primary-cal", "name": "Calendar"},
            {"id": "archive-cal", "name": "Archive Calendar"}
        ]
        
        with patch.object(resolver, '_get_msgraph_calendars', return_value=mock_calendars):
            # Test various URI formats with account validation
            test_cases = [
                (f"msgraph://{mock_user.email}/calendars/Calendar", "primary-cal"),
                (f"msgraph://{mock_user.username}/calendars/\"Archive Calendar\"", "archive-cal"),
                (f"msgraph://{mock_user.id}/calendars/Calendar", "primary-cal"),
                ("msgraph://calendars/Calendar", "primary-cal"),  # Legacy format
            ]
            
            for uri, expected_id in test_cases:
                result = resolver.resolve_calendar(uri)
                assert result == expected_id

    def test_account_validation_performance(self, resolver, mock_user):
        """Test that account validation doesn't significantly impact performance"""
        import time
        
        # Test multiple validations
        start_time = time.time()
        for _ in range(100):
            resolver._validate_account_context(mock_user.email)
        end_time = time.time()
        
        # Should complete quickly (less than 1 second for 100 validations)
        assert (end_time - start_time) < 1.0

    def test_account_validation_with_unicode_characters(self, mock_msgraph_client):
        """Test account validation with Unicode characters"""
        # User with Unicode characters
        user = Mock()
        user.id = 123
        user.email = "tëst@éxample.com"
        user.username = "tëst_üser"
        
        resolver = CalendarResolver(user, mock_msgraph_client)
        
        # Should handle Unicode correctly
        resolver._validate_account_context("tëst@éxample.com")
        resolver._validate_account_context("tëst_üser")

    def test_account_validation_logging(self, resolver, mock_user):
        """Test that account validation includes appropriate logging"""
        with patch('core.utilities.calendar_resolver.logger') as mock_logger:
            # Valid account should log debug message
            resolver._validate_account_context(mock_user.email)
            mock_logger.debug.assert_called()
            
            # Check log message content
            log_calls = [str(call) for call in mock_logger.debug.call_args_list]
            assert any("validated against user email" in call for call in log_calls)

    def test_account_validation_with_none_user_attributes(self, mock_msgraph_client):
        """Test account validation when user attributes are None"""
        # User with all None attributes except ID
        user = Mock()
        user.id = 123
        user.email = None
        user.username = None
        
        resolver = CalendarResolver(user, mock_msgraph_client)
        
        # Should only validate against user ID
        resolver._validate_account_context("123")
        
        # Should reject other accounts
        with pytest.raises(CalendarResolutionError):
            resolver._validate_account_context("test@example.com")
        
        with pytest.raises(CalendarResolutionError):
            resolver._validate_account_context("testuser")

    def test_account_validation_error_details(self, resolver, mock_user):
        """Test that account validation errors include detailed information"""
        try:
            resolver._validate_account_context("invalid@example.com")
            pytest.fail("Expected CalendarResolutionError")
        except CalendarResolutionError as e:
            error_msg = str(e)
            
            # Should include the invalid account
            assert "invalid@example.com" in error_msg
            
            # Should include all valid user identifiers
            assert f"email: {mock_user.email}" in error_msg
            assert f"username: {mock_user.username}" in error_msg
            assert f"ID: {mock_user.id}" in error_msg
