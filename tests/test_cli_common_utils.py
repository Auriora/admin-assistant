import locale
from datetime import date
from types import SimpleNamespace

from core.cli.common import utils as cu


def test_get_week_start_day_with_us_locale(monkeypatch):
    # Simulate US locale
    monkeypatch.setattr('locale.getlocale', lambda: ('en_US', 'UTF-8'))
    assert cu.get_week_start_day() == 6  # Sunday

    # Non-US locale
    monkeypatch.setattr('locale.getlocale', lambda: ('en_GB', 'UTF-8'))
    assert cu.get_week_start_day() == 0  # Monday


def test_get_last_month_and_week_ranges():
    # Use a fixed reference date to verify ranges
    ref = date(2025, 10, 15)  # a Wednesday

    # Week start: default implementation uses locale; force Monday (0)
    monkeypatch_target = 'core.cli.common.utils.get_week_start_day'

    # If week starts Monday
    original = cu.get_week_start_day
    cu.get_week_start_day = lambda: 0
    wk_start, wk_end = cu.get_last_week_range(reference_date=ref)
    # Previous week Monday-Sunday before the week containing ref (ref week start is 2025-10-13), previous is 06-10 to 12-10
    assert wk_start == date(2025, 10, 6)
    assert wk_end == date(2025, 10, 12)

    # Restore
    cu.get_week_start_day = original

    # Last month
    lm_start, lm_end = cu.get_last_month_range(reference_date=ref)
    assert lm_start == date(2025, 9, 1)
    assert lm_end == date(2025, 9, 30)


def test_parse_flexible_date_and_range():
    # explicit day-month-year
    d = cu.parse_flexible_date('31-12-2024')
    assert d == date(2024, 12, 31)

    # day-month short name and no year (defaults to current year) - ensure format works
    dt = cu.parse_flexible_date('1-Oct')
    assert isinstance(dt, date)

    # ISO date
    iso = cu.parse_flexible_date('2025-10-18')
    assert iso == date(2025, 10, 18)

    # range parsing
    start, end = cu.parse_date_range('01-10-2025 to 03-10-2025')
    assert start == date(2025, 10, 1)
    assert end == date(2025, 10, 3)


def test_account_context_and_uri_helpers(monkeypatch):
    # get_account_context_for_user
    user = SimpleNamespace(id=5, username='bob', email='bob@example.com')
    assert cu.get_account_context_for_user(user) == 'bob@example.com'

    # Fallback to username
    user2 = SimpleNamespace(id=6, username='alice', email='')
    assert cu.get_account_context_for_user(user2) == 'alice'

    # Last resort -> id
    user3 = SimpleNamespace(id=7, username='', email='')
    assert cu.get_account_context_for_user(user3) == '7'

    # suggest_uri_with_account_context: when parsed has account already -> return original
    parsed_with_account = SimpleNamespace(scheme='msgraph', namespace='calendars', identifier='id', account='acct')
    monkeypatch.setattr('core.cli.common.utils.parse_resource_uri', lambda u: parsed_with_account)
    assert cu.suggest_uri_with_account_context('msgraph://calendars/primary', user) == 'msgraph://calendars/primary'

    # When no account present, construct_resource_uri should be called
    parsed_no_account = SimpleNamespace(scheme='msgraph', namespace='calendars', identifier='primary', account='')
    monkeypatch.setattr('core.cli.common.utils.parse_resource_uri', lambda u: parsed_no_account)
    monkeypatch.setattr('core.cli.common.utils.construct_resource_uri', lambda scheme, namespace, identifier, user_friendly, account: f"{scheme}://{account}/{namespace}/{identifier}")
    suggested = cu.suggest_uri_with_account_context('msgraph://calendars/primary', user)
    assert 'bob@example.com' in suggested

    # validate_uri_account_context: matching email
    parsed_e = SimpleNamespace(account='bob@example.com')
    monkeypatch.setattr('core.cli.common.utils.parse_resource_uri', lambda u: parsed_e)
    ok, err = cu.validate_uri_account_context('msgraph://calendars/primary', user)
    assert ok is True and err is None

    # matching username
    parsed_u = SimpleNamespace(account='alice')
    monkeypatch.setattr('core.cli.common.utils.parse_resource_uri', lambda u: parsed_u)
    ok, err = cu.validate_uri_account_context('msgraph://calendars/primary', user2)
    assert ok is True and err is None

    # mismatch
    parsed_m = SimpleNamespace(account='other')
    monkeypatch.setattr('core.cli.common.utils.parse_resource_uri', lambda u: parsed_m)
    ok, err = cu.validate_uri_account_context('msgraph://calendars/primary', user)
    assert ok is False and err is not None

    # parse raises URIParseError
    class MyParseError(Exception):
        pass

    monkeypatch.setattr('core.cli.common.utils.parse_resource_uri', lambda u: (_ for _ in ()).throw(cu.URIParseError('bad')))
    ok, err = cu.validate_uri_account_context('bad', user)
    assert ok is False and 'Invalid URI format' in err


def test_get_uri_autocompletion_suggestions():
    user = SimpleNamespace(id=9, username='sam', email='sam@example.com')
    sug = cu.get_uri_autocompletion_suggestions(user)
    assert any('sam@example.com' in s for s in sug)
    assert any('calendars' in s for s in sug)

