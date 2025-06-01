# Specific Test Cases Examples - Core & CLI Focus

## Document Information
- **Document ID**: STCE-001
- **Document Name**: Specific Test Cases Examples - Core & CLI Focus
- **Created By**: Admin Assistant System
- **Creation Date**: 2024-12-19
- **Status**: ACTIVE

### 1. CLI Category Commands Tests (`tests/unit/cli/test_category_commands.py`)

```python
import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from cli.main import cli

class TestCategoryCLICommands:
    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def mock_category_service(self):
        with patch('cli.main.CategoryService') as mock:
            yield mock.return_value

    def test_category_list_command_success(self, runner, mock_category_service):
        """Test successful category listing."""
        mock_category_service.list.return_value = [
            MagicMock(id=1, name='Client A - Hourly', user_id=1),
            MagicMock(id=2, name='Client B - Fixed', user_id=1)
        ]

        result = runner.invoke(cli, ['category', 'list', '--user-email', 'test@example.com'])

        assert result.exit_code == 0
        assert 'Client A - Hourly' in result.output
        assert 'Client B - Fixed' in result.output

    def test_category_add_command_success(self, runner, mock_category_service):
        """Test successful category creation."""
        mock_category_service.create.return_value = MagicMock(id=1, name='New Client - Hourly')

        result = runner.invoke(cli, [
            'category', 'add',
            '--user-email', 'test@example.com',
            '--name', 'New Client - Hourly'
        ])

        assert result.exit_code == 0
        assert 'Category created successfully' in result.output
        mock_category_service.create.assert_called_once()

    def test_category_validate_command_with_issues(self, runner):
        """Test category validation with issues found."""
        with patch('cli.main.CategoryProcessingService') as mock_service:
            mock_service.return_value.get_category_statistics.return_value = {
                'total_appointments': 100,
                'valid_categories': 80,
                'invalid_categories': 20,
                'validation_issues': [
                    {'appointment_id': '123', 'issue': 'Invalid format'},
                    {'appointment_id': '456', 'issue': 'Missing billing type'}
                ]
            }

            result = runner.invoke(cli, [
                'category', 'validate',
                '--user-email', 'test@example.com',
                '--start-date', '2024-01-01',
                '--end-date', '2024-01-31'
            ])

            assert result.exit_code == 0
            assert 'Validation Issues Found' in result.output
            assert 'Invalid format' in result.output

    def test_category_delete_command_confirmation(self, runner, mock_category_service):
        """Test category deletion with confirmation."""
        mock_category_service.get_by_id.return_value = MagicMock(id=1, name='Test Category')

        result = runner.invoke(cli, [
            'category', 'delete',
            '--user-email', 'test@example.com',
            '--category-id', '1'
        ], input='y\n')

        assert result.exit_code == 0
        mock_category_service.delete.assert_called_once_with(1)
```

### 2. Auth Utility Tests (`tests/unit/utilities/test_auth_utility.py`)

```python
import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock, mock_open
from core.utilities.auth_utility import (
    ensure_secure_cache_dir,
    get_msal_app,
    msal_login,
    get_cached_access_token,
    msal_logout
)

class TestAuthUtility:
    def test_ensure_secure_cache_dir_creates_directory(self):
        """Test secure cache directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = os.path.join(temp_dir, 'test_cache')

            with patch('core.utilities.auth_utility.CACHE_DIR', cache_dir):
                ensure_secure_cache_dir()

                assert os.path.exists(cache_dir)
                # Check permissions (owner read/write/execute only)
                stat_info = os.stat(cache_dir)
                assert oct(stat_info.st_mode)[-3:] == '700'

    def test_ensure_secure_cache_dir_fixes_permissions(self):
        """Test fixing permissions on existing directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = os.path.join(temp_dir, 'test_cache')
            os.makedirs(cache_dir, mode=0o755)  # Insecure permissions

            with patch('core.utilities.auth_utility.CACHE_DIR', cache_dir):
                ensure_secure_cache_dir()

                stat_info = os.stat(cache_dir)
                assert oct(stat_info.st_mode)[-3:] == '700'

    @patch('core.utilities.auth_utility.msal.PublicClientApplication')
    @patch('core.utilities.auth_utility.msal.SerializableTokenCache')
    def test_get_msal_app_new_cache(self, mock_cache_class, mock_msal):
        """Test MSAL application creation with new cache."""
        mock_app = MagicMock()
        mock_cache = MagicMock()
        mock_msal.return_value = mock_app
        mock_cache_class.return_value = mock_cache

        with patch.dict(os.environ, {
            'MS_CLIENT_ID': 'test_client_id',
            'MS_TENANT_ID': 'test_tenant_id'
        }):
            with patch('core.utilities.auth_utility.os.path.exists', return_value=False):
                app, cache = get_msal_app()

                assert app == mock_app
                assert cache == mock_cache
                mock_msal.assert_called_once()

    @patch('core.utilities.auth_utility.get_msal_app')
    def test_msal_login_with_cached_token(self, mock_get_app):
        """Test login with cached valid token."""
        mock_app = MagicMock()
        mock_cache = MagicMock()
        mock_get_app.return_value = (mock_app, mock_cache)

        # Mock successful silent token acquisition
        mock_app.get_accounts.return_value = [{'account': 'test'}]
        mock_app.acquire_token_silent.return_value = {'access_token': 'token123'}

        with patch('builtins.open', mock_open()):
            with patch('core.utilities.auth_utility.os.chmod'):
                result = msal_login()

        assert result['access_token'] == 'token123'
        mock_app.acquire_token_silent.assert_called_once()

    @patch('core.utilities.auth_utility.get_msal_app')
    def test_msal_login_device_flow(self, mock_get_app):
        """Test login using device flow."""
        mock_app = MagicMock()
        mock_cache = MagicMock()
        mock_get_app.return_value = (mock_app, mock_cache)

        # Mock no cached accounts
        mock_app.get_accounts.return_value = []
        mock_app.acquire_token_silent.return_value = None

        # Mock device flow
        mock_app.initiate_device_flow.return_value = {
            'user_code': 'ABC123',
            'message': 'Enter code ABC123'
        }
        mock_app.acquire_token_by_device_flow.return_value = {'access_token': 'token123'}

        with patch('builtins.open', mock_open()):
            with patch('core.utilities.auth_utility.os.chmod'):
                with patch('builtins.print'):  # Mock print for device flow message
                    result = msal_login()

        assert result['access_token'] == 'token123'
        mock_app.initiate_device_flow.assert_called_once()

    @patch('core.utilities.auth_utility.os.path.exists')
    @patch('core.utilities.auth_utility.os.remove')
    def test_msal_logout(self, mock_remove, mock_exists):
        """Test token cleanup during logout."""
        mock_exists.return_value = True

        msal_logout()

        mock_remove.assert_called_once()

    @patch('core.utilities.auth_utility.get_msal_app')
    def test_get_cached_access_token_success(self, mock_get_app):
        """Test successful cached token retrieval."""
        mock_app = MagicMock()
        mock_cache = MagicMock()
        mock_get_app.return_value = (mock_app, mock_cache)

        mock_app.get_accounts.return_value = [{'account': 'test'}]
        mock_app.acquire_token_silent.return_value = {'access_token': 'cached_token'}

        result = get_cached_access_token()

        assert result == 'cached_token'

    @patch('core.utilities.auth_utility.get_msal_app')
    def test_get_cached_access_token_no_token(self, mock_get_app):
        """Test cached token retrieval when no token available."""
        mock_app = MagicMock()
        mock_cache = MagicMock()
        mock_get_app.return_value = (mock_app, mock_cache)

        mock_app.get_accounts.return_value = []

        result = get_cached_access_token()

        assert result is None
```

### 3. Background Job Service Enhanced Tests (`tests/unit/services/test_background_job_service_enhanced.py`)

```python
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, date
from core.services.background_job_service import BackgroundJobService

class TestBackgroundJobServiceEnhanced:
    @pytest.fixture
    def mock_scheduler(self):
        return MagicMock()

    @pytest.fixture
    def service(self, mock_scheduler):
        return BackgroundJobService(mock_scheduler)

    def test_schedule_weekly_archive_job(self, service, mock_scheduler):
        """Test weekly archive job scheduling."""
        service.schedule_weekly_archive_job(
            user_id=1,
            archive_config_id=1,
            day_of_week=1,  # Tuesday
            hour=9,
            minute=30
        )

        mock_scheduler.add_job.assert_called_once()
        call_args = mock_scheduler.add_job.call_args
        assert call_args[1]['trigger'] == 'cron'
        assert call_args[1]['day_of_week'] == 1
        assert call_args[1]['hour'] == 9
        assert call_args[1]['minute'] == 30

    def test_remove_scheduled_job_exists(self, service, mock_scheduler):
        """Test job removal when job exists."""
        job_id = 'test_job_123'
        mock_job = MagicMock()
        mock_scheduler.get_job.return_value = mock_job

        result = service.remove_scheduled_job(job_id)

        mock_scheduler.remove_job.assert_called_once_with(job_id)
        assert result is True

    def test_remove_scheduled_job_not_exists(self, service, mock_scheduler):
        """Test job removal when job doesn't exist."""
        job_id = 'nonexistent_job'
        mock_scheduler.get_job.return_value = None

        result = service.remove_scheduled_job(job_id)

        mock_scheduler.remove_job.assert_not_called()
        assert result is False

    @patch('core.services.background_job_service.CalendarArchiveOrchestrator')
    def test_run_scheduled_archive_success(self, mock_orchestrator, service):
        """Test successful scheduled archive execution."""
        mock_orchestrator_instance = MagicMock()
        mock_orchestrator.return_value = mock_orchestrator_instance
        mock_orchestrator_instance.archive_user_appointments.return_value = {
            'status': 'success',
            'archived_count': 5,
            'errors': []
        }

        with patch.object(service, 'archive_config_service') as mock_config_service:
            mock_config_service.get_by_id.return_value = MagicMock(is_active=True)

            result = service._run_scheduled_archive(1, 1)

            assert result['status'] == 'success'
            assert result['archived_count'] == 5

    def test_get_job_status_details(self, service, mock_scheduler):
        """Test detailed job status retrieval."""
        mock_job = MagicMock()
        mock_job.id = 'test_job'
        mock_job.next_run_time = datetime(2024, 1, 1, 9, 0)
        mock_job.trigger = MagicMock()
        mock_scheduler.get_jobs.return_value = [mock_job]

        status = service.get_job_status_details()

        assert len(status['jobs']) == 1
        assert status['jobs'][0]['id'] == 'test_job'
        assert status['total_jobs'] == 1

    def test_schedule_all_job_configurations_success(self, service):
        """Test bulk job configuration scheduling."""
        with patch.object(service, 'job_config_service') as mock_job_service:
            mock_configs = [
                MagicMock(id=1, schedule_type='daily', user_id=1),
                MagicMock(id=2, schedule_type='weekly', user_id=2)
            ]
            mock_job_service.get_scheduled_configs.return_value = mock_configs

            with patch.object(service, 'schedule_from_job_configuration') as mock_schedule:
                mock_schedule.return_value = 'job_123'

                result = service.schedule_all_job_configurations()

                assert len(result['scheduled_jobs']) == 2
                assert result['total_configs'] == 2
                assert len(result['failed_jobs']) == 0
```

### 4. Calendar Archive Service Tests (`tests/unit/services/test_calendar_archive_service.py`)

```python
import pytest
from unittest.mock import MagicMock, patch
from datetime import date
from core.services.calendar_archive_service import CalendarArchiveService

class TestCalendarArchiveService:
    @pytest.fixture
    def service(self):
        return CalendarArchiveService()

    @patch('core.services.calendar_archive_service.CalendarArchiveOrchestrator')
    def test_archive_appointments_basic(self, mock_orchestrator, service):
        """Test basic appointment archiving."""
        mock_orchestrator_instance = MagicMock()
        mock_orchestrator.return_value = mock_orchestrator_instance
        mock_orchestrator_instance.archive_user_appointments.return_value = {
            'status': 'success',
            'archived_count': 10,
            'errors': []
        }

        result = service.archive_appointments(
            user_id=1,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )

        assert result['status'] == 'success'
        assert result['archived_count'] == 10

    @patch('core.services.calendar_archive_service.CalendarArchiveOrchestrator')
    def test_archive_appointments_with_conflicts(self, mock_orchestrator, service):
        """Test archiving with overlap conflicts."""
        mock_orchestrator_instance = MagicMock()
        mock_orchestrator.return_value = mock_orchestrator_instance
        mock_orchestrator_instance.archive_user_appointments.return_value = {
            'status': 'overlap',
            'conflicts': [
                {'appointment_id': '123', 'conflict_type': 'time_overlap'}
            ]
        }

        result = service.archive_appointments(
            user_id=1,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )

        assert result['status'] == 'overlap'
        assert len(result['conflicts']) == 1

    def test_archive_appointments_error_scenarios(self, service):
        """Test error handling during archiving."""
        with patch('core.services.calendar_archive_service.CalendarArchiveOrchestrator') as mock_orchestrator:
            mock_orchestrator.side_effect = Exception('Archive service unavailable')

            with pytest.raises(Exception) as exc_info:
                service.archive_appointments(
                    user_id=1,
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 31)
                )

            assert 'Archive service unavailable' in str(exc_info.value)
```

## Integration Test Examples

### 5. CLI Integration Tests (`tests/integration/test_cli_integration.py`)

```python
import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from cli.main import cli

class TestCLIIntegration:
    @pytest.fixture
    def runner(self):
        return CliRunner()

    @patch('cli.main.CategoryService')
    @patch('cli.main.UserService')
    def test_cli_to_core_service_integration(self, mock_user_service, mock_category_service, runner):
        """Test CLI command integration with core services."""
        # Mock user lookup
        mock_user_service.return_value.get_by_email.return_value = MagicMock(id=1, email='test@example.com')

        # Mock category service
        mock_category_service.return_value.list.return_value = [
            MagicMock(id=1, name='Client A - Hourly'),
            MagicMock(id=2, name='Client B - Fixed')
        ]

        result = runner.invoke(cli, ['category', 'list', '--user-email', 'test@example.com'])

        assert result.exit_code == 0
        assert 'Client A - Hourly' in result.output
        # Verify service integration
        mock_user_service.return_value.get_by_email.assert_called_once_with('test@example.com')
        mock_category_service.return_value.list.assert_called_once()

    @patch('cli.main.msal_login')
    def test_cli_authentication_workflow(self, mock_msal_login, runner):
        """Test CLI authentication workflow."""
        mock_msal_login.return_value = {'access_token': 'test_token'}

        result = runner.invoke(cli, ['auth', 'login'])

        assert result.exit_code == 0
        assert 'Authentication successful' in result.output
        mock_msal_login.assert_called_once()

    def test_cli_error_propagation(self, runner):
        """Test error handling across CLI layers."""
        with patch('cli.main.CategoryService') as mock_service:
            mock_service.side_effect = Exception('Database connection failed')

            result = runner.invoke(cli, ['category', 'list', '--user-email', 'test@example.com'])

            assert result.exit_code != 0
            assert 'Error' in result.output
```

## Key Testing Patterns

These examples demonstrate:

1. **CLI Testing with Click**: Using `CliRunner` for command-line interface testing
2. **Comprehensive Mocking**: Proper mocking of external dependencies and services
3. **Authentication Testing**: Security-focused testing for auth utilities
4. **Service Integration**: Testing interactions between different layers
5. **Error Handling**: Robust error scenario testing
6. **File System Security**: Testing file permissions and security measures

The test cases focus on the core and CLI modules that will provide the highest coverage improvement with the most business value, targeting the gap from 61% to 80%+ coverage.
