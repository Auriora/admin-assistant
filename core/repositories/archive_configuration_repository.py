from typing import List, Optional
from core.models.archive_configuration import ArchiveConfiguration
from core.db import SessionLocal

class ArchiveConfigurationRepository:
    """
    Repository for managing ArchiveConfiguration entities.
    """
    def __init__(self, session=None):
        self.session = session or SessionLocal()

    def get_by_id(self, config_id: int) -> Optional[ArchiveConfiguration]:
        """Retrieve an ArchiveConfiguration by its ID."""
        return self.session.get(ArchiveConfiguration, config_id)

    def add(self, config: ArchiveConfiguration) -> None:
        """Add a new ArchiveConfiguration."""
        self.session.add(config)
        self.session.commit()

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