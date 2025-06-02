"""
Unit tests for BackgroundJobService

Tests the background job scheduling functionality including:
- Job scheduling (daily/weekly)
- Manual job triggering
- Job status monitoring
- Job removal
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime, timedelta
from core.services.background_job_service import BackgroundJobService
try:
    from tests.utils.test_helpers import ServiceMockHelper, MockValidator, assert_mock_called_with_subset
except ImportError:
    # Fallback for when running tests individually
    from utils.test_helpers import ServiceMockHelper, MockValidator, assert_mock_called_with_subset


class TestBackgroundJobService:
    """Test cases for BackgroundJobService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_scheduler = Mock()
        self.service = BackgroundJobService(self.mock_scheduler)
        
    def test_init_without_scheduler(self):
        """Test initialization without scheduler."""
        service = BackgroundJobService()
        assert service.scheduler is None
        
    def test_set_scheduler(self):
        """Test setting scheduler after initialization."""
        service = BackgroundJobService()
        mock_scheduler = Mock()
        service.set_scheduler(mock_scheduler)
        assert service.scheduler == mock_scheduler
        
    def test_schedule_daily_archive_job_success(self):
        """Test successful daily job scheduling."""
        # Setup mocks using helper
        mock_user_service = ServiceMockHelper.create_user_service_mock([
            {"id": 1, "email": "test@example.com", "name": "Test User"}
        ])
        mock_config_service = ServiceMockHelper.create_archive_config_service_mock([
            {"id": 1, "is_active": True, "name": "Test Config"}
        ])

        # Mock the service methods directly
        with patch.object(self.service.user_service, 'get_by_id', mock_user_service.get_by_id), \
             patch.object(self.service.archive_config_service, 'get_by_id', mock_config_service.get_by_id):

            self.mock_scheduler.get_job.return_value = None  # No existing job

            # Test
            job_id = self.service.schedule_daily_archive_job(
                user_id=1,
                archive_config_id=1,
                hour=10,
                minute=30
            )

            # Verify using improved assertions
            assert job_id == "daily_archive_user_1_config_1"
            self.mock_scheduler.add_job.assert_called_once()

            # Use helper to validate specific call arguments
            assert_mock_called_with_subset(
                self.mock_scheduler.add_job,
                id=job_id,
                trigger='cron',
                hour=10,
                minute=30
            )
        
    def test_schedule_daily_archive_job_user_not_found(self):
        """Test job scheduling with non-existent user."""
        with patch.object(self.service.user_service, 'get_by_id', return_value=None):
            with pytest.raises(ValueError, match="User with ID 999 not found"):
                self.service.schedule_daily_archive_job(
                    user_id=999,
                    archive_config_id=1
                )
            
    def test_schedule_daily_archive_job_config_not_found(self):
        """Test job scheduling with non-existent config."""
        mock_user = Mock()

        with patch.object(self.service.user_service, 'get_by_id', return_value=mock_user), \
             patch.object(self.service.archive_config_service, 'get_by_id', return_value=None):

            with pytest.raises(ValueError, match="Archive configuration with ID 999 not found"):
                self.service.schedule_daily_archive_job(
                    user_id=1,
                    archive_config_id=999
                )
            
    @patch('core.services.background_job_service.UserService')
    @patch('core.services.background_job_service.ArchiveConfigurationService')
    def test_schedule_daily_archive_job_config_inactive(self, mock_archive_service, mock_user_service):
        """Test job scheduling with inactive config."""
        mock_user = Mock()
        mock_user_service.return_value.get_by_id.return_value = mock_user

        mock_config = Mock()
        mock_config.is_active = False
        mock_archive_service.return_value.get_by_id.return_value = mock_config

        # Create a new service instance after patches are applied
        service = BackgroundJobService(self.mock_scheduler)

        with pytest.raises(ValueError, match="Archive configuration 1 is not active"):
            service.schedule_daily_archive_job(
                user_id=1,
                archive_config_id=1
            )
            
    def test_schedule_daily_archive_job_no_scheduler(self):
        """Test job scheduling without scheduler."""
        service = BackgroundJobService()
        
        with pytest.raises(ValueError, match="Scheduler not initialized"):
            service.schedule_daily_archive_job(
                user_id=1,
                archive_config_id=1
            )
            
    def test_schedule_weekly_archive_job_success(self):
        """Test successful weekly job scheduling."""
        # Setup mocks
        mock_user = Mock()
        mock_user.email = "test@example.com"

        mock_config = Mock()
        mock_config.is_active = True

        # Mock the service methods directly
        with patch.object(self.service.user_service, 'get_by_id', return_value=mock_user), \
             patch.object(self.service.archive_config_service, 'get_by_id', return_value=mock_config):

            self.mock_scheduler.get_job.return_value = None  # No existing job

            # Test
            job_id = self.service.schedule_weekly_archive_job(
                user_id=1,
                archive_config_id=1,
                day_of_week=5,  # Friday
                hour=14,
                minute=0
            )
        
            # Verify
            assert job_id == "weekly_archive_user_1_config_1"
            self.mock_scheduler.add_job.assert_called_once()
            call_args = self.mock_scheduler.add_job.call_args
            assert call_args[1]['id'] == job_id
            assert call_args[1]['trigger'] == 'cron'
            assert call_args[1]['day_of_week'] == 5
            assert call_args[1]['hour'] == 14
            assert call_args[1]['minute'] == 0
        
    def test_trigger_manual_archive_success(self):
        """Test successful manual archive triggering."""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 15)
        
        job_id = self.service.trigger_manual_archive(
            user_id=1,
            archive_config_id=1,
            start_date=start_date,
            end_date=end_date
        )
        
        # Verify job ID format
        assert job_id.startswith("manual_archive_1_1_")
        
        # Verify scheduler was called
        self.mock_scheduler.add_job.assert_called_once()
        call_args = self.mock_scheduler.add_job.call_args
        assert call_args[1]['trigger'] == 'date'
        assert len(call_args[1]['args']) == 4  # user_id, config_id, start_date, end_date
        
    def test_trigger_manual_archive_default_dates(self):
        """Test manual archive with default dates (yesterday)."""
        job_id = self.service.trigger_manual_archive(
            user_id=1,
            archive_config_id=1
        )
        
        # Verify job was scheduled
        assert job_id.startswith("manual_archive_1_1_")
        self.mock_scheduler.add_job.assert_called_once()
        
    def test_remove_job_success(self):
        """Test successful job removal."""
        job_id = "test_job_123"
        
        result = self.service.remove_job(job_id)
        
        assert result is True
        self.mock_scheduler.remove_job.assert_called_once_with(job_id)
        
    def test_remove_job_failure(self):
        """Test job removal failure."""
        job_id = "nonexistent_job"
        self.mock_scheduler.remove_job.side_effect = Exception("Job not found")
        
        result = self.service.remove_job(job_id)
        
        assert result is False
        
    def test_get_job_status_success(self):
        """Test successful job status retrieval."""
        mock_job = Mock()
        mock_job.id = "test_job"
        mock_job.name = "Test Job"
        mock_job.func = "test_function"
        mock_job.trigger = "cron"
        mock_job.next_run_time = datetime(2024, 1, 15, 10, 30)
        mock_job.args = [1, 2]
        mock_job.kwargs = {'key': 'value'}
        
        self.mock_scheduler.get_job.return_value = mock_job
        
        status = self.service.get_job_status("test_job")
        
        assert status is not None
        assert status['id'] == "test_job"
        assert status['name'] == "Test Job"
        assert status['next_run_time'] == datetime(2024, 1, 15, 10, 30)
        
    def test_get_job_status_not_found(self):
        """Test job status retrieval for non-existent job."""
        self.mock_scheduler.get_job.return_value = None
        
        status = self.service.get_job_status("nonexistent_job")
        
        assert status is None
        
    def test_list_jobs_success(self):
        """Test successful job listing."""
        mock_job1 = Mock()
        mock_job1.id = "job1"
        mock_job1.name = "Job 1"
        mock_job1.func = "function1"
        mock_job1.trigger = "cron"
        mock_job1.next_run_time = datetime(2024, 1, 15, 10, 30)
        mock_job1.args = []
        mock_job1.kwargs = {}
        
        mock_job2 = Mock()
        mock_job2.id = "job2"
        mock_job2.name = "Job 2"
        mock_job2.func = "function2"
        mock_job2.trigger = "interval"
        mock_job2.next_run_time = datetime(2024, 1, 15, 11, 0)
        mock_job2.args = [1]
        mock_job2.kwargs = {'test': True}
        
        self.mock_scheduler.get_jobs.return_value = [mock_job1, mock_job2]
        
        jobs = self.service.list_jobs()
        
        assert len(jobs) == 2
        assert jobs[0]['id'] == "job1"
        assert jobs[1]['id'] == "job2"
        
    def test_list_jobs_empty(self):
        """Test job listing with no jobs."""
        self.mock_scheduler.get_jobs.return_value = []
        
        jobs = self.service.list_jobs()
        
        assert jobs == []
        
    @patch('core.services.background_job_service.logger')
    def test_run_scheduled_archive_success(self, mock_logger):
        """Test successful scheduled archive execution."""
        # Mock the job config service to return no job configs (uses default 1 day window)
        with patch.object(self.service.job_config_service, 'get_by_archive_config_id') as mock_get_configs:
            mock_get_configs.return_value = []

            with patch.object(self.service.archive_runner, 'run_archive_job') as mock_run:
                mock_run.return_value = {'status': 'success', 'archived_count': 5}

                # Call the internal method directly
                self.service._run_scheduled_archive(1, 1)

                # Verify archive runner was called with yesterday's date
                yesterday = date.today() - timedelta(days=1)
                mock_run.assert_called_once_with(
                    user_id=1,
                    archive_config_id=1,
                    start_date=yesterday,
                    end_date=yesterday
                )
            
    @patch('core.services.background_job_service.logger')
    def test_run_scheduled_archive_error(self, mock_logger):
        """Test scheduled archive execution with error."""
        # Mock the job config service to return no job configs (uses default 1 day window)
        with patch.object(self.service.job_config_service, 'get_by_archive_config_id') as mock_get_configs:
            mock_get_configs.return_value = []

            with patch.object(self.service.archive_runner, 'run_archive_job') as mock_run:
                mock_run.return_value = {'status': 'error', 'error': 'Test error'}

                # Call the internal method directly
                self.service._run_scheduled_archive(1, 1)

                # Verify error was logged
                mock_logger.error.assert_called_once()
            
    @patch('core.services.background_job_service.logger')
    def test_run_manual_archive_success(self, mock_logger):
        """Test successful manual archive execution."""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 15)
        
        with patch.object(self.service.archive_runner, 'run_archive_job') as mock_run:
            mock_run.return_value = {'status': 'success', 'archived_count': 3}
            
            # Call the internal method directly
            self.service._run_manual_archive(1, 1, start_date, end_date)
            
            # Verify archive runner was called with correct parameters
            mock_run.assert_called_once_with(
                user_id=1,
                archive_config_id=1,
                start_date=start_date,
                end_date=end_date
            )
