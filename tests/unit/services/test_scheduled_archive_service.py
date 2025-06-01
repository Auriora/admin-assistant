"""
Unit tests for ScheduledArchiveService

Tests the business logic for managing scheduled archive operations including
auto-scheduling, schedule management, and health monitoring.
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from core.services.scheduled_archive_service import ScheduledArchiveService
from core.services.background_job_service import BackgroundJobService
from core.services.user_service import UserService
from core.services.archive_configuration_service import ArchiveConfigurationService
from core.services.job_configuration_service import JobConfigurationService
from core.models.archive_configuration import ArchiveConfiguration
from core.models.user import User


class TestScheduledArchiveService:
    """Test suite for ScheduledArchiveService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_background_job_service = Mock(spec=BackgroundJobService)
        self.mock_user_service = Mock(spec=UserService)
        self.mock_archive_config_service = Mock(spec=ArchiveConfigurationService)
        self.mock_job_config_service = Mock(spec=JobConfigurationService)
        
        self.service = ScheduledArchiveService(
            background_job_service=self.mock_background_job_service
        )
        # Replace the auto-created services with our mocks
        self.service.user_service = self.mock_user_service
        self.service.archive_config_service = self.mock_archive_config_service
        self.service.job_config_service = self.mock_job_config_service
    
    def test_init_with_background_job_service(self):
        """Test service initialization with provided background job service"""
        service = ScheduledArchiveService(
            background_job_service=self.mock_background_job_service
        )
        assert service.background_job_service == self.mock_background_job_service
    
    def test_init_with_default_background_job_service(self):
        """Test service initialization with default background job service"""
        service = ScheduledArchiveService()
        assert service.background_job_service is not None
        assert isinstance(service.background_job_service, BackgroundJobService)
    
    def test_set_background_job_service(self):
        """Test setting background job service"""
        new_service = Mock(spec=BackgroundJobService)
        self.service.set_background_job_service(new_service)
        assert self.service.background_job_service == new_service
    
    def test_schedule_all_active_users_success(self):
        """Test successful scheduling for all active users"""
        # Arrange
        mock_config1 = Mock(spec=ArchiveConfiguration)
        mock_config1.id = 1
        mock_config1.user_id = 123
        mock_config1.name = "Config 1"
        
        mock_config2 = Mock(spec=ArchiveConfiguration)
        mock_config2.id = 2
        mock_config2.user_id = 456
        mock_config2.name = "Config 2"
        
        mock_user1 = Mock(spec=User)
        mock_user1.email = "user1@example.com"
        
        mock_user2 = Mock(spec=User)
        mock_user2.email = "user2@example.com"
        
        self.mock_archive_config_service.get_all_active.return_value = [mock_config1, mock_config2]
        self.mock_user_service.get_by_id.side_effect = [mock_user1, mock_user2]
        self.mock_background_job_service.schedule_daily_archive_job.side_effect = ["job1", "job2"]
        
        # Act
        result = self.service.schedule_all_active_users()
        
        # Assert
        assert result["total_users"] == 2
        assert result["total_configs"] == 2
        assert len(result["scheduled_jobs"]) == 2
        assert len(result["failed_jobs"]) == 0
        assert len(result["skipped_jobs"]) == 0
        
        # Verify job scheduling calls
        assert self.mock_background_job_service.schedule_daily_archive_job.call_count == 2
        
        # Verify first job
        first_job = result["scheduled_jobs"][0]
        assert first_job["job_id"] == "job1"
        assert first_job["user_id"] == 123
        assert first_job["config_id"] == 1
        assert first_job["schedule_type"] == "daily"
    
    def test_schedule_all_active_users_weekly(self):
        """Test scheduling weekly jobs for all active users"""
        # Arrange
        mock_config = Mock(spec=ArchiveConfiguration)
        mock_config.id = 1
        mock_config.user_id = 123
        mock_config.name = "Config 1"
        
        mock_user = Mock(spec=User)
        mock_user.email = "user@example.com"
        
        self.mock_archive_config_service.get_all_active.return_value = [mock_config]
        self.mock_user_service.get_by_id.return_value = mock_user
        self.mock_background_job_service.schedule_weekly_archive_job.return_value = "weekly_job1"
        
        # Act
        result = self.service.schedule_all_active_users(
            schedule_type="weekly",
            day_of_week=1,
            hour=10,
            minute=30
        )
        
        # Assert
        assert len(result["scheduled_jobs"]) == 1
        job = result["scheduled_jobs"][0]
        assert job["schedule_type"] == "weekly"
        
        self.mock_background_job_service.schedule_weekly_archive_job.assert_called_once_with(
            user_id=123,
            archive_config_id=1,
            day_of_week=1,
            hour=10,
            minute=30
        )
    
    def test_schedule_all_active_users_user_not_found(self):
        """Test scheduling when user is not found"""
        # Arrange
        mock_config = Mock(spec=ArchiveConfiguration)
        mock_config.id = 1
        mock_config.user_id = 999
        mock_config.name = "Config 1"
        
        self.mock_archive_config_service.get_all_active.return_value = [mock_config]
        self.mock_user_service.get_by_id.return_value = None
        
        # Act
        result = self.service.schedule_all_active_users()
        
        # Assert
        assert len(result["scheduled_jobs"]) == 0
        assert len(result["skipped_jobs"]) == 1
        
        skipped = result["skipped_jobs"][0]
        assert skipped["user_id"] == 999
        assert skipped["reason"] == "User not found"
    
    def test_schedule_all_active_users_job_scheduling_failure(self):
        """Test scheduling when job scheduling fails"""
        # Arrange
        mock_config = Mock(spec=ArchiveConfiguration)
        mock_config.id = 1
        mock_config.user_id = 123
        mock_config.name = "Config 1"
        
        mock_user = Mock(spec=User)
        mock_user.email = "user@example.com"
        
        self.mock_archive_config_service.get_all_active.return_value = [mock_config]
        self.mock_user_service.get_by_id.return_value = mock_user
        self.mock_background_job_service.schedule_daily_archive_job.side_effect = Exception("Scheduling failed")
        
        # Act
        result = self.service.schedule_all_active_users()
        
        # Assert
        assert len(result["scheduled_jobs"]) == 0
        assert len(result["failed_jobs"]) == 1
        
        failed = result["failed_jobs"][0]
        assert failed["user_id"] == 123
        assert failed["config_id"] == 1
        assert failed["error"] == "Scheduling failed"
    
    def test_schedule_all_active_users_unsupported_schedule_type(self):
        """Test scheduling with unsupported schedule type"""
        # Arrange
        mock_config = Mock(spec=ArchiveConfiguration)
        mock_config.id = 1
        mock_config.user_id = 123
        mock_config.name = "Config 1"
        
        mock_user = Mock(spec=User)
        mock_user.email = "user@example.com"
        
        self.mock_archive_config_service.get_all_active.return_value = [mock_config]
        self.mock_user_service.get_by_id.return_value = mock_user
        
        # Act
        result = self.service.schedule_all_active_users(schedule_type="invalid")
        
        # Assert
        assert len(result["scheduled_jobs"]) == 0
        assert len(result["failed_jobs"]) == 1
        
        failed = result["failed_jobs"][0]
        assert "Unsupported schedule type: invalid" in failed["error"]
    
    def test_schedule_all_active_users_no_configs(self):
        """Test scheduling when no active configurations exist"""
        # Arrange
        self.mock_archive_config_service.get_all_active.return_value = []
        
        # Act
        result = self.service.schedule_all_active_users()
        
        # Assert
        assert result["total_users"] == 0
        assert result["total_configs"] == 0
        assert len(result["scheduled_jobs"]) == 0
        assert len(result["failed_jobs"]) == 0
        assert len(result["skipped_jobs"]) == 0
    
    def test_update_user_schedule_success(self):
        """Test successful user schedule update"""
        # Arrange
        mock_config = Mock(spec=ArchiveConfiguration)
        mock_config.id = 1
        mock_config.name = "Config 1"
        
        mock_user = Mock(spec=User)
        mock_user.email = "user@example.com"
        
        self.mock_archive_config_service.get_active_for_user.return_value = [mock_config]
        self.mock_user_service.get_by_id.return_value = mock_user
        self.mock_background_job_service.schedule_daily_archive_job.return_value = "new_job1"
        
        # Act
        result = self.service.update_user_schedule(
            user_id=123,
            schedule_type="daily",
            hour=10,
            minute=30
        )
        
        # Assert
        assert result["user_id"] == 123
        assert len(result["updated_jobs"]) == 1
        assert len(result["failed_jobs"]) == 0
        
        updated_job = result["updated_jobs"][0]
        assert updated_job["job_id"] == "new_job1"
        assert updated_job["config_id"] == 1
        assert updated_job["schedule_type"] == "daily"
        
        # Verify old jobs were removed
        expected_old_daily = "daily_archive_user_123_config_1"
        expected_old_weekly = "weekly_archive_user_123_config_1"
        self.mock_background_job_service.remove_job.assert_any_call(expected_old_daily)
        self.mock_background_job_service.remove_job.assert_any_call(expected_old_weekly)
    
    def test_update_user_schedule_no_configs(self):
        """Test user schedule update when no active configs exist"""
        # Arrange
        self.mock_archive_config_service.get_active_for_user.return_value = []
        
        # Act
        result = self.service.update_user_schedule(user_id=123)
        
        # Assert
        assert result["user_id"] == 123
        assert len(result["updated_jobs"]) == 0
        assert len(result["failed_jobs"]) == 0
    
    def test_update_user_schedule_user_not_found(self):
        """Test user schedule update when user is not found"""
        # Arrange
        mock_config = Mock(spec=ArchiveConfiguration)
        self.mock_archive_config_service.get_active_for_user.return_value = [mock_config]
        self.mock_user_service.get_by_id.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="User 123 not found"):
            self.service.update_user_schedule(user_id=123)
    
    def test_update_user_schedule_single_config(self):
        """Test user schedule update with single config (not in list)"""
        # Arrange
        mock_config = Mock(spec=ArchiveConfiguration)
        mock_config.id = 1
        mock_config.name = "Config 1"
        
        mock_user = Mock(spec=User)
        mock_user.email = "user@example.com"
        
        # Return single config, not a list
        self.mock_archive_config_service.get_active_for_user.return_value = mock_config
        self.mock_user_service.get_by_id.return_value = mock_user
        self.mock_background_job_service.schedule_daily_archive_job.return_value = "new_job1"
        
        # Act
        result = self.service.update_user_schedule(user_id=123)
        
        # Assert
        assert len(result["updated_jobs"]) == 1

    def test_remove_user_schedule_success(self):
        """Test successful removal of user schedules"""
        # Arrange
        mock_jobs = [
            {"id": "daily_archive_user_123_config_1", "trigger": "daily"},
            {"id": "weekly_archive_user_123_config_2", "trigger": "weekly"},
            {"id": "daily_archive_user_456_config_3", "trigger": "daily"}  # Different user
        ]

        self.mock_background_job_service.list_jobs.return_value = mock_jobs
        self.mock_background_job_service.remove_job.return_value = True

        # Act
        result = self.service.remove_user_schedule(user_id=123)

        # Assert
        assert result["user_id"] == 123
        assert len(result["removed_jobs"]) == 2  # Only jobs for user 123
        assert len(result["failed_removals"]) == 0

        # Verify correct jobs were removed
        assert "daily_archive_user_123_config_1" in result["removed_jobs"]
        assert "weekly_archive_user_123_config_2" in result["removed_jobs"]

        # Verify remove_job was called for user 123 jobs only
        assert self.mock_background_job_service.remove_job.call_count == 2

    def test_remove_user_schedule_removal_failure(self):
        """Test user schedule removal when job removal fails"""
        # Arrange
        mock_jobs = [
            {"id": "daily_archive_user_123_config_1", "trigger": "daily"}
        ]

        self.mock_background_job_service.list_jobs.return_value = mock_jobs
        self.mock_background_job_service.remove_job.return_value = False

        # Act
        result = self.service.remove_user_schedule(user_id=123)

        # Assert
        assert len(result["removed_jobs"]) == 0
        assert len(result["failed_removals"]) == 1

        failed = result["failed_removals"][0]
        assert failed["job_id"] == "daily_archive_user_123_config_1"
        assert failed["error"] == "Job removal returned False"

    def test_remove_user_schedule_exception(self):
        """Test user schedule removal when exception occurs"""
        # Arrange
        mock_jobs = [
            {"id": "daily_archive_user_123_config_1", "trigger": "daily"}
        ]

        self.mock_background_job_service.list_jobs.return_value = mock_jobs
        self.mock_background_job_service.remove_job.side_effect = Exception("Removal failed")

        # Act
        result = self.service.remove_user_schedule(user_id=123)

        # Assert
        assert len(result["removed_jobs"]) == 0
        assert len(result["failed_removals"]) == 1

        failed = result["failed_removals"][0]
        assert failed["job_id"] == "daily_archive_user_123_config_1"
        assert failed["error"] == "Removal failed"

    def test_get_user_schedule_status_with_configs_and_jobs(self):
        """Test getting user schedule status with configs and jobs"""
        # Arrange
        mock_config = Mock(spec=ArchiveConfiguration)
        mock_config.id = 1
        mock_config.name = "Config 1"
        mock_config.source_calendar_uri = "source://calendar"
        mock_config.destination_calendar_uri = "dest://calendar"

        mock_jobs = [
            {
                "id": "daily_archive_user_123_config_1",
                "trigger": "daily",
                "next_run_time": "2024-01-01T10:00:00",
                "args": [123, 1]
            }
        ]

        self.mock_archive_config_service.get_active_for_user.return_value = [mock_config]
        self.mock_background_job_service.list_jobs.return_value = mock_jobs

        # Act
        result = self.service.get_user_schedule_status(user_id=123)

        # Assert
        assert result["user_id"] == 123
        assert result["has_schedule"] is True
        assert len(result["active_configs"]) == 1
        assert len(result["scheduled_jobs"]) == 1

        config_info = result["active_configs"][0]
        assert config_info["id"] == 1
        assert config_info["name"] == "Config 1"

        job_info = result["scheduled_jobs"][0]
        assert job_info["job_id"] == "daily_archive_user_123_config_1"
        assert job_info["trigger"] == "daily"

    def test_get_user_schedule_status_no_configs(self):
        """Test getting user schedule status with no configs"""
        # Arrange
        self.mock_archive_config_service.get_active_for_user.return_value = []
        self.mock_background_job_service.list_jobs.return_value = []

        # Act
        result = self.service.get_user_schedule_status(user_id=123)

        # Assert
        assert result["user_id"] == 123
        assert result["has_schedule"] is False
        assert len(result["active_configs"]) == 0
        assert len(result["scheduled_jobs"]) == 0

    def test_get_user_schedule_status_single_config(self):
        """Test getting user schedule status with single config (not in list)"""
        # Arrange
        mock_config = Mock(spec=ArchiveConfiguration)
        mock_config.id = 1
        mock_config.name = "Config 1"
        mock_config.source_calendar_uri = "source://calendar"
        mock_config.destination_calendar_uri = "dest://calendar"

        # Return single config, not a list
        self.mock_archive_config_service.get_active_for_user.return_value = mock_config
        self.mock_background_job_service.list_jobs.return_value = []

        # Act
        result = self.service.get_user_schedule_status(user_id=123)

        # Assert
        assert len(result["active_configs"]) == 1

    def test_health_check_healthy(self):
        """Test health check when all jobs are healthy"""
        # Arrange
        mock_jobs = [
            {"id": "job1", "next_run_time": "2024-01-01T10:00:00"},
            {"id": "job2", "next_run_time": "2024-01-01T11:00:00"}
        ]

        mock_configs = [Mock(), Mock()]  # 2 active configs

        self.mock_background_job_service.list_jobs.return_value = mock_jobs
        self.mock_archive_config_service.get_all_active.return_value = mock_configs

        # Act
        result = self.service.health_check()

        # Assert
        assert result["status"] == "healthy"
        assert result["total_jobs"] == 2
        assert result["active_jobs"] == 2
        assert result["failed_jobs"] == 0
        assert len(result["issues"]) == 0
        assert "timestamp" in result

    def test_health_check_with_failed_jobs(self):
        """Test health check when some jobs have failed"""
        # Arrange
        mock_jobs = [
            {"id": "job1", "next_run_time": "2024-01-01T10:00:00"},
            {"id": "job2", "next_run_time": None}  # Failed job
        ]

        mock_configs = [Mock(), Mock()]

        self.mock_background_job_service.list_jobs.return_value = mock_jobs
        self.mock_archive_config_service.get_all_active.return_value = mock_configs

        # Act
        result = self.service.health_check()

        # Assert
        assert result["status"] == "unhealthy"
        assert result["active_jobs"] == 1
        assert result["failed_jobs"] == 1
        assert len(result["issues"]) == 2  # Failed job + job count mismatch
        assert "Job job2 has no next run time" in result["issues"]

    def test_health_check_missing_jobs(self):
        """Test health check when expected jobs are missing"""
        # Arrange
        mock_jobs = [
            {"id": "job1", "next_run_time": "2024-01-01T10:00:00"}
        ]

        mock_configs = [Mock(), Mock(), Mock()]  # 3 configs but only 1 job

        self.mock_background_job_service.list_jobs.return_value = mock_jobs
        self.mock_archive_config_service.get_all_active.return_value = mock_configs

        # Act
        result = self.service.health_check()

        # Assert
        assert result["status"] == "warning"
        assert "Expected 3 jobs but only 1 are active" in result["issues"]

    def test_health_check_exception(self):
        """Test health check when exception occurs"""
        # Arrange
        self.mock_background_job_service.list_jobs.side_effect = Exception("Service error")

        # Act
        result = self.service.health_check()

        # Assert
        assert result["status"] == "error"
        assert "Health check error: Service error" in result["issues"]

    def test_schedule_from_job_configurations(self):
        """Test scheduling from job configurations"""
        # Arrange
        expected_result = {"scheduled": 5, "failed": 0}
        self.mock_background_job_service.schedule_all_job_configurations.return_value = expected_result

        # Act
        result = self.service.schedule_from_job_configurations(user_id=123)

        # Assert
        assert result == expected_result
        self.mock_background_job_service.schedule_all_job_configurations.assert_called_once_with(
            user_id=123
        )

    def test_schedule_from_job_configurations_all_users(self):
        """Test scheduling from job configurations for all users"""
        # Arrange
        expected_result = {"scheduled": 10, "failed": 1}
        self.mock_background_job_service.schedule_all_job_configurations.return_value = expected_result

        # Act
        result = self.service.schedule_from_job_configurations()

        # Assert
        assert result == expected_result
        self.mock_background_job_service.schedule_all_job_configurations.assert_called_once_with(
            user_id=None
        )

    def test_create_default_job_configurations_success(self):
        """Test successful creation of default job configurations"""
        # Arrange
        mock_config1 = Mock(spec=ArchiveConfiguration)
        mock_config1.id = 1
        mock_config1.user_id = 123
        mock_config1.name = "Config 1"

        mock_config2 = Mock(spec=ArchiveConfiguration)
        mock_config2.id = 2
        mock_config2.user_id = 456
        mock_config2.name = "Config 2"

        self.mock_archive_config_service.get_all_active.return_value = [mock_config1, mock_config2]

        # Mock repository method
        mock_repo = Mock()
        self.mock_job_config_service.repository = mock_repo
        mock_repo.get_by_user_and_archive_config.return_value = None  # No existing configs

        # Act
        result = self.service.create_default_job_configurations()

        # Assert
        assert result["total_archive_configs"] == 2
        assert len(result["created_configs"]) == 2
        assert len(result["failed_configs"]) == 0
        assert len(result["skipped_configs"]) == 0

        # Verify job config service was called
        assert self.mock_job_config_service.create_default_for_archive_config.call_count == 2

    def test_create_default_job_configurations_for_user(self):
        """Test creation of default job configurations for specific user"""
        # Arrange
        mock_config = Mock(spec=ArchiveConfiguration)
        mock_config.id = 1
        mock_config.user_id = 123
        mock_config.name = "Config 1"

        self.mock_archive_config_service.get_active_for_user.return_value = [mock_config]

        # Mock repository method
        mock_repo = Mock()
        self.mock_job_config_service.repository = mock_repo
        mock_repo.get_by_user_and_archive_config.return_value = None

        # Act
        result = self.service.create_default_job_configurations(user_id=123)

        # Assert
        assert result["total_archive_configs"] == 1
        assert len(result["created_configs"]) == 1

        self.mock_archive_config_service.get_active_for_user.assert_called_once_with(123)

    def test_create_default_job_configurations_single_config(self):
        """Test creation when get_active_for_user returns single config"""
        # Arrange
        mock_config = Mock(spec=ArchiveConfiguration)
        mock_config.id = 1
        mock_config.user_id = 123
        mock_config.name = "Config 1"

        # Return single config, not a list
        self.mock_archive_config_service.get_active_for_user.return_value = mock_config

        # Mock repository method
        mock_repo = Mock()
        self.mock_job_config_service.repository = mock_repo
        mock_repo.get_by_user_and_archive_config.return_value = None

        # Act
        result = self.service.create_default_job_configurations(user_id=123)

        # Assert
        assert result["total_archive_configs"] == 1
        assert len(result["created_configs"]) == 1

    def test_create_default_job_configurations_existing_config(self):
        """Test creation when job configuration already exists"""
        # Arrange
        mock_config = Mock(spec=ArchiveConfiguration)
        mock_config.id = 1
        mock_config.user_id = 123
        mock_config.name = "Config 1"

        self.mock_archive_config_service.get_all_active.return_value = [mock_config]

        # Mock repository method - return existing config
        mock_repo = Mock()
        self.mock_job_config_service.repository = mock_repo
        mock_existing = Mock()
        mock_repo.get_by_user_and_archive_config.return_value = mock_existing

        # Act
        result = self.service.create_default_job_configurations()

        # Assert
        assert len(result["created_configs"]) == 0
        assert len(result["skipped_configs"]) == 1

        skipped = result["skipped_configs"][0]
        assert skipped["archive_config_id"] == 1
        assert skipped["reason"] == "JobConfiguration already exists"

    def test_create_default_job_configurations_creation_failure(self):
        """Test creation when job configuration creation fails"""
        # Arrange
        mock_config = Mock(spec=ArchiveConfiguration)
        mock_config.id = 1
        mock_config.user_id = 123
        mock_config.name = "Config 1"

        self.mock_archive_config_service.get_all_active.return_value = [mock_config]

        # Mock repository method
        mock_repo = Mock()
        self.mock_job_config_service.repository = mock_repo
        mock_repo.get_by_user_and_archive_config.return_value = None

        # Mock creation failure
        self.mock_job_config_service.create_default_for_archive_config.side_effect = Exception("Creation failed")

        # Act
        result = self.service.create_default_job_configurations()

        # Assert
        assert len(result["created_configs"]) == 0
        assert len(result["failed_configs"]) == 1

        failed = result["failed_configs"][0]
        assert failed["archive_config_id"] == 1
        assert failed["error"] == "Creation failed"

    def test_create_default_job_configurations_no_configs(self):
        """Test creation when no active archive configurations exist"""
        # Arrange
        self.mock_archive_config_service.get_all_active.return_value = []

        # Act
        result = self.service.create_default_job_configurations()

        # Assert
        assert result["total_archive_configs"] == 0
        assert len(result["created_configs"]) == 0
        assert len(result["failed_configs"]) == 0
        assert len(result["skipped_configs"]) == 0
