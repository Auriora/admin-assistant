from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from core.db import Base
from core.models.appointment import UTCDateTime


class Calendar(Base):
    """
    SQLAlchemy model for a user calendar (local, MS Graph, or virtual).
    Attributes:
        id (int): Primary key.
        user_id (int): Foreign key to User.
        ms_calendar_id (str): MS Graph calendar id (nullable).
        name (str): Human-readable name for the calendar.
        description (str): Optional description.
        calendar_type (str): Type of calendar ('real', 'archive', 'virtual', etc.).
        is_primary (bool): Whether this is the user's primary calendar.
        is_active (bool): Whether this calendar is active.
        created_at (datetime): Creation timestamp.
        updated_at (datetime): Last update timestamp.
        user (User): Relationship to User.
    """

    __tablename__ = "calendars"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ms_calendar_id = Column(String(255), nullable=True, doc="MS Graph calendar id")
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    calendar_type = Column(String(32), nullable=False, default="real")
    is_primary = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(UTCDateTime(), default=datetime.now(UTC), nullable=False)
    updated_at = Column(
        UTCDateTime(),
        default=datetime.now(UTC),
        onupdate=datetime.now(UTC),
        nullable=False,
    )

    user = relationship("User", back_populates="calendars")

    def __repr__(self) -> str:
        return f"<Calendar id={self.id} user_id={self.user_id} name={self.name} ms_calendar_id={self.ms_calendar_id} type={self.calendar_type} primary={self.is_primary} active={self.is_active}>"
