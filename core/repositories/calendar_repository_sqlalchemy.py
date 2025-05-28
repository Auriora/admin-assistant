from typing import List, Optional
from core.models.calendar import Calendar
from core.db import SessionLocal
from .calendar_repository_base import BaseCalendarRepository
from core.models.user import User

class SQLAlchemyCalendarRepository(BaseCalendarRepository):
    """
    Repository for managing Calendar entities using SQLAlchemy.
    """
    def __init__(self, user: User, session=None):
        super().__init__(user)
        self.session = session or SessionLocal()

    def get_by_id(self, calendar_id: int) -> Optional[Calendar]:
        """Retrieve a calendar by its ID."""
        return self.session.get(Calendar, calendar_id)

    def add(self, calendar: Calendar) -> None:
        """Add a new calendar."""
        self.session.add(calendar)
        self.session.commit()

    def list(self) -> List[Calendar]:
        """List all calendars for the repository's user."""
        return self.session.query(Calendar).filter_by(user_id=self.user.id).all()

    def update(self, calendar: Calendar) -> None:
        """Update an existing calendar."""
        self.session.merge(calendar)
        self.session.commit()

    def delete(self, calendar_id: int) -> None:
        """Delete a calendar by its ID."""
        calendar = self.get_by_id(calendar_id)
        if calendar:
            self.session.delete(calendar)
            self.session.commit() 