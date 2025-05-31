from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON, TypeDecorator
from datetime import datetime, timezone
from core.db import Base

class UTCDateTime(TypeDecorator):
    """
    SQLAlchemy type that always stores datetimes as UTC (naive in DB) and returns them as UTC-aware.
    Ensures cross-database consistency (SQLite, Postgres, MySQL).
    """
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and isinstance(value, datetime):
            if value.tzinfo is not None:
                value = value.astimezone(timezone.utc)
            return value.replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return value.replace(tzinfo=timezone.utc)
        return value

class Appointment(Base):
    """
    SQLAlchemy model for an appointment.
    - ms_event_id: Original MS Graph event id (nullable string)
    - recurrence: RFC 5545 RRULE string for recurring events (nullable)
    - ms_event_data: Full original MS Graph event as JSON (nullable)
    """
    __tablename__ = 'appointments'
    id = Column(Integer, primary_key=True)
    ms_event_id = Column(String, nullable=True, doc="Original MS Graph event id.")
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    start_time = Column(UTCDateTime(), nullable=False)
    end_time = Column(UTCDateTime(), nullable=False)
    subject = Column(String)
    location_id = Column(Integer, ForeignKey('locations.id'), nullable=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    timesheet_id = Column(Integer, ForeignKey('timesheets.id'), nullable=True)
    recurrence = Column(String, nullable=True, doc="RFC 5545 RRULE string for recurring events.")
    ms_event_data = Column(JSON, nullable=True, doc="Full original MS Graph event as JSON.")
    created_at = Column(UTCDateTime(), default=datetime.now(timezone.utc))
    updated_at = Column(UTCDateTime(), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    show_as = Column(String, nullable=True, doc="MS Graph showAs value (free, tentative, busy, oof, workingElsewhere, unknown)")
    sensitivity = Column(String, nullable=True, doc="MS Graph sensitivity value (normal, personal, private, confidential)")
    location = Column(String, nullable=True, doc="Event location (simple string)")
    attendees = Column(JSON, nullable=True, doc="List of attendees (MS Graph format)")
    organizer = Column(JSON, nullable=True, doc="Organizer info (MS Graph format)")
    categories = Column(JSON, nullable=True, doc="List of categories (MS Graph format)")
    importance = Column(String, nullable=True, doc="Event importance (low, normal, high)")
    reminder_minutes_before_start = Column(Integer, nullable=True, doc="Reminder minutes before start")
    is_all_day = Column(Boolean, nullable=True, doc="All-day event flag")
    response_status = Column(JSON, nullable=True, doc="Response status (MS Graph format)")
    series_master_id = Column(String, nullable=True, doc="Recurring event master id")
    online_meeting = Column(JSON, nullable=True, doc="Online meeting info (MS Graph format)")
    body_content = Column(String, nullable=True, doc="Event body content (text or html)")
    body_content_type = Column(String, nullable=True, doc="Body content type (text or html)")
    body_preview = Column(String, nullable=True, doc="Short preview of body content")
    calendar_id = Column(String, nullable=False, doc="ID of the calendar this appointment belongs to")
    is_archived = Column(Boolean, nullable=False, default=False, doc="Whether this appointment has been archived and is immutable")
    # Relationships (optional, for completeness)
    # user = relationship('User', back_populates='appointments')
    # location = relationship('Location')
    # category = relationship('Category')
    # timesheet = relationship('Timesheet')

    @property
    def is_private(self) -> bool:
        """Returns True if sensitivity is 'private'. Handles SQLAlchemy Column objects safely."""
        def safe_str(val):
            from sqlalchemy.orm.attributes import InstrumentedAttribute
            if hasattr(val, 'expression') or isinstance(val, InstrumentedAttribute):
                return ''
            return val or ''
        return safe_str(self.sensitivity).lower() == 'private'

    @property
    def is_out_of_office(self) -> bool:
        """Returns True if show_as is 'oof' (out of office). Handles SQLAlchemy Column objects safely."""
        def safe_str(val):
            from sqlalchemy.orm.attributes import InstrumentedAttribute
            if hasattr(val, 'expression') or isinstance(val, InstrumentedAttribute):
                return ''
            return val or ''
        return safe_str(self.show_as).lower() == 'oof'

    def is_immutable(self, current_user=None) -> bool:
        """
        Returns True if this appointment is immutable (archived and not modifiable).
        Archived appointments are immutable except for the user who owns them.

        Args:
            current_user: The user attempting to modify the appointment (optional)

        Returns:
            bool: True if the appointment is immutable for the given user
        """
        from sqlalchemy.orm.attributes import InstrumentedAttribute

        # Handle SQLAlchemy Column objects safely
        def safe_bool(val):
            if hasattr(val, 'expression') or isinstance(val, InstrumentedAttribute):
                return False
            return bool(val)

        # If not archived, it's not immutable
        if not safe_bool(self.is_archived):
            return False

        # If no current user provided, assume immutable
        if current_user is None:
            return True

        # If current user is the owner, they can modify archived appointments
        if hasattr(current_user, 'id') and hasattr(self, 'user_id'):
            return current_user.id != self.user_id

        # Default to immutable for safety
        return True

    def validate_modification_allowed(self, current_user=None) -> None:
        """
        Validates that modification is allowed for this appointment.
        Raises an exception if the appointment is immutable for the current user.

        Args:
            current_user: The user attempting to modify the appointment (optional)

        Raises:
            ImmutableAppointmentException: If the appointment is immutable and cannot be modified
        """
        if self.is_immutable(current_user):
            from core.exceptions import ImmutableAppointmentException
            raise ImmutableAppointmentException(
                f"Cannot modify archived appointment '{getattr(self, 'subject', 'Unknown')}' "
                f"(ID: {getattr(self, 'id', 'Unknown')}). Archived appointments are immutable "
                f"except for the original user."
            )