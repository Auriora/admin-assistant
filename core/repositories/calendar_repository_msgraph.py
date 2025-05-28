from typing import List, Optional
from core.models.calendar import Calendar
from .calendar_repository_base import BaseCalendarRepository
from core.models.user import User

class MSGraphCalendarRepository(BaseCalendarRepository):
    """
    Repository for managing Calendar entities via Microsoft Graph API.
    """
    def __init__(self, msgraph_client, user: User):
        super().__init__(user)
        self.client = msgraph_client

    def get_by_id(self, calendar_id: int) -> Optional[Calendar]:
        """Retrieve a calendar by its ID from MS Graph."""
        raise NotImplementedError("MSGraphCalendarRepository.get_by_id not implemented yet.")

    def add(self, calendar: Calendar) -> None:
        """Add a new calendar via MS Graph."""
        raise NotImplementedError("MSGraphCalendarRepository.add not implemented yet.")

    def list(self) -> List[Calendar]:
        """List all calendars for the repository's user via MS Graph."""
        calendars = []
        try:
            ms_calendars = self.client.users.by_user_id(self.user.email).calendars.get()
            for ms_cal in getattr(ms_calendars, 'value', []):
                calendars.append(Calendar(
                    user_id=self.user.id,
                    ms_calendar_id=getattr(ms_cal, 'id', None),
                    name=getattr(ms_cal, 'name', None),
                    description=getattr(ms_cal, 'description', None),
                    is_primary=getattr(ms_cal, 'is_default', False),
                    is_active=True
                ))
            return calendars
        except Exception as e:
            raise RuntimeError(f"Failed to list calendars for user {self.user.id} via MS Graph: {e}")

    def update(self, calendar: Calendar) -> None:
        """Update an existing calendar via MS Graph."""
        raise NotImplementedError("MSGraphCalendarRepository.update not implemented yet.")

    def delete(self, calendar_id: int) -> None:
        """Delete a calendar by its ID via MS Graph."""
        raise NotImplementedError("MSGraphCalendarRepository.delete not implemented yet.") 