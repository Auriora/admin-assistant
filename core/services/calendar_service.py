from typing import List, Optional
from core.models.calendar import Calendar
from core.repositories.calendar_repository_base import BaseCalendarRepository

class CalendarService:
    """
    Service for business logic related to Calendar entities.
    """
    def __init__(self, repository: BaseCalendarRepository):
        self.repository = repository

    def get_by_id(self, calendar_id: int) -> Optional[Calendar]:
        """Retrieve a calendar by its ID."""
        return self.repository.get_by_id(calendar_id)

    def create(self, calendar: Calendar) -> None:
        """Create a new calendar after validation."""
        self.validate(calendar)
        self.repository.add(calendar)

    def list(self) -> List[Calendar]:
        """List all calendars for a given user."""
        return self.repository.list()

    def update(self, calendar: Calendar) -> None:
        """Update an existing calendar after validation."""
        self.validate(calendar)
        self.repository.update(calendar)

    def delete(self, calendar_id: int) -> None:
        """Delete a calendar by its ID."""
        self.repository.delete(calendar_id)

    def validate(self, calendar: Calendar) -> None:
        """
        Validate Calendar fields. Raises ValueError if invalid.
        """
        name = getattr(calendar, 'name', None)
        if not name or not str(name).strip():
            raise ValueError("Calendar name is required.")
        # Add further validation as needed 