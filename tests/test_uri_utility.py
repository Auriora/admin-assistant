import urllib.parse
from types import SimpleNamespace
import pytest

from core.utilities import uri_utility as uu


def test_parse_user_friendly_identifier_variants():
    assert uu.parse_user_friendly_identifier('"Activity Archive"') == 'Activity Archive'
    assert uu.parse_user_friendly_identifier("'Single Quote'") == 'Single Quote'
    assert uu.parse_user_friendly_identifier('Activity\\ Archive') == 'Activity Archive'
    assert uu.parse_user_friendly_identifier('Calendar: "My Calendar"') == 'My Calendar'
    assert uu.parse_user_friendly_identifier('primary') == 'primary'
    assert uu.parse_user_friendly_identifier('') == ''


def test_format_user_friendly_identifier_and_calendar_prefix():
    # No spaces -> no quotes unless forced
    assert uu.format_user_friendly_identifier('primary') == 'primary'
    assert uu.format_user_friendly_identifier('primary', force_quotes=True) == '"primary"'

    # Spaces -> quoted
    assert uu.format_user_friendly_identifier('Activity Archive') == '"Activity Archive"'
    # With calendar prefix
    assert uu.format_user_friendly_identifier('My Cal', use_calendar_prefix=True).startswith('Calendar: ')


def test_validate_account_various():
    assert uu.validate_account('user@example.com') is True
    assert uu.validate_account('sub.domain.com') is True
    assert uu.validate_account('12345') is True
    assert uu.validate_account('local_user') is True
    assert uu.validate_account('') is False
    assert uu.validate_account('bad@com') is False


def test_parse_resource_uri_basic_and_legacy():
    # Empty / legacy shortcuts
    p = uu.parse_resource_uri('')
    assert p.scheme == 'msgraph' and p.namespace == 'calendars' and p.identifier == 'primary'

    # Legacy encoded identifier
    encoded = 'Activity%20Archive'
    uri = f'msgraph://calendars/{encoded}'
    p2 = uu.parse_resource_uri(uri)
    assert p2.namespace == 'calendars'
    assert p2.identifier == 'Activity Archive'
    assert p2.account is None

    # User-friendly quoted identifier
    uri_q = 'msgraph://calendars/"Activity Archive"'
    p3 = uu.parse_resource_uri(uri_q)
    assert p3.identifier == 'Activity Archive'

    # New format with account
    uri_acc = 'msgraph://user@example.com/calendars/primary'
    p4 = uu.parse_resource_uri(uri_acc)
    assert p4.account == 'user@example.com'
    assert p4.namespace == 'calendars'
    assert p4.identifier == 'primary'

    # Path-only format
    uri_path = 'msgraph:///calendars/primary'
    p5 = uu.parse_resource_uri(uri_path)
    assert p5.namespace == 'calendars' and p5.identifier == 'primary'


def test_construct_resource_uri_and_encoded():
    u1 = uu.construct_resource_uri('msgraph', 'calendars', 'Activity Archive', user_friendly=True)
    assert '"Activity Archive"' in u1

    u2 = uu.construct_resource_uri('msgraph', 'calendars', 'Activity Archive', user_friendly=False)
    assert urllib.parse.quote('Activity Archive', safe='') in u2

    u3 = uu.construct_resource_uri('msgraph', 'calendars', 'primary', user_friendly=True, account='user@example.com')
    assert u3.startswith('msgraph://user@example.com/')

    # construct_resource_uri_encoded wrapper
    u4 = uu.construct_resource_uri_encoded('msgraph', 'calendars', 'Activity Archive', account='user@example.com')
    assert '%20' in u4


def test_normalize_and_legacy_lookup_key_and_migrate():
    name = '  Activity: Archive!! '
    norm = uu.normalize_calendar_name_for_lookup(name)
    assert 'activity archive' in norm

    key = uu.create_legacy_compatible_lookup_key('My Calendar Name')
    assert 'my-calendar-name' == key

    # Migrate legacy msgraph without namespace
    migrated = uu.migrate_legacy_uri('msgraph://activity-archive')
    assert migrated == 'msgraph://calendars/activity-archive'

    migrated_acc = uu.migrate_legacy_uri('msgraph://activity-archive', account='me@example.com')
    assert migrated_acc.startswith('msgraph://me@example.com/')

    # local:// migration
    mloc = uu.migrate_legacy_uri('local://archive')
    assert mloc.startswith('local://calendars/')


def test_validate_uri_components_and_primary_and_conversions():
    assert uu.validate_uri_components('msgraph', 'calendars', 'primary') is True
    with pytest.raises(uu.URIValidationError):
        uu.validate_uri_components('', 'calendars')
    with pytest.raises(uu.URIValidationError):
        uu.validate_uri_components('msgraph', 'unknown')

    assert uu.get_primary_calendar_uri() == 'msgraph://calendars/primary'
    assert uu.get_primary_calendar_uri(account='bob@x.com') == 'msgraph://bob@x.com/calendars/primary'

    # convert encoded <-> friendly roundtrip
    original = 'msgraph://calendars/"Activity Archive"'
    encoded = uu.convert_uri_to_encoded(original)
    friendly = uu.convert_uri_to_user_friendly(encoded)
    assert 'Activity Archive' in friendly


def test_parse_resource_uri_errors():
    with pytest.raises(uu.URIParseError):
        uu.parse_resource_uri('noscheme')
    with pytest.raises(uu.URIParseError):
        uu.parse_resource_uri('msgraph:///')


