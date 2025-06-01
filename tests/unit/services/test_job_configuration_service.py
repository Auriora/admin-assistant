"""
Tests for job_configuration_service module.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, UTC
from typing import List, Optional

from core.services.job_configuration_service import JobConfigurationService
from core.models.job_configuration import JobConfiguration
from core.models.user import User
from core.models.archive_configuration import ArchiveConfiguration


class TestJobConfigurationService:
    """Test cases for JobConfigurationService class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.mock_repository = Mock()
        self.mock_archive_config_repository = Mock()
        self.mock_user_repository = Mock()
        self.service = JobConfigurationService(
            self.mock_repository,
            self.mock_archive_config_repository,
            self.mock_user_repository
        )

    @patch('core.services.job_configuration_service.JobConfigurationRepository')
    @patch('core.services.job_configuration_service.ArchiveConfigurationRepository')
    @patch('core.services.job_configuration_service.UserRepository')
    def test_init_with_default_repositories(self, mock_user_repo_class, mock_archive_repo_class, mock_job_repo_class):
        """Test initialization with default repositories."""
        # Arrange
        mock_job_repo_instance = Mock()
        mock_archive_repo_instance = Mock()
        mock_user_repo_instance = Mock()
        
        mock_job_repo_class.return_value = mock_job_repo_instance
        mock_archive_repo_class.return_value = mock_archive_repo_instance
        mock_user_repo_class.return_value = mock_user_repo_instance
        
        # Act
        service = JobConfigurationService()
        
        # Assert
        mock_job_repo_class.assert_called_once_with()
        mock_archive_repo_class.assert_called_once_with()
        mock_user_repo_class.assert_called_once_with()
        assert service.repository == mock_job_repo_instance
        assert service.archive_config_repository == mock_archive_repo_instance
        assert service.user_repository == mock_user_repo_instance

    def test_init_with_provided_repositories(self):
        """Test initialization with provided repositories."""
        # Arrange & Act
        service = JobConfigurationService(
            self.mock_repository,
            self.mock_archive_config_repository,
            self.mock_user_repository
        )
        
        # Assert
        assert service.repository == self.mock_repository
        assert service.archive_config_repository == self.mock_archive_config_repository
        assert service.user_repository == self.mock_user_repository

    def test_get_by_id_success(self):
        """Test successful retrieval of job configuration by ID."""
        # Arrange
        job_config_id = 1
        expected_config = Mock(spec=JobConfiguration)
        self.mock_repository.get_by_id.return_value = expected_config
        
        # Act
        result = self.service.get_by_id(job_config_id)
        
        # Assert
        assert result == expected_config
        self.mock_repository.get_by_id.assert_called_once_with(job_config_id)

    def test_get_by_id_not_found(self):
        """Test retrieval when job configuration is not found."""
        # Arrange
        job_config_id = 999
        self.mock_repository.get_by_id.return_value = None
        
        # Act
        result = self.service.get_by_id(job_config_id)
        
        # Assert
        assert result is None
        self.mock_repository.get_by_id.assert_called_once_with(job_config_id)

    def test_get_by_user_id(self):
        """Test retrieving job configurations by user ID."""
        # Arrange
        user_id = 123
        expected_configs = [Mock(spec=JobConfiguration), Mock(spec=JobConfiguration)]
        self.mock_repository.get_by_user_id.return_value = expected_configs
        
        # Act
        result = self.service.get_by_user_id(user_id)
        
        # Assert
        assert result == expected_configs
        self.mock_repository.get_by_user_id.assert_called_once_with(user_id)

    def test_get_by_archive_config_id(self):
        """Test retrieving job configurations by archive config ID."""
        # Arrange
        archive_config_id = 456
        expected_configs = [Mock(spec=JobConfiguration)]
        self.mock_repository.get_by_archive_config_id.return_value = expected_configs
        
        # Act
        result = self.service.get_by_archive_config_id(archive_config_id)
        
        # Assert
        assert result == expected_configs
        self.mock_repository.get_by_archive_config_id.assert_called_once_with(archive_config_id)

    def test_get_active_by_user_id(self):
        """Test retrieving active job configurations by user ID."""
        # Arrange
        user_id = 123
        expected_configs = [Mock(spec=JobConfiguration)]
        self.mock_repository.get_active_by_user_id.return_value = expected_configs
        
        # Act
        result = self.service.get_active_by_user_id(user_id)
        
        # Assert
        assert result == expected_configs
        self.mock_repository.get_active_by_user_id.assert_called_once_with(user_id)

    def test_create_success(self):
        """Test successful creation of job configuration."""
        # Arrange
        job_config = Mock(spec=JobConfiguration)
        job_config.user_id = 123
        job_config.archive_configuration_id = 456
        job_config.validate = Mock()
        
        # Mock validation dependencies
        user = Mock(spec=User)
        archive_config = Mock(spec=ArchiveConfiguration)
        archive_config.user_id = 123
        
        self.mock_user_repository.get_by_id.return_value = user
        self.mock_archive_config_repository.get_by_id.return_value = archive_config
        self.mock_repository.get_by_user_and_archive_config.return_value = None  # No existing config
        
        # Act
        result = self.service.create(job_config)
        
        # Assert
        assert result == job_config
        job_config.validate.assert_called_once()
        self.mock_user_repository.get_by_id.assert_called_once_with(123)
        self.mock_archive_config_repository.get_by_id.assert_called_once_with(456)
        self.mock_repository.get_by_user_and_archive_config.assert_called_once_with(123, 456)
        self.mock_repository.add.assert_called_once_with(job_config)

    def test_create_duplicate_config_error(self):
        """Test creation fails when duplicate configuration exists."""
        # Arrange
        job_config = Mock(spec=JobConfiguration)
        job_config.user_id = 123
        job_config.archive_configuration_id = 456
        job_config.validate = Mock()
        
        # Mock validation dependencies
        user = Mock(spec=User)
        archive_config = Mock(spec=ArchiveConfiguration)
        archive_config.user_id = 123
        existing_config = Mock(spec=JobConfiguration)
        
        self.mock_user_repository.get_by_id.return_value = user
        self.mock_archive_config_repository.get_by_id.return_value = archive_config
        self.mock_repository.get_by_user_and_archive_config.return_value = existing_config
        
        # Act & Assert
        with pytest.raises(ValueError, match="JobConfiguration already exists for user 123 and archive config 456"):
            self.service.create(job_config)
        
        job_config.validate.assert_called_once()
        self.mock_repository.add.assert_not_called()

    def test_create_validation_error(self):
        """Test creation fails when validation fails."""
        # Arrange
        job_config = Mock(spec=JobConfiguration)
        job_config.validate.side_effect = ValueError("Invalid schedule type")
        
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid schedule type"):
            self.service.create(job_config)
        
        job_config.validate.assert_called_once()
        self.mock_repository.add.assert_not_called()

    def test_create_user_not_found_error(self):
        """Test creation fails when user doesn't exist."""
        # Arrange
        job_config = Mock(spec=JobConfiguration)
        job_config.user_id = 999
        job_config.archive_configuration_id = 456
        job_config.validate = Mock()
        
        self.mock_user_repository.get_by_id.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="User with ID 999 not found"):
            self.service.create(job_config)
        
        self.mock_repository.add.assert_not_called()

    def test_create_archive_config_not_found_error(self):
        """Test creation fails when archive config doesn't exist."""
        # Arrange
        job_config = Mock(spec=JobConfiguration)
        job_config.user_id = 123
        job_config.archive_configuration_id = 999
        job_config.validate = Mock()
        
        user = Mock(spec=User)
        self.mock_user_repository.get_by_id.return_value = user
        self.mock_archive_config_repository.get_by_id.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="ArchiveConfiguration with ID 999 not found"):
            self.service.create(job_config)
        
        self.mock_repository.add.assert_not_called()

    def test_create_archive_config_user_mismatch_error(self):
        """Test creation fails when archive config belongs to different user."""
        # Arrange
        job_config = Mock(spec=JobConfiguration)
        job_config.user_id = 123
        job_config.archive_configuration_id = 456
        job_config.validate = Mock()
        
        user = Mock(spec=User)
        archive_config = Mock(spec=ArchiveConfiguration)
        archive_config.user_id = 999  # Different user
        
        self.mock_user_repository.get_by_id.return_value = user
        self.mock_archive_config_repository.get_by_id.return_value = archive_config
        
        # Act & Assert
        with pytest.raises(ValueError, match="ArchiveConfiguration 456 does not belong to user 123"):
            self.service.create(job_config)
        
        self.mock_repository.add.assert_not_called()

    @patch('core.services.job_configuration_service.datetime')
    def test_update_success(self, mock_datetime):
        """Test successful update of job configuration."""
        # Arrange
        mock_now = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_now

        job_config = Mock(spec=JobConfiguration)
        job_config.user_id = 123
        job_config.archive_configuration_id = 456
        job_config.validate = Mock()

        # Mock validation dependencies
        user = Mock(spec=User)
        archive_config = Mock(spec=ArchiveConfiguration)
        archive_config.user_id = 123

        self.mock_user_repository.get_by_id.return_value = user
        self.mock_archive_config_repository.get_by_id.return_value = archive_config

        # Act
        result = self.service.update(job_config)

        # Assert
        assert result == job_config
        assert job_config.updated_at == mock_now
        job_config.validate.assert_called_once()
        self.mock_repository.update.assert_called_once_with(job_config)

    def test_delete_success(self):
        """Test successful deletion of job configuration."""
        # Arrange
        job_config_id = 1
        self.mock_repository.delete.return_value = True

        # Act
        result = self.service.delete(job_config_id)

        # Assert
        assert result is True
        self.mock_repository.delete.assert_called_once_with(job_config_id)

    def test_delete_not_found(self):
        """Test deletion when job configuration doesn't exist."""
        # Arrange
        job_config_id = 999
        self.mock_repository.delete.return_value = False

        # Act
        result = self.service.delete(job_config_id)

        # Assert
        assert result is False
        self.mock_repository.delete.assert_called_once_with(job_config_id)

    def test_list_no_filters(self):
        """Test listing job configurations without filters."""
        # Arrange
        expected_configs = [Mock(spec=JobConfiguration), Mock(spec=JobConfiguration)]
        self.mock_repository.list.return_value = expected_configs

        # Act
        result = self.service.list()

        # Assert
        assert result == expected_configs
        self.mock_repository.list.assert_called_once_with(user_id=None, is_active=None)

    def test_list_with_filters(self):
        """Test listing job configurations with filters."""
        # Arrange
        user_id = 123
        is_active = True
        expected_configs = [Mock(spec=JobConfiguration)]
        self.mock_repository.list.return_value = expected_configs

        # Act
        result = self.service.list(user_id=user_id, is_active=is_active)

        # Assert
        assert result == expected_configs
        self.mock_repository.list.assert_called_once_with(user_id=user_id, is_active=is_active)

    @patch('core.services.job_configuration_service.datetime')
    def test_activate_success(self, mock_datetime):
        """Test successful activation of job configuration."""
        # Arrange
        mock_now = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_now

        job_config_id = 1
        job_config = Mock(spec=JobConfiguration)
        job_config.is_active = False

        self.mock_repository.get_by_id.return_value = job_config

        # Act
        result = self.service.activate(job_config_id)

        # Assert
        assert result == job_config
        assert job_config.is_active is True
        assert job_config.updated_at == mock_now
        self.mock_repository.get_by_id.assert_called_once_with(job_config_id)
        self.mock_repository.update.assert_called_once_with(job_config)

    def test_activate_not_found(self):
        """Test activation when job configuration doesn't exist."""
        # Arrange
        job_config_id = 999
        self.mock_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="JobConfiguration with ID 999 not found"):
            self.service.activate(job_config_id)

        self.mock_repository.update.assert_not_called()

    @patch('core.services.job_configuration_service.datetime')
    def test_deactivate_success(self, mock_datetime):
        """Test successful deactivation of job configuration."""
        # Arrange
        mock_now = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_now

        job_config_id = 1
        job_config = Mock(spec=JobConfiguration)
        job_config.is_active = True

        self.mock_repository.get_by_id.return_value = job_config

        # Act
        result = self.service.deactivate(job_config_id)

        # Assert
        assert result == job_config
        assert job_config.is_active is False
        assert job_config.updated_at == mock_now
        self.mock_repository.get_by_id.assert_called_once_with(job_config_id)
        self.mock_repository.update.assert_called_once_with(job_config)

    def test_deactivate_not_found(self):
        """Test deactivation when job configuration doesn't exist."""
        # Arrange
        job_config_id = 999
        self.mock_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="JobConfiguration with ID 999 not found"):
            self.service.deactivate(job_config_id)

        self.mock_repository.update.assert_not_called()

    def test_get_scheduled_configs_no_filter(self):
        """Test getting scheduled configurations without filter."""
        # Arrange
        expected_configs = [Mock(spec=JobConfiguration), Mock(spec=JobConfiguration)]
        self.mock_repository.get_scheduled_configs.return_value = expected_configs

        # Act
        result = self.service.get_scheduled_configs()

        # Assert
        assert result == expected_configs
        self.mock_repository.get_scheduled_configs.assert_called_once_with(schedule_type=None)

    def test_get_scheduled_configs_with_filter(self):
        """Test getting scheduled configurations with schedule type filter."""
        # Arrange
        schedule_type = "daily"
        expected_configs = [Mock(spec=JobConfiguration)]
        self.mock_repository.get_scheduled_configs.return_value = expected_configs

        # Act
        result = self.service.get_scheduled_configs(schedule_type=schedule_type)

        # Assert
        assert result == expected_configs
        self.mock_repository.get_scheduled_configs.assert_called_once_with(schedule_type=schedule_type)

    def test_create_default_for_archive_config_success(self):
        """Test successful creation of default job configuration."""
        # Arrange
        archive_config_id = 456
        archive_config = Mock(spec=ArchiveConfiguration)
        archive_config.user_id = 123

        self.mock_archive_config_repository.get_by_id.return_value = archive_config
        self.mock_repository.get_by_user_and_archive_config.return_value = None  # No existing config

        # Mock the create method to avoid full validation
        created_config = Mock(spec=JobConfiguration)
        self.service.create = Mock(return_value=created_config)

        # Act
        result = self.service.create_default_for_archive_config(archive_config_id)

        # Assert
        assert result == created_config
        self.mock_archive_config_repository.get_by_id.assert_called_once_with(archive_config_id)
        self.mock_repository.get_by_user_and_archive_config.assert_called_once_with(123, archive_config_id)

        # Verify the JobConfiguration was created with correct defaults
        self.service.create.assert_called_once()
        created_job_config = self.service.create.call_args[0][0]
        assert created_job_config.user_id == 123
        assert created_job_config.archive_configuration_id == archive_config_id
        assert created_job_config.archive_window_days == 30
        assert created_job_config.schedule_type == "daily"
        assert created_job_config.schedule_hour == 23
        assert created_job_config.schedule_minute == 59
        assert created_job_config.schedule_day_of_week is None
        assert created_job_config.is_active is True

    def test_create_default_for_archive_config_with_custom_params(self):
        """Test creation of default job configuration with custom parameters."""
        # Arrange
        archive_config_id = 456
        archive_config = Mock(spec=ArchiveConfiguration)
        archive_config.user_id = 123

        self.mock_archive_config_repository.get_by_id.return_value = archive_config
        self.mock_repository.get_by_user_and_archive_config.return_value = None

        created_config = Mock(spec=JobConfiguration)
        self.service.create = Mock(return_value=created_config)

        # Act
        result = self.service.create_default_for_archive_config(
            archive_config_id,
            schedule_type="weekly",
            schedule_hour=9,
            schedule_minute=0,
            schedule_day_of_week=1,  # Tuesday
            archive_window_days=60
        )

        # Assert
        assert result == created_config
        created_job_config = self.service.create.call_args[0][0]
        assert created_job_config.schedule_type == "weekly"
        assert created_job_config.schedule_hour == 9
        assert created_job_config.schedule_minute == 0
        assert created_job_config.schedule_day_of_week == 1
        assert created_job_config.archive_window_days == 60

    def test_create_default_for_archive_config_archive_not_found(self):
        """Test creation fails when archive configuration doesn't exist."""
        # Arrange
        archive_config_id = 999
        self.mock_archive_config_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="ArchiveConfiguration with ID 999 not found"):
            self.service.create_default_for_archive_config(archive_config_id)

        self.mock_repository.get_by_user_and_archive_config.assert_not_called()

    def test_create_default_for_archive_config_already_exists(self):
        """Test creation fails when job configuration already exists."""
        # Arrange
        archive_config_id = 456
        archive_config = Mock(spec=ArchiveConfiguration)
        archive_config.user_id = 123
        existing_config = Mock(spec=JobConfiguration)

        self.mock_archive_config_repository.get_by_id.return_value = archive_config
        self.mock_repository.get_by_user_and_archive_config.return_value = existing_config

        # Act & Assert
        with pytest.raises(ValueError, match="JobConfiguration already exists for archive config 456"):
            self.service.create_default_for_archive_config(archive_config_id)

    def test_sync_with_archive_config_status_activate(self):
        """Test syncing job configurations when archive config is active."""
        # Arrange
        archive_config_id = 456
        archive_config = Mock(spec=ArchiveConfiguration)
        archive_config.is_active = True

        self.mock_archive_config_repository.get_by_id.return_value = archive_config
        self.mock_repository.activate_by_archive_config_id.return_value = 3

        # Act
        result = self.service.sync_with_archive_config_status(archive_config_id)

        # Assert
        assert result == {"action": "activated", "count": 3}
        self.mock_archive_config_repository.get_by_id.assert_called_once_with(archive_config_id)
        self.mock_repository.activate_by_archive_config_id.assert_called_once_with(archive_config_id)

    def test_sync_with_archive_config_status_deactivate(self):
        """Test syncing job configurations when archive config is inactive."""
        # Arrange
        archive_config_id = 456
        archive_config = Mock(spec=ArchiveConfiguration)
        archive_config.is_active = False

        self.mock_archive_config_repository.get_by_id.return_value = archive_config
        self.mock_repository.deactivate_by_archive_config_id.return_value = 2

        # Act
        result = self.service.sync_with_archive_config_status(archive_config_id)

        # Assert
        assert result == {"action": "deactivated", "count": 2}
        self.mock_archive_config_repository.get_by_id.assert_called_once_with(archive_config_id)
        self.mock_repository.deactivate_by_archive_config_id.assert_called_once_with(archive_config_id)

    def test_sync_with_archive_config_status_not_found(self):
        """Test syncing fails when archive configuration doesn't exist."""
        # Arrange
        archive_config_id = 999
        self.mock_archive_config_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="ArchiveConfiguration with ID 999 not found"):
            self.service.sync_with_archive_config_status(archive_config_id)

    def test_validate_success(self):
        """Test successful validation of job configuration."""
        # Arrange
        job_config = Mock(spec=JobConfiguration)
        job_config.validate = Mock()

        # Act - should not raise exception
        self.service.validate(job_config)

        # Assert
        job_config.validate.assert_called_once()

    def test_validate_none_config(self):
        """Test validation fails for None job configuration."""
        # Act & Assert
        with pytest.raises(ValueError, match="JobConfiguration cannot be None"):
            self.service.validate(None)

    def test_validate_model_validation_error(self):
        """Test validation fails when model validation fails."""
        # Arrange
        job_config = Mock(spec=JobConfiguration)
        job_config.validate.side_effect = ValueError("Invalid schedule type")

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid schedule type"):
            self.service.validate(job_config)

        job_config.validate.assert_called_once()

    def test_get_summary_for_user_with_configs(self):
        """Test getting user summary with multiple configurations."""
        # Arrange
        user_id = 123

        # Create mock configurations
        config1 = Mock(spec=JobConfiguration)
        config1.id = 1
        config1.archive_configuration_id = 101
        config1.schedule_type = "daily"
        config1.archive_window_days = 30
        config1.is_active = True
        config1.get_schedule_description.return_value = "Daily at 23:59"

        config2 = Mock(spec=JobConfiguration)
        config2.id = 2
        config2.archive_configuration_id = 102
        config2.schedule_type = "weekly"
        config2.archive_window_days = 60
        config2.is_active = True
        config2.get_schedule_description.return_value = "Weekly on Monday at 09:00"

        config3 = Mock(spec=JobConfiguration)
        config3.id = 3
        config3.archive_configuration_id = 103
        config3.schedule_type = "daily"
        config3.archive_window_days = 14
        config3.is_active = False
        config3.get_schedule_description.return_value = "Daily at 12:00"

        all_configs = [config1, config2, config3]
        self.mock_repository.get_by_user_id.return_value = all_configs

        # Act
        result = self.service.get_summary_for_user(user_id)

        # Assert
        assert result["total_configs"] == 3
        assert result["active_configs"] == 2
        assert result["inactive_configs"] == 1
        assert result["schedule_types"] == {"daily": 1, "weekly": 1}

        assert len(result["configs"]) == 3

        # Check first config details
        config1_summary = result["configs"][0]
        assert config1_summary["id"] == 1
        assert config1_summary["archive_config_id"] == 101
        assert config1_summary["schedule_description"] == "Daily at 23:59"
        assert config1_summary["archive_window_days"] == 30
        assert config1_summary["is_active"] is True

        self.mock_repository.get_by_user_id.assert_called_once_with(user_id)

    def test_get_summary_for_user_no_configs(self):
        """Test getting user summary when user has no configurations."""
        # Arrange
        user_id = 123
        self.mock_repository.get_by_user_id.return_value = []

        # Act
        result = self.service.get_summary_for_user(user_id)

        # Assert
        assert result["total_configs"] == 0
        assert result["active_configs"] == 0
        assert result["inactive_configs"] == 0
        assert result["schedule_types"] == {}
        assert result["configs"] == []

        self.mock_repository.get_by_user_id.assert_called_once_with(user_id)

    def test_get_summary_for_user_all_inactive(self):
        """Test getting user summary when all configurations are inactive."""
        # Arrange
        user_id = 123

        config1 = Mock(spec=JobConfiguration)
        config1.id = 1
        config1.archive_configuration_id = 101
        config1.schedule_type = "daily"
        config1.archive_window_days = 30
        config1.is_active = False
        config1.get_schedule_description.return_value = "Daily at 23:59"

        config2 = Mock(spec=JobConfiguration)
        config2.id = 2
        config2.archive_configuration_id = 102
        config2.schedule_type = "weekly"
        config2.archive_window_days = 60
        config2.is_active = False
        config2.get_schedule_description.return_value = "Weekly on Monday at 09:00"

        all_configs = [config1, config2]
        self.mock_repository.get_by_user_id.return_value = all_configs

        # Act
        result = self.service.get_summary_for_user(user_id)

        # Assert
        assert result["total_configs"] == 2
        assert result["active_configs"] == 0
        assert result["inactive_configs"] == 2
        assert result["schedule_types"] == {}  # No active configs, so no schedule types counted

        self.mock_repository.get_by_user_id.assert_called_once_with(user_id)
