from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from core.db import SessionLocal
from core.models.restoration_configuration import RestorationConfiguration


class RestorationConfigurationRepository:
    """
    Repository for managing RestorationConfiguration entities.
    """

    def __init__(self, session: Optional[Session] = None):
        self.session = session or SessionLocal()

    def add(self, config: RestorationConfiguration) -> RestorationConfiguration:
        """Add a new RestorationConfiguration and return it with ID populated."""
        self.session.add(config)
        self.session.commit()
        self.session.refresh(config)
        return config

    def get_by_id(self, config_id: int) -> Optional[RestorationConfiguration]:
        """Retrieve a RestorationConfiguration by its ID."""
        return self.session.get(RestorationConfiguration, config_id)

    def update(self, config: RestorationConfiguration) -> RestorationConfiguration:
        """Update an existing RestorationConfiguration."""
        self.session.merge(config)
        self.session.commit()
        self.session.refresh(config)
        return config

    def delete(self, config_id: int) -> bool:
        """Delete a RestorationConfiguration by ID. Returns True if deleted, False if not found."""
        config = self.get_by_id(config_id)
        if config:
            self.session.delete(config)
            self.session.commit()
            return True
        return False

    def list_for_user(self, user_id: int) -> List[RestorationConfiguration]:
        """List all RestorationConfigurations for a specific user."""
        return (
            self.session.query(RestorationConfiguration)
            .filter_by(user_id=user_id)
            .order_by(desc(RestorationConfiguration.created_at))
            .all()
        )

    def list_active_for_user(self, user_id: int) -> List[RestorationConfiguration]:
        """List all active RestorationConfigurations for a specific user."""
        return (
            self.session.query(RestorationConfiguration)
            .filter_by(user_id=user_id, is_active=True)
            .order_by(desc(RestorationConfiguration.created_at))
            .all()
        )

    def get_by_name(self, name: str, user_id: int) -> Optional[RestorationConfiguration]:
        """Get a RestorationConfiguration by name for a specific user."""
        return (
            self.session.query(RestorationConfiguration)
            .filter_by(name=name, user_id=user_id)
            .first()
        )

    def list_by_source_type(
        self, source_type: str, user_id: Optional[int] = None
    ) -> List[RestorationConfiguration]:
        """List RestorationConfigurations by source type, optionally filtered by user."""
        query = self.session.query(RestorationConfiguration).filter_by(source_type=source_type)
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        return query.order_by(desc(RestorationConfiguration.created_at)).all()

    def list_by_destination_type(
        self, destination_type: str, user_id: Optional[int] = None
    ) -> List[RestorationConfiguration]:
        """List RestorationConfigurations by destination type, optionally filtered by user."""
        query = self.session.query(RestorationConfiguration).filter_by(destination_type=destination_type)
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        return query.order_by(desc(RestorationConfiguration.created_at)).all()

    def search(
        self,
        filters: Dict[str, Any],
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[RestorationConfiguration]:
        """
        Advanced search with multiple filters.

        Args:
            filters: Dict with possible keys:
                - user_id: int
                - source_type: str
                - destination_type: str
                - is_active: bool
                - name_contains: str (for text search in name)
        """
        query = self.session.query(RestorationConfiguration)

        # Apply filters
        if "user_id" in filters:
            query = query.filter_by(user_id=filters["user_id"])

        if "source_type" in filters:
            query = query.filter_by(source_type=filters["source_type"])

        if "destination_type" in filters:
            query = query.filter_by(destination_type=filters["destination_type"])

        if "is_active" in filters:
            query = query.filter_by(is_active=filters["is_active"])

        if "name_contains" in filters:
            query = query.filter(
                RestorationConfiguration.name.ilike(f"%{filters['name_contains']}%")
            )

        # Order by creation date (newest first)
        query = query.order_by(desc(RestorationConfiguration.created_at))

        # Apply pagination
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        return query.all()

    def count_for_user(self, user_id: int) -> int:
        """Count total RestorationConfigurations for a user."""
        return (
            self.session.query(RestorationConfiguration)
            .filter_by(user_id=user_id)
            .count()
        )

    def count_active_for_user(self, user_id: int) -> int:
        """Count active RestorationConfigurations for a user."""
        return (
            self.session.query(RestorationConfiguration)
            .filter_by(user_id=user_id, is_active=True)
            .count()
        )

    def deactivate_all_for_user(self, user_id: int) -> int:
        """Deactivate all RestorationConfigurations for a user. Returns count of deactivated configs."""
        count = (
            self.session.query(RestorationConfiguration)
            .filter_by(user_id=user_id, is_active=True)
            .update({"is_active": False})
        )
        self.session.commit()
        return count

    def activate_by_id(self, config_id: int) -> bool:
        """Activate a specific RestorationConfiguration. Returns True if activated, False if not found."""
        config = self.get_by_id(config_id)
        if config:
            config.is_active = True
            self.session.commit()
            return True
        return False

    def deactivate_by_id(self, config_id: int) -> bool:
        """Deactivate a specific RestorationConfiguration. Returns True if deactivated, False if not found."""
        config = self.get_by_id(config_id)
        if config:
            config.is_active = False
            self.session.commit()
            return True
        return False
