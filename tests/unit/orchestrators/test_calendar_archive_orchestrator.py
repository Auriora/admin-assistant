import pytest
from datetime import datetime, date, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.models.appointment import Appointment, Base as AppointmentBase
from core.models.action_log import ActionLog, Base as ActionLogBase
from core.models.entity_association import EntityAssociation, Base as AssocBase
from core.orchestrators.calendar_archive_orchestrator import CalendarArchiveOrchestrator

# --- Mock MS Graph Repository ---
class MockMSGraphAppointmentRepository:
    def __init__(self, appointments=None):
        self._appointments = appointments or []
        self.added = []

    def list_for_user(self, start_date, end_date):
        return self._appointments

    def add(self, appointment):
        self.added.append(appointment)

# --- Fixtures for DB and User ---
@pytest.fixture(scope="function")
def db_session():
    engine = create_engine('sqlite:///:memory:')
    # Create all tables for all models
    AppointmentBase.metadata.create_all(engine)
    ActionLogBase.metadata.create_all(engine)
    AssocBase.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    sess = Session()
    yield sess
    sess.close()
    engine.dispose()

@pytest.fixture
def user():
    class User:
        id = 1
        email = "test@example.com"
    return User()

@pytest.fixture
def msgraph_client():
    # Not used in the mock, but required by the orchestrator signature
    return object()

# --- Test Data ---
def make_appointment(subject, start, end, ms_event_id=None):
    return Appointment(
        ms_event_id=ms_event_id,
        user_id=1,
        start_time=start,
        end_time=end,
        subject=subject,
        calendar_id="source"
    )

@pytest.fixture
def appointments():
    now = datetime.now(timezone.utc)
    # Two overlapping, one non-overlapping
    return [
        make_appointment("A", now, now + timedelta(hours=1), "evt1"),
        make_appointment("B", now + timedelta(minutes=30), now + timedelta(hours=1, minutes=30), "evt2"),
        make_appointment("C", now + timedelta(hours=2), now + timedelta(hours=3), "evt3"),
    ]

def make_duplicate_appointments():
    now = datetime.now(timezone.utc)
    # Two identical appointments (should be merged)
    return [
        make_appointment("D", now, now + timedelta(hours=1), "evt4"),
        make_appointment("D", now, now + timedelta(hours=1), "evt5"),
    ]

def make_recurring_appointments():
    now = datetime.now(timezone.utc)
    # Simulate recurring by providing three sequential appointments
    return [
        make_appointment("Daily Standup", now + timedelta(days=i), now + timedelta(days=i, hours=1), f"evt{i+10}")
        for i in range(3)
    ]

def make_timezone_appointment():
    # Appointment with explicit UTC offset
    start = datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)
    end = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    return [make_appointment("TZ Meeting", start, end, "evt100")]

# --- The Test ---
def test_archive_user_appointments(user, msgraph_client, db_session, appointments, monkeypatch):
    # Track the archive repo instance
    archive_repo_instance = {}
    def repo_factory(client, user_obj, calendar_id):
        if calendar_id == "source":
            return MockMSGraphAppointmentRepository(appointments)
        else:
            repo = MockMSGraphAppointmentRepository()
            archive_repo_instance['repo'] = repo
            return repo
    monkeypatch.setattr("core.orchestrators.calendar_archive_orchestrator.MSGraphAppointmentRepository", repo_factory)

    orchestrator = CalendarArchiveOrchestrator()
    result = orchestrator.archive_user_appointments(
        user=user,
        msgraph_client=msgraph_client,
        source_calendar_id="source",
        archive_calendar_id="archive",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=1),
        db_session=db_session,
        logger=None
    )

    # Only the non-overlapping appointment should be archived
    archive_repo = archive_repo_instance['repo']
    assert len(archive_repo.added) == 1
    assert archive_repo.added[0].subject == "C"

    # Overlaps should be logged in the DB
    logs = db_session.query(ActionLog).all()
    assert len(logs) == 2
    assert all(log.event_type == "overlap" for log in logs)

    # Associations should be created
    assocs = db_session.query(EntityAssociation).all()
    assert len(assocs) == 2
    assert all(assoc.source_type == "action_log" and assoc.target_type == "appointment" for assoc in assocs)

    # Result summary
    assert result["archived_count"] == 1
    assert result["overlap_count"] == 2
    assert result["errors"] == []

# --- Migrated General Case Tests ---
def test_archive_appointments_success(user, msgraph_client, db_session, monkeypatch):
    appts = [make_appointment("Team Sync", datetime.now(timezone.utc), datetime.now(timezone.utc) + timedelta(hours=1), "evt200")]
    archive_repo_instance = {}
    def repo_factory(client, user_obj, calendar_id):
        if calendar_id == "source":
            return MockMSGraphAppointmentRepository(appts)
        else:
            repo = MockMSGraphAppointmentRepository()
            archive_repo_instance['repo'] = repo
            return repo
    monkeypatch.setattr("core.orchestrators.calendar_archive_orchestrator.MSGraphAppointmentRepository", repo_factory)
    orchestrator = CalendarArchiveOrchestrator()
    result = orchestrator.archive_user_appointments(
        user=user,
        msgraph_client=msgraph_client,
        source_calendar_id="source",
        archive_calendar_id="archive",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=1),
        db_session=db_session,
        logger=None
    )
    archive_repo = archive_repo_instance['repo']
    assert len(archive_repo.added) == 1
    assert archive_repo.added[0].subject == "Team Sync"
    assert result["archived_count"] == 1
    assert result["overlap_count"] == 0
    assert result["errors"] == []

def test_archive_appointments_merges_duplicates(user, msgraph_client, db_session, monkeypatch):
    appts = make_duplicate_appointments()
    archive_repo_instance = {}
    def repo_factory(client, user_obj, calendar_id):
        if calendar_id == "source":
            return MockMSGraphAppointmentRepository(appts)
        else:
            repo = MockMSGraphAppointmentRepository()
            archive_repo_instance['repo'] = repo
            return repo
    monkeypatch.setattr("core.orchestrators.calendar_archive_orchestrator.MSGraphAppointmentRepository", repo_factory)
    orchestrator = CalendarArchiveOrchestrator()
    result = orchestrator.archive_user_appointments(
        user=user,
        msgraph_client=msgraph_client,
        source_calendar_id="source",
        archive_calendar_id="archive",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=1),
        db_session=db_session,
        logger=None
    )
    archive_repo = archive_repo_instance['repo']
    assert len(archive_repo.added) == 1  # Duplicates merged
    assert result["archived_count"] == 1
    assert result["overlap_count"] == 0
    assert result["errors"] == []

def test_archive_appointments_detects_overlaps(user, msgraph_client, db_session, appointments, monkeypatch):
    archive_repo_instance = {}
    def repo_factory(client, user_obj, calendar_id):
        if calendar_id == "source":
            return MockMSGraphAppointmentRepository(appointments)
        else:
            repo = MockMSGraphAppointmentRepository()
            archive_repo_instance['repo'] = repo
            return repo
    monkeypatch.setattr("core.orchestrators.calendar_archive_orchestrator.MSGraphAppointmentRepository", repo_factory)
    orchestrator = CalendarArchiveOrchestrator()
    result = orchestrator.archive_user_appointments(
        user=user,
        msgraph_client=msgraph_client,
        source_calendar_id="source",
        archive_calendar_id="archive",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=1),
        db_session=db_session,
        logger=None
    )
    archive_repo = archive_repo_instance['repo']
    assert len(archive_repo.added) == 1  # Only non-overlapping archived
    assert result["archived_count"] == 1
    assert result["overlap_count"] == 2
    assert result["errors"] == []

def test_archive_appointments_expands_recurring(user, msgraph_client, db_session, monkeypatch):
    appts = make_recurring_appointments()
    archive_repo_instance = {}
    def repo_factory(client, user_obj, calendar_id):
        if calendar_id == "source":
            return MockMSGraphAppointmentRepository(appts)
        else:
            repo = MockMSGraphAppointmentRepository()
            archive_repo_instance['repo'] = repo
            return repo
    monkeypatch.setattr("core.orchestrators.calendar_archive_orchestrator.MSGraphAppointmentRepository", repo_factory)
    orchestrator = CalendarArchiveOrchestrator()
    result = orchestrator.archive_user_appointments(
        user=user,
        msgraph_client=msgraph_client,
        source_calendar_id="source",
        archive_calendar_id="archive",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=3),
        db_session=db_session,
        logger=None
    )
    archive_repo = archive_repo_instance['repo']
    assert len(archive_repo.added) == 3
    assert all(a.subject == "Daily Standup" for a in archive_repo.added)
    assert result["archived_count"] == 3
    assert result["overlap_count"] == 0
    assert result["errors"] == []

def test_archive_appointments_handles_partial_failure(user, msgraph_client, db_session, monkeypatch):
    appts = [make_appointment("Team Sync", datetime.now(timezone.utc), datetime.now(timezone.utc) + timedelta(hours=1), "evt201")]
    archive_repo_instance = {}
    def repo_factory(client, user_obj, calendar_id):
        if calendar_id == "source":
            return MockMSGraphAppointmentRepository(appts)
        else:
            repo = MockMSGraphAppointmentRepository()
            archive_repo_instance['repo'] = repo
            return repo
    monkeypatch.setattr("core.orchestrators.calendar_archive_orchestrator.MSGraphAppointmentRepository", repo_factory)
    # Simulate DB commit failure
    def fail_commit():
        raise Exception("DB commit failed")
    db_session.commit = fail_commit
    orchestrator = CalendarArchiveOrchestrator()
    result = orchestrator.archive_user_appointments(
        user=user,
        msgraph_client=msgraph_client,
        source_calendar_id="source",
        archive_calendar_id="archive",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=1),
        db_session=db_session,
        logger=None
    )
    assert result["archived_count"] == 0
    assert result["overlap_count"] == 0
    assert result["errors"]

def test_archive_appointments_time_zone_conversion(user, msgraph_client, db_session, monkeypatch):
    appts = make_timezone_appointment()
    archive_repo_instance = {}
    def repo_factory(client, user_obj, calendar_id):
        if calendar_id == "source":
            return MockMSGraphAppointmentRepository(appts)
        else:
            repo = MockMSGraphAppointmentRepository()
            archive_repo_instance['repo'] = repo
            return repo
    monkeypatch.setattr("core.orchestrators.calendar_archive_orchestrator.MSGraphAppointmentRepository", repo_factory)
    orchestrator = CalendarArchiveOrchestrator()
    result = orchestrator.archive_user_appointments(
        user=user,
        msgraph_client=msgraph_client,
        source_calendar_id="source",
        archive_calendar_id="archive",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
        db_session=db_session,
        logger=None
    )
    archive_repo = archive_repo_instance['repo']
    assert len(archive_repo.added) == 1
    archived = archive_repo.added[0]
    assert archived.start_time.tzinfo is not None
    assert archived.start_time.utcoffset() == timedelta(0)
    assert result["archived_count"] == 1
    assert result["errors"] == [] 