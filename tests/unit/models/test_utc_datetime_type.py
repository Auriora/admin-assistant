from datetime import datetime, timezone
from typing import cast

from sqlalchemy.engine.interfaces import Dialect
from core.models.appointment import UTCDateTime


def test_utcdatetime_bind_and_result_roundtrip():
    td = UTCDateTime()
    aware = datetime(2025, 10, 18, 12, 30, tzinfo=timezone.utc)
    dialect = cast(Dialect, None)
    bound = td.process_bind_param(aware, dialect=dialect)
    assert bound.tzinfo is None
    result = td.process_result_value(bound, dialect=dialect)
    assert result.tzinfo == timezone.utc
    assert result.year == aware.year and result.hour == aware.hour
