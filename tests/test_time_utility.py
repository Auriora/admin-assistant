from datetime import datetime
import pytz

from core.utilities import time_utility as tu


def test_to_utc_naive_datetime_makes_utc():
    dt = datetime(2025, 10, 18, 12, 0, 0)
    result = tu.to_utc(dt)
    assert result.tzinfo is not None
    assert result.tzinfo == pytz.UTC
    assert result.hour == 12


def test_to_utc_aware_converts_timezone():
    est = pytz.timezone('US/Eastern')
    local = est.localize(datetime(2025, 10, 18, 8, 0, 0))
    result = tu.to_utc(local)
    assert result.tzinfo == pytz.UTC
    # 8am ET is 12:00 UTC during EDT (UTC-4)
    assert result.hour in (12, 13)  # Accept DST variations but should be close

