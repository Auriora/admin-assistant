"""
Integration tests for the complete archiving flow.
"""
import pytest
from datetime import datetime, UTC, date
from unittest.mock import MagicMock, patch, AsyncMock
from core.orchestrators.calendar_archive_orchestrator import CalendarArchiveOrchestrator
from core.orchestrators.archive_job_runner import ArchiveJobRunner
from core.models.appointment import Appointment
from core.models.archive_configuration import ArchiveConfiguration
from core.services.user_service import UserService
from core.services.archive_configuration_service import ArchiveConfigurationService


@pytest.mark.integration
@pytest.mark.slow
class TestArchivingFlowIntegration:
    """Integration tests for the complete archiving workflow."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance."""
        return CalendarArchiveOrchestrator()

    @pytest.fixture
    def job_runner(self):
        """Create job runner instance."""
        return ArchiveJobRunner()

    @pytest.fixture
    def sample_appointments(self, test_user):
        """Create sample appointments for testing."""
        return [
            Appointment(
                user_id=test_user.id,
                subject="Team Meeting",
                start_time=datetime(2025, 6, 1, 9, 0, tzinfo=UTC),
                end_time=datetime(2025, 6, 1, 10, 0, tzinfo=UTC),
                calendar_id="source-calendar",
                ms_event_id="event-1",
                location="Conference Room A",
                body="Weekly team sync"
            ),
            Appointment(
                user_id=test_user.id,
                subject="Client Call",
                start_time=datetime(2025, 6, 1, 14, 0, tzinfo=UTC),
                end_time=datetime(2025, 6, 1, 15, 0, tzinfo=UTC),
                calendar_id="source-calendar",
                ms_event_id="event-2",
                location="Online",
                body="Quarterly review"
            ),
            Appointment(
                user_id=test_user.id,
                subject="Project Planning",
                start_time=datetime(2025, 6, 2, 10, 0, tzinfo=UTC),
                end_time=datetime(2025, 6, 2, 11, 30, tzinfo=UTC),
                calendar_id="source-calendar",
                ms_event_id="event-3",
                location="Office",
                body="Q3 planning session"
            )
        ]

    @patch('core.orchestrators.calendar_archive_orchestrator.MSGraphAppointmentRepository')
    def test_end_to_end_archiving_flow(
        self, mock_repo_class, orchestrator, test_user, mock_msgraph_client, 
        db_session, sample_appointments
    ):
        """Test the complete end-to-end archiving flow."""
        # Setup mock repository
        mock_source_repo = MagicMock()
        mock_archive_repo = MagicMock()
        mock_repo_class.side_effect = [mock_source_repo, mock_archive_repo]
        
        # Mock source repository to return sample appointments
        mock_source_repo.list_for_user.return_value = sample_appointments
        
        # Mock archive repository
        mock_archive_repo.add = MagicMock()
        
        # Execute archiving
        result = orchestrator.archive_user_appointments(
            user=test_user,
            msgraph_client=mock_msgraph_client,
            source_calendar_uri="msgraph://source-calendar",
            archive_calendar_id="archive-calendar",
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 2),
            db_session=db_session
        )
        
        # Verify results
        assert result["archived_count"] == 3
        assert result["overlap_count"] == 0
        assert len(result["errors"]) == 0
        assert "correlation_id" in result
        
        # Verify appointments were processed
        mock_source_repo.list_for_user.assert_called_once()
        assert mock_archive_repo.add.call_count == 3

    @patch('core.orchestrators.calendar_archive_orchestrator.MSGraphAppointmentRepository')
    def test_archiving_with_overlaps(
        self, mock_repo_class, orchestrator, test_user, mock_msgraph_client, 
        db_session
    ):
        """Test archiving flow with overlapping appointments."""
        # Create overlapping appointments
        overlapping_appointments = [
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
                subject="Overlapping Meeting",
                start_time=datetime(2025, 6, 1, 9, 30, tzinfo=UTC),
                end_time=datetime(2025, 6, 1, 10, 30, tzinfo=UTC),
                calendar_id="source-calendar",
                ms_event_id="event-2"
            )
        ]
        
        # Setup mock repository
        mock_source_repo = MagicMock()
        mock_archive_repo = MagicMock()
        mock_repo_class.side_effect = [mock_source_repo, mock_archive_repo]
        
        mock_source_repo.list_for_user.return_value = overlapping_appointments
        
        # Execute archiving
        result = orchestrator.archive_user_appointments(
            user=test_user,
            msgraph_client=mock_msgraph_client,
            source_calendar_uri="msgraph://source-calendar",
            archive_calendar_id="archive-calendar",
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 1),
            db_session=db_session
        )
        
        # Verify overlap handling
        assert result["archived_count"] == 0  # No appointments archived due to overlaps
        assert result["overlap_count"] >= 1  # At least one overlap detected
        assert result.get("status") in ["partial", "success"]

    @patch('core.services.user_service.UserService.get_by_id')
    @patch('core.services.archive_configuration_service.ArchiveConfigurationService.get_by_id')
    @patch('core.orchestrators.calendar_archive_orchestrator.CalendarArchiveOrchestrator.archive_user_appointments')
    def test_archive_job_runner_integration(
        self, mock_archive, mock_config_service, mock_user_service,
        job_runner, test_user, test_archive_config
    ):
        """Test the ArchiveJobRunner integration."""
        # Setup mocks
        mock_user_service.return_value = test_user
        mock_config_service.return_value = test_archive_config
        mock_archive.return_value = {
            "status": "success",
            "archived_count": 5,
            "overlap_count": 0,
            "errors": []
        }
        
        # Execute job
        result = job_runner.run_archive_job(
            user_id=test_user.id,
            archive_config_id=test_archive_config.id,
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 1)
        )
        
        # Verify results
        assert result["status"] == "success"
        assert result["archived_count"] == 5
        assert result["overlap_count"] == 0
        
        # Verify services were called
        mock_user_service.assert_called_once_with(test_user.id)
        mock_config_service.assert_called_once_with(test_archive_config.id)
        mock_archive.assert_called_once()

    def test_archive_configuration_service_integration(self, db_session, test_user):
        """Test ArchiveConfigurationService integration."""
        service = ArchiveConfigurationService()
        
        # Create configuration
        config = ArchiveConfiguration(
            user_id=test_user.id,
            name="Integration Test Config",
            source_calendar_uri="msgraph://test-source",
            archive_calendar_id="test-archive",
            is_active=True
        )
        
        # Test create
        created_config = service.create(config)
        assert created_config.id is not None
        assert created_config.name == "Integration Test Config"
        
        # Test get
        retrieved_config = service.get_by_id(created_config.id)
        assert retrieved_config is not None
        assert retrieved_config.name == created_config.name
        
        # Test update
        retrieved_config.name = "Updated Config"
        updated_config = service.update(retrieved_config)
        assert updated_config.name == "Updated Config"
        
        # Test list
        configs = service.list_for_user(test_user.id)
        assert len(configs) >= 1
        assert any(c.id == created_config.id for c in configs)

    @patch('core.orchestrators.calendar_archive_orchestrator.MSGraphAppointmentRepository')
    def test_archiving_with_errors(
        self, mock_repo_class, orchestrator, test_user, mock_msgraph_client, 
        db_session, sample_appointments
    ):
        """Test archiving flow with errors during processing."""
        # Setup mock repository
        mock_source_repo = MagicMock()
        mock_archive_repo = MagicMock()
        mock_repo_class.side_effect = [mock_source_repo, mock_archive_repo]
        
        mock_source_repo.list_for_user.return_value = sample_appointments
        
        # Mock archive repository to fail on second appointment
        def mock_add(appointment):
            if appointment.subject == "Client Call":
                raise Exception("Archive failed")
        
        mock_archive_repo.add.side_effect = mock_add
        
        # Execute archiving
        result = orchestrator.archive_user_appointments(
            user=test_user,
            msgraph_client=mock_msgraph_client,
            source_calendar_uri="msgraph://source-calendar",
            archive_calendar_id="archive-calendar",
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 2),
            db_session=db_session
        )
        
        # Verify error handling
        assert result["archived_count"] == 2  # Two successful, one failed
        assert len(result["errors"]) == 1
        assert "Archive failed" in result["errors"][0]

    def test_user_service_integration(self, db_session, test_user):
        """Test UserService integration."""
        service = UserService()
        
        # Test get by id
        retrieved_user = service.get_by_id(test_user.id)
        assert retrieved_user is not None
        assert retrieved_user.email == test_user.email
        
        # Test get by email
        retrieved_user = service.get_by_email(test_user.email)
        assert retrieved_user is not None
        assert retrieved_user.id == test_user.id
