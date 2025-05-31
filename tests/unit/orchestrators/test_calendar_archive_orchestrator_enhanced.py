"""
Enhanced unit tests for CalendarArchiveOrchestrator.
"""
import pytest
from datetime import datetime, UTC, date
from unittest.mock import MagicMock, patch, AsyncMock
from core.orchestrators.calendar_archive_orchestrator import CalendarArchiveOrchestrator
from core.models.appointment import Appointment
from core.models.action_log import ActionLog


@pytest.mark.unit
class TestCalendarArchiveOrchestrator:
    """Test cases for CalendarArchiveOrchestrator."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance."""
        return CalendarArchiveOrchestrator()

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        import logging
        return logging.getLogger(__name__)

    @pytest.fixture
    def sample_appointments(self, test_user):
        """Create sample appointments for testing."""
        return [
            Appointment(
                user_id=test_user.id,
                subject="Meeting 1",
                start_time=datetime(2025, 6, 1, 9, 0, tzinfo=UTC),
                end_time=datetime(2025, 6, 1, 10, 0, tzinfo=UTC),
                calendar_id="source-calendar",
                ms_event_id="event-1"
            ),
            Appointment(
                user_id=test_user.id,
                subject="Meeting 2",
                start_time=datetime(2025, 6, 1, 11, 0, tzinfo=UTC),
                end_time=datetime(2025, 6, 1, 12, 0, tzinfo=UTC),
                calendar_id="source-calendar",
                ms_event_id="event-2"
            )
        ]

    @patch('core.orchestrators.calendar_archive_orchestrator.fetch_appointments')
    @patch('core.orchestrators.calendar_archive_orchestrator.prepare_appointments_for_archive')
    @patch('core.orchestrators.calendar_archive_orchestrator.store_appointments')
    def test_archive_user_appointments_success(
        self, mock_store, mock_prepare, mock_fetch, 
        orchestrator, test_user, mock_msgraph_client, db_session, mock_logger, sample_appointments
    ):
        """Test successful archiving of user appointments."""
        # Setup mocks
        mock_fetch.return_value = sample_appointments
        mock_prepare.return_value = {
            "status": "ok",
            "appointments": sample_appointments,
            "conflicts": [],
            "errors": []
        }
        mock_store.return_value = {"stored_count": 2}
        
        result = orchestrator.archive_user_appointments(
            user=test_user,
            msgraph_client=mock_msgraph_client,
            source_calendar_uri="msgraph://source-calendar",
            archive_calendar_id="archive-calendar",
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 1),
            db_session=db_session,
            logger=mock_logger
        )
        
        assert result["status"] == "success"
        assert result["archived_count"] == 2
        assert result["overlap_count"] == 0
        assert len(result["errors"]) == 0
        
        # Verify mocks were called
        mock_fetch.assert_called_once()
        mock_prepare.assert_called_once()
        mock_store.assert_called_once()

    @patch('core.orchestrators.calendar_archive_orchestrator.fetch_appointments')
    @patch('core.orchestrators.calendar_archive_orchestrator.prepare_appointments_for_archive')
    def test_archive_user_appointments_with_overlaps(
        self, mock_prepare, mock_fetch,
        orchestrator, test_user, mock_msgraph_client, db_session, mock_logger, sample_appointments
    ):
        """Test archiving with overlapping appointments."""
        # Setup mocks
        mock_fetch.return_value = sample_appointments
        mock_prepare.return_value = {
            "status": "overlap",
            "appointments": [],
            "conflicts": [
                [sample_appointments[0], sample_appointments[1]]
            ],
            "errors": []
        }
        
        with patch('core.orchestrators.calendar_archive_orchestrator.ActionLogRepository') as mock_action_repo:
            mock_repo_instance = MagicMock()
            mock_action_repo.return_value = mock_repo_instance
            
            result = orchestrator.archive_user_appointments(
                user=test_user,
                msgraph_client=mock_msgraph_client,
                source_calendar_uri="msgraph://source-calendar",
                archive_calendar_id="archive-calendar",
                start_date=date(2025, 6, 1),
                end_date=date(2025, 6, 1),
                db_session=db_session,
                logger=mock_logger
            )
        
        assert result["status"] == "partial"
        assert result["archived_count"] == 0
        assert result["overlap_count"] == 1
        
        # Verify overlap was logged
        mock_repo_instance.add.assert_called()

    @patch('core.orchestrators.calendar_archive_orchestrator.fetch_appointments')
    def test_archive_user_appointments_fetch_error(
        self, mock_fetch,
        orchestrator, test_user, mock_msgraph_client, db_session, mock_logger
    ):
        """Test handling of fetch errors."""
        # Setup mock to raise exception
        mock_fetch.side_effect = Exception("Fetch failed")
        
        result = orchestrator.archive_user_appointments(
            user=test_user,
            msgraph_client=mock_msgraph_client,
            source_calendar_uri="msgraph://source-calendar",
            archive_calendar_id="archive-calendar",
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 1),
            db_session=db_session,
            logger=mock_logger
        )
        
        assert result["status"] == "error"
        assert "Fetch failed" in result["error"]
        assert result["archived_count"] == 0

    @patch('core.orchestrators.calendar_archive_orchestrator.fetch_appointments')
    @patch('core.orchestrators.calendar_archive_orchestrator.prepare_appointments_for_archive')
    @patch('core.orchestrators.calendar_archive_orchestrator.store_appointments')
    def test_archive_user_appointments_store_error(
        self, mock_store, mock_prepare, mock_fetch,
        orchestrator, test_user, mock_msgraph_client, db_session, mock_logger, sample_appointments
    ):
        """Test handling of store errors."""
        # Setup mocks
        mock_fetch.return_value = sample_appointments
        mock_prepare.return_value = {
            "status": "ok",
            "appointments": sample_appointments,
            "conflicts": [],
            "errors": []
        }
        mock_store.side_effect = Exception("Store failed")
        
        result = orchestrator.archive_user_appointments(
            user=test_user,
            msgraph_client=mock_msgraph_client,
            source_calendar_uri="msgraph://source-calendar",
            archive_calendar_id="archive-calendar",
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 1),
            db_session=db_session,
            logger=mock_logger
        )
        
        assert result["status"] == "error"
        assert "Store failed" in result["error"]

    @patch('core.orchestrators.calendar_archive_orchestrator.fetch_appointments')
    @patch('core.orchestrators.calendar_archive_orchestrator.prepare_appointments_for_archive')
    @patch('core.orchestrators.calendar_archive_orchestrator.store_appointments')
    def test_archive_user_appointments_with_preparation_errors(
        self, mock_store, mock_prepare, mock_fetch,
        orchestrator, test_user, mock_msgraph_client, db_session, mock_logger, sample_appointments
    ):
        """Test archiving with preparation errors."""
        # Setup mocks
        mock_fetch.return_value = sample_appointments
        mock_prepare.return_value = {
            "status": "ok",
            "appointments": [sample_appointments[0]],  # Only one appointment processed
            "conflicts": [],
            "errors": ["Error processing appointment 2"]
        }
        mock_store.return_value = {"stored_count": 1}
        
        result = orchestrator.archive_user_appointments(
            user=test_user,
            msgraph_client=mock_msgraph_client,
            source_calendar_uri="msgraph://source-calendar",
            archive_calendar_id="archive-calendar",
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 1),
            db_session=db_session,
            logger=mock_logger
        )
        
        assert result["status"] == "partial"
        assert result["archived_count"] == 1
        assert len(result["errors"]) == 1
        assert "Error processing appointment 2" in result["errors"]

    def test_archive_user_appointments_without_logger(
        self, orchestrator, test_user, mock_msgraph_client, db_session
    ):
        """Test archiving without providing a logger."""
        with patch('core.orchestrators.calendar_archive_orchestrator.fetch_appointments') as mock_fetch:
            mock_fetch.return_value = []
            
            result = orchestrator.archive_user_appointments(
                user=test_user,
                msgraph_client=mock_msgraph_client,
                source_calendar_uri="msgraph://source-calendar",
                archive_calendar_id="archive-calendar",
                start_date=date(2025, 6, 1),
                end_date=date(2025, 6, 1),
                db_session=db_session
                # No logger provided
            )
        
        assert result["status"] == "success"
        assert result["archived_count"] == 0

    @patch('core.orchestrators.calendar_archive_orchestrator.EntityAssociationHelper')
    def test_log_overlap_conflict(self, mock_helper, orchestrator, test_user, db_session, sample_appointments):
        """Test logging of overlap conflicts."""
        mock_helper_instance = MagicMock()
        mock_helper.return_value = mock_helper_instance
        
        with patch('core.orchestrators.calendar_archive_orchestrator.ActionLogRepository') as mock_action_repo:
            mock_repo_instance = MagicMock()
            mock_action_repo.return_value = mock_repo_instance
            mock_action_log = MagicMock()
            mock_action_log.id = 123
            mock_repo_instance.add.return_value = mock_action_log
            
            # Call the private method directly for testing
            orchestrator._log_overlap_conflict(
                conflict_group=sample_appointments,
                user=test_user,
                db_session=db_session
            )
            
            # Verify action log was created
            mock_repo_instance.add.assert_called_once()
            
            # Verify entity associations were created
            assert mock_helper_instance.associate_appointments_with_action.call_count == len(sample_appointments)

    def test_parse_calendar_uri(self, orchestrator):
        """Test parsing of calendar URI."""
        # Test msgraph URI
        backend, calendar_id = orchestrator._parse_calendar_uri("msgraph://test-calendar-id")
        assert backend == "msgraph"
        assert calendar_id == "test-calendar-id"
        
        # Test sqlalchemy URI
        backend, calendar_id = orchestrator._parse_calendar_uri("sqlalchemy://local-calendar")
        assert backend == "sqlalchemy"
        assert calendar_id == "local-calendar"
        
        # Test invalid URI
        with pytest.raises(ValueError):
            orchestrator._parse_calendar_uri("invalid-uri")

    @patch('core.orchestrators.calendar_archive_orchestrator.get_appointment_repository')
    def test_get_source_repository(self, mock_get_repo, orchestrator, test_user, mock_msgraph_client, db_session):
        """Test getting source repository."""
        mock_repo = MagicMock()
        mock_get_repo.return_value = mock_repo
        
        result = orchestrator._get_source_repository(
            calendar_uri="msgraph://test-calendar",
            user=test_user,
            msgraph_client=mock_msgraph_client,
            db_session=db_session
        )
        
        assert result == mock_repo
        mock_get_repo.assert_called_once_with(
            backend="msgraph",
            user=test_user,
            calendar_id="test-calendar",
            msgraph_client=mock_msgraph_client,
            session=db_session
        )
