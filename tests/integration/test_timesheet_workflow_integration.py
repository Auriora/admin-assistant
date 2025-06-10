"""
Integration tests for the complete timesheet workflow.

Tests the end-to-end functionality including URI parsing with account context,
timesheet filtering, overlap resolution, and CLI integration.
"""
import pytest
from datetime import datetime, UTC, date, timedelta
from unittest.mock import MagicMock, patch, Mock
from core.orchestrators.calendar_archive_orchestrator import CalendarArchiveOrchestrator
from core.services.timesheet_archive_service import TimesheetArchiveService
from core.utilities.uri_utility import parse_resource_uri, construct_resource_uri
from core.utilities.calendar_resolver import CalendarResolver
from core.models.appointment import Appointment
from core.models.archive_configuration import ArchiveConfiguration


@pytest.mark.integration
@pytest.mark.slow
class TestTimesheetWorkflowIntegration:
    """Integration tests for the complete timesheet workflow."""

    @pytest.fixture
    def timesheet_service(self):
        """Create timesheet service instance."""
        return TimesheetArchiveService()

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance."""
        return CalendarArchiveOrchestrator()

    @pytest.fixture
    def sample_business_appointments(self, test_user):
        """Create sample business appointments for testing."""
        return [
            Appointment(
                user_id=test_user.id,
                subject="Client Consultation",
                start_time=datetime(2025, 6, 1, 9, 0, tzinfo=UTC),
                end_time=datetime(2025, 6, 1, 10, 0, tzinfo=UTC),
                calendar_id="source-calendar",
                ms_event_id="event-1",
                categories=["Acme Corp - billable"],
                location="Client Office",
                body_content="Quarterly review meeting"
            ),
            Appointment(
                user_id=test_user.id,
                subject="Team Standup",
                start_time=datetime(2025, 6, 1, 10, 30, tzinfo=UTC),
                end_time=datetime(2025, 6, 1, 11, 0, tzinfo=UTC),
                calendar_id="source-calendar",
                ms_event_id="event-2",
                categories=["Admin - non-billable"],
                location="Conference Room",
                body_content="Daily team sync"
            ),
            Appointment(
                user_id=test_user.id,
                subject="Travel to Client Site",
                start_time=datetime(2025, 6, 1, 8, 0, tzinfo=UTC),
                end_time=datetime(2025, 6, 1, 9, 0, tzinfo=UTC),
                calendar_id="source-calendar",
                ms_event_id="event-3",
                location="En route",
                body_content="Drive to client office"
            ),
            Appointment(
                user_id=test_user.id,
                subject="Personal Doctor Appointment",
                start_time=datetime(2025, 6, 1, 14, 0, tzinfo=UTC),
                end_time=datetime(2025, 6, 1, 15, 0, tzinfo=UTC),
                calendar_id="source-calendar",
                ms_event_id="event-4",
                location="Medical Center",
                body_content="Annual checkup"
            ),
            Appointment(
                user_id=test_user.id,
                subject="Available Time",
                start_time=datetime(2025, 6, 1, 16, 0, tzinfo=UTC),
                end_time=datetime(2025, 6, 1, 17, 0, tzinfo=UTC),
                calendar_id="source-calendar",
                ms_event_id="event-5",
                show_as="free",
                location="Office",
                body_content="Open for meetings"
            ),
        ]

    def test_end_to_end_timesheet_workflow(
        self, orchestrator, timesheet_service, test_user, mock_msgraph_client, 
        db_session, sample_business_appointments
    ):
        """Test the complete end-to-end timesheet workflow."""
        
        # Test URI parsing with account context
        source_uri = f"msgraph://{test_user.email}/calendars/primary"
        parsed_uri = parse_resource_uri(source_uri)
        assert parsed_uri.account == test_user.email
        assert parsed_uri.namespace == "calendars"
        assert parsed_uri.identifier == "primary"

        # Test timesheet filtering
        result = timesheet_service.process_appointments_for_timesheet(
            sample_business_appointments, include_travel=True
        )
        
        # Verify filtering results
        assert len(result["filtered_appointments"]) == 3  # billable + non-billable + travel
        assert len(result["excluded_appointments"]) == 2  # personal + free
        
        # Verify business appointments are included
        business_subjects = [apt.subject for apt in result["filtered_appointments"]]
        assert "Client Consultation" in business_subjects
        assert "Team Standup" in business_subjects
        assert "Travel to Client Site" in business_subjects
        
        # Verify personal and free appointments are excluded
        excluded_subjects = [apt.subject for apt in result["excluded_appointments"]]
        assert "Personal Doctor Appointment" in excluded_subjects
        assert "Available Time" in excluded_subjects

        # Verify statistics
        stats = result["statistics"]
        assert stats["total_appointments"] == 5
        assert stats["business_appointments"] == 3
        assert stats["excluded_appointments"] == 2
        assert stats["exclusion_rate"] == 0.4  # 2/5
        assert stats["business_rate"] == 0.6  # 3/5

    @patch('core.orchestrators.calendar_archive_orchestrator.MSGraphAppointmentRepository')
    def test_timesheet_archive_orchestrator_integration(
        self, mock_repo_class, orchestrator, test_user, mock_msgraph_client, 
        db_session, sample_business_appointments
    ):
        """Test timesheet archiving through the orchestrator."""
        
        # Setup mock repository
        mock_source_repo = MagicMock()
        mock_archive_repo = MagicMock()
        mock_repo_class.side_effect = [mock_source_repo, mock_archive_repo]
        
        mock_source_repo.list_for_user.return_value = sample_business_appointments
        mock_archive_repo.add_bulk = MagicMock(return_value=[])
        mock_archive_repo.check_for_duplicates = MagicMock(side_effect=lambda appts, start, end: appts)

        # Create audit service
        from core.repositories.audit_log_repository import AuditLogRepository
        from core.services.audit_log_service import AuditLogService
        audit_repo = AuditLogRepository(session=db_session)
        audit_service = AuditLogService(repository=audit_repo)

        # Execute timesheet archiving with account context URI
        source_uri = f"msgraph://{test_user.email}/calendars/primary"
        result = orchestrator.archive_user_appointments(
            user=test_user,
            msgraph_client=mock_msgraph_client,
            source_calendar_uri=source_uri,
            archive_calendar_id="timesheet-archive",
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 1),
            db_session=db_session,
            audit_service=audit_service,
            archive_purpose='timesheet'
        )

        # Verify timesheet-specific results
        assert result["status"] == "success"
        assert result["archive_type"] == "timesheet"
        assert result["business_appointments"] == 3
        assert result["excluded_appointments"] == 2
        assert "timesheet_statistics" in result
        assert "correlation_id" in result

        # Verify only business appointments were archived
        call_args = mock_archive_repo.add_bulk.call_args[0]
        archived_appointments = call_args[0]
        assert len(archived_appointments) == 3
        
        archived_subjects = [apt.subject for apt in archived_appointments]
        assert "Client Consultation" in archived_subjects
        assert "Team Standup" in archived_subjects
        assert "Travel to Client Site" in archived_subjects
        assert "Personal Doctor Appointment" not in archived_subjects
        assert "Available Time" not in archived_subjects

    def test_uri_account_validation_integration(self, test_user):
        """Test URI account validation integration."""
        
        # Create calendar resolver
        resolver = CalendarResolver(test_user, Mock())
        
        # Test valid account contexts
        valid_uris = [
            f"msgraph://{test_user.email}/calendars/primary",
            f"msgraph://{test_user.username}/calendars/archive",
            f"msgraph://{test_user.id}/calendars/timesheet"
        ]
        
        for uri in valid_uris:
            parsed = parse_resource_uri(uri)
            # Should not raise exception
            resolver._validate_account_context(parsed.account)

        # Test invalid account context
        invalid_uri = "msgraph://wrong@example.com/calendars/primary"
        parsed = parse_resource_uri(invalid_uri)
        
        with pytest.raises(Exception):  # Should raise CalendarResolutionError
            resolver._validate_account_context(parsed.account)

    def test_archive_configuration_with_new_columns(self, db_session, test_user):
        """Test archive configuration with new columns."""
        from core.repositories.archive_configuration_repository import ArchiveConfigurationRepository
        from core.services.archive_configuration_service import ArchiveConfigurationService

        # Create service with test database session
        repository = ArchiveConfigurationRepository(session=db_session)
        service = ArchiveConfigurationService(repository=repository)
        
        # Create timesheet configuration with new columns
        config = ArchiveConfiguration(
            user_id=test_user.id,
            name="Timesheet Archive Config",
            source_calendar_uri=f"msgraph://{test_user.email}/calendars/primary",
            destination_calendar_uri=f"msgraph://{test_user.email}/calendars/timesheet",
            is_active=True,
            timezone="UTC",
            allow_overlaps=True,  # New column
            archive_purpose="timesheet"  # New column
        )
        
        # Test create
        service.create(config)
        assert config.id is not None
        assert config.allow_overlaps == True
        assert config.archive_purpose == "timesheet"
        
        # Test get
        retrieved_config = service.get_by_id(config.id)
        assert retrieved_config is not None
        assert retrieved_config.allow_overlaps == True
        assert retrieved_config.archive_purpose == "timesheet"
        assert test_user.email in retrieved_config.source_calendar_uri
        assert test_user.email in retrieved_config.destination_calendar_uri

    @patch('core.orchestrators.calendar_archive_orchestrator.MSGraphAppointmentRepository')
    def test_overlap_resolution_integration(
        self, mock_repo_class, orchestrator, test_user, mock_msgraph_client, 
        db_session
    ):
        """Test overlap resolution in timesheet workflow."""
        
        # Create overlapping business appointments
        overlapping_appointments = [
            Appointment(
                user_id=test_user.id,
                subject="Important Client Meeting",
                start_time=datetime(2025, 6, 1, 9, 0, tzinfo=UTC),
                end_time=datetime(2025, 6, 1, 10, 0, tzinfo=UTC),
                calendar_id="source-calendar",
                ms_event_id="event-1",
                categories=["Acme Corp - billable"],
                importance="high",
                response_status="accepted"
            ),
            Appointment(
                user_id=test_user.id,
                subject="Tentative Internal Meeting",
                start_time=datetime(2025, 6, 1, 9, 30, tzinfo=UTC),
                end_time=datetime(2025, 6, 1, 10, 30, tzinfo=UTC),
                calendar_id="source-calendar",
                ms_event_id="event-2",
                categories=["Admin - non-billable"],
                importance="normal",
                response_status="tentative"
            ),
            Appointment(
                user_id=test_user.id,
                subject="Free Time Block",
                start_time=datetime(2025, 6, 1, 9, 15, tzinfo=UTC),
                end_time=datetime(2025, 6, 1, 10, 15, tzinfo=UTC),
                calendar_id="source-calendar",
                ms_event_id="event-3",
                show_as="free"
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

        # Execute timesheet archiving
        result = orchestrator.archive_user_appointments(
            user=test_user,
            msgraph_client=mock_msgraph_client,
            source_calendar_uri=f"msgraph://{test_user.email}/calendars/primary",
            archive_calendar_id="timesheet-archive",
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 1),
            db_session=db_session,
            audit_service=audit_service,
            archive_purpose='timesheet'
        )

        # Verify overlap resolution occurred
        assert result["status"] == "success"
        assert result["archive_type"] == "timesheet"
        
        # Should have resolved overlaps automatically
        # Free appointment should be filtered out
        # Tentative should be resolved in favor of confirmed high-importance
        assert result["business_appointments"] <= 2  # After resolution
        assert "overlap_resolutions" in result["timesheet_statistics"]

    @patch('src.cli.calendar_commands.CalendarArchiveOrchestrator')
    @patch('src.cli.calendar_commands.get_graph_client')
    @patch('src.cli.calendar_commands.get_cached_access_token')
    @patch('src.cli.calendar_commands.UserService')
    def test_cli_timesheet_command_integration(
        self, mock_user_service, mock_get_token, mock_get_client, mock_orchestrator,
        test_user, sample_business_appointments
    ):
        """Test CLI timesheet command integration"""
        from click.testing import CliRunner
        from src.cli.main import cli

        # Setup mocks
        mock_user_service.return_value.get_by_email.return_value = test_user
        mock_get_token.return_value = "fake_token"
        mock_get_client.return_value = Mock()

        mock_orchestrator_instance = Mock()
        mock_orchestrator.return_value = mock_orchestrator_instance
        mock_orchestrator_instance.archive_user_appointments.return_value = {
            "status": "success",
            "archive_type": "timesheet",
            "business_appointments": 3,
            "excluded_appointments": 2,
            "timesheet_statistics": {
                "total_appointments": 5,
                "business_appointments": 3,
                "excluded_appointments": 2,
                "exclusion_rate": 0.4,
                "business_rate": 0.6
            },
            "correlation_id": "test-cli-123"
        }

        # Execute CLI command
        runner = CliRunner()
        result = runner.invoke(cli, [
            'calendar', 'timesheet',
            '--user-email', test_user.email,
            '--source-calendar', f'msgraph://{test_user.email}/calendars/primary',
            '--archive-calendar', 'timesheet-archive',
            '--start-date', '2025-06-01',
            '--end-date', '2025-06-01',
            '--include-travel'
        ])

        # Verify CLI execution
        assert result.exit_code == 0
        assert "Timesheet archive completed successfully" in result.output
        assert "Business appointments: 3" in result.output
        assert "Excluded appointments: 2" in result.output

        # Verify orchestrator was called with correct parameters
        mock_orchestrator_instance.archive_user_appointments.assert_called_once()
        call_kwargs = mock_orchestrator_instance.archive_user_appointments.call_args[1]
        assert call_kwargs['archive_purpose'] == 'timesheet'
        assert test_user.email in call_kwargs['source_calendar_uri']

    def test_migration_script_integration(self, db_session, test_user):
        """Test migration script integration with real database"""
        from core.repositories.archive_configuration_repository import ArchiveConfigurationRepository
        from core.services.archive_configuration_service import ArchiveConfigurationService
        from core.models.archive_configuration import ArchiveConfiguration

        # Create service with test database session
        repository = ArchiveConfigurationRepository(session=db_session)
        service = ArchiveConfigurationService(repository=repository)

        # Create legacy configuration (without account context)
        legacy_config = ArchiveConfiguration(
            user_id=test_user.id,
            name="Legacy Config",
            source_calendar_uri="msgraph://calendars/primary",
            destination_calendar_uri="msgraph://calendars/archive",
            is_active=True,
            timezone="UTC"
        )

        service.create(legacy_config)

        # Simulate migration by updating URIs manually
        from core.utilities.uri_utility import migrate_legacy_uri

        migrated_source = migrate_legacy_uri(legacy_config.source_calendar_uri, test_user.email)
        migrated_dest = migrate_legacy_uri(legacy_config.destination_calendar_uri, test_user.email)

        # Update configuration
        legacy_config.source_calendar_uri = migrated_source
        legacy_config.destination_calendar_uri = migrated_dest
        legacy_config.allow_overlaps = True
        legacy_config.archive_purpose = "timesheet"

        service.update(legacy_config)

        # Verify migration results
        updated_config = service.get_by_id(legacy_config.id)
        assert test_user.email in updated_config.source_calendar_uri
        assert test_user.email in updated_config.destination_calendar_uri
        assert updated_config.allow_overlaps == True
        assert updated_config.archive_purpose == "timesheet"

    def test_error_handling_integration(self, orchestrator, test_user, mock_msgraph_client, db_session):
        """Test error handling throughout the workflow"""

        # Test with invalid URI
        with pytest.raises(Exception):  # Should raise URIParseError or similar
            orchestrator.archive_user_appointments(
                user=test_user,
                msgraph_client=mock_msgraph_client,
                source_calendar_uri="invalid-uri",
                archive_calendar_id="archive",
                start_date=date(2025, 6, 1),
                end_date=date(2025, 6, 1),
                db_session=db_session,
                archive_purpose='timesheet'
            )

    def test_performance_integration(self, timesheet_service, test_user):
        """Test performance with large datasets"""
        import time

        # Create large dataset
        large_appointment_set = []
        for i in range(100):
            appointment = Mock()
            appointment.subject = f"Meeting {i}"
            appointment.categories = ["Acme Corp - billable"] if i % 2 == 0 else []
            appointment.show_as = "busy"
            appointment.start_time = datetime(2025, 6, 1, 9 + (i % 8), 0, tzinfo=UTC)
            appointment.end_time = datetime(2025, 6, 1, 10 + (i % 8), 0, tzinfo=UTC)
            large_appointment_set.append(appointment)

        # Measure processing time
        start_time = time.time()
        result = timesheet_service.process_appointments_for_timesheet(
            large_appointment_set, include_travel=True
        )
        end_time = time.time()

        # Should complete within reasonable time (less than 5 seconds for 100 appointments)
        processing_time = end_time - start_time
        assert processing_time < 5.0

        # Verify results are correct
        assert len(result["filtered_appointments"]) + len(result["excluded_appointments"]) == 100
        assert result["statistics"]["total_appointments"] == 100

    def test_backward_compatibility_integration(self, orchestrator, test_user, mock_msgraph_client, db_session):
        """Test backward compatibility with legacy URI formats"""

        # Mock repository setup
        with patch('core.orchestrators.calendar_archive_orchestrator.MSGraphAppointmentRepository') as mock_repo_class:
            mock_source_repo = Mock()
            mock_archive_repo = Mock()
            mock_repo_class.side_effect = [mock_source_repo, mock_archive_repo]

            mock_source_repo.list_for_user.return_value = []
            mock_archive_repo.add_bulk = Mock(return_value=[])
            mock_archive_repo.check_for_duplicates = Mock(side_effect=lambda appts, start, end: appts)

            # Create audit service
            from core.repositories.audit_log_repository import AuditLogRepository
            from core.services.audit_log_service import AuditLogService
            audit_repo = AuditLogRepository(session=db_session)
            audit_service = AuditLogService(repository=audit_repo)

            # Test with legacy URI format (no account context)
            result = orchestrator.archive_user_appointments(
                user=test_user,
                msgraph_client=mock_msgraph_client,
                source_calendar_uri="msgraph://calendars/primary",  # Legacy format
                archive_calendar_id="archive",
                start_date=date(2025, 6, 1),
                end_date=date(2025, 6, 1),
                db_session=db_session,
                audit_service=audit_service,
                archive_purpose='general'  # Test general purpose too
            )

            # Should work without errors
            assert result["status"] == "success"
