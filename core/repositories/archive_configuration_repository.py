from typing import List, Optional

from core.db import SessionLocal
from core.models.archive_configuration import ArchiveConfiguration


class ArchiveConfigurationRepository:
    """
    Repository for managing ArchiveConfiguration entities.
    """

    def __init__(self, session=None):
        self.session = session or SessionLocal()

    def get_by_id(self, config_id: int) -> Optional[ArchiveConfiguration]:
        """Retrieve an ArchiveConfiguration by its ID."""
        return self.session.get(ArchiveConfiguration, config_id)

    def add(self, config: ArchiveConfiguration) -> ArchiveConfiguration:
        """Add a new ArchiveConfiguration and return it with ID populated."""
        self.session.add(config)
        self.session.commit()
        self.session.refresh(config)
        return config

    def list_for_user(self, user_id: int) -> List[ArchiveConfiguration]:
        """List all ArchiveConfigurations for a given user."""
        return self.session.query(ArchiveConfiguration).filter_by(user_id=user_id).all()

    def update(self, config: ArchiveConfiguration) -> None:
        """Update an existing ArchiveConfiguration."""
        self.session.merge(config)
        self.session.commit()

    def delete(self, config_id: int) -> None:
        """Delete an ArchiveConfiguration by its ID."""
        config = self.get_by_id(config_id)
        if config:
            self.session.delete(config)
            self.session.commit()

    def list(self, user_id: Optional[int] = None) -> List[ArchiveConfiguration]:
        """List all ArchiveConfigurations, optionally filtered by user."""
        query = self.session.query(ArchiveConfiguration)
        if user_id is not None:
            query = query.filter_by(user_id=user_id)
        return query.all()

    def list_active(self, user_id: Optional[int] = None) -> List[ArchiveConfiguration]:
        """List all active ArchiveConfigurations, optionally filtered by user."""
        query = self.session.query(ArchiveConfiguration).filter_by(is_active=True)
        if user_id is not None:
            query = query.filter_by(user_id=user_id)
        return query.all()

    def get_by_name(self, name: str, user_id: Optional[int] = None) -> Optional[ArchiveConfiguration]:
        """Retrieve an ArchiveConfiguration by its name, optionally filtered by user."""
        query = self.session.query(ArchiveConfiguration).filter_by(name=name)
        if user_id is not None:
            query = query.filter_by(user_id=user_id)
        return query.first()
