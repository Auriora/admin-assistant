import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, date, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.models.appointment import Appointment, Base as AppointmentBase
from core.models.action_log import ActionLog, Base as ActionLogBase
from core.models.entity_association import EntityAssociation, Base as AssocBase
from core.models.audit_log import AuditLog
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
    # AuditLog uses the same Base as other models, so we need to ensure it's created
    from core.db import Base
    Base.metadata.create_all(engine)

    # Create session with proper transaction handling
    Session = sessionmaker(bind=engine)
    session = Session()

    # Start a transaction for test isolation
    connection = engine.connect()
    transaction = connection.begin()
    session.bind = connection

    try:
        yield session
    finally:
        # Ensure proper cleanup regardless of test outcome
        session.close()
        transaction.rollback()
        connection.close()
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
def make_appointment(subject, start, end, ms_event_id=None, categories=None):
    appointment = Appointment(
        ms_event_id=ms_event_id,
        user_id=1,
        start_time=start,
        end_time=end,
        subject=subject,
        calendar_id="source"
    )
    if categories is not None:
        appointment.categories = categories
    return appointment

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

    # Mock calendar resolver to avoid URI resolution warnings
    def mock_resolve_calendar_uri(uri, user, access_token):
        return uri  # Just return the URI as-is for testing
    monkeypatch.setattr("core.utilities.calendar_resolver.resolve_calendar_uri", mock_resolve_calendar_uri)

    # Mock access token to avoid auth issues
    def mock_get_cached_access_token():
        return "mock_token"
    monkeypatch.setattr("core.utilities.auth_utility.get_cached_access_token", mock_get_cached_access_token)

    orchestrator = CalendarArchiveOrchestrator()
    result = orchestrator.archive_user_appointments(
        user=user,
        msgraph_client=msgraph_client,
        source_calendar_uri="source",
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
    overlap_logs = [log for log in logs if log.event_type == "overlap"]
    category_logs = [log for log in logs if log.event_type == "category_validation"]
    assert len(overlap_logs) == 2
    assert len(category_logs) == 3  # Category validation issues are also logged
    assert len(logs) == 5  # Total logs

    # Associations should be created (only for overlaps)
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

    # Mock calendar resolver to avoid URI resolution warnings
    def mock_resolve_calendar_uri(uri, user, access_token):
        return uri  # Just return the URI as-is for testing
    monkeypatch.setattr("core.utilities.calendar_resolver.resolve_calendar_uri", mock_resolve_calendar_uri)

    # Mock access token to avoid auth issues
    def mock_get_cached_access_token():
        return "mock_token"
    monkeypatch.setattr("core.utilities.auth_utility.get_cached_access_token", mock_get_cached_access_token)
    orchestrator = CalendarArchiveOrchestrator()
    result = orchestrator.archive_user_appointments(
        user=user,
        msgraph_client=msgraph_client,
        source_calendar_uri="source",
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
        source_calendar_uri="source",
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
        source_calendar_uri="source",
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
        source_calendar_uri="source",
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

    # Mock the AuditContext to avoid database operations
    mock_audit_context = Mock()
    mock_audit_context.__enter__ = Mock(return_value=mock_audit_context)
    mock_audit_context.__exit__ = Mock(return_value=None)
    mock_audit_context.set_request_data = Mock()
    mock_audit_context.add_detail = Mock()
    mock_audit_context.set_response_data = Mock()

    # Simulate DB commit failure
    def fail_commit():
        raise Exception("DB commit failed")
    db_session.commit = fail_commit

    with patch("core.orchestrators.calendar_archive_orchestrator.AuditContext", return_value=mock_audit_context):
        orchestrator = CalendarArchiveOrchestrator()
        result = orchestrator.archive_user_appointments(
            user=user,
            msgraph_client=msgraph_client,
            source_calendar_uri="source",
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
        source_calendar_uri="source",
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


class TestCalendarArchiveOrchestratorTimesheet:
    """Test suite for timesheet-specific archive functionality"""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance"""
        return CalendarArchiveOrchestrator()

    @pytest.fixture
    def timesheet_appointments(self, user):
        """Create sample appointments for timesheet testing"""
        return [
            make_appointment(
                "Client Meeting",
                datetime.now(timezone.utc),
                datetime.now(timezone.utc) + timedelta(hours=1),
                "evt1",
                categories=["Acme Corp - billable"]
            ),
            make_appointment(
                "Internal Meeting",
                datetime.now(timezone.utc) + timedelta(hours=2),
                datetime.now(timezone.utc) + timedelta(hours=3),
                "evt2",
                categories=["Admin - non-billable"]
            ),
            make_appointment(
                "Travel to Client",
                datetime.now(timezone.utc) + timedelta(hours=4),
                datetime.now(timezone.utc) + timedelta(hours=5),
                "evt3"
            ),
            make_appointment(
                "Personal Appointment",
                datetime.now(timezone.utc) + timedelta(hours=6),
                datetime.now(timezone.utc) + timedelta(hours=7),
                "evt4"
            ),
        ]

    @patch('core.orchestrators.calendar_archive_orchestrator.MSGraphAppointmentRepository')
    def test_archive_with_timesheet_purpose(
        self, mock_repo_class, orchestrator, user, msgraph_client,
        db_session, timesheet_appointments
    ):
        """Test archiving with timesheet purpose"""
        # Setup mock repository
        mock_source_repo = MagicMock()
        mock_archive_repo = MagicMock()
        mock_repo_class.side_effect = [mock_source_repo, mock_archive_repo]

        mock_source_repo.list_for_user.return_value = timesheet_appointments
        mock_archive_repo.add_bulk = MagicMock(return_value=[])
        mock_archive_repo.check_for_duplicates = MagicMock(side_effect=lambda appts, start, end: appts)

        # Create audit service
        from core.repositories.audit_log_repository import AuditLogRepository
        from core.services.audit_log_service import AuditLogService
        audit_repo = AuditLogRepository(session=db_session)
        audit_service = AuditLogService(repository=audit_repo)

        # Execute timesheet archiving
        result = orchestrator.archive_user_appointments(
            user=user,
            msgraph_client=msgraph_client,
            source_calendar_uri="msgraph://calendars/primary",
            archive_calendar_id="timesheet-archive",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
            db_session=db_session,
            audit_service=audit_service,
            archive_purpose='timesheet'
        )

        # Verify timesheet-specific results
        assert result["status"] == "success"
        assert result["archive_type"] == "timesheet"
        assert "business_appointments" in result
        assert "excluded_appointments" in result
        assert "timesheet_statistics" in result
        assert "correlation_id" in result

        # Verify appointments were processed through timesheet service
        # Should have filtered out personal appointment
        assert result["business_appointments"] >= 2  # At least billable + non-billable

    @patch('core.orchestrators.calendar_archive_orchestrator.MSGraphAppointmentRepository')
    def test_archive_with_general_purpose_allow_overlaps(
        self, mock_repo_class, orchestrator, user, msgraph_client,
        db_session, timesheet_appointments
    ):
        """Test archiving with general purpose and allow_overlaps=True"""
        # Create overlapping appointments
        overlapping_appointments = [
            make_appointment(
                "Meeting 1",
                datetime.now(timezone.utc),
                datetime.now(timezone.utc) + timedelta(hours=1),
                "evt1"
            ),
            make_appointment(
                "Overlapping Meeting",
                datetime.now(timezone.utc) + timedelta(minutes=30),
                datetime.now(timezone.utc) + timedelta(hours=1, minutes=30),
                "evt2"
            ),
        ]

        # Setup mock repository
        mock_source_repo = MagicMock()
        mock_archive_repo = MagicMock()
        mock_repo_class.side_effect = [mock_source_repo, mock_archive_repo]

        mock_source_repo.list_for_user.return_value = overlapping_appointments
        mock_archive_repo.add_bulk = MagicMock(return_value=[])
        mock_archive_repo.check_for_duplicates = MagicMock(side_effect=lambda appts, start, end: appts)

        # Create audit service
        from core.repositories.audit_log_repository import AuditLogRepository
        from core.services.audit_log_service import AuditLogService
        audit_repo = AuditLogRepository(session=db_session)
        audit_service = AuditLogService(repository=audit_repo)

        # Execute general archiving with allow_overlaps=True
        result = orchestrator.archive_user_appointments(
            user=user,
            msgraph_client=msgraph_client,
            source_calendar_uri="msgraph://calendars/primary",
            archive_calendar_id="general-archive",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
            db_session=db_session,
            audit_service=audit_service,
            archive_purpose='general',
            allow_overlaps=True
        )

        # Verify overlaps were allowed
        assert result["archived_count"] == 2  # Both appointments archived despite overlap
        assert result["overlap_count"] >= 1  # Overlaps detected but allowed

    @patch('core.orchestrators.calendar_archive_orchestrator.MSGraphAppointmentRepository')
    @patch('core.services.timesheet_archive_service.TimesheetArchiveService.process_appointments_for_timesheet')
    def test_timesheet_service_integration(
        self, mock_timesheet_process, mock_repo_class, orchestrator,
        user, msgraph_client, db_session, timesheet_appointments
    ):
        """Test integration with TimesheetArchiveService"""
        # Setup mock timesheet service response
        mock_timesheet_process.return_value = {
            "filtered_appointments": timesheet_appointments[:3],  # Exclude personal
            "excluded_appointments": timesheet_appointments[3:],  # Personal only
            "overlap_resolutions": [],
            "statistics": {
                "total_appointments": 4,
                "business_appointments": 3,
                "excluded_appointments": 1,
                "overlap_groups_processed": 0
            },
            "issues": []
        }

        # Setup mock repository
        mock_source_repo = MagicMock()
        mock_archive_repo = MagicMock()
        mock_repo_class.side_effect = [mock_source_repo, mock_archive_repo]

        mock_source_repo.list_for_user.return_value = timesheet_appointments
        mock_archive_repo.add_bulk = MagicMock(return_value=[])
        mock_archive_repo.check_for_duplicates = MagicMock(side_effect=lambda appts, start, end: appts)

        # Create audit service
        from core.repositories.audit_log_repository import AuditLogRepository
        from core.services.audit_log_service import AuditLogService
        audit_repo = AuditLogRepository(session=db_session)
        audit_service = AuditLogService(repository=audit_repo)

        # Execute timesheet archiving
        result = orchestrator.archive_user_appointments(
            user=user,
            msgraph_client=msgraph_client,
            source_calendar_uri="msgraph://calendars/primary",
            archive_calendar_id="timesheet-archive",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
            db_session=db_session,
            audit_service=audit_service,
            archive_purpose='timesheet'
        )

        # Verify timesheet service was called
        mock_timesheet_process.assert_called_once()
        call_args = mock_timesheet_process.call_args[0]
        assert len(call_args[0]) == 4  # All appointments passed to timesheet service

        # Verify results include timesheet-specific data
        assert result["archive_type"] == "timesheet"
        assert result["business_appointments"] == 3
        assert result["excluded_appointments"] == 1
        assert "timesheet_statistics" in result

    def test_archive_purpose_routing(self, orchestrator):
        """Test that archive_purpose parameter routes to correct service"""
        # This test verifies the routing logic without full integration

        # Test timesheet purpose routing
        with patch.object(orchestrator, '_archive_with_timesheet_service') as mock_timesheet:
            mock_timesheet.return_value = {"status": "success", "archive_type": "timesheet"}

            result = orchestrator.archive_user_appointments(
                user=Mock(),
                msgraph_client=Mock(),
                source_calendar_uri="msgraph://calendars/primary",
                archive_calendar_id="archive",
                start_date=date.today(),
                end_date=date.today(),
                db_session=Mock(),
                archive_purpose='timesheet'
            )

            mock_timesheet.assert_called_once()
            assert result["archive_type"] == "timesheet"

        # Test general purpose routing
        with patch.object(orchestrator, '_archive_with_general_logic') as mock_general:
            mock_general.return_value = {"status": "success", "archive_type": "general"}

            result = orchestrator.archive_user_appointments(
                user=Mock(),
                msgraph_client=Mock(),
                source_calendar_uri="msgraph://calendars/primary",
                archive_calendar_id="archive",
                start_date=date.today(),
                end_date=date.today(),
                db_session=Mock(),
                archive_purpose='general'
            )

            mock_general.assert_called_once()
            assert result["archive_type"] == "general"