"""
SQLAlchemy model for BackupConfiguration.
Stores configuration for calendar backup per user.
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from core.db import Base
from core.models.appointment import UTCDateTime


class BackupConfiguration(Base):
    """
    Stores configuration for calendar backup per user.

    Attributes:
        id (int): Primary key.
        user_id (int): Foreign key to User.
        name (str): Human-readable name for this backup configuration.
        source_calendar_uri (str): URI of the source calendar to backup.
        destination_uri (str): URI of the backup destination (file or calendar).
        backup_format (str): Backup format ('csv', 'json', 'ics', 'local_calendar').
        include_metadata (bool): Whether to include metadata in backup.
        is_active (bool): Whether this configuration is active.
        timezone (str): Timezone for backup operations (IANA format).
        created_at (datetime): Creation timestamp.
        updated_at (datetime): Last update timestamp.
        user (User): Relationship to User.
    """

    __tablename__ = "backup_configurations"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        doc="User this configuration belongs to",
    )
    name = Column(
        String(100),
        nullable=False,
        doc="Human-readable name for this backup configuration",
    )
    source_calendar_uri = Column(
        String(500),
        nullable=False,
        doc="URI of the source calendar to backup (e.g., msgraph://calendars/Work Calendar)",
    )
    destination_uri = Column(
        String(500),
        nullable=False,
        doc="URI of the backup destination (e.g., file:///backups/work.csv, local://calendars/Backup)",
    )
    backup_format = Column(
        String(32),
        nullable=False,
        default="csv",
        doc="Backup format: 'csv', 'json', 'ics', or 'local_calendar'",
    )
    include_metadata = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether to include metadata in backup",
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this configuration is active",
    )
    timezone = Column(
        String(64),
        nullable=False,
        doc="Timezone for backup operations (IANA format)",
    )
    created_at = Column(UTCDateTime(), default=datetime.now(UTC), nullable=False)
    updated_at = Column(
        UTCDateTime(),
        default=datetime.now(UTC),
        onupdate=datetime.now(UTC),
        nullable=False,
    )

    user = relationship("User", back_populates="backup_configurations")

    def __repr__(self) -> str:
        return (
            f"<BackupConfiguration(name={self.name}, user_id={self.user_id}, "
            f"source={self.source_calendar_uri}, dest={self.destination_uri}, "
            f"format={self.backup_format}, active={self.is_active})>"
        )

    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "source_calendar_uri": self.source_calendar_uri,
            "destination_uri": self.destination_uri,
            "backup_format": self.backup_format,
            "include_metadata": self.include_metadata,
            "is_active": self.is_active,
            "timezone": self.timezone,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
