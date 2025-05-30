# DEPRECATED: All tests in this file referencing 'archive_appointments' are obsolete.
# The archiving workflow is now tested via CalendarArchiveOrchestrator in test_calendar_archive_orchestrator.py.
# These tests are commented out to avoid linter errors and confusion.
#
# If you need to test archiving, add new tests to test_calendar_archive_orchestrator.py using the orchestrator and mocks.

import os
import json
from datetime import datetime, timedelta, UTC, date
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.models.user import User
from core.models.appointment import Appointment
from core.db import Base
from core.utilities.time_utility import to_utc
from core.exceptions import CalendarServiceException

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), '../../data')

def load_appointments(filename, user_id):
    path = os.path.abspath(os.path.join(TEST_DATA_DIR, filename))
    with open(path, 'r') as f:
        data = json.load(f)
    appointments = []
    for appt in data:
        start = appt['start']
        end = appt['end']
        start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
        start_dt = to_utc(start_dt)
        end_dt = to_utc(end_dt)
        appointment = Appointment(
            user_id=user_id,
            subject=appt.get('subject', 'Test'),
            start_time=start_dt,
            end_time=end_dt,
            recurrence=appt.get('recurrence'),
            calendar_id=appt.get('calendar_id', 'test-calendar-id')
        )
        appointments.append(appointment)
    return appointments

@pytest.fixture(scope="function")
def db_session():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()

@pytest.fixture(scope="function")
def user(db_session):
    user = User(email="testuser@example.com", name="Test User")
    db_session.add(user)
    db_session.commit()
    return user

# pytest.skip("archive_appointments has been removed; tests need migration to new orchestrator workflow", allow_module_level=True)

# def test_archive_appointments_success(db_session, user):
#     appts = load_appointments('ms365_calendar_success.json', user.id)
#     start_date = appts[0].start_time.date()
#     end_date = appts[0].end_time.date()
#     result = archive_appointments(user, appts, start_date, end_date, db_session)
#     assert len(result["appointments"]) == 1
#     archived = db_session.query(Appointment).filter_by(user_id=user.id).first()
#     assert archived is not None
#     assert archived.subject == "Team Sync"
#     assert archived.is_archived

# def test_archive_appointments_merges_duplicates(db_session, user):
#     appts = load_appointments('ms365_calendar_duplicates.json', user.id)
#     start_date = appts[0].start_time.date()
#     end_date = appts[0].end_time.date()
#     result = archive_appointments(user, appts, start_date, end_date, db_session)
#     assert len(result["appointments"]) == 1
#     archived = db_session.query(Appointment).filter_by(user_id=user.id).all()
#     assert len(archived) == 1

# def test_archive_appointments_detects_overlaps(db_session, user):
#     appts = load_appointments('ms365_calendar_overlaps.json', user.id)
#     start_date = appts[0].start_time.date()
#     end_date = appts[0].end_time.date()
#     result = archive_appointments(user, appts, start_date, end_date, db_session)
#     assert result["status"] == "overlap"
#     assert "conflicts" in result
#     assert len(result["conflicts"]) == 1
#     assert len(result["conflicts"][0]) == 2

# def test_archive_appointments_expands_recurring(db_session, user):
#     appts = load_appointments('ms365_calendar_recurring.json', user.id)
#     start_date = appts[0].start_time.date()
#     end_date = start_date + timedelta(days=2)
#     result = archive_appointments(user, appts, start_date, end_date, db_session)
#     assert len(result["appointments"]) == 3
#     archived = db_session.query(Appointment).filter_by(user_id=user.id).all()
#     assert len(archived) == 3
#     for a in archived:
#         assert a.subject == "Daily Standup"

# def test_archive_appointments_handles_partial_failure(db_session, user, monkeypatch):
#     appts = load_appointments('ms365_calendar_success.json', user.id)
#     start_date = appts[0].start_time.date()
#     end_date = appts[0].end_time.date()
#     def fail_commit():
#         raise Exception("DB commit failed")
#     monkeypatch.setattr(db_session, "commit", fail_commit)
#     with pytest.raises(CalendarServiceException) as exc_info:
#         archive_appointments(user, appts, start_date, end_date, db_session)
#     assert "Failed to persist archived appointments" in str(exc_info.value)

# def test_archive_appointments_time_zone_conversion(db_session, user):
#     appts = load_appointments('ms365_calendar_timezone.json', user.id)
#     start_date = appts[0].start_time.date()
#     end_date = appts[0].end_time.date()
#     result = archive_appointments(user, appts, start_date, end_date, db_session)
#     archived = db_session.query(Appointment).filter_by(user_id=user.id).first()
#     assert archived is not None
#     # Should be stored in UTC
#     assert archived.start_time.tzinfo is not None
#     assert archived.start_time.utcoffset() == timedelta(0)
        