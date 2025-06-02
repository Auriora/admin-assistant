from typing import List, Optional

from core.models.archive_configuration import ArchiveConfiguration
from core.repositories.archive_configuration_repository import (
    ArchiveConfigurationRepository,
)


class ArchiveConfigurationService:
    """
    Service for business logic related to ArchiveConfiguration.
    """

    def __init__(self, repository: Optional[ArchiveConfigurationRepository] = None):
        self.repository = repository or ArchiveConfigurationRepository()

    def get_by_id(self, config_id: int) -> Optional[ArchiveConfiguration]:
        """Retrieve an ArchiveConfiguration by its ID."""
        return self.repository.get_by_id(config_id)

    def create(self, config: ArchiveConfiguration) -> None:
        """Create a new ArchiveConfiguration after validation."""
        self.validate(config)
        self.repository.add(config)

    def list_for_user(self, user_id: int) -> List[ArchiveConfiguration]:
        """List all ArchiveConfigurations for a given user."""
        return self.repository.list_for_user(user_id)

    def update(self, config: ArchiveConfiguration) -> None:
        """Update an existing ArchiveConfiguration after validation."""
        self.validate(config)
        self.repository.update(config)

    def delete(self, config_id: int) -> None:
        """Delete an ArchiveConfiguration by its ID."""
        self.repository.delete(config_id)

    def validate(self, config: ArchiveConfiguration) -> None:
        """
        Validate ArchiveConfiguration fields. Raises ValueError if invalid.
        """
        name = getattr(config, "name", None)
        source_calendar_uri = getattr(config, "source_calendar_uri", None)
        destination_calendar_uri = getattr(config, "destination_calendar_uri", None)
        timezone = getattr(config, "timezone", None)
        if not name or not str(name).strip():
            raise ValueError("Archive configuration name is required.")
        if not source_calendar_uri or not destination_calendar_uri:
            raise ValueError("Source and destination calendar URIs are required.")
        if not timezone or not str(timezone).strip():
            raise ValueError("Timezone is required.")

    def get_active_for_user(self, user_id: int) -> Optional[ArchiveConfiguration]:
        """
        Return the active ArchiveConfiguration for a user, or None if not found.

        Args:
            user_id (int): The user ID to search for.

        Returns:
            Optional[ArchiveConfiguration]: The active configuration, or None if not found.
        """
        configs = self.list_for_user(user_id)
        return next((c for c in configs if getattr(c, "is_active", False)), None)

    def list(self, user_id: Optional[int] = None) -> List[ArchiveConfiguration]:
        """List all ArchiveConfigurations, optionally filtered by user."""
        return self.repository.list(user_id=user_id)

    def list_active(self, user_id: Optional[int] = None) -> List[ArchiveConfiguration]:
        """List all active ArchiveConfigurations, optionally filtered by user."""
        return self.repository.list_active(user_id=user_id)

    def get_all_active(self) -> List[ArchiveConfiguration]:
        """Get all active ArchiveConfigurations across all users."""
        return self.repository.list_active()
