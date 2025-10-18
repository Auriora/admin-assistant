import pytest

from core.repositories.factory import AppointmentRepositoryFactory, get_appointment_repository


class DummyUser:
    def __init__(self, id=1):
        self.id = id


def test_factory_create_requires_calendar_id():
    with pytest.raises(ValueError):
        AppointmentRepositoryFactory.create('sqlalchemy')


def test_factory_unknown_backend_raises():
    with pytest.raises(ValueError):
        AppointmentRepositoryFactory.create('unknown', calendar_id='cal-1')


def test_get_appointment_repository_use_mock_requires_mock_data():
    user = DummyUser()
    with pytest.raises(ValueError):
        get_appointment_repository(user, calendar_id='cal-1', use_mock=True, mock_data=None)


def test_get_appointment_repository_requires_graph_client_if_no_session_and_not_mock():
    user = DummyUser()
    with pytest.raises(ValueError):
        # not providing session or mock_data should raise about graph_client
        get_appointment_repository(user, calendar_id='cal-1')

