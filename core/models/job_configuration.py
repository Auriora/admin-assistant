"""
SQLAlchemy model for JobConfiguration.
Stores job scheduling parameters for calendar archiving per user and archive configuration.
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from core.db import Base
from core.models.appointment import UTCDateTime


class JobConfiguration(Base):
    """
    Stores job scheduling parameters for calendar archiving.

    Attributes:
        id (int): Primary key.
        user_id (int): Foreign key to User.
        archive_configuration_id (int): Foreign key to ArchiveConfiguration.
        archive_window_days (int): Number of days to look back for archiving.
        schedule_type (str): Type of schedule ('daily', 'weekly', 'manual').
        schedule_hour (int): Hour to run scheduled jobs (0-23).
        schedule_minute (int): Minute to run scheduled jobs (0-59).
        schedule_day_of_week (int): Day of week for weekly jobs (0=Monday, 6=Sunday, nullable).
        is_active (bool): Whether this job configuration is active.
        created_at (datetime): Creation timestamp.
        updated_at (datetime): Last update timestamp.
        user (User): Relationship to User.
        archive_configuration (ArchiveConfiguration): Relationship to ArchiveConfiguration.
    """

    __tablename__ = "job_configurations"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        doc="User this job configuration belongs to",
    )
    archive_configuration_id = Column(
        Integer,
        ForeignKey("archive_configurations.id"),
        nullable=False,
        index=True,
        doc="Archive configuration this job uses",
    )
    archive_window_days = Column(
        Integer,
        nullable=False,
        default=30,
        doc="Number of days to look back for archiving",
    )
    schedule_type = Column(
        String(16),
        nullable=False,
        default="daily",
        doc="Type of schedule: 'daily', 'weekly', or 'manual'",
    )
    schedule_hour = Column(
        Integer, nullable=False, default=23, doc="Hour to run scheduled jobs (0-23)"
    )
    schedule_minute = Column(
        Integer, nullable=False, default=59, doc="Minute to run scheduled jobs (0-59)"
    )
    schedule_day_of_week = Column(
        Integer, nullable=True, doc="Day of week for weekly jobs (0=Monday, 6=Sunday)"
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this job configuration is active",
    )
    created_at = Column(UTCDateTime(), default=datetime.now(UTC), nullable=False)
    updated_at = Column(
        UTCDateTime(),
        default=datetime.now(UTC),
        onupdate=datetime.now(UTC),
        nullable=False,
    )

    user = relationship("User", back_populates="job_configurations")
    archive_configuration = relationship(
        "ArchiveConfiguration", back_populates="job_configurations"
    )

    def __repr__(self) -> str:
        return f"<JobConfiguration id={self.id} user_id={self.user_id} archive_config_id={self.archive_configuration_id} schedule={self.schedule_type} active={self.is_active}>"

    def get_schedule_description(self) -> str:
        """Get a human-readable description of the schedule."""
        if self.schedule_type == "daily":
            return f"Daily at {self.schedule_hour:02d}:{self.schedule_minute:02d}"
        elif self.schedule_type == "weekly":
            days = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]
            day_name = (
                days[self.schedule_day_of_week]
                if self.schedule_day_of_week is not None
                else "Unknown"
            )
            return f"Weekly on {day_name} at {self.schedule_hour:02d}:{self.schedule_minute:02d}"
        elif self.schedule_type == "manual":
            return "Manual execution only"
        else:
            return f"Unknown schedule type: {self.schedule_type}"

    def validate(self) -> None:
        """Validate the job configuration parameters."""
        if self.schedule_type not in ["daily", "weekly", "manual"]:
            raise ValueError(f"Invalid schedule_type: {self.schedule_type}")

        if not (0 <= self.schedule_hour <= 23):
            raise ValueError(
                f"Invalid schedule_hour: {self.schedule_hour} (must be 0-23)"
            )

        if not (0 <= self.schedule_minute <= 59):
            raise ValueError(
                f"Invalid schedule_minute: {self.schedule_minute} (must be 0-59)"
            )

        if self.schedule_type == "weekly":
            if self.schedule_day_of_week is None:
                raise ValueError(
                    "schedule_day_of_week is required for weekly schedules"
                )
            if not (0 <= self.schedule_day_of_week <= 6):
                raise ValueError(
                    f"Invalid schedule_day_of_week: {self.schedule_day_of_week} (must be 0-6)"
                )

        if self.archive_window_days <= 0:
            raise ValueError(
                f"Invalid archive_window_days: {self.archive_window_days} (must be > 0)"
            )
