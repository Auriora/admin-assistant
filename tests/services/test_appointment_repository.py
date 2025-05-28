import pytest
from datetime import datetime, UTC
from core.models.appointment import Appointment
from core.repositories.factory import AppointmentRepositoryFactory
from unittest.mock import MagicMock
from app import create_app, db
from app.models import User, Appointment as AppAppointment, Location, Category, Timesheet

@pytest.fixture(scope="function")
def app_context():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    with app.app_context():
        db.create_all()  # All tables (User, Appointment, Location, Category, Timesheet) will be created
        user = User()
        user.email = "testuser@example.com"
        user.name = "Test User"
        db.session.add(user)
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def db_session(app_context):
    return db.session

@pytest.fixture
def user(app_context):
    return User.query.first()

@pytest.fixture
def sqlalchemy_repo(db_session, user):
    # Use a test calendar_id for the test calendar
    calendar_id = 'test-calendar-id'
    repo = AppointmentRepositoryFactory.create('sqlalchemy', session=db_session, user=user, calendar_id=calendar_id)
    return repo

@pytest.fixture
def msgraph_repo(client, user):
    # Use a test calendar_id for the test calendar
    calendar_id = 'test-calendar-id'
    repo = AppointmentRepositoryFactory.create('msgraph', msgraph_client=client, user=user, calendar_id=calendar_id)
    return repo

@pytest.fixture
def appointment(user):
    return Appointment(
        user_id=user.id,
        subject="Repo Test",
        start_time=datetime(2025, 6, 1, 9, 0, tzinfo=UTC),
        end_time=datetime(2025, 6, 1, 10, 0, tzinfo=UTC),
        is_private=False,
        is_archived=False,
        is_out_of_office=False
    )

def test_sqlalchemy_repo_crud(sqlalchemy_repo, db_session, appointment):
    # Add
    sqlalchemy_repo.add(appointment)
    assert appointment.id is not None
    # Get
    fetched = sqlalchemy_repo.get_by_id(appointment.id)
    assert fetched.subject == "Repo Test"
    # List
    results = sqlalchemy_repo.list_for_user(appointment.user_id)
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
    repo, client = msgraph_repo
    # Add
    repo.add(appointment)
    client.create_event.assert_called_once()
    # Get
    client.get_event.return_value = {
        'id': 1,
        'user_id': appointment.user_id,
        'start_time': appointment.start_time,
        'end_time': appointment.end_time,
        'subject': appointment.subject,
        'is_private': appointment.is_private,
        'is_archived': appointment.is_archived,
        'is_out_of_office': appointment.is_out_of_office
    }
    fetched = repo.get_by_id(1)
    assert fetched.subject == appointment.subject
    # List
    client.list_events.return_value = ([client.get_event.return_value], 1)
    results = repo.list_for_user(appointment.user_id)
    assert any(a.subject == appointment.subject for a in results)
    # Update
    repo.update(appointment)
    client.update_event.assert_called_once()
    # Delete
    repo.delete(1)
    client.delete_event.assert_called_once_with(1) 