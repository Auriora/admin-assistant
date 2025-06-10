"""
Unit tests for timesheet CLI commands.

Tests the new timesheet commands in the admin-assistant CLI including
timesheet archive and configuration commands.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, timedelta
from click.testing import CliRunner
from src.cli.main import cli


class TestTimesheetCommands:
    """Test suite for timesheet CLI commands"""

    def setup_method(self):
        """Set up test fixtures"""
        self.runner = CliRunner()

    @patch('src.cli.calendar_commands.CalendarArchiveOrchestrator')
    @patch('src.cli.calendar_commands.get_graph_client')
    @patch('src.cli.calendar_commands.get_cached_access_token')
    @patch('src.cli.calendar_commands.UserService')
    def test_calendar_timesheet_command(
        self, mock_user_service, mock_get_token, mock_get_client, mock_orchestrator
    ):
        """Test the 'admin-assistant calendar timesheet' command"""
        
        # Setup mocks
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user_service.return_value.get_by_email.return_value = mock_user
        
        mock_get_token.return_value = "fake_token"
        mock_get_client.return_value = Mock()
        
        mock_orchestrator_instance = Mock()
        mock_orchestrator.return_value = mock_orchestrator_instance
        mock_orchestrator_instance.archive_user_appointments.return_value = {
            "status": "success",
            "archive_type": "timesheet",
            "business_appointments": 5,
            "excluded_appointments": 2,
            "timesheet_statistics": {
                "total_appointments": 7,
                "business_appointments": 5,
                "excluded_appointments": 2
            },
            "correlation_id": "test-123"
        }

        # Execute command
        result = self.runner.invoke(cli, [
            'calendar', 'timesheet',
            '--user-email', 'test@example.com',
            '--source-calendar', 'msgraph://test@example.com/calendars/primary',
            '--archive-calendar', 'timesheet-archive',
            '--start-date', '2025-06-01',
            '--end-date', '2025-06-01'
        ])

        # Verify command executed successfully
        assert result.exit_code == 0
        assert "Timesheet archive completed successfully" in result.output
        assert "Business appointments: 5" in result.output
        assert "Excluded appointments: 2" in result.output

        # Verify orchestrator was called with correct parameters
        mock_orchestrator_instance.archive_user_appointments.assert_called_once()
        call_args = mock_orchestrator_instance.archive_user_appointments.call_args
        assert call_args[1]['archive_purpose'] == 'timesheet'
        assert call_args[1]['source_calendar_uri'] == 'msgraph://test@example.com/calendars/primary'

    @patch('src.cli.calendar_commands.CalendarArchiveOrchestrator')
    @patch('src.cli.calendar_commands.get_graph_client')
    @patch('src.cli.calendar_commands.get_cached_access_token')
    @patch('src.cli.calendar_commands.UserService')
    def test_calendar_timesheet_with_travel_option(
        self, mock_user_service, mock_get_token, mock_get_client, mock_orchestrator
    ):
        """Test timesheet command with --include-travel option"""
        
        # Setup mocks
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user_service.return_value.get_by_email.return_value = mock_user
        
        mock_get_token.return_value = "fake_token"
        mock_get_client.return_value = Mock()
        
        mock_orchestrator_instance = Mock()
        mock_orchestrator.return_value = mock_orchestrator_instance
        mock_orchestrator_instance.archive_user_appointments.return_value = {
            "status": "success",
            "archive_type": "timesheet",
            "business_appointments": 7,  # Including travel
            "excluded_appointments": 2,
            "timesheet_statistics": {
                "total_appointments": 9,
                "business_appointments": 7,
                "excluded_appointments": 2,
                "travel_appointments": 2
            }
        }

        # Execute command with travel option
        result = self.runner.invoke(cli, [
            'calendar', 'timesheet',
            '--user-email', 'test@example.com',
            '--source-calendar', 'msgraph://test@example.com/calendars/primary',
            '--archive-calendar', 'timesheet-archive',
            '--start-date', '2025-06-01',
            '--end-date', '2025-06-01',
            '--include-travel'
        ])

        # Verify command executed successfully
        assert result.exit_code == 0
        assert "Business appointments: 7" in result.output
        assert "travel" in result.output.lower()

    def test_calendar_timesheet_missing_required_args(self):
        """Test timesheet command with missing required arguments"""
        
        # Test missing user email
        result = self.runner.invoke(cli, [
            'calendar', 'timesheet',
            '--source-calendar', 'msgraph://calendars/primary',
            '--archive-calendar', 'timesheet-archive',
            '--start-date', '2025-06-01',
            '--end-date', '2025-06-01'
        ])
        
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    @patch('src.cli.config_commands.ArchiveConfigurationService')
    @patch('src.cli.config_commands.UserService')
    def test_config_calendar_timesheet_create_command(
        self, mock_user_service, mock_config_service
    ):
        """Test the 'admin-assistant config calendar timesheet create' command"""
        
        # Setup mocks
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user_service.return_value.get_by_email.return_value = mock_user
        
        mock_config_service_instance = Mock()
        mock_config_service.return_value = mock_config_service_instance
        
        mock_config = Mock()
        mock_config.id = 123
        mock_config.name = "Test Timesheet Config"
        mock_config.archive_purpose = "timesheet"
        mock_config_service_instance.create.return_value = mock_config

        # Execute command
        result = self.runner.invoke(cli, [
            'config', 'calendar', 'timesheet', 'create',
            '--user-email', 'test@example.com',
            '--name', 'Test Timesheet Config',
            '--source-calendar', 'msgraph://test@example.com/calendars/primary',
            '--destination-calendar', 'msgraph://test@example.com/calendars/timesheet',
            '--timezone', 'UTC'
        ])

        # Verify command executed successfully
        assert result.exit_code == 0
        assert "Timesheet archive configuration created" in result.output
        assert "ID: 123" in result.output

        # Verify configuration was created with correct parameters
        mock_config_service_instance.create.assert_called_once()
        call_args = mock_config_service_instance.create.call_args[0][0]
        assert call_args.archive_purpose == "timesheet"
        assert call_args.allow_overlaps == True  # Default for timesheet
        assert "test@example.com" in call_args.source_calendar_uri
        assert "test@example.com" in call_args.destination_calendar_uri

    @patch('src.cli.config_commands.ArchiveConfigurationService')
    @patch('src.cli.config_commands.UserService')
    def test_config_calendar_timesheet_create_with_options(
        self, mock_user_service, mock_config_service
    ):
        """Test timesheet config create with additional options"""
        
        # Setup mocks
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user_service.return_value.get_by_email.return_value = mock_user
        
        mock_config_service_instance = Mock()
        mock_config_service.return_value = mock_config_service_instance
        
        mock_config = Mock()
        mock_config.id = 456
        mock_config_service_instance.create.return_value = mock_config

        # Execute command with additional options
        result = self.runner.invoke(cli, [
            'config', 'calendar', 'timesheet', 'create',
            '--user-email', 'test@example.com',
            '--name', 'Advanced Timesheet Config',
            '--source-calendar', 'msgraph://test@example.com/calendars/primary',
            '--destination-calendar', 'msgraph://test@example.com/calendars/timesheet',
            '--timezone', 'America/New_York',
            '--no-allow-overlaps',  # Override default
            '--description', 'Custom timesheet configuration'
        ])

        # Verify command executed successfully
        assert result.exit_code == 0

        # Verify configuration was created with custom options
        call_args = mock_config_service_instance.create.call_args[0][0]
        assert call_args.archive_purpose == "timesheet"
        assert call_args.allow_overlaps == False  # Overridden
        assert call_args.timezone == "America/New_York"
        assert call_args.description == "Custom timesheet configuration"

    def test_timesheet_command_help(self):
        """Test that timesheet commands show proper help"""
        
        # Test main timesheet command help
        result = self.runner.invoke(cli, ['calendar', 'timesheet', '--help'])
        assert result.exit_code == 0
        assert "timesheet" in result.output.lower()
        assert "business" in result.output.lower()
        assert "billable" in result.output.lower()

        # Test timesheet config create help
        result = self.runner.invoke(cli, ['config', 'calendar', 'timesheet', 'create', '--help'])
        assert result.exit_code == 0
        assert "timesheet" in result.output.lower()
        assert "archive-purpose" in result.output.lower() or "purpose" in result.output.lower()

    @patch('src.cli.calendar_commands.CalendarArchiveOrchestrator')
    @patch('src.cli.calendar_commands.get_graph_client')
    @patch('src.cli.calendar_commands.get_cached_access_token')
    @patch('src.cli.calendar_commands.UserService')
    def test_timesheet_command_error_handling(
        self, mock_user_service, mock_get_token, mock_get_client, mock_orchestrator
    ):
        """Test error handling in timesheet commands"""
        
        # Setup mocks to simulate error
        mock_user_service.return_value.get_by_email.side_effect = Exception("User not found")

        # Execute command
        result = self.runner.invoke(cli, [
            'calendar', 'timesheet',
            '--user-email', 'nonexistent@example.com',
            '--source-calendar', 'msgraph://calendars/primary',
            '--archive-calendar', 'timesheet-archive',
            '--start-date', '2025-06-01',
            '--end-date', '2025-06-01'
        ])

        # Verify error handling
        assert result.exit_code != 0
        assert "error" in result.output.lower() or "failed" in result.output.lower()

    @patch('src.cli.calendar_commands.CalendarArchiveOrchestrator')
    @patch('src.cli.calendar_commands.get_graph_client')
    @patch('src.cli.calendar_commands.get_cached_access_token')
    @patch('src.cli.calendar_commands.UserService')
    def test_timesheet_command_with_account_context_uri(
        self, mock_user_service, mock_get_token, mock_get_client, mock_orchestrator
    ):
        """Test timesheet command with account context in URI"""
        
        # Setup mocks
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user_service.return_value.get_by_email.return_value = mock_user
        
        mock_get_token.return_value = "fake_token"
        mock_get_client.return_value = Mock()
        
        mock_orchestrator_instance = Mock()
        mock_orchestrator.return_value = mock_orchestrator_instance
        mock_orchestrator_instance.archive_user_appointments.return_value = {
            "status": "success",
            "archive_type": "timesheet",
            "business_appointments": 3,
            "excluded_appointments": 1
        }

        # Execute command with account context URI
        result = self.runner.invoke(cli, [
            'calendar', 'timesheet',
            '--user-email', 'test@example.com',
            '--source-calendar', 'msgraph://test@example.com/calendars/primary',
            '--archive-calendar', 'timesheet-archive',
            '--start-date', '2025-06-01',
            '--end-date', '2025-06-01'
        ])

        # Verify command executed successfully
        assert result.exit_code == 0

        # Verify URI with account context was passed correctly
        call_args = mock_orchestrator_instance.archive_user_appointments.call_args
        source_uri = call_args[1]['source_calendar_uri']
        assert 'test@example.com' in source_uri
        assert source_uri.startswith('msgraph://test@example.com/')

    def test_timesheet_command_date_validation(self):
        """Test date validation in timesheet commands"""
        
        # Test invalid date format
        result = self.runner.invoke(cli, [
            'calendar', 'timesheet',
            '--user-email', 'test@example.com',
            '--source-calendar', 'msgraph://calendars/primary',
            '--archive-calendar', 'timesheet-archive',
            '--start-date', 'invalid-date',
            '--end-date', '2025-06-01'
        ])
        
        assert result.exit_code != 0
        assert "date" in result.output.lower() or "invalid" in result.output.lower()

        # Test end date before start date
        result = self.runner.invoke(cli, [
            'calendar', 'timesheet',
            '--user-email', 'test@example.com',
            '--source-calendar', 'msgraph://calendars/primary',
            '--archive-calendar', 'timesheet-archive',
            '--start-date', '2025-06-02',
            '--end-date', '2025-06-01'
        ])
        
        assert result.exit_code != 0
