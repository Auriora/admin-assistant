"""
Unit tests for URI transformation functions in the account context migration.

Tests the URI transformation functions used in the database migration:
- add_account_context_to_uri
- remove_account_context_from_uri  
- get_account_context_for_user

These tests ensure proper handling of all URI formats, edge cases, and
database scenarios for the migration.
"""

import pytest
from unittest.mock import Mock, MagicMock
import sys
import os

# Add the migration module to the path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src/core/migrations/versions'))

# Import the migration functions
try:
    # Try importing from the migration module
    import importlib.util
    migration_path = os.path.join(os.path.dirname(__file__), '../../../src/core/migrations/versions/20250610_add_account_context_to_uris.py')
    spec = importlib.util.spec_from_file_location("migration_module", migration_path)
    migration_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration_module)

    add_account_context_to_uri = migration_module.add_account_context_to_uri
    remove_account_context_from_uri = migration_module.remove_account_context_from_uri
    get_account_context_for_user = migration_module.get_account_context_for_user
except ImportError:
    # Fallback for when running tests in different environments
    pytest.skip("Migration module not available for testing")


class TestAddAccountContextToURI:
    """Test suite for add_account_context_to_uri function"""

    def test_add_context_to_legacy_msgraph_uri(self):
        """Test adding account context to legacy msgraph URI"""
        result = add_account_context_to_uri("msgraph://calendars/primary", "user@example.com")
        assert result == "msgraph://user@example.com/calendars/primary"

    def test_add_context_to_legacy_local_uri(self):
        """Test adding account context to legacy local URI"""
        result = add_account_context_to_uri("local://calendars/personal", "user@example.com")
        assert result == "local://user@example.com/calendars/personal"

    def test_add_context_to_complex_identifier(self):
        """Test adding account context to URI with complex identifier"""
        result = add_account_context_to_uri("msgraph://calendars/Activity Archive", "user@example.com")
        assert result == "msgraph://user@example.com/calendars/Activity Archive"

    def test_add_context_already_has_email_account(self):
        """Test adding context to URI that already has email account context"""
        uri = "msgraph://user@example.com/calendars/primary"
        result = add_account_context_to_uri(uri, "different@example.com")
        assert result == uri  # Should not change

    def test_add_context_already_has_numeric_account(self):
        """Test adding context to URI that already has numeric account context"""
        uri = "msgraph://123/calendars/primary"
        result = add_account_context_to_uri(uri, "user@example.com")
        assert result == uri  # Should not change

    def test_add_context_empty_account_context(self):
        """Test adding empty account context returns original URI"""
        uri = "msgraph://calendars/primary"
        result = add_account_context_to_uri(uri, "")
        assert result == uri

    def test_add_context_none_account_context(self):
        """Test adding None account context returns original URI"""
        uri = "msgraph://calendars/primary"
        result = add_account_context_to_uri(uri, None)
        assert result == uri

    def test_add_context_empty_legacy_uri(self):
        """Test adding context to empty legacy URI"""
        result = add_account_context_to_uri("", "user@example.com")
        assert result == "msgraph://user@example.com/calendars/primary"

    def test_add_context_calendar_legacy_uri(self):
        """Test adding context to 'calendar' legacy URI"""
        result = add_account_context_to_uri("calendar", "user@example.com")
        assert result == "msgraph://user@example.com/calendars/primary"

    def test_add_context_primary_legacy_uri(self):
        """Test adding context to 'primary' legacy URI"""
        result = add_account_context_to_uri("primary", "user@example.com")
        assert result == "msgraph://user@example.com/calendars/primary"

    def test_add_context_malformed_uri_no_scheme(self):
        """Test adding context to malformed URI without scheme"""
        result = add_account_context_to_uri("calendars/primary", "user@example.com")
        assert result == "msgraph://user@example.com/calendars/calendars/primary"

    def test_add_context_malformed_uri_just_identifier(self):
        """Test adding context to malformed URI that's just an identifier"""
        result = add_account_context_to_uri("my-calendar", "user@example.com")
        assert result == "msgraph://user@example.com/calendars/my-calendar"

    def test_add_context_unknown_scheme(self):
        """Test adding context to URI with unknown scheme"""
        result = add_account_context_to_uri("google://calendars/primary", "user@example.com")
        assert result == "google://user@example.com/calendars/primary"

    def test_add_context_single_part_after_scheme(self):
        """Test adding context to URI with single part after scheme"""
        result = add_account_context_to_uri("msgraph://primary", "user@example.com")
        assert result == "msgraph://user@example.com/primary"

    def test_add_context_with_special_characters(self):
        """Test adding context with special characters in account"""
        result = add_account_context_to_uri("msgraph://calendars/primary", "user+test@example.com")
        assert result == "msgraph://user+test@example.com/calendars/primary"


class TestRemoveAccountContextFromURI:
    """Test suite for remove_account_context_from_uri function"""

    def test_remove_context_from_email_account_uri(self):
        """Test removing email account context from URI"""
        result = remove_account_context_from_uri("msgraph://user@example.com/calendars/primary")
        assert result == "msgraph://calendars/primary"

    def test_remove_context_from_numeric_account_uri(self):
        """Test removing numeric account context from URI"""
        result = remove_account_context_from_uri("msgraph://123/calendars/primary")
        assert result == "msgraph://calendars/primary"

    def test_remove_context_from_local_uri(self):
        """Test removing account context from local URI"""
        result = remove_account_context_from_uri("local://user@example.com/calendars/personal")
        assert result == "local://calendars/personal"

    def test_remove_context_from_complex_identifier(self):
        """Test removing context from URI with complex identifier"""
        result = remove_account_context_from_uri("msgraph://user@example.com/calendars/Activity Archive")
        assert result == "msgraph://calendars/Activity Archive"

    def test_remove_context_legacy_uri_no_change(self):
        """Test removing context from legacy URI returns unchanged"""
        uri = "msgraph://calendars/primary"
        result = remove_account_context_from_uri(uri)
        assert result == uri

    def test_remove_context_empty_uri(self):
        """Test removing context from empty URI"""
        result = remove_account_context_from_uri("")
        assert result == ""

    def test_remove_context_none_uri(self):
        """Test removing context from None URI"""
        result = remove_account_context_from_uri(None)
        assert result is None

    def test_remove_context_malformed_uri_no_scheme(self):
        """Test removing context from malformed URI without scheme"""
        uri = "calendars/primary"
        result = remove_account_context_from_uri(uri)
        assert result == uri

    def test_remove_context_single_part_after_scheme(self):
        """Test removing context from URI with single part after scheme"""
        uri = "msgraph://primary"
        result = remove_account_context_from_uri(uri)
        assert result == uri

    def test_remove_context_unknown_scheme(self):
        """Test removing context from URI with unknown scheme"""
        result = remove_account_context_from_uri("google://user@example.com/calendars/primary")
        assert result == "google://calendars/primary"

    def test_remove_context_with_special_characters(self):
        """Test removing context with special characters in account"""
        result = remove_account_context_from_uri("msgraph://user+test@example.com/calendars/primary")
        assert result == "msgraph://calendars/primary"

    def test_remove_context_multiple_slashes(self):
        """Test removing context from URI with multiple path segments"""
        result = remove_account_context_from_uri("msgraph://user@example.com/calendars/subfolder/calendar")
        assert result == "msgraph://calendars/subfolder/calendar"


class TestRoundTripTransformations:
    """Test suite for roundtrip URI transformations"""

    def test_roundtrip_legacy_msgraph_uri(self):
        """Test roundtrip transformation of legacy msgraph URI"""
        original = "msgraph://calendars/primary"
        with_context = add_account_context_to_uri(original, "user@example.com")
        back_to_legacy = remove_account_context_from_uri(with_context)
        assert back_to_legacy == original

    def test_roundtrip_legacy_local_uri(self):
        """Test roundtrip transformation of legacy local URI"""
        original = "local://calendars/personal"
        with_context = add_account_context_to_uri(original, "user@example.com")
        back_to_legacy = remove_account_context_from_uri(with_context)
        assert back_to_legacy == original

    def test_roundtrip_complex_identifier(self):
        """Test roundtrip transformation with complex identifier"""
        original = "msgraph://calendars/Activity Archive"
        with_context = add_account_context_to_uri(original, "user@example.com")
        back_to_legacy = remove_account_context_from_uri(with_context)
        assert back_to_legacy == original

    def test_roundtrip_numeric_account(self):
        """Test roundtrip transformation with numeric account"""
        original = "msgraph://calendars/primary"
        with_context = add_account_context_to_uri(original, "123")
        back_to_legacy = remove_account_context_from_uri(with_context)
        assert back_to_legacy == original

    def test_roundtrip_preserves_already_contextualized_uri(self):
        """Test that already contextualized URI is preserved in roundtrip"""
        original = "msgraph://user@example.com/calendars/primary"
        # Adding context should not change it
        with_context = add_account_context_to_uri(original, "different@example.com")
        assert with_context == original
        # Removing context should work
        back_to_legacy = remove_account_context_from_uri(with_context)
        assert back_to_legacy == "msgraph://calendars/primary"


class TestGetAccountContextForUser:
    """Test suite for get_account_context_for_user function"""

    def test_get_context_with_valid_email(self):
        """Test getting context for user with valid email"""
        # Mock database connection and result
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = ("user@example.com", "username")
        mock_connection.execute.return_value = mock_result

        result = get_account_context_for_user(mock_connection, 1)
        assert result == "user@example.com"

    def test_get_context_with_email_and_whitespace(self):
        """Test getting context for user with email that has whitespace"""
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = ("  user@example.com  ", "username")
        mock_connection.execute.return_value = mock_result

        result = get_account_context_for_user(mock_connection, 1)
        assert result == "user@example.com"

    def test_get_context_fallback_to_username(self):
        """Test getting context falls back to username when email is invalid"""
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = ("", "username")
        mock_connection.execute.return_value = mock_result

        result = get_account_context_for_user(mock_connection, 1)
        assert result == "username"

    def test_get_context_fallback_to_username_no_at_symbol(self):
        """Test getting context falls back to username when email has no @ symbol"""
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = ("invalid-email", "username")
        mock_connection.execute.return_value = mock_result

        result = get_account_context_for_user(mock_connection, 1)
        assert result == "username"

    def test_get_context_fallback_to_user_id(self):
        """Test getting context falls back to user_id when email and username are invalid"""
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = ("", "")
        mock_connection.execute.return_value = mock_result

        result = get_account_context_for_user(mock_connection, 123)
        assert result == "123"

    def test_get_context_user_not_found(self):
        """Test getting context when user is not found"""
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_connection.execute.return_value = mock_result

        result = get_account_context_for_user(mock_connection, 999)
        assert result == "999"

    def test_get_context_database_error(self):
        """Test getting context when database error occurs"""
        mock_connection = Mock()
        mock_connection.execute.side_effect = Exception("Database error")

        result = get_account_context_for_user(mock_connection, 1)
        assert result == "1"

    def test_get_context_username_with_whitespace(self):
        """Test getting context with username that has whitespace"""
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = (None, "  username  ")
        mock_connection.execute.return_value = mock_result

        result = get_account_context_for_user(mock_connection, 1)
        assert result == "username"

    def test_get_context_none_values(self):
        """Test getting context when email and username are None"""
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = (None, None)
        mock_connection.execute.return_value = mock_result

        result = get_account_context_for_user(mock_connection, 456)
        assert result == "456"


class TestEdgeCasesAndErrorHandling:
    """Test suite for edge cases and error handling"""

    def test_add_context_uri_with_multiple_schemes(self):
        """Test adding context to URI with multiple :// patterns"""
        result = add_account_context_to_uri("msgraph://test://calendars/primary", "user@example.com")
        assert result == "msgraph://user@example.com/test://calendars/primary"

    def test_remove_context_uri_with_multiple_schemes(self):
        """Test removing context from URI with multiple :// patterns"""
        result = remove_account_context_from_uri("msgraph://user@example.com/test://calendars/primary")
        assert result == "msgraph://test://calendars/primary"

    def test_add_context_uri_with_query_parameters(self):
        """Test adding context to URI with query parameters"""
        result = add_account_context_to_uri("msgraph://calendars/primary?param=value", "user@example.com")
        assert result == "msgraph://user@example.com/calendars/primary?param=value"

    def test_remove_context_uri_with_query_parameters(self):
        """Test removing context from URI with query parameters"""
        result = remove_account_context_from_uri("msgraph://user@example.com/calendars/primary?param=value")
        assert result == "msgraph://calendars/primary?param=value"

    def test_add_context_very_long_uri(self):
        """Test adding context to very long URI"""
        long_identifier = "a" * 1000
        result = add_account_context_to_uri(f"msgraph://calendars/{long_identifier}", "user@example.com")
        assert result == f"msgraph://user@example.com/calendars/{long_identifier}"

    def test_remove_context_very_long_uri(self):
        """Test removing context from very long URI"""
        long_identifier = "a" * 1000
        result = remove_account_context_from_uri(f"msgraph://user@example.com/calendars/{long_identifier}")
        assert result == f"msgraph://calendars/{long_identifier}"

    def test_unicode_characters_in_uri(self):
        """Test handling Unicode characters in URI"""
        result = add_account_context_to_uri("msgraph://calendars/日本語カレンダー", "user@example.com")
        assert result == "msgraph://user@example.com/calendars/日本語カレンダー"

    def test_unicode_characters_in_account(self):
        """Test handling Unicode characters in account"""
        result = add_account_context_to_uri("msgraph://calendars/primary", "用户@example.com")
        assert result == "msgraph://用户@example.com/calendars/primary"


class TestMalformedURIHandling:
    """Test suite for malformed URI handling"""

    def test_add_context_uri_only_scheme(self):
        """Test adding context to URI with only scheme"""
        result = add_account_context_to_uri("msgraph://", "user@example.com")
        assert result == "msgraph://user@example.com/"

    def test_remove_context_uri_only_scheme(self):
        """Test removing context from URI with only scheme"""
        result = remove_account_context_from_uri("msgraph://")
        assert result == "msgraph://"

    def test_add_context_uri_with_port(self):
        """Test adding context to URI with port number"""
        result = add_account_context_to_uri("msgraph://server:8080/calendars/primary", "user@example.com")
        assert result == "msgraph://user@example.com/server:8080/calendars/primary"

    def test_remove_context_uri_with_port(self):
        """Test removing context from URI with port number"""
        result = remove_account_context_from_uri("msgraph://user@example.com/server:8080/calendars/primary")
        assert result == "msgraph://server:8080/calendars/primary"

    def test_add_context_uri_with_fragment(self):
        """Test adding context to URI with fragment"""
        result = add_account_context_to_uri("msgraph://calendars/primary#section", "user@example.com")
        assert result == "msgraph://user@example.com/calendars/primary#section"

    def test_remove_context_uri_with_fragment(self):
        """Test removing context from URI with fragment"""
        result = remove_account_context_from_uri("msgraph://user@example.com/calendars/primary#section")
        assert result == "msgraph://calendars/primary#section"

    def test_add_context_uri_with_encoded_characters(self):
        """Test adding context to URI with URL-encoded characters"""
        result = add_account_context_to_uri("msgraph://calendars/My%20Calendar", "user@example.com")
        assert result == "msgraph://user@example.com/calendars/My%20Calendar"

    def test_remove_context_uri_with_encoded_characters(self):
        """Test removing context from URI with URL-encoded characters"""
        result = remove_account_context_from_uri("msgraph://user@example.com/calendars/My%20Calendar")
        assert result == "msgraph://calendars/My%20Calendar"


class TestSpecialAccountFormats:
    """Test suite for special account formats"""

    def test_add_context_numeric_account_string(self):
        """Test adding context with numeric account as string"""
        result = add_account_context_to_uri("msgraph://calendars/primary", "12345")
        assert result == "msgraph://12345/calendars/primary"

    def test_remove_context_numeric_account_string(self):
        """Test removing context with numeric account"""
        result = remove_account_context_from_uri("msgraph://12345/calendars/primary")
        assert result == "msgraph://calendars/primary"

    def test_add_context_email_with_subdomain(self):
        """Test adding context with email containing subdomain"""
        result = add_account_context_to_uri("msgraph://calendars/primary", "user@mail.example.com")
        assert result == "msgraph://user@mail.example.com/calendars/primary"

    def test_remove_context_email_with_subdomain(self):
        """Test removing context with email containing subdomain"""
        result = remove_account_context_from_uri("msgraph://user@mail.example.com/calendars/primary")
        assert result == "msgraph://calendars/primary"

    def test_add_context_email_with_plus_addressing(self):
        """Test adding context with email using plus addressing"""
        result = add_account_context_to_uri("msgraph://calendars/primary", "user+tag@example.com")
        assert result == "msgraph://user+tag@example.com/calendars/primary"

    def test_remove_context_email_with_plus_addressing(self):
        """Test removing context with email using plus addressing"""
        result = remove_account_context_from_uri("msgraph://user+tag@example.com/calendars/primary")
        assert result == "msgraph://calendars/primary"

    def test_add_context_account_with_dots(self):
        """Test adding context with account containing dots"""
        result = add_account_context_to_uri("msgraph://calendars/primary", "first.last@example.com")
        assert result == "msgraph://first.last@example.com/calendars/primary"

    def test_remove_context_account_with_dots(self):
        """Test removing context with account containing dots"""
        result = remove_account_context_from_uri("msgraph://first.last@example.com/calendars/primary")
        assert result == "msgraph://calendars/primary"


class TestLegacyURIFormats:
    """Test suite for legacy URI format handling"""

    def test_add_context_to_bare_calendar_name(self):
        """Test adding context to bare calendar name"""
        result = add_account_context_to_uri("Activity Archive", "user@example.com")
        assert result == "msgraph://user@example.com/calendars/Activity Archive"

    def test_add_context_to_calendar_with_spaces(self):
        """Test adding context to calendar name with spaces"""
        result = add_account_context_to_uri("My Personal Calendar", "user@example.com")
        assert result == "msgraph://user@example.com/calendars/My Personal Calendar"

    def test_add_context_to_quoted_calendar_name(self):
        """Test adding context to quoted calendar name"""
        result = add_account_context_to_uri('"Activity Archive"', "user@example.com")
        assert result == 'msgraph://user@example.com/calendars/"Activity Archive"'

    def test_roundtrip_legacy_formats(self):
        """Test roundtrip transformation of various legacy formats"""
        legacy_formats = [
            "",
            "calendar",
            "primary",
            "Activity Archive",
            "My Calendar"
        ]

        for legacy_uri in legacy_formats:
            with_context = add_account_context_to_uri(legacy_uri, "user@example.com")
            # For legacy formats, we can't roundtrip back to the exact original
            # because they get normalized to proper URI format
            assert "user@example.com" in with_context
            assert "msgraph://" in with_context


class TestDatabaseScenarios:
    """Test suite for database-related scenarios"""

    def test_get_context_with_international_email(self):
        """Test getting context for user with international email"""
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = ("用户@example.com", "username")
        mock_connection.execute.return_value = mock_result

        result = get_account_context_for_user(mock_connection, 1)
        assert result == "用户@example.com"

    def test_get_context_with_very_long_email(self):
        """Test getting context for user with very long email"""
        long_email = "a" * 50 + "@" + "b" * 50 + ".com"
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = (long_email, "username")
        mock_connection.execute.return_value = mock_result

        result = get_account_context_for_user(mock_connection, 1)
        assert result == long_email

    def test_get_context_with_special_characters_in_username(self):
        """Test getting context with special characters in username"""
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = ("", "user-name_123")
        mock_connection.execute.return_value = mock_result

        result = get_account_context_for_user(mock_connection, 1)
        assert result == "user-name_123"

    def test_get_context_sql_injection_attempt(self):
        """Test getting context handles potential SQL injection"""
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = ("'; DROP TABLE users; --@example.com", "username")
        mock_connection.execute.return_value = mock_result

        result = get_account_context_for_user(mock_connection, 1)
        assert result == "'; DROP TABLE users; --@example.com"  # Should return as-is, not execute

    def test_get_context_connection_timeout(self):
        """Test getting context when connection times out"""
        mock_connection = Mock()
        mock_connection.execute.side_effect = TimeoutError("Connection timeout")

        result = get_account_context_for_user(mock_connection, 1)
        assert result == "1"

    def test_get_context_with_zero_user_id(self):
        """Test getting context for user ID zero"""
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_connection.execute.return_value = mock_result

        result = get_account_context_for_user(mock_connection, 0)
        assert result == "0"

    def test_get_context_with_negative_user_id(self):
        """Test getting context for negative user ID"""
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_connection.execute.return_value = mock_result

        result = get_account_context_for_user(mock_connection, -1)
        assert result == "-1"


class TestPerformanceAndLimits:
    """Test suite for performance and limit scenarios"""

    def test_add_context_extremely_long_account(self):
        """Test adding very long account context"""
        long_account = "a" * 1000 + "@example.com"
        result = add_account_context_to_uri("msgraph://calendars/primary", long_account)
        assert result == f"msgraph://{long_account}/calendars/primary"

    def test_remove_context_extremely_long_account(self):
        """Test removing very long account context"""
        long_account = "a" * 1000 + "@example.com"
        uri = f"msgraph://{long_account}/calendars/primary"
        result = remove_account_context_from_uri(uri)
        assert result == "msgraph://calendars/primary"

    def test_add_context_many_path_segments(self):
        """Test adding context to URI with many path segments"""
        uri = "msgraph://calendars/folder1/folder2/folder3/calendar"
        result = add_account_context_to_uri(uri, "user@example.com")
        assert result == "msgraph://user@example.com/calendars/folder1/folder2/folder3/calendar"

    def test_remove_context_many_path_segments(self):
        """Test removing context from URI with many path segments"""
        uri = "msgraph://user@example.com/calendars/folder1/folder2/folder3/calendar"
        result = remove_account_context_from_uri(uri)
        assert result == "msgraph://calendars/folder1/folder2/folder3/calendar"

    def test_roundtrip_stress_test(self):
        """Test roundtrip transformation with various complex scenarios"""
        test_cases = [
            ("msgraph://calendars/primary", "user@example.com"),
            ("local://calendars/personal", "123"),
            ("msgraph://calendars/Activity Archive", "user+tag@example.com"),
            ("exchange://calendars/shared", "first.last@example.com"),
            ("msgraph://calendars/日本語", "用户@example.com"),
        ]

        for original_uri, account in test_cases:
            with_context = add_account_context_to_uri(original_uri, account)
            back_to_legacy = remove_account_context_from_uri(with_context)
            assert back_to_legacy == original_uri, f"Roundtrip failed for {original_uri} with account {account}"
