from core.utilities import uri_utility as uu
import pytest


def test_parse_user_friendly_identifier_variants():
    assert uu.parse_user_friendly_identifier('"Activity Archive"') == 'Activity Archive'
    assert uu.parse_user_friendly_identifier("Activity\\ Archive") == 'Activity Archive'
    assert uu.parse_user_friendly_identifier("Calendar: \"My Calendar\"") == 'My Calendar'
    assert uu.parse_user_friendly_identifier("primary") == 'primary'


def test_format_user_friendly_identifier_and_calendar_prefix():
    s = 'Activity Archive'
    assert uu.format_user_friendly_identifier(s) == '"Activity Archive"'
    assert uu.format_user_friendly_identifier(s, force_quotes=True) == '"Activity Archive"'
    assert uu.format_user_friendly_identifier(s, use_calendar_prefix=True) == 'Calendar: "Activity Archive"'
    assert uu.format_user_friendly_identifier('Simple') == 'Simple'


def test_validate_account_various():
    assert uu.validate_account('user@example.com') is True
    assert uu.validate_account('sub.domain.com') is True
    assert uu.validate_account('12345') is True
    assert uu.validate_account('username_123') is True
    assert uu.validate_account('') is False
    assert uu.validate_account('not valid!') is False


def test_construct_resource_uri_invalid_account_raises():
    # invalid account should raise URIValidationError
    with pytest.raises(uu.URIValidationError):
        uu.construct_resource_uri('msgraph', 'calendars', 'primary', user_friendly=True, account='bad@@')


def test_parse_resource_uri_errors_and_legacy_handling():
    # Missing scheme should raise
    with pytest.raises(uu.URIParseError):
        uu.parse_resource_uri('not-a-uri')

    # Legacy special-case strings
    parsed = uu.parse_resource_uri('calendar')
    assert parsed.namespace == 'calendars'
    assert parsed.identifier == 'primary'


def test_migrate_legacy_uri_variants():
    # legacy without namespace
    migrated = uu.migrate_legacy_uri('msgraph://my-old-calendar', account='user@example.com')
    assert migrated.startswith('msgraph://user@example.com/calendars/')

    # already has namespace and account -> unchanged
    orig = 'msgraph://user@example.com/calendars/primary'
    assert uu.migrate_legacy_uri(orig, account='user@example.com') == orig

    # local scheme handling
    migrated_local = uu.migrate_legacy_uri('local://mycal', account=None)
    assert migrated_local.startswith('local://calendars/')


def test_normalize_and_legacy_lookup_key():
    assert uu.normalize_calendar_name_for_lookup('  My  Calendar!! ') == 'my calendar'
    assert uu.create_legacy_compatible_lookup_key('My Calendar!!') == 'my-calendar'

