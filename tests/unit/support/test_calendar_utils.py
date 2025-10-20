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
    # The sample includes active events on 2025-05-21 and 2025-05-22 (cancelled/free entries are ignored)
    assert start == date(2025, 5, 21)
    assert end == date(2025, 5, 22)


def test_get_event_date_range_empty_returns_none():
    assert get_event_date_range([]) is None


@pytest.mark.parametrize(
    "filename, expected_start, expected_end",
    [
        ("ms365_calendar_overlaps.json", date(2025, 5, 21), date(2025, 5, 21)),
        ("ms365_calendar_duplicates.json", date(2025, 5, 21), date(2025, 5, 21)),
        ("ms365_calendar_recurring.json", date(2025, 6, 1), date(2025, 6, 1)),
        ("ms365_calendar_success.json", date(2025, 5, 22), date(2025, 5, 22)),
        ("ms365_calendar_timezone.json", date(2025, 6, 1), date(2025, 6, 1)),
    ],
)
def test_get_event_date_range_real_world_parametrized(filename: str, expected_start: date, expected_end: date):
    sample_path = Path("tests/data") / filename
    assert sample_path.exists(), f"Sample file not found: {sample_path}"

    events = load_events_from_file(str(sample_path))
    rng = get_event_date_range(events)
    assert rng is not None
    start, end = rng
    assert start == expected_start
    assert end == expected_end


@pytest.mark.parametrize("sample_path", sorted((Path("tests/data").glob("*.json"))), ids=lambda p: p.name)
def test_get_event_date_range_glob_all_samples(sample_path: Path):
    assert sample_path.exists(), f"Sample file not found: {sample_path}"
    events = load_events_from_file(str(sample_path))

    # Skip if file content is not a list of events
    if not isinstance(events, list):
        pytest.skip(f"Skipping {sample_path.name}: unexpected JSON structure (not a list)")

    rng = get_event_date_range(events)
    if rng is None:
        pytest.skip(f"Skipping {sample_path.name}: no parseable start/end dateTime fields found")

    start, end = rng
    # Basic sanity: start/end should be date objects and ordered
    assert isinstance(start, date) and isinstance(end, date)
    assert start <= end, f"Invalid range in {sample_path.name}: {start} > {end}"
