from core.utilities import uri_utility as uu


def test_construct_resource_uri_and_encoded():
    # User-friendly with account
    uri = uu.construct_resource_uri('msgraph', 'calendars', 'My Cal', user_friendly=True, account='user@example.com')
    assert uri.startswith('msgraph://user@example.com/')
    assert 'My Cal' in uri or '"My Cal"' in uri

    # Encoded form
    enc = uu.construct_resource_uri('msgraph', 'calendars', 'My Cal', user_friendly=False, account='user@example.com')
    assert '%20' in enc

    # Without account (legacy)
    legacy = uu.construct_resource_uri('msgraph', 'calendars', 'primary', user_friendly=True, account=None)
    assert legacy == 'msgraph://calendars/primary'


def test_parse_resource_uri_with_account_and_encoded_identifier():
    parsed = uu.parse_resource_uri('msgraph://user@example.com/calendars/primary')
    assert parsed.account == 'user@example.com'
    assert parsed.namespace == 'calendars'
    assert parsed.identifier == 'primary'

    parsed2 = uu.parse_resource_uri('msgraph://calendars/Activity%20Archive')
    assert parsed2.account is None
    assert parsed2.identifier == 'Activity Archive'


def test_validate_uri_components_and_primary():
    # valid components
    assert uu.validate_uri_components('msgraph', 'calendars', 'primary') is True

    # invalid scheme
    try:
        uu.validate_uri_components('badscheme', 'calendars')
        raised = False
    except uu.URIValidationError:
        raised = True
    assert raised

    # invalid namespace
    try:
        uu.validate_uri_components('msgraph', 'not-a-namespace')
        raised = False
    except uu.URIValidationError:
        raised = True
    assert raised


def test_construct_resource_uri_encoded_helper_and_primary():
    enc = uu.construct_resource_uri_encoded('msgraph', 'calendars', 'My Cal', account=None)
    assert 'msgraph://calendars/' in enc
    assert '%20' in enc

    prim = uu.get_primary_calendar_uri('msgraph', account='user@example.com')
    assert prim == 'msgraph://user@example.com/calendars/primary'


def test_convert_uri_to_user_friendly_and_encoded_roundtrip():
    original = 'msgraph://calendars/Activity%20Archive'
    friendly = uu.convert_uri_to_user_friendly(original)
    assert 'Activity' in friendly
    encoded = uu.convert_uri_to_encoded(friendly)
    assert '%20' in encoded or 'Activity%20' in encoded

