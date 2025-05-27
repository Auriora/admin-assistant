from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON
from datetime import datetime, UTC
from core.db import Base

class Appointment(Base):
    """
    SQLAlchemy model for an appointment.
    - recurrence: RFC 5545 RRULE string for recurring events (nullable)
    - ms_event_data: Full original MS Graph event as JSON (nullable)
    """
    __tablename__ = 'appointments'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    subject = Column(String)
    location_id = Column(Integer, ForeignKey('locations.id'), nullable=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    timesheet_id = Column(Integer, ForeignKey('timesheets.id'), nullable=True)
    is_private = Column(Boolean, default=False)
    is_out_of_office = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    recurrence = Column(String, nullable=True, doc="RFC 5545 RRULE string for recurring events.")
    ms_event_data = Column(JSON, nullable=True, doc="Full original MS Graph event as JSON.")
    created_at = Column(DateTime(timezone=True), default=datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(UTC), onupdate=datetime.now(UTC))
    # Relationships (optional, for completeness)
    # user = relationship('User', back_populates='appointments')
    # location = relationship('Location')
    # category = relationship('Category')
    # timesheet = relationship('Timesheet') 