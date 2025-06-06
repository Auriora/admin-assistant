"""
Repository for BackupConfiguration model.
Provides data access methods for backup configurations.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from core.models.backup_configuration import BackupConfiguration


class BackupConfigurationRepository:
    """Repository for BackupConfiguration operations."""

    def __init__(self, session: Session):
        self.session = session

    def add(self, backup_config: BackupConfiguration) -> BackupConfiguration:
        """Add a new backup configuration."""
        self.session.add(backup_config)
        self.session.commit()
        self.session.refresh(backup_config)
        return backup_config

    def get_by_id(self, backup_config_id: int) -> Optional[BackupConfiguration]:
        """Get backup configuration by ID."""
        return self.session.get(BackupConfiguration, backup_config_id)

    def get_by_name(self, name: str, user_id: int) -> Optional[BackupConfiguration]:
        """Get backup configuration by name and user ID."""
        return (
            self.session.query(BackupConfiguration)
            .filter(
                BackupConfiguration.user_id == user_id,
                BackupConfiguration.name == name,
            )
            .first()
        )

    def list(
        self,
        user_id: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> List[BackupConfiguration]:
        """List backup configurations with optional filters."""
        query = self.session.query(BackupConfiguration)

        if user_id is not None:
            query = query.filter(BackupConfiguration.user_id == user_id)

        if is_active is not None:
            query = query.filter(BackupConfiguration.is_active == is_active)

        return query.order_by(BackupConfiguration.created_at.desc()).all()

    def update(self, backup_config: BackupConfiguration) -> BackupConfiguration:
        """Update an existing backup configuration."""
        self.session.merge(backup_config)
        self.session.commit()
        self.session.refresh(backup_config)
        return backup_config

    def delete(self, backup_config_id: int) -> bool:
        """Delete a backup configuration by ID."""
        backup_config = self.get_by_id(backup_config_id)
        if backup_config:
            self.session.delete(backup_config)
            self.session.commit()
            return True
        return False

    def get_active_configs_for_user(self, user_id: int) -> List[BackupConfiguration]:
        """Get all active backup configurations for a user."""
        return (
            self.session.query(BackupConfiguration)
            .filter(
                BackupConfiguration.user_id == user_id,
                BackupConfiguration.is_active == True,
            )
            .order_by(BackupConfiguration.created_at.desc())
            .all()
        )

    def activate_config(self, backup_config_id: int) -> bool:
        """Activate a specific backup configuration."""
        backup_config = self.get_by_id(backup_config_id)
        if backup_config:
            backup_config.is_active = True
            self.session.commit()
            return True
        return False

    def deactivate_config(self, backup_config_id: int) -> bool:
        """Deactivate a specific backup configuration."""
        backup_config = self.get_by_id(backup_config_id)
        if backup_config:
            backup_config.is_active = False
            self.session.commit()
            return True
        return False
