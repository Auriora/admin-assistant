from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime, UTC

Base = declarative_base()

class Appointment(Base):
    """
    SQLAlchemy model for an appointment.
    """
    __tablename__ = 'appointments'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    subject = Column(String)
    location_id = Column(Integer, ForeignKey('locations.id'))
    category_id = Column(Integer, ForeignKey('categories.id'))
    is_private = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    is_out_of_office = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relationships (optional, can be commented out if not needed in core)
    # user = relationship('User', back_populates='appointments')
    # location = relationship('Location', back_populates='appointments')
    # category = relationship('Category', back_populates='appointments')
    # timesheet_id = Column(Integer, ForeignKey('timesheets.id'))
    # timesheet = relationship('Timesheet', back_populates='appointments') 