from core.repositories.factory import AppointmentRepositoryFactory, get_appointment_repository


class DummyRepo:
    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs


def test_create_sqlalchemy_returns_instance(monkeypatch):
    # Monkeypatch the concrete repository classes to simple dummies
    monkeypatch.setattr('core.repositories.factory.SQLAlchemyAppointmentRepository', DummyRepo)
    user = object()
    session = object()
    inst = AppointmentRepositoryFactory.create('sqlalchemy', calendar_id='cal-1', session=session, user=user)
    assert isinstance(inst, DummyRepo)


def test_create_msgraph_returns_instance(monkeypatch):
    monkeypatch.setattr('core.repositories.factory.MSGraphAppointmentRepository', DummyRepo)
    user = object()
    client = object()
    inst = AppointmentRepositoryFactory.create('msgraph', calendar_id='cal-1', msgraph_client=client, user=user)
    assert isinstance(inst, DummyRepo)


def test_get_appointment_repository_with_session_uses_sqlalchemy(monkeypatch):
    # ensure get_appointment_repository returns the SQLAlchemy repo when session passed
    monkeypatch.setattr('core.repositories.factory.SQLAlchemyAppointmentRepository', DummyRepo)
    user = object()
    session = object()
    inst = get_appointment_repository(user, calendar_id='cal-1', session=session)
    assert isinstance(inst, DummyRepo)

