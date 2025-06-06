"""
Repository for BackupJobConfiguration model.
Provides data access methods for backup job configurations.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from core.models.backup_job_configuration import BackupJobConfiguration


class BackupJobConfigurationRepository:
    """Repository for BackupJobConfiguration operations."""

    def __init__(self, session: Session):
        self.session = session

    def add(self, backup_job_config: BackupJobConfiguration) -> BackupJobConfiguration:
        """Add a new backup job configuration."""
        self.session.add(backup_job_config)
        self.session.commit()
        self.session.refresh(backup_job_config)
        return backup_job_config

    def get_by_id(self, backup_job_config_id: int) -> Optional[BackupJobConfiguration]:
        """Get backup job configuration by ID."""
        return self.session.get(BackupJobConfiguration, backup_job_config_id)

    def get_by_user_and_source(
        self, user_id: int, source_calendar_name: str
    ) -> Optional[BackupJobConfiguration]:
        """Get backup job configuration by user ID and source calendar name."""
        return (
            self.session.query(BackupJobConfiguration)
            .filter(
                BackupJobConfiguration.user_id == user_id,
                BackupJobConfiguration.source_calendar_name == source_calendar_name,
            )
            .first()
        )

    def list(
        self,
        user_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        schedule_type: Optional[str] = None,
    ) -> List[BackupJobConfiguration]:
        """List backup job configurations with optional filters."""
        query = self.session.query(BackupJobConfiguration)

        if user_id is not None:
            query = query.filter(BackupJobConfiguration.user_id == user_id)

        if is_active is not None:
            query = query.filter(BackupJobConfiguration.is_active == is_active)

        if schedule_type is not None:
            query = query.filter(BackupJobConfiguration.schedule_type == schedule_type)

        return query.order_by(BackupJobConfiguration.created_at.desc()).all()

    def update(self, backup_job_config: BackupJobConfiguration) -> BackupJobConfiguration:
        """Update an existing backup job configuration."""
        self.session.merge(backup_job_config)
        self.session.commit()
        self.session.refresh(backup_job_config)
        return backup_job_config

    def delete(self, backup_job_config_id: int) -> bool:
        """Delete a backup job configuration by ID."""
        backup_job_config = self.get_by_id(backup_job_config_id)
        if backup_job_config:
            self.session.delete(backup_job_config)
            self.session.commit()
            return True
        return False

    def get_active_configs_for_user(self, user_id: int) -> List[BackupJobConfiguration]:
        """Get all active backup job configurations for a user."""
        return (
            self.session.query(BackupJobConfiguration)
            .filter(
                BackupJobConfiguration.user_id == user_id,
                BackupJobConfiguration.is_active == True,
            )
            .order_by(BackupJobConfiguration.created_at.desc())
            .all()
        )

    def get_scheduled_configs(self, schedule_type: str) -> List[BackupJobConfiguration]:
        """Get all active backup job configurations for a specific schedule type."""
        return (
            self.session.query(BackupJobConfiguration)
            .filter(
                BackupJobConfiguration.is_active == True,
                BackupJobConfiguration.schedule_type == schedule_type,
            )
            .all()
        )

    def deactivate_user_configs(self, user_id: int) -> int:
        """Deactivate all backup job configurations for a user."""
        count = (
            self.session.query(BackupJobConfiguration)
            .filter(
                BackupJobConfiguration.user_id == user_id,
                BackupJobConfiguration.is_active == True,
            )
            .update({"is_active": False})
        )
        self.session.commit()
        return count

    def activate_config(self, backup_job_config_id: int) -> bool:
        """Activate a specific backup job configuration."""
        backup_job_config = self.get_by_id(backup_job_config_id)
        if backup_job_config:
            backup_job_config.is_active = True
            self.session.commit()
            return True
        return False

    def deactivate_config(self, backup_job_config_id: int) -> bool:
        """Deactivate a specific backup job configuration."""
        backup_job_config = self.get_by_id(backup_job_config_id)
        if backup_job_config:
            backup_job_config.is_active = False
            self.session.commit()
            return True
        return False
