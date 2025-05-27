import os
import json
from datetime import datetime, timedelta, UTC
import pytest
from flask import Flask
from app import create_app, db
from app.models import User, Appointment
from core.services.calendar_fetch_service import fetch_appointments
from core.services.calendar_archive_service import archive_appointments
import pytz

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), '../data')

def load_appointments(filename):
    path = os.path.join(TEST_DATA_DIR, filename)
    with open(path, 'r') as f:
        data = json.load(f)
    # Convert start/end to datetime objects, preserve recurrence
    for appt in data:
        # Support both short and full real entries
        if 'start' in appt and isinstance(appt['start'], dict):
            start = appt['start']
            end = appt['end']
            tz = pytz.timezone(start.get('timeZone', 'UTC'))
            appt['start'] = tz.localize(datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00')))
            appt['end'] = tz.localize(datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00')))
            appt['recurrence'] = appt.get('recurrence')
        else:
            # fallback for legacy short format
            appt['start'] = appt['start']
            appt['end'] = appt['end']
            appt['recurrence'] = appt.get('recurrence')
    return data

@pytest.fixture(scope="function")
def app_context():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    with app.app_context():
        db.create_all()
        user = User()
        user.email = "testuser@example.com"
        user.name = "Test User"
        db.session.add(user)
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def user(app_context):
    return User.query.first()

def test_archive_appointments_success(app_context, user):
    appts = load_appointments('ms365_calendar_success.json')
    start_date = appts[0]['start'].date()
    end_date = appts[0]['end'].date()
    result = archive_appointments(user, appts, start_date, end_date, db.session)
    assert result["archived"] == 1
    archived = Appointment.query.filter_by(user_id=user.id).first()
    assert archived is not None
    assert archived.subject == "Team Sync"
    assert archived.is_archived

def test_archive_appointments_merges_duplicates(app_context, user):
    appts = load_appointments('ms365_calendar_duplicates.json')
    start_date = appts[0]['start'].date()
    end_date = appts[0]['end'].date()
    result = archive_appointments(user, appts, start_date, end_date, db.session)
    assert result["archived"] == 1
    archived = Appointment.query.filter_by(user_id=user.id).all()
    assert len(archived) == 1

def test_archive_appointments_detects_overlaps(app_context, user):
    appts = load_appointments('ms365_calendar_overlaps.json')
    start_date = appts[0]['start'].date()
    end_date = appts[0]['end'].date()
    result = archive_appointments(user, appts, start_date, end_date, db.session)
    assert result["status"] == "overlap"
    assert "conflicts" in result
    assert len(result["conflicts"]) == 1
    assert len(result["conflicts"][0]) == 2

def test_archive_appointments_expands_recurring(app_context, user):
    appts = load_appointments('ms365_calendar_recurring.json')
    start_date = appts[0]['start'].date()
    end_date = start_date + timedelta(days=2)
    result = archive_appointments(user, appts, start_date, end_date, db.session)
    assert result["archived"] == 3
    archived = Appointment.query.filter_by(user_id=user.id).all()
    assert len(archived) == 3
    for a in archived:
        assert a.subject == "Daily Standup"

def test_archive_appointments_handles_partial_failure(app_context, user, monkeypatch):
    appts = load_appointments('ms365_calendar_success.json')
    start_date = appts[0]['start'].date()
    end_date = appts[0]['end'].date()
    def fail_commit():
        raise Exception("DB commit failed")
    monkeypatch.setattr(db.session, "commit", fail_commit)
    result = archive_appointments(user, appts, start_date, end_date, db.session)
    assert "DB commit failed" in result["errors"][0]

def test_archive_appointments_time_zone_conversion(app_context, user):
    appts = load_appointments('ms365_calendar_timezone.json')
    start_date = appts[0]['start'].date()
    end_date = appts[0]['end'].date()
    result = archive_appointments(user, appts, start_date, end_date, db.session)
    archived = Appointment.query.filter_by(user_id=user.id).first()
    assert archived is not None
    # Should be stored in UTC
    engine_name = db.engine.name
    if engine_name == 'sqlite':
        # SQLite does not preserve tzinfo, so just check the value
        assert archived.start_time == datetime(2025, 6, 1, 13, 0)
    else:
        assert archived.start_time.tzinfo is not None
        assert archived.start_time.utcoffset() == timedelta(0)

@pytest.mark.skipif(not os.getenv('RUN_REAL_MS365_TESTS'), reason="Real MS365 test skipped unless RUN_REAL_MS365_TESTS is set.")
def test_fetch_and_save_ms365_calendar_data(app_context, user, monkeypatch):
    from core.services.calendar_fetch_service import fetch_appointments
    import types
    class MockSession:
        def get(self, endpoint, params=None):
            class Response:
                def raise_for_status(self): pass
                def json(self): return {'value': []}
            return Response()
    msgraph_session = MockSession()
    start_date = datetime.now(UTC).date()
    end_date = start_date
    result = fetch_appointments(user, start_date, end_date, msgraph_session)
    assert isinstance(result, list)
        