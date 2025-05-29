import pytest
from datetime import datetime, UTC
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.models.user import User
from core.models.appointment import Appointment
from core.models.location import Location
from core.models.category import Category
from core.models.timesheet import Timesheet
from core.db import Base
from core.repositories.factory import AppointmentRepositoryFactory
from unittest.mock import MagicMock, AsyncMock

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

@pytest.fixture
def sqlalchemy_repo(db_session, user):
    calendar_id = 'test-calendar-id'
    repo = AppointmentRepositoryFactory.create('sqlalchemy', session=db_session, user=user, calendar_id=calendar_id)
    return repo

@pytest.fixture
def client():
    mock = MagicMock()
    # Setup nested async mocks for events
    calendar = MagicMock()
    events = MagicMock()
    events.post = AsyncMock()
    events.get = AsyncMock()
    # by_event_id returns an object with patch, delete, get as AsyncMock
    by_event_id_mock = MagicMock()
    by_event_id_mock.patch = AsyncMock()
    by_event_id_mock.delete = AsyncMock()
    by_event_id_mock.get = AsyncMock()
    events.by_event_id = MagicMock(return_value=by_event_id_mock)
    calendar.events = events
    # calendar_view for alist_for_user
    calendar_view = MagicMock()
    calendar_view.with_url = MagicMock(return_value=MagicMock(get=AsyncMock()))
    calendar.calendar_view = calendar_view
    mock.users.by_user_id.return_value.calendars.by_calendar_id.return_value = calendar
    mock.users.by_user_id.return_value.calendar = calendar
    return mock

@pytest.fixture
def msgraph_repo(client, user):
    calendar_id = 'test-calendar-id'
    repo = AppointmentRepositoryFactory.create('msgraph', msgraph_client=client, user=user, calendar_id=calendar_id)
    return repo

@pytest.fixture
def appointment(user):
    appt = Appointment(
        user_id=user.id,
        subject="Repo Test",
        start_time=datetime(2025, 6, 1, 9, 0, tzinfo=UTC),
        end_time=datetime(2025, 6, 1, 10, 0, tzinfo=UTC),
        calendar_id='test-calendar-id'
    )
    appt.is_archived = False
    return appt

def test_sqlalchemy_repo_crud(sqlalchemy_repo, db_session, appointment):
    # Add
    sqlalchemy_repo.add(appointment)
    assert appointment.id is not None
    # Get
    fetched = sqlalchemy_repo.get_by_id(appointment.id)
    assert fetched.subject == "Repo Test"
    # List
    results = sqlalchemy_repo.list_for_user()
    assert any(a.id == appointment.id for a in results)
    # Update
    appointment.subject = "Updated"
    sqlalchemy_repo.update(appointment)
    updated = sqlalchemy_repo.get_by_id(appointment.id)
    assert updated.subject == "Updated"
    # Delete
    sqlalchemy_repo.delete(appointment.id)
    assert sqlalchemy_repo.get_by_id(appointment.id) is None

def test_msgraph_repo_crud(msgraph_repo, appointment):
    repo = msgraph_repo
    client = repo.client
    # Patch both possible .events.post call chains with AsyncMock
    by_cal_post = client.users.by_user_id.return_value.calendars.by_calendar_id.return_value.events.post = AsyncMock()
    cal_post = client.users.by_user_id.return_value.calendar.events.post = AsyncMock()
    # Add
    repo.add(appointment)
    assert by_cal_post.called or cal_post.called
    # Get
    # Create a mock event object with MS Graph fields
    mock_event = MagicMock()
    mock_event.id = "1"
    mock_event.subject = appointment.subject
    mock_event.start = {'dateTime': appointment.start_time.isoformat(), 'timeZone': 'UTC'}
    mock_event.end = {'dateTime': appointment.end_time.isoformat(), 'timeZone': 'UTC'}
    # Patch the correct get method to return the mock event
    client.users.by_user_id.return_value.calendars.by_calendar_id.return_value.events.by_event_id.return_value.get = AsyncMock(return_value=mock_event)
    client.users.by_user_id.return_value.calendar.events.by_event_id.return_value.get = AsyncMock(return_value=mock_event)
    fetched = repo.get_by_id("1")
    assert fetched.subject == appointment.subject
    # List
    mock_events_page = MagicMock()
    mock_events_page.value = [mock_event]
    client.users.by_user_id.return_value.calendars.by_calendar_id.return_value.events.get = AsyncMock(return_value=mock_events_page)
    client.users.by_user_id.return_value.calendar.events.get = AsyncMock(return_value=mock_events_page)
    results = repo.list_for_user()
    assert any(a.subject == appointment.subject for a in results)
    # Update
    appointment.ms_event_id = "1"
    by_cal_patch = client.users.by_user_id.return_value.calendars.by_calendar_id.return_value.events.by_event_id.return_value.patch = AsyncMock()
    cal_patch = client.users.by_user_id.return_value.calendar.events.by_event_id.return_value.patch = AsyncMock()
    repo.update(appointment)
    assert by_cal_patch.called or cal_patch.called
    # Delete
    by_cal_delete = client.users.by_user_id.return_value.calendars.by_calendar_id.return_value.events.by_event_id.return_value.delete = AsyncMock()
    cal_delete = client.users.by_user_id.return_value.calendar.events.by_event_id.return_value.delete = AsyncMock()
    repo.delete("1")
    assert by_cal_delete.called or cal_delete.called 