from abc import ABC, abstractmethod
from typing import List, Optional

from core.models.calendar import Calendar
from core.models.user import User


class BaseCalendarRepository(ABC):
    def __init__(self, user: User):
        self.user = user

    @abstractmethod
    def get_by_id(self, calendar_id: int) -> Optional[Calendar]:
        """Retrieve a calendar by its ID."""
        pass

    @abstractmethod
    def add(self, calendar: Calendar) -> None:
        """Add a new calendar."""
        pass

    @abstractmethod
    def list(self) -> List[Calendar]:
        """List all calendars for the repository's user."""
        pass

    @abstractmethod
    def update(self, calendar: Calendar) -> None:
        """Update an existing calendar."""
        pass

    @abstractmethod
    def delete(self, calendar_id: int) -> None:
        """Delete a calendar by its ID."""
        pass
