"""
Service for BackupConfiguration management.
Provides business logic for backup configuration operations.
"""

from datetime import UTC, datetime
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.models.backup_configuration import BackupConfiguration
    from core.repositories.backup_configuration_repository import BackupConfigurationRepository as _BCRepo
    from core.services.user_service import UserService as _UserService


class BackupConfigurationService:
    """Service for BackupConfiguration operations."""

    def __init__(self, repository: Optional["_BCRepo"] = None, user_service: Optional["_UserService"] = None):
        self._repository = repository
        self._user_service = user_service

    @property
    def repository(self) -> "_BCRepo":
        if self._repository is None:
            from core.db import get_session
            from core.repositories.backup_configuration_repository import BackupConfigurationRepository as _Repo

            session = get_session()
            self._repository = _Repo(session)
        return self._repository

    @property
    def user_service(self) -> "_UserService":
        if self._user_service is None:
            from core.services.user_service import UserService as _Svc

            self._user_service = _Svc()
        return self._user_service

    def validate(self, backup_config: "BackupConfiguration") -> None:
        """Validate a backup configuration."""
        if not backup_config.name:
            raise ValueError("Backup configuration name is required")

        if not backup_config.source_calendar_uri:
            raise ValueError("Source calendar URI is required")

        if not backup_config.destination_uri:
            raise ValueError("Destination URI is required")

        if backup_config.backup_format not in ["csv", "json", "ics", "local_calendar"]:
            raise ValueError(
                "Backup format must be one of: csv, json, ics, local_calendar"
            )

        if not backup_config.timezone:
            raise ValueError("Timezone is required")

    def _validate_relationships(self, backup_config: "BackupConfiguration") -> None:
        """Validate that related entities exist."""
        user = self.user_service.get_by_id(backup_config.user_id)
        if not user:
            raise ValueError(f"User with ID {backup_config.user_id} not found")

    def create(self, backup_config: "BackupConfiguration") -> "BackupConfiguration":
        """Create a new BackupConfiguration after validation."""
        self.validate(backup_config)
        self._validate_relationships(backup_config)

        # Check for existing configuration with the same name for this user
        existing = self.get_by_name(backup_config.name, backup_config.user_id)
        if existing:
            raise ValueError(
                f"BackupConfiguration with name '{backup_config.name}' already exists for user {backup_config.user_id}"
            )

        self.repository.add(backup_config)
        return backup_config

    def update(self, backup_config: "BackupConfiguration") -> "BackupConfiguration":
        """Update an existing BackupConfiguration after validation."""
        self.validate(backup_config)
        self._validate_relationships(backup_config)

        # Update the updated_at timestamp
        backup_config.updated_at = datetime.now(UTC)

        self.repository.update(backup_config)
        return backup_config

    def delete(self, backup_config_id: int) -> bool:
        """Delete a BackupConfiguration by ID."""
        return self.repository.delete(backup_config_id)

    def list(
        self,
        user_id: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> List["BackupConfiguration"]:
        """List BackupConfigurations with optional filters."""
        return self.repository.list(user_id=user_id, is_active=is_active)

    def get_by_id(self, backup_config_id: int) -> Optional["BackupConfiguration"]:
        """Get BackupConfiguration by ID."""
        return self.repository.get_by_id(backup_config_id)

    def get_by_name(self, name: str, user_id: int) -> Optional["BackupConfiguration"]:
        """Get BackupConfiguration by name and user ID."""
        return self.repository.get_by_name(name, user_id)

    def get_active_configs_for_user(self, user_id: int) -> List["BackupConfiguration"]:
        """Get all active backup configurations for a user."""
        return self.repository.list(user_id=user_id, is_active=True)

    def create_from_parameters(
        self,
        user_id: int,
        name: str,
        source_calendar_uri: str,
        destination_uri: str,
        backup_format: str = "csv",
        include_metadata: bool = True,
        timezone: str = "UTC",
    ) -> "BackupConfiguration":
        """Create a BackupConfiguration from individual parameters."""
        # Validate user exists
        user = self.user_service.get_by_id(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        # Check for existing configuration
        existing = self.get_by_name(name, user_id)
        if existing:
            raise ValueError(
                f"BackupConfiguration with name '{name}' already exists for user {user_id}"
            )

        from core.models.backup_configuration import BackupConfiguration as _BC

        backup_config = _BC(
            user_id=user_id,
            name=name,
            source_calendar_uri=source_calendar_uri,
            destination_uri=destination_uri,
            backup_format=backup_format,
            include_metadata=include_metadata,
            timezone=timezone,
            is_active=True,
        )

        return self.create(backup_config)

    def activate_config(self, backup_config_id: int) -> bool:
        """Activate a specific backup configuration."""
        backup_config = self.get_by_id(backup_config_id)
        if backup_config:
            backup_config.is_active = True
            self.repository.update(backup_config)
            return True
        return False

    def deactivate_config(self, backup_config_id: int) -> bool:
        """Deactivate a specific backup configuration."""
        backup_config = self.get_by_id(backup_config_id)
        if backup_config:
            backup_config.is_active = False
            self.repository.update(backup_config)
            return True
        return False

    def deactivate_user_configs(self, user_id: int) -> int:
        """Deactivate all backup configurations for a user."""
        configs = self.get_active_configs_for_user(user_id)
        count = 0
        for config in configs:
            config.is_active = False
            self.repository.update(config)
            count += 1
        return count
