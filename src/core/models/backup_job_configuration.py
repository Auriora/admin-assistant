"""
SQLAlchemy model for BackupJobConfiguration.
Stores job scheduling parameters for calendar backup per user.
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from core.db import Base
from core.models.appointment import UTCDateTime


class BackupJobConfiguration(Base):
    """
    Stores job scheduling parameters for calendar backup.

    Attributes:
        id (int): Primary key.
        user_id (int): Foreign key to User.
        source_calendar_uri (str): URI of the source calendar to backup.
        destination_uri (str): Backup destination URI.
        backup_format (str): Backup format ('csv', 'json', 'ics', 'local_calendar').
        schedule_type (str): Type of schedule ('daily', 'weekly', 'manual').
        schedule_hour (int): Hour to run scheduled jobs (0-23).
        schedule_minute (int): Minute to run scheduled jobs (0-59).
        schedule_day_of_week (int): Day of week for weekly jobs (0=Monday, 6=Sunday, nullable).
        include_metadata (bool): Whether to include metadata in backup.
        is_active (bool): Whether this job configuration is active.
        created_at (datetime): Creation timestamp.
        updated_at (datetime): Last update timestamp.
        user (User): Relationship to User.
    """

    __tablename__ = "backup_job_configurations"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        doc="User this backup job configuration belongs to",
    )
    source_calendar_uri = Column(
        String(500),
        nullable=False,
        doc="URI of the source calendar to backup (e.g., msgraph://calendars/Work Calendar)",
    )
    destination_uri = Column(
        String(500),
        nullable=False,
        doc="Backup destination URI (e.g., file:///backups/work.csv, local://calendars/Backup)",
    )
    backup_format = Column(
        String(32),
        nullable=False,
        default="csv",
        doc="Backup format: 'csv', 'json', 'ics', or 'local_calendar'",
    )
    schedule_type = Column(
        String(16),
        nullable=False,
        default="daily",
        doc="Type of schedule: 'daily', 'weekly', or 'manual'",
    )
    schedule_hour = Column(
        Integer, nullable=False, default=2, doc="Hour to run scheduled jobs (0-23)"
    )
    schedule_minute = Column(
        Integer, nullable=False, default=0, doc="Minute to run scheduled jobs (0-59)"
    )
    schedule_day_of_week = Column(
        Integer, nullable=True, doc="Day of week for weekly jobs (0=Monday, 6=Sunday)"
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
        doc="Whether this backup job configuration is active",
    )
    created_at = Column(UTCDateTime(), default=datetime.now(UTC), nullable=False)
    updated_at = Column(
        UTCDateTime(),
        default=datetime.now(UTC),
        onupdate=datetime.now(UTC),
        nullable=False,
    )

    user = relationship("User", back_populates="backup_job_configurations")

    def __repr__(self):
        return (
            f"<BackupJobConfiguration(id={self.id}, user_id={self.user_id}, "
            f"source='{self.source_calendar_uri}', destination='{self.destination_uri}', "
            f"format='{self.backup_format}', schedule='{self.schedule_type}', "
            f"active={self.is_active})>"
        )

    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "source_calendar_uri": self.source_calendar_uri,
            "destination_uri": self.destination_uri,
            "backup_format": self.backup_format,
            "schedule_type": self.schedule_type,
            "schedule_hour": self.schedule_hour,
            "schedule_minute": self.schedule_minute,
            "schedule_day_of_week": self.schedule_day_of_week,
            "include_metadata": self.include_metadata,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
