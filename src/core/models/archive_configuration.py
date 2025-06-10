"""
SQLAlchemy model for ArchiveConfiguration.
Stores configuration for calendar archiving per user.
"""

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from core.db import Base
from core.models.appointment import UTCDateTime
from core.utilities.uri_utility import parse_resource_uri, URIParseError


class ArchiveConfiguration(Base):
    """
    Stores configuration for calendar archiving per user.

    Attributes:
        id (int): Primary key.
        user_id (int): Foreign key to User.
        name (str): Human-readable name for this archive configuration.
        source_calendar_uri (str): URI of the source (main) calendar with account context
            (e.g., msgraph://user@example.com/calendars/primary, local://user@example.com/calendars/work).
        destination_calendar_uri (str): URI of the archive calendar with account context
            (e.g., msgraph://user@example.com/calendars/archive, local://user@example.com/calendars/backup).
        is_active (bool): Whether this configuration is active (disables all jobs using this config).
        timezone (str): Timezone for archiving operations (IANA format).
        allow_overlaps (bool): Whether to allow overlapping appointments in archive operations.
        archive_purpose (str): Purpose of the archive configuration ('general', 'timesheet', 'billing', 'travel', etc.).
        created_at (datetime): Creation timestamp.
        updated_at (datetime): Last update timestamp.
        user (User): Relationship to User.
    """

    __tablename__ = "archive_configurations"

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
        doc="Human-readable name for this archive configuration",
    )
    source_calendar_uri = Column(
        String(255),
        nullable=False,
        doc="URI of the source (main) calendar with account context (e.g., msgraph://user@example.com/calendars/primary)",
    )
    destination_calendar_uri = Column(
        String(255),
        nullable=False,
        doc="URI of the archive calendar with account context (e.g., msgraph://user@example.com/calendars/archive)",
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this configuration is active (disables all jobs using this config)",
    )
    timezone = Column(
        String(64),
        nullable=False,
        doc="Timezone for archiving operations (IANA format)",
    )
    allow_overlaps = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether to allow overlapping appointments in archive operations",
    )
    archive_purpose = Column(
        String(50),
        default='general',
        nullable=False,
        doc="Purpose of the archive configuration ('general', 'timesheet', 'billing', 'travel', etc.)",
    )
    created_at = Column(UTCDateTime(), default=datetime.now(UTC), nullable=False)
    updated_at = Column(
        UTCDateTime(),
        default=datetime.now(UTC),
        onupdate=datetime.now(UTC),
        nullable=False,
    )

    user = relationship("User", back_populates="archive_configurations")
    job_configurations = relationship(
        "JobConfiguration", back_populates="archive_configuration"
    )

    def __init__(self, **kwargs):
        """Initialize ArchiveConfiguration with proper defaults for new fields."""
        # Set defaults for new fields if not provided
        if 'allow_overlaps' not in kwargs:
            kwargs['allow_overlaps'] = True
        if 'archive_purpose' not in kwargs:
            kwargs['archive_purpose'] = 'general'

        super().__init__(**kwargs)

    @property
    def is_timesheet_archive(self) -> bool:
        """
        Check if this archive configuration is for timesheet purposes.

        Returns:
            True if archive_purpose is 'timesheet', False otherwise
        """
        return self.archive_purpose == 'timesheet'

    def get_account_context(self, uri_type: str = 'source') -> Optional[str]:
        """
        Extract account context from the specified URI.

        Args:
            uri_type: Which URI to parse ('source' or 'destination')

        Returns:
            Account context from the URI (e.g., 'user@example.com') or None if not found

        Raises:
            ValueError: If uri_type is not 'source' or 'destination'
        """
        if uri_type not in ('source', 'destination'):
            raise ValueError("uri_type must be 'source' or 'destination'")

        uri = self.source_calendar_uri if uri_type == 'source' else self.destination_calendar_uri

        try:
            parsed = parse_resource_uri(uri)
            return parsed.account
        except URIParseError:
            # Return None for malformed URIs or legacy URIs without account context
            return None

    def __repr__(self) -> str:
        return f"<ArchiveConfiguration name={self.name} user_id={self.user_id} source={self.source_calendar_uri} dest={self.destination_calendar_uri} active={self.is_active} purpose={self.archive_purpose} overlaps={self.allow_overlaps}>"
