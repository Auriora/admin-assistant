from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship

from core.db import Base
from core.models.appointment import UTCDateTime


class RestorationType(Enum):
    """Types of restoration operations."""
    AUDIT_LOG = "audit_log"
    BACKUP_CALENDAR = "backup_calendar"
    EXPORT_FILE = "export_file"


class DestinationType(Enum):
    """Types of restoration destinations."""
    LOCAL_CALENDAR = "local_calendar"
    MSGRAPH_CALENDAR = "msgraph_calendar"
    EXPORT_FILE = "export_file"


class RestorationConfiguration(Base):
    """
    Configuration for appointment restoration operations.
    
    This model defines how appointments should be restored from various sources
    (audit logs, backup calendars, export files) to various destinations
    (local calendars, MSGraph calendars, export files).
    
    Attributes:
        id (int): Primary key.
        user_id (int): Foreign key to User.
        name (str): Human-readable name for this restoration configuration.
        description (str): Optional description of the restoration configuration.
        source_type (str): Type of restoration source (audit_log, backup_calendar, export_file).
        source_config (dict): Source-specific configuration (calendar IDs, file paths, etc.).
        destination_type (str): Type of restoration destination (local_calendar, msgraph_calendar, export_file).
        destination_config (dict): Destination-specific configuration (calendar names, file formats, etc.).
        restoration_policy (dict): Policies for restoration (conflict resolution, date ranges, etc.).
        is_active (bool): Whether this configuration is active.
        created_at (datetime): Creation timestamp.
        updated_at (datetime): Last update timestamp.
    """

    __tablename__ = "restoration_configurations"

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
        doc="Human-readable name for this restoration configuration",
    )
    description = Column(
        Text,
        nullable=True,
        doc="Optional description of the restoration configuration",
    )
    
    # Source configuration
    source_type = Column(
        String(50),
        nullable=False,
        doc="Type of restoration source (audit_log, backup_calendar, export_file)",
    )
    source_config = Column(
        JSON,
        nullable=False,
        doc="Source-specific configuration (calendar IDs, file paths, audit log filters, etc.)",
    )
    
    # Destination configuration
    destination_type = Column(
        String(50),
        nullable=False,
        doc="Type of restoration destination (local_calendar, msgraph_calendar, export_file)",
    )
    destination_config = Column(
        JSON,
        nullable=False,
        doc="Destination-specific configuration (calendar names, file formats, etc.)",
    )
    
    # Restoration policies
    restoration_policy = Column(
        JSON,
        nullable=True,
        doc="Policies for restoration (conflict resolution, date ranges, duplicate handling, etc.)",
    )
    
    # Status and metadata
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this configuration is active",
    )
    
    # Timestamps
    created_at = Column(UTCDateTime(), default=datetime.now, nullable=False)
    updated_at = Column(
        UTCDateTime(),
        default=datetime.now,
        onupdate=datetime.now,
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="restoration_configurations")

    def __repr__(self):
        return f"<RestorationConfiguration(id={self.id}, name='{self.name}', source_type='{self.source_type}', destination_type='{self.destination_type}')>"

    def validate_source_config(self) -> bool:
        """Validate source configuration based on source type."""
        if self.source_type == RestorationType.AUDIT_LOG.value:
            required_keys = ["action_types", "date_range"]
            return all(key in self.source_config for key in required_keys)
        elif self.source_type == RestorationType.BACKUP_CALENDAR.value:
            required_keys = ["calendar_names"]
            return all(key in self.source_config for key in required_keys)
        elif self.source_type == RestorationType.EXPORT_FILE.value:
            required_keys = ["file_path", "file_format"]
            return all(key in self.source_config for key in required_keys)
        return False

    def validate_destination_config(self) -> bool:
        """Validate destination configuration based on destination type."""
        if self.destination_type == DestinationType.LOCAL_CALENDAR.value:
            required_keys = ["calendar_name"]
            return all(key in self.destination_config for key in required_keys)
        elif self.destination_type == DestinationType.MSGRAPH_CALENDAR.value:
            required_keys = ["calendar_name"]
            return all(key in self.destination_config for key in required_keys)
        elif self.destination_type == DestinationType.EXPORT_FILE.value:
            required_keys = ["file_path", "file_format"]
            return all(key in self.destination_config for key in required_keys)
        return False

    def is_valid(self) -> bool:
        """Check if the configuration is valid."""
        return self.validate_source_config() and self.validate_destination_config()
