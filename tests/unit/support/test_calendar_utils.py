import json
from datetime import date
from pathlib import Path

import pytest

from support.calendar_utils import load_events_from_file, get_event_date_range


def test_load_events_from_file_success(tmp_path):
    events = [
        {
            "id": "1",
            "subject": "Meeting",
            "start": {"dateTime": "2025-10-18T09:00:00Z"},
            "end": {"dateTime": "2025-10-18T10:00:00Z"},
        },
        {
            "id": "2",
            "subject": "Another",
            "start": {"dateTime": "2025-10-19T12:30:00+00:00"},
            "end": {"dateTime": "2025-10-19T13:00:00+00:00"},
        },
    ]
    p = tmp_path / "events.json"
    p.write_text(json.dumps(events), encoding="utf-8")

    loaded = load_events_from_file(str(p))
    assert isinstance(loaded, list)
    assert loaded == events


def test_load_events_from_file_missing(tmp_path):
    missing = tmp_path / "nope.json"
    with pytest.raises(FileNotFoundError):
        load_events_from_file(str(missing))


def test_load_events_from_file_invalid_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json}", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load_events_from_file(str(p))


def test_get_event_date_range_parses_and_handles_z_suffix():
    events = [
        {
            "start": {"dateTime": "2025-10-18T09:00:00Z"},
            "end": {"dateTime": "2025-10-18T10:00:00Z"},
        },
        {
            "start": {"dateTime": "2025-10-19T23:59:59+00:00"},
            "end": {"dateTime": "2025-10-20T00:15:00+00:00"},
        },
    ]
    rng = get_event_date_range(events)
    assert rng is not None
    start, end = rng
    assert start == date(2025, 10, 18)
    assert end == date(2025, 10, 20)


def test_get_event_date_range_ignores_invalid_entries():
    events = [
        {"start": {"dateTime": "not-a-date"}, "end": {"dateTime": None}},
        {"start": {}, "end": {}},
        {},
    ]
    assert get_event_date_range(events) is None


def test_get_event_date_range_mixed_valid_and_invalid():
    events = [
        {"start": {"dateTime": "2025-01-01T00:00:00Z"}},
        {"end": {"dateTime": "2025-01-10T12:00:00+00:00"}},
        {"start": {"dateTime": "bad"}, "end": {"dateTime": "worse"}},
    ]
    rng = get_event_date_range(events)
    assert rng == (date(2025, 1, 1), date(2025, 1, 10))


def test_get_event_date_range_from_real_world_sample():
    sample_path = Path("tests/data/ms365_calendar_sample.json")
    assert sample_path.exists(), f"Sample file not found: {sample_path}"
    events = load_events_from_file(str(sample_path))

    rng = get_event_date_range(events)
    assert rng is not None
    start, end = rng
    # The sample contains events on 2025-05-21 (including overlaps/duplicates)
    assert start == date(2025, 5, 21)
    assert end == date(2025, 5, 21)


def test_get_event_date_range_empty_returns_none():
    assert get_event_date_range([]) is None
