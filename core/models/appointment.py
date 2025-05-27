from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON
from datetime import datetime, UTC
from core.db import Base

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
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    subject = Column(String)
    location_id = Column(Integer, ForeignKey('locations.id'), nullable=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    timesheet_id = Column(Integer, ForeignKey('timesheets.id'), nullable=True)
    recurrence = Column(String, nullable=True, doc="RFC 5545 RRULE string for recurring events.")
    ms_event_data = Column(JSON, nullable=True, doc="Full original MS Graph event as JSON.")
    created_at = Column(DateTime(timezone=True), default=datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(UTC), onupdate=datetime.now(UTC))
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