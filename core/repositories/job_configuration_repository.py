"""
Repository for managing JobConfiguration entities.
"""
from typing import List, Optional
from core.models.job_configuration import JobConfiguration
from core.models.user import User
from core.db import SessionLocal

class JobConfigurationRepository:
    """
    Repository for managing JobConfiguration entities.
    """
    def __init__(self, session=None):
        self.session = session or SessionLocal()

    def get_by_id(self, job_config_id: int) -> Optional[JobConfiguration]:
        """Retrieve a JobConfiguration by its ID."""
        return self.session.get(JobConfiguration, job_config_id)

    def get_by_user_id(self, user_id: int) -> List[JobConfiguration]:
        """Retrieve all JobConfigurations for a specific user."""
        return self.session.query(JobConfiguration).filter_by(user_id=user_id).all()

    def get_by_archive_config_id(self, archive_config_id: int) -> List[JobConfiguration]:
        """Retrieve all JobConfigurations for a specific archive configuration."""
        return self.session.query(JobConfiguration).filter_by(archive_configuration_id=archive_config_id).all()

    def get_active_by_user_id(self, user_id: int) -> List[JobConfiguration]:
        """Retrieve all active JobConfigurations for a specific user."""
        return self.session.query(JobConfiguration).filter_by(user_id=user_id, is_active=True).all()

    def get_active_by_archive_config_id(self, archive_config_id: int) -> List[JobConfiguration]:
        """Retrieve all active JobConfigurations for a specific archive configuration."""
        return self.session.query(JobConfiguration).filter_by(archive_configuration_id=archive_config_id, is_active=True).all()

    def get_by_user_and_archive_config(self, user_id: int, archive_config_id: int) -> Optional[JobConfiguration]:
        """Retrieve a JobConfiguration by user_id and archive_configuration_id (should be unique)."""
        return self.session.query(JobConfiguration).filter_by(
            user_id=user_id, 
            archive_configuration_id=archive_config_id
        ).first()

    def add(self, job_config: JobConfiguration) -> None:
        """Add a new JobConfiguration."""
        self.session.add(job_config)
        self.session.commit()

    def update(self, job_config: JobConfiguration) -> None:
        """Update an existing JobConfiguration."""
        self.session.merge(job_config)
        self.session.commit()

    def delete(self, job_config_id: int) -> bool:
        """Delete a JobConfiguration by ID. Returns True if deleted, False if not found."""
        job_config = self.get_by_id(job_config_id)
        if job_config:
            self.session.delete(job_config)
            self.session.commit()
            return True
        return False

    def list(self, user_id: Optional[int] = None, is_active: Optional[bool] = None) -> List[JobConfiguration]:
        """List JobConfigurations with optional filters."""
        query = self.session.query(JobConfiguration)
        
        if user_id is not None:
            query = query.filter_by(user_id=user_id)
        
        if is_active is not None:
            query = query.filter_by(is_active=is_active)
        
        return query.all()

    def get_scheduled_configs(self, schedule_type: Optional[str] = None) -> List[JobConfiguration]:
        """Get all active job configurations that have scheduled execution (not manual)."""
        query = self.session.query(JobConfiguration).filter_by(is_active=True)
        
        if schedule_type:
            query = query.filter_by(schedule_type=schedule_type)
        else:
            # Exclude manual-only configurations
            query = query.filter(JobConfiguration.schedule_type != 'manual')
        
        return query.all()

    def deactivate_by_archive_config_id(self, archive_config_id: int) -> int:
        """Deactivate all JobConfigurations for a specific archive configuration. Returns count of deactivated configs."""
        count = self.session.query(JobConfiguration).filter_by(
            archive_configuration_id=archive_config_id,
            is_active=True
        ).update({'is_active': False})
        self.session.commit()
        return count

    def activate_by_archive_config_id(self, archive_config_id: int) -> int:
        """Activate all JobConfigurations for a specific archive configuration. Returns count of activated configs."""
        count = self.session.query(JobConfiguration).filter_by(
            archive_configuration_id=archive_config_id,
            is_active=False
        ).update({'is_active': True})
        self.session.commit()
        return count

    def count_by_user_id(self, user_id: int) -> int:
        """Count total JobConfigurations for a user."""
        return self.session.query(JobConfiguration).filter_by(user_id=user_id).count()

    def count_active_by_user_id(self, user_id: int) -> int:
        """Count active JobConfigurations for a user."""
        return self.session.query(JobConfiguration).filter_by(user_id=user_id, is_active=True).count()
