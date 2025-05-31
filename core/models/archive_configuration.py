"""
SQLAlchemy model for ArchiveConfiguration.
Stores configuration for calendar archiving per user.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from core.db import Base
from datetime import datetime, UTC
from core.models.appointment import UTCDateTime

class ArchiveConfiguration(Base):
    """
    Stores configuration for calendar archiving per user.

    Attributes:
        id (int): Primary key.
        user_id (int): Foreign key to User.
        name (str): Human-readable name for this archive configuration.
        source_calendar_uri (str): URI of the source (main) calendar, including backend context (e.g., msgraph://, sqlite://, google://, etc.).
        destination_calendar_uri (str): URI of the archive calendar, including backend context (e.g., msgraph://, sqlite://, google://, etc.).
        is_active (bool): Whether this configuration is active (disables all jobs using this config).
        timezone (str): Timezone for archiving operations (IANA format).
        created_at (datetime): Creation timestamp.
        updated_at (datetime): Last update timestamp.
        user (User): Relationship to User.
    """
    __tablename__ = 'archive_configurations'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True, doc="User this configuration belongs to")
    name = Column(String(100), nullable=False, doc="Human-readable name for this archive configuration")
    source_calendar_uri = Column(String(255), nullable=False, doc="URI of the source (main) calendar, including backend context (e.g., msgraph://, sqlite://, google://, etc.)")
    destination_calendar_uri = Column(String(255), nullable=False, doc="URI of the archive calendar, including backend context (e.g., msgraph://, sqlite://, google://, etc.)")
    is_active = Column(Boolean, default=True, nullable=False, doc="Whether this configuration is active (disables all jobs using this config)")
    timezone = Column(String(64), nullable=False, doc="Timezone for archiving operations (IANA format)")
    created_at = Column(UTCDateTime(), default=datetime.now(UTC), nullable=False)
    updated_at = Column(UTCDateTime(), default=datetime.now(UTC), onupdate=datetime.now(UTC), nullable=False)

    user = relationship("User", back_populates="archive_configurations")
    job_configurations = relationship("JobConfiguration", back_populates="archive_configuration")

    def __repr__(self) -> str:
        return f"<ArchiveConfiguration name={self.name} user_id={self.user_id} source={self.source_calendar_uri} dest={self.destination_calendar_uri} active={self.is_active}>" 