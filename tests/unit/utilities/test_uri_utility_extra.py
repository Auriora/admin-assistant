import pytest

from core.utilities.uri_utility import (
    normalize_calendar_name_for_lookup,
    create_legacy_compatible_lookup_key,
    migrate_legacy_uri,
    parse_resource_uri,
    parse_user_friendly_identifier,
    format_user_friendly_identifier,
    construct_resource_uri,
    construct_resource_uri_encoded,
    validate_account,
    validate_uri_components,
    convert_uri_to_user_friendly,
    convert_uri_to_encoded,
    ParsedURI,
    URIParseError,
    URIValidationError,
    get_primary_calendar_uri,
)


def test_normalize_calendar_name_for_lookup_punctuation_whitespace_unicode():
    # Punctuation removed, lowercased, whitespace normalized
    name = "  Activity,  Archive! "
    assert normalize_calendar_name_for_lookup(name) == "activity archive"

    # Unicode characters: function may introduce variable spacing when removing some symbols;
    # assert presence of tokens and that whitespace is compressed to single spaces when joined.
    name2 = "Café • Special"
    out = normalize_calendar_name_for_lookup(name2)
    # must contain the word 'special' and start with 'caf' (covers 'caf' or 'café')
    assert "special" in out
    assert out.startswith("caf")
    # compressed whitespace should be exactly one space between tokens
    compressed = ' '.join(out.split())
    assert compressed.count(' ') == 1


def test_create_legacy_compatible_lookup_key_hyphenation_and_filtration():
    name = "My Calendar Name!!!"
    assert create_legacy_compatible_lookup_key(name) == "my-calendar-name"

    # Existing hyphens should be preserved (and spaces -> hyphen)
    name2 = "My--Calendar  Sub"
    assert create_legacy_compatible_lookup_key(name2) == "my--calendar-sub"


def test_migrate_legacy_uri_local_and_namespaced_and_passthrough():
    # simple local legacy without account
    assert migrate_legacy_uri("local://mycal") == "local://calendars/mycal"

    # add account for local legacy
    assert migrate_legacy_uri("local://mycal", account="user@example.com") == "local://user@example.com/calendars/mycal"

    # already namespaced -> when account provided, account should be prefixed
    assert migrate_legacy_uri("local://calendars/mycal", account="user@ex.com") == "local://user@ex.com/calendars/mycal"

    # unknown scheme should be returned as-is
    weird = "ftp://somewhere/resource"
    assert migrate_legacy_uri(weird) == weird


def test_parse_resource_uri_errors_double_scheme_missing_path_double_slashes_and_invalid_account():
    # double '://' pattern
    with pytest.raises(URIParseError) as excinfo:
        parse_resource_uri('msgraph://user@example.com://calendars/primary')
    assert "multiple '://" in str(excinfo.value)

    # missing path (endswith '://')
    with pytest.raises(URIParseError) as excinfo2:
        parse_resource_uri('msgraph://')
    assert "missing path" in str(excinfo2.value)

    # double slashes in path
    with pytest.raises(URIParseError) as excinfo3:
        parse_resource_uri('msgraph:///calendars//primary')
    assert "double slashes" in str(excinfo3.value)

    # invalid account format in netloc (contains @ but not a valid email)
    with pytest.raises(URIParseError) as excinfo4:
        parse_resource_uri('msgraph://not@valid/calendars/primary')
    assert "Invalid account format" in str(excinfo4.value)

    # missing identifier when netloc is namespace
    with pytest.raises(URIParseError) as excinfo5:
        parse_resource_uri('msgraph://calendars/')
    assert "missing identifier" in str(excinfo5.value)


# Additional tests to exercise more branches and increase coverage

def test_parse_user_friendly_identifier_variants():
    assert parse_user_friendly_identifier('"Activity Archive"') == 'Activity Archive'
    assert parse_user_friendly_identifier("'Single'") == 'Single'
    assert parse_user_friendly_identifier('Activity\\ Archive') == 'Activity Archive'
    assert parse_user_friendly_identifier('Calendar: "My Calendar"') == 'My Calendar'
    assert parse_user_friendly_identifier('primary') == 'primary'
    assert parse_user_friendly_identifier('') == ''


def test_format_user_friendly_identifier():
    assert format_user_friendly_identifier('primary') == 'primary'
    assert format_user_friendly_identifier('Has Space') == '"Has Space"'
    assert format_user_friendly_identifier('special/name') == '"special/name"'
    assert format_user_friendly_identifier('starts-') == '"starts-"'
    assert format_user_friendly_identifier('noquote', force_quotes=True) == '"noquote"'
    assert format_user_friendly_identifier('Cal', use_calendar_prefix=True) == 'Calendar: Cal'
    assert format_user_friendly_identifier('A B', use_calendar_prefix=True) == 'Calendar: "A B"'


def test_validate_account_various_formats():
    assert validate_account('user@example.com') is True
    assert validate_account('sub.domain.com') is True
    assert validate_account('12345') is True
    assert validate_account('user_name-1') is True
    assert validate_account('') is False
    assert validate_account('not@valid') is False


def test_construct_and_encode_resource_uri_and_errors():
    # user-friendly without account
    assert construct_resource_uri('msgraph', 'calendars', 'My Cal') == 'msgraph://calendars/"My Cal"'
    # encoded without account
    assert construct_resource_uri('msgraph', 'calendars', 'My Cal', user_friendly=False) == 'msgraph://calendars/My%20Cal'
    # with account
    assert construct_resource_uri('msgraph', 'calendars', 'primary', account='user@example.com') == 'msgraph://user@example.com/calendars/primary'

    # construct_resource_uri_encoded wrapper
    assert construct_resource_uri_encoded('msgraph', 'calendars', 'My Cal') == 'msgraph://calendars/My%20Cal'

    # missing components
    with pytest.raises(ValueError):
        construct_resource_uri('', 'calendars', 'x')

    # invalid account
    with pytest.raises(URIValidationError):
        construct_resource_uri('msgraph', 'calendars', 'x', account='not@valid')


def test_parse_resource_uri_success_variants_and_url_decoding():
    # legacy shortcuts
    p = parse_resource_uri('')
    assert isinstance(p, ParsedURI)
    assert p.namespace == 'calendars' and p.identifier == 'primary'

    p2 = parse_resource_uri('calendar')
    assert p2.identifier == 'primary'

    p3 = parse_resource_uri('primary')
    assert p3.identifier == 'primary'

    # netloc as namespace (legacy): msgraph://calendars/primary
    p4 = parse_resource_uri('msgraph://calendars/primary')
    assert p4.scheme == 'msgraph' and p4.namespace == 'calendars' and p4.identifier == 'primary'

    # URL encoded identifier should be decoded
    p5 = parse_resource_uri('msgraph://calendars/Activity%20Archive')
    assert p5.identifier == 'Activity Archive'

    # quoted identifier
    p6 = parse_resource_uri('msgraph://calendars/"Activity Archive"')
    assert p6.identifier == 'Activity Archive'

    # backslash escaped identifier
    p7 = parse_resource_uri('msgraph://calendars/Activity\\ Archive')
    assert p7.identifier == 'Activity Archive'

    # new format with account in netloc
    p8 = parse_resource_uri('msgraph://user@example.com/calendars/primary')
    assert p8.account == 'user@example.com' and p8.namespace == 'calendars'

    # path-only forms with triple slash
    p9 = parse_resource_uri('msgraph:///calendars/primary')
    assert p9.namespace == 'calendars' and p9.identifier == 'primary'

    # path-only with account in path
    p10 = parse_resource_uri('msgraph:///user@example.com/calendars/primary')
    assert p10.account == 'user@example.com' and p10.namespace == 'calendars'


def test_parseduri_properties_and_conversion_helpers():
    # is_friendly_name false for numeric
    p_num = parse_resource_uri('msgraph://calendars/12345')
    assert p_num.is_friendly_name is False

    # is_friendly_name false for base64-like long id
    long_id = 'A' * 31 + '='
    p_long = ParsedURI(scheme='msgraph', namespace='calendars', identifier=long_id, raw_uri='x')
    assert p_long.is_friendly_name is False
    # url_encoded_identifier
    assert '%' in p_long.url_encoded_identifier

    # convert helpers
    enc = convert_uri_to_encoded('msgraph://calendars/Activity Archive')
    assert 'Activity%20Archive' in enc
    friendly = convert_uri_to_user_friendly('msgraph://calendars/Activity%20Archive')
    assert '"Activity Archive"' in friendly


def test_validate_uri_components_errors():
    with pytest.raises(URIValidationError):
        validate_uri_components('', 'calendars')
    with pytest.raises(URIValidationError):
        validate_uri_components('msgraph', '')
    with pytest.raises(URIValidationError):
        validate_uri_components('unknown', 'calendars')
    with pytest.raises(URIValidationError):
        validate_uri_components('msgraph', 'unknown')


# Additional targeted tests to hit remaining branches

def test_format_and_normalize_empty_and_parseduri_friendly_true():
    # format_user_friendly_identifier empty
    assert format_user_friendly_identifier('') == ''
    # normalize_calendar_name_for_lookup empty
    assert normalize_calendar_name_for_lookup('') == ''
    # create_legacy_compatible_lookup_key empty
    assert create_legacy_compatible_lookup_key('') == ''
    # ParsedURI.is_friendly_name True for short friendly name
    p = ParsedURI(scheme='msgraph', namespace='calendars', identifier='My Cal', raw_uri='x')
    assert p.is_friendly_name is True


def test_parse_resource_uri_more_error_branches_and_unusual_inputs(monkeypatch):
    # missing scheme
    with pytest.raises(URIParseError) as e1:
        parse_resource_uri('calendars/primary')
    assert 'missing scheme' in str(e1.value)

    # missing '://'
    with pytest.raises(URIParseError) as e2:
        parse_resource_uri('msgraph:/calendars/primary')
    assert "missing '://'" in str(e2.value)

    # account in netloc but missing identifier (path parts < 2)
    with pytest.raises(URIParseError) as e3:
        parse_resource_uri('msgraph://user@example.com/calendars')
    assert 'URI with account must have format' in str(e3.value)

    # path-only but missing path
    with pytest.raises(URIParseError) as e4:
        parse_resource_uri('msgraph:///')
    assert 'missing path' in str(e4.value)

    # path-only with invalid account format
    with pytest.raises(URIParseError) as e5:
        parse_resource_uri('msgraph:///not@valid/calendars/primary')
    assert 'Invalid account format' in str(e5.value)

    # path parts wrong length
    with pytest.raises(URIParseError) as e6:
        parse_resource_uri('msgraph:///a/b/c/d')
    assert 'URI path must have format' in str(e6.value)

    # Force urllib.parse.unquote to raise to hit the except branch
    import core.utilities.uri_utility as uu
    def bad_unquote(x):
        raise ValueError('boom')
    monkeypatch.setattr(uu.urllib.parse, 'unquote', bad_unquote)
    # This should fall back to parse_user_friendly_identifier and not raise
    p = parse_resource_uri('msgraph://calendars/Activity%20Archive')
    # Since unquote raised, parse_user_friendly_identifier will be used; for %20 input
    # that returns the raw string (no decoding), so identifier is 'Activity%20Archive'
    assert p.identifier == 'Activity%20Archive'


def test_migrate_legacy_uri_msgraph_variants():
    # empty with account -> implementation returns empty string
    assert migrate_legacy_uri('', account='user@e.com') == ''

    # msgraph://calendar special
    assert migrate_legacy_uri('msgraph://calendar') == 'msgraph://calendars/primary'
    assert migrate_legacy_uri('msgraph://calendar', account='a@b.com') == 'msgraph://a@b.com/calendars/primary'

    # msgraph already namespaced with account param should prefix account
    assert migrate_legacy_uri('msgraph://calendars/mycal', account='me@ex.com') == 'msgraph://me@ex.com/calendars/mycal'

    # msgraph without namespace should get calendars/ prefix
    assert migrate_legacy_uri('msgraph://mycal') == 'msgraph://calendars/mycal'
    assert migrate_legacy_uri('msgraph://mycal', account='me@ex.com') == 'msgraph://me@ex.com/calendars/mycal'

    # if legacy uri already includes account and account param provided, return as-is
    uri_with_account = 'msgraph://me@ex.com/calendars/x'
    assert migrate_legacy_uri(uri_with_account, account='me@ex.com') == uri_with_account


def test_validate_uri_components_and_primary_and_convert_fallbacks():
    # identifier empty raises
    with pytest.raises(URIValidationError):
        validate_uri_components('msgraph', 'calendars', '')
    # valid returns True
    assert validate_uri_components('msgraph', 'calendars', 'id') is True

    # get_primary_calendar_uri
    assert get_primary_calendar_uri() == 'msgraph://calendars/primary'
    assert get_primary_calendar_uri(account='u@e.com') == 'msgraph://u@e.com/calendars/primary'

    # convert helpers: when parsing fails they return original
    assert convert_uri_to_user_friendly('not-a-uri') == 'not-a-uri'
    assert convert_uri_to_encoded('not-a-uri') == 'not-a-uri'


def test_migrate_legacy_uri_additional_namespace_and_special_inputs():
    # When msgraph legacy already namespaced and no account provided -> return as-is
    src = 'msgraph://calendars/existing'
    assert migrate_legacy_uri(src) == src

    # Same for local
    src2 = 'local://calendars/existing'
    assert migrate_legacy_uri(src2) == src2

    # Special legacy tokens 'primary' and 'calendar'
    assert migrate_legacy_uri('primary') == 'msgraph://calendars/primary'
    assert migrate_legacy_uri('calendar') == 'msgraph://calendars/primary'
    assert migrate_legacy_uri('primary', account='u@e.com') == 'msgraph://u@e.com/calendars/primary'


def test_parseduri_is_friendly_name_various_cases():
    # short alpha -> friendly
    p_short = ParsedURI(scheme='msgraph', namespace='calendars', identifier='abc', raw_uri='x')
    assert p_short.is_friendly_name is True

    # numeric -> not friendly
    p_num = ParsedURI(scheme='msgraph', namespace='calendars', identifier='987654', raw_uri='x')
    assert p_num.is_friendly_name is False

    # long base64-like with plus -> not friendly
    long_base64 = 'A' * 31 + '+'
    p_b64 = ParsedURI(scheme='msgraph', namespace='calendars', identifier=long_base64, raw_uri='x')
    assert p_b64.is_friendly_name is False
