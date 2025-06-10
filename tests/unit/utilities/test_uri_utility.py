"""
Unit tests for URI utility functions.

Tests the URI parsing, construction, and validation functions for both
legacy and new URI formats with account context support.
"""

import pytest
from core.utilities.uri_utility import (
    ParsedURI,
    URIParseError,
    URIValidationError,
    parse_resource_uri,
    construct_resource_uri,
    construct_resource_uri_encoded,
    get_primary_calendar_uri,
    convert_uri_to_user_friendly,
    convert_uri_to_encoded,
    parse_user_friendly_identifier,
    format_user_friendly_identifier,
    validate_uri_components,
    validate_account,
    migrate_legacy_uri
)


class TestParsedURI:
    """Test suite for ParsedURI dataclass"""

    def test_parsed_uri_creation_legacy(self):
        """Test creating ParsedURI with legacy format (no account)"""
        parsed = ParsedURI(
            scheme='msgraph',
            namespace='calendars',
            identifier='primary',
            raw_uri='msgraph://calendars/primary',
            account=None
        )
        
        assert parsed.scheme == 'msgraph'
        assert parsed.namespace == 'calendars'
        assert parsed.identifier == 'primary'
        assert parsed.raw_uri == 'msgraph://calendars/primary'
        assert parsed.account is None

    def test_parsed_uri_creation_with_account(self):
        """Test creating ParsedURI with account context"""
        parsed = ParsedURI(
            scheme='msgraph',
            namespace='calendars',
            identifier='primary',
            raw_uri='msgraph://user@example.com/calendars/primary',
            account='user@example.com'
        )
        
        assert parsed.scheme == 'msgraph'
        assert parsed.namespace == 'calendars'
        assert parsed.identifier == 'primary'
        assert parsed.raw_uri == 'msgraph://user@example.com/calendars/primary'
        assert parsed.account == 'user@example.com'

    def test_is_friendly_name_property(self):
        """Test is_friendly_name property"""
        # Friendly name
        parsed_friendly = ParsedURI('msgraph', 'calendars', 'Activity Archive', 'test', None)
        assert parsed_friendly.is_friendly_name is True

        # Technical ID (long with special chars - base64-like)
        parsed_technical = ParsedURI('msgraph', 'calendars', 'AQMkADAwATM3ZmYAZS05ZmQzLTljNjAtMDACLTAwCgAAAAAAABYAAAAA==', 'test', None)
        assert parsed_technical.is_friendly_name is False

        # Numeric ID
        parsed_numeric = ParsedURI('msgraph', 'calendars', '123', 'test', None)
        assert parsed_numeric.is_friendly_name is False


class TestParseResourceURI:
    """Test suite for parse_resource_uri function"""

    def test_parse_legacy_uri_simple(self):
        """Test parsing simple legacy URI"""
        result = parse_resource_uri('msgraph://calendars/primary')
        
        assert result.scheme == 'msgraph'
        assert result.namespace == 'calendars'
        assert result.identifier == 'primary'
        assert result.account is None
        assert result.raw_uri == 'msgraph://calendars/primary'

    def test_parse_legacy_uri_with_spaces(self):
        """Test parsing legacy URI with spaces in identifier"""
        result = parse_resource_uri('msgraph://calendars/"Activity Archive"')
        
        assert result.scheme == 'msgraph'
        assert result.namespace == 'calendars'
        assert result.identifier == 'Activity Archive'
        assert result.account is None

    def test_parse_new_uri_with_account(self):
        """Test parsing new URI format with account context"""
        result = parse_resource_uri('msgraph://user@example.com/calendars/primary')
        
        assert result.scheme == 'msgraph'
        assert result.namespace == 'calendars'
        assert result.identifier == 'primary'
        assert result.account == 'user@example.com'
        assert result.raw_uri == 'msgraph://user@example.com/calendars/primary'

    def test_parse_new_uri_with_account_and_spaces(self):
        """Test parsing new URI with account and spaces in identifier"""
        result = parse_resource_uri('msgraph://user@example.com/calendars/"Activity Archive"')
        
        assert result.scheme == 'msgraph'
        assert result.namespace == 'calendars'
        assert result.identifier == 'Activity Archive'
        assert result.account == 'user@example.com'

    def test_parse_legacy_special_cases(self):
        """Test parsing legacy special cases"""
        # Empty string
        result = parse_resource_uri('')
        assert result.scheme == 'msgraph'
        assert result.namespace == 'calendars'
        assert result.identifier == 'primary'
        assert result.account is None
        
        # 'calendar'
        result = parse_resource_uri('calendar')
        assert result.scheme == 'msgraph'
        assert result.namespace == 'calendars'
        assert result.identifier == 'primary'
        assert result.account is None
        
        # 'primary'
        result = parse_resource_uri('primary')
        assert result.scheme == 'msgraph'
        assert result.namespace == 'calendars'
        assert result.identifier == 'primary'
        assert result.account is None

    def test_parse_url_encoded_identifier(self):
        """Test parsing URI with URL-encoded identifier"""
        result = parse_resource_uri('msgraph://calendars/Activity%20Archive')
        
        assert result.scheme == 'msgraph'
        assert result.namespace == 'calendars'
        assert result.identifier == 'Activity Archive'
        assert result.account is None

    def test_parse_invalid_uris(self):
        """Test parsing invalid URIs raises appropriate errors"""
        with pytest.raises(URIParseError, match="URI missing scheme"):
            parse_resource_uri('calendars/primary')

        with pytest.raises(URIParseError, match="URI missing path"):
            parse_resource_uri('msgraph://')

        with pytest.raises(URIParseError, match="URI missing path"):
            parse_resource_uri('msgraph://calendars')

    def test_parse_account_detection(self):
        """Test account detection logic"""
        # Email-like account
        result = parse_resource_uri('msgraph://user@domain.com/calendars/primary')
        assert result.account == 'user@domain.com'
        
        # Domain-like account
        result = parse_resource_uri('msgraph://subdomain.domain.com/calendars/primary')
        assert result.account == 'subdomain.domain.com'
        
        # Simple namespace (legacy)
        result = parse_resource_uri('msgraph://calendars/primary')
        assert result.account is None


class TestConstructResourceURI:
    """Test suite for construct_resource_uri function"""

    def test_construct_legacy_uri(self):
        """Test constructing legacy URI without account"""
        result = construct_resource_uri('msgraph', 'calendars', 'primary')
        assert result == 'msgraph://calendars/primary'

    def test_construct_new_uri_with_account(self):
        """Test constructing new URI with account context"""
        result = construct_resource_uri('msgraph', 'calendars', 'primary', account='user@example.com')
        assert result == 'msgraph://user@example.com/calendars/primary'

    def test_construct_uri_with_spaces_user_friendly(self):
        """Test constructing URI with spaces in user-friendly format"""
        result = construct_resource_uri('msgraph', 'calendars', 'Activity Archive', user_friendly=True)
        assert result == 'msgraph://calendars/"Activity Archive"'

    def test_construct_uri_with_spaces_encoded(self):
        """Test constructing URI with spaces in encoded format"""
        result = construct_resource_uri('msgraph', 'calendars', 'Activity Archive', user_friendly=False)
        assert result == 'msgraph://calendars/Activity%20Archive'

    def test_construct_uri_missing_components(self):
        """Test constructing URI with missing components raises error"""
        with pytest.raises(ValueError, match="All components .* are required"):
            construct_resource_uri('', 'calendars', 'primary')
        
        with pytest.raises(ValueError, match="All components .* are required"):
            construct_resource_uri('msgraph', '', 'primary')
        
        with pytest.raises(ValueError, match="All components .* are required"):
            construct_resource_uri('msgraph', 'calendars', '')


class TestConstructResourceURIEncoded:
    """Test suite for construct_resource_uri_encoded function"""

    def test_construct_encoded_uri_legacy(self):
        """Test constructing encoded URI without account"""
        result = construct_resource_uri_encoded('msgraph', 'calendars', 'Activity Archive')
        assert result == 'msgraph://calendars/Activity%20Archive'

    def test_construct_encoded_uri_with_account(self):
        """Test constructing encoded URI with account"""
        result = construct_resource_uri_encoded('msgraph', 'calendars', 'Activity Archive', account='user@example.com')
        assert result == 'msgraph://user@example.com/calendars/Activity%20Archive'


class TestGetPrimaryCalendarURI:
    """Test suite for get_primary_calendar_uri function"""

    def test_get_primary_calendar_uri_default(self):
        """Test getting primary calendar URI with default scheme"""
        result = get_primary_calendar_uri()
        assert result == 'msgraph://calendars/primary'

    def test_get_primary_calendar_uri_custom_scheme(self):
        """Test getting primary calendar URI with custom scheme"""
        result = get_primary_calendar_uri('local')
        assert result == 'local://calendars/primary'

    def test_get_primary_calendar_uri_with_account(self):
        """Test getting primary calendar URI with account context"""
        result = get_primary_calendar_uri('msgraph', 'user@example.com')
        assert result == 'msgraph://user@example.com/calendars/primary'


class TestConvertURIFunctions:
    """Test suite for URI conversion functions"""

    def test_convert_uri_to_user_friendly_legacy(self):
        """Test converting legacy URI to user-friendly format"""
        result = convert_uri_to_user_friendly('msgraph://calendars/Activity%20Archive')
        assert result == 'msgraph://calendars/"Activity Archive"'

    def test_convert_uri_to_user_friendly_with_account(self):
        """Test converting URI with account to user-friendly format"""
        result = convert_uri_to_user_friendly('msgraph://user@example.com/calendars/Activity%20Archive')
        assert result == 'msgraph://user@example.com/calendars/"Activity Archive"'

    def test_convert_uri_to_encoded_legacy(self):
        """Test converting legacy URI to encoded format"""
        result = convert_uri_to_encoded('msgraph://calendars/"Activity Archive"')
        assert result == 'msgraph://calendars/Activity%20Archive'

    def test_convert_uri_to_encoded_with_account(self):
        """Test converting URI with account to encoded format"""
        result = convert_uri_to_encoded('msgraph://user@example.com/calendars/"Activity Archive"')
        assert result == 'msgraph://user@example.com/calendars/Activity%20Archive'

    def test_convert_invalid_uri_returns_original(self):
        """Test converting invalid URI returns original"""
        invalid_uri = 'invalid-uri'
        assert convert_uri_to_user_friendly(invalid_uri) == invalid_uri
        assert convert_uri_to_encoded(invalid_uri) == invalid_uri


class TestBackwardCompatibility:
    """Test suite for backward compatibility"""

    def test_round_trip_legacy_uri(self):
        """Test round-trip parsing and construction of legacy URI"""
        original = 'msgraph://calendars/primary'
        parsed = parse_resource_uri(original)
        reconstructed = construct_resource_uri(parsed.scheme, parsed.namespace, parsed.identifier, account=parsed.account)
        assert reconstructed == original

    def test_round_trip_new_uri(self):
        """Test round-trip parsing and construction of new URI"""
        original = 'msgraph://user@example.com/calendars/primary'
        parsed = parse_resource_uri(original)
        reconstructed = construct_resource_uri(parsed.scheme, parsed.namespace, parsed.identifier, account=parsed.account)
        assert reconstructed == original

    def test_legacy_functions_still_work(self):
        """Test that legacy function calls still work without account parameter"""
        # These should not raise errors
        uri = construct_resource_uri('msgraph', 'calendars', 'primary')
        assert uri == 'msgraph://calendars/primary'
        
        primary_uri = get_primary_calendar_uri()
        assert primary_uri == 'msgraph://calendars/primary'


class TestValidateAccount:
    """Test suite for validate_account function"""

    def test_validate_email_accounts(self):
        """Test validation of email account formats"""
        # Valid email formats
        assert validate_account('user@example.com') == True
        assert validate_account('user.name@domain.co.uk') == True
        assert validate_account('test+tag@subdomain.domain.com') == True
        assert validate_account('user123@example.org') == True

    def test_validate_domain_accounts(self):
        """Test validation of domain account formats"""
        # Valid domain formats
        assert validate_account('subdomain.domain.com') == True
        assert validate_account('domain.com') == True
        assert validate_account('example.org') == True

    def test_validate_username_accounts(self):
        """Test validation of simple username formats"""
        # Valid username formats
        assert validate_account('username') == True
        assert validate_account('user123') == True
        assert validate_account('user_name') == True
        assert validate_account('user-name') == True
        assert validate_account('user.name') == True

    def test_validate_invalid_accounts(self):
        """Test validation of invalid account formats"""
        # Invalid formats
        assert validate_account('') == False
        assert validate_account('   ') == False
        assert validate_account('@domain.com') == False  # Missing username
        assert validate_account('user@') == False  # Missing domain
        assert validate_account('user@domain') == False  # Missing TLD
        assert validate_account('user name') == False  # Space in username
        assert validate_account('user@domain space.com') == False  # Space in domain
        assert validate_account('user!@domain.com') == False  # Invalid character
        assert validate_account(None) == False  # None input


class TestAccountValidationInParsing:
    """Test suite for account validation during URI parsing"""

    def test_parse_uri_with_invalid_account_email(self):
        """Test parsing URI with invalid email account format"""
        with pytest.raises(URIParseError, match="Invalid account format"):
            parse_resource_uri('msgraph://@domain.com/calendars/primary')

    def test_parse_uri_with_invalid_account_domain(self):
        """Test parsing URI with invalid domain account format"""
        with pytest.raises(URIParseError, match="Invalid account format"):
            parse_resource_uri('msgraph://user@domain/calendars/primary')  # Missing TLD in email

    def test_construct_uri_with_invalid_account(self):
        """Test constructing URI with invalid account format"""
        with pytest.raises(URIValidationError, match="Invalid account format"):
            construct_resource_uri('msgraph', 'calendars', 'primary', account='@invalid')


class TestEnhancedAccountSupport:
    """Test suite for enhanced account context support"""

    def test_parse_various_account_formats(self):
        """Test parsing URIs with various valid account formats"""
        # Email format
        result = parse_resource_uri('msgraph://user@example.com/calendars/primary')
        assert result.account == 'user@example.com'

        # Domain format
        result = parse_resource_uri('msgraph://subdomain.domain.com/calendars/primary')
        assert result.account == 'subdomain.domain.com'

        # Username format (when using path-based format)
        result = parse_resource_uri('msgraph:///username/calendars/primary')
        assert result.account == 'username'

    def test_validate_account_function(self):
        """Test the validate_account function with various inputs"""
        # Valid email formats
        assert validate_account('user@example.com') == True
        assert validate_account('test.user+tag@domain.co.uk') == True

        # Valid domain formats
        assert validate_account('subdomain.domain.com') == True
        assert validate_account('localhost') == True

        # Valid username formats
        assert validate_account('username123') == True
        assert validate_account('user_name') == True

        # Invalid formats
        assert validate_account('') == False
        assert validate_account('   ') == False
        assert validate_account('user@') == False
        assert validate_account('@domain.com') == False
        assert validate_account('user space@domain.com') == False

    def test_migrate_legacy_uri_function(self):
        """Test the migrate_legacy_uri function"""
        # Test migration with account
        result = migrate_legacy_uri('msgraph://calendars/primary', 'user@example.com')
        assert result == 'msgraph://user@example.com/calendars/primary'

        # Test migration without account (should return original)
        result = migrate_legacy_uri('msgraph://calendars/primary', None)
        assert result == 'msgraph://calendars/primary'

        # Test migration with empty account
        result = migrate_legacy_uri('msgraph://calendars/primary', '')
        assert result == 'msgraph://calendars/primary'

        # Test migration of already migrated URI
        result = migrate_legacy_uri('msgraph://user@example.com/calendars/primary', 'user@example.com')
        assert result == 'msgraph://user@example.com/calendars/primary'

    def test_account_context_edge_cases(self):
        """Test edge cases for account context handling"""
        # Account with special characters
        result = parse_resource_uri('msgraph://user+tag@example.com/calendars/primary')
        assert result.account == 'user+tag@example.com'

        # Account with subdomain
        result = parse_resource_uri('msgraph://user@mail.example.com/calendars/primary')
        assert result.account == 'user@mail.example.com'

        # Numeric account (user ID)
        result = parse_resource_uri('msgraph://12345/calendars/primary')
        assert result.account == '12345'

        # Account with hyphens
        result = parse_resource_uri('msgraph://test-user@example-domain.com/calendars/primary')
        assert result.account == 'test-user@example-domain.com'

    def test_uri_validation_with_account_context(self):
        """Test URI validation with account context"""
        # Valid URIs with account context
        valid_uris = [
            'msgraph://user@example.com/calendars/primary',
            'msgraph://subdomain.domain.com/calendars/archive',
            'msgraph://username/calendars/"Custom Calendar"',
            'local://user@local.com/calendars/backup'
        ]

        for uri in valid_uris:
            try:
                result = parse_resource_uri(uri)
                assert result.account is not None
                assert len(result.account) > 0
            except Exception as e:
                pytest.fail(f"Valid URI failed to parse: {uri}, error: {e}")

    def test_construct_uri_with_special_characters(self):
        """Test URI construction with special characters in account"""
        # Email with plus sign
        result = construct_resource_uri('msgraph', 'calendars', 'primary', account='user+tag@example.com')
        assert result == 'msgraph://user+tag@example.com/calendars/primary'

        # Account with hyphens
        result = construct_resource_uri('msgraph', 'calendars', 'primary', account='test-user@example.com')
        assert result == 'msgraph://test-user@example.com/calendars/primary'

        # Identifier with spaces (should be quoted)
        result = construct_resource_uri('msgraph', 'calendars', 'Custom Calendar', account='user@example.com')
        assert result == 'msgraph://user@example.com/calendars/"Custom Calendar"'


class TestURIValidationAndErrorHandling:
    """Test suite for URI validation and comprehensive error handling"""

    def test_validate_uri_components_success(self):
        """Test successful URI component validation"""
        # Valid components
        validate_uri_components('msgraph', 'calendars', 'primary')  # Should not raise
        validate_uri_components('local', 'calendars', 'archive')  # Should not raise
        validate_uri_components('msgraph', 'calendars', 'Custom Calendar')  # Should not raise

    def test_validate_uri_components_failures(self):
        """Test URI component validation failures"""
        # Empty scheme
        with pytest.raises(URIValidationError, match="Scheme cannot be empty"):
            validate_uri_components('', 'calendars', 'primary')

        # Empty namespace
        with pytest.raises(URIValidationError, match="Namespace cannot be empty"):
            validate_uri_components('msgraph', '', 'primary')

        # Empty identifier
        with pytest.raises(URIValidationError, match="Identifier cannot be empty"):
            validate_uri_components('msgraph', 'calendars', '')

        # None values
        with pytest.raises(URIValidationError):
            validate_uri_components(None, 'calendars', 'primary')

    def test_parse_malformed_uris(self):
        """Test parsing of malformed URIs"""
        malformed_uris = [
            'not-a-uri',
            'msgraph://',
            'msgraph:///',
            'msgraph://account/',
            'msgraph://account/namespace/',
            '://calendars/primary',
            'msgraph:calendars/primary',  # Missing //
            'msgraph://account//calendars/primary',  # Double slash
        ]

        for uri in malformed_uris:
            with pytest.raises(URIParseError):
                parse_resource_uri(uri)

    def test_account_validation_edge_cases(self):
        """Test account validation with edge cases"""
        # Test with whitespace
        assert validate_account('  user@example.com  ') == True  # Should trim whitespace

        # Test with tabs and newlines
        assert validate_account('\tuser@example.com\n') == True

        # Test with only whitespace
        assert validate_account('   \t\n   ') == False

        # Test with None
        assert validate_account(None) == False

    def test_uri_encoding_edge_cases(self):
        """Test URI encoding with edge cases"""
        # Special characters in identifier
        special_identifiers = [
            'Calendar with spaces',
            'Calendar@with@symbols',
            'Calendar#with#hash',
            'Calendar%with%percent',
            'Calendar&with&ampersand'
        ]

        for identifier in special_identifiers:
            # Test encoding
            encoded_uri = construct_resource_uri_encoded('msgraph', 'calendars', identifier)
            assert encoded_uri is not None

            # Test that parsing the encoded URI works
            parsed = parse_resource_uri(encoded_uri)
            assert parsed.identifier == identifier

    def test_user_friendly_conversion_edge_cases(self):
        """Test user-friendly conversion with edge cases"""
        # Test with already quoted identifier
        uri = 'msgraph://calendars/"Already Quoted"'
        friendly = convert_uri_to_user_friendly(uri)
        assert 'Already Quoted' in friendly

        # Test with encoded identifier
        uri = 'msgraph://calendars/Encoded%20Calendar'
        friendly = convert_uri_to_user_friendly(uri)
        assert 'Encoded Calendar' in friendly

        # Test with account context
        uri = 'msgraph://user@example.com/calendars/primary'
        friendly = convert_uri_to_user_friendly(uri)
        assert 'user@example.com' in friendly
        assert 'primary' in friendly

    def test_parse_user_friendly_identifier_edge_cases(self):
        """Test parsing user-friendly identifiers with edge cases"""
        # Test with various formats
        test_cases = [
            ('Calendar: "My Calendar"', 'My Calendar'),
            ('Calendar: My Calendar', 'My Calendar'),
            ('Calendar: primary', 'primary'),
            ('Calendar: "Calendar with quotes"', 'Calendar with quotes'),
        ]

        for input_str, expected in test_cases:
            result = parse_user_friendly_identifier(input_str)
            assert result == expected

    def test_format_user_friendly_identifier_edge_cases(self):
        """Test formatting user-friendly identifiers with edge cases"""
        # Test with various identifiers
        test_cases = [
            ('primary', 'Calendar: primary'),
            ('My Calendar', 'Calendar: "My Calendar"'),
            ('Calendar with "quotes"', 'Calendar: "Calendar with \\"quotes\\""'),
        ]

        for identifier, expected in test_cases:
            result = format_user_friendly_identifier(identifier)
            assert result == expected

    def test_construct_with_various_account_formats(self):
        """Test constructing URIs with various valid account formats"""
        # Email format
        result = construct_resource_uri('msgraph', 'calendars', 'primary', account='user@example.com')
        assert result == 'msgraph://user@example.com/calendars/primary'

        # Domain format
        result = construct_resource_uri('msgraph', 'calendars', 'primary', account='subdomain.domain.com')
        assert result == 'msgraph://subdomain.domain.com/calendars/primary'

        # Username format
        result = construct_resource_uri('msgraph', 'calendars', 'primary', account='username')
        assert result == 'msgraph://username/calendars/primary'
