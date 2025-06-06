"""
Service for BackupJobConfiguration management.
Provides business logic for backup job configuration operations.
"""

from datetime import UTC, datetime
from typing import List, Optional

from core.models.backup_job_configuration import BackupJobConfiguration
from core.repositories.backup_job_configuration_repository import BackupJobConfigurationRepository
from core.services.user_service import UserService


class BackupJobConfigurationService:
    """Service for BackupJobConfiguration operations."""

    def __init__(self, repository: BackupJobConfigurationRepository, user_service: UserService):
        self.repository = repository
        self.user_service = user_service

    def validate(self, backup_job_config: BackupJobConfiguration) -> None:
        """Validate a backup job configuration."""
        if not backup_job_config.source_calendar_name:
            raise ValueError("Source calendar name is required")

        if not backup_job_config.backup_destination:
            raise ValueError("Backup destination is required")

        if backup_job_config.backup_format not in ["csv", "json", "ics", "local_calendar"]:
            raise ValueError(
                "Backup format must be one of: csv, json, ics, local_calendar"
            )

        if backup_job_config.schedule_type not in ["daily", "weekly", "manual"]:
            raise ValueError("Schedule type must be one of: daily, weekly, manual")

        if not (0 <= backup_job_config.schedule_hour <= 23):
            raise ValueError("Schedule hour must be between 0 and 23")

        if not (0 <= backup_job_config.schedule_minute <= 59):
            raise ValueError("Schedule minute must be between 0 and 59")

        if (
            backup_job_config.schedule_type == "weekly"
            and backup_job_config.schedule_day_of_week is not None
            and not (0 <= backup_job_config.schedule_day_of_week <= 6)
        ):
            raise ValueError("Schedule day of week must be between 0 (Monday) and 6 (Sunday)")

    def _validate_relationships(self, backup_job_config: BackupJobConfiguration) -> None:
        """Validate that related entities exist."""
        user = self.user_service.get_by_id(backup_job_config.user_id)
        if not user:
            raise ValueError(f"User with ID {backup_job_config.user_id} not found")

    def create(self, backup_job_config: BackupJobConfiguration) -> BackupJobConfiguration:
        """Create a new BackupJobConfiguration after validation."""
        self.validate(backup_job_config)
        self._validate_relationships(backup_job_config)

        # Check for existing configuration for the same user and source calendar
        existing = self.repository.get_by_user_and_source(
            backup_job_config.user_id, backup_job_config.source_calendar_name
        )
        if existing:
            raise ValueError(
                f"BackupJobConfiguration already exists for user {backup_job_config.user_id} "
                f"and source calendar '{backup_job_config.source_calendar_name}'"
            )

        self.repository.add(backup_job_config)
        return backup_job_config

    def update(self, backup_job_config: BackupJobConfiguration) -> BackupJobConfiguration:
        """Update an existing BackupJobConfiguration after validation."""
        self.validate(backup_job_config)
        self._validate_relationships(backup_job_config)

        # Update the updated_at timestamp
        backup_job_config.updated_at = datetime.now(UTC)

        self.repository.update(backup_job_config)
        return backup_job_config

    def delete(self, backup_job_config_id: int) -> bool:
        """Delete a BackupJobConfiguration by ID."""
        return self.repository.delete(backup_job_config_id)

    def list(
        self,
        user_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        schedule_type: Optional[str] = None,
    ) -> List[BackupJobConfiguration]:
        """List BackupJobConfigurations with optional filters."""
        return self.repository.list(
            user_id=user_id, is_active=is_active, schedule_type=schedule_type
        )

    def get_by_id(self, backup_job_config_id: int) -> Optional[BackupJobConfiguration]:
        """Get BackupJobConfiguration by ID."""
        return self.repository.get_by_id(backup_job_config_id)

    def get_active_configs_for_user(self, user_id: int) -> List[BackupJobConfiguration]:
        """Get all active backup job configurations for a user."""
        return self.repository.get_active_configs_for_user(user_id)

    def get_scheduled_configs(self, schedule_type: str) -> List[BackupJobConfiguration]:
        """Get all active backup job configurations for a specific schedule type."""
        return self.repository.get_scheduled_configs(schedule_type)

    def create_from_parameters(
        self,
        user_id: int,
        source_calendar_name: str,
        backup_destination: str,
        backup_format: str = "csv",
        schedule_type: str = "daily",
        schedule_hour: int = 2,
        schedule_minute: int = 0,
        schedule_day_of_week: Optional[int] = None,
        include_metadata: bool = True,
    ) -> BackupJobConfiguration:
        """Create a BackupJobConfiguration from individual parameters."""
        # Validate user exists
        user = self.user_service.get_by_id(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        # Check for existing configuration
        existing = self.repository.get_by_user_and_source(user_id, source_calendar_name)
        if existing:
            raise ValueError(
                f"BackupJobConfiguration already exists for source calendar '{source_calendar_name}'"
            )

        backup_job_config = BackupJobConfiguration(
            user_id=user_id,
            source_calendar_name=source_calendar_name,
            backup_destination=backup_destination,
            backup_format=backup_format,
            schedule_type=schedule_type,
            schedule_hour=schedule_hour,
            schedule_minute=schedule_minute,
            schedule_day_of_week=schedule_day_of_week,
            include_metadata=include_metadata,
            is_active=True,
        )

        return self.create(backup_job_config)

    def activate_config(self, backup_job_config_id: int) -> bool:
        """Activate a specific backup job configuration."""
        return self.repository.activate_config(backup_job_config_id)

    def deactivate_config(self, backup_job_config_id: int) -> bool:
        """Deactivate a specific backup job configuration."""
        return self.repository.deactivate_config(backup_job_config_id)

    def deactivate_user_configs(self, user_id: int) -> int:
        """Deactivate all backup job configurations for a user."""
        return self.repository.deactivate_user_configs(user_id)
