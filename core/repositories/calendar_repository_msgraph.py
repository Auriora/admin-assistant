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

    def get_by_id(self, ms_calendar_id: str) -> Optional[Calendar]:
        """Retrieve a calendar by its MS Graph ID for the current user."""
        try:
            ms_cal = self.client.users.by_user_id(self.user.email).calendars.by_calendar_id(ms_calendar_id).get()
            if ms_cal:
                return Calendar(
                    user_id=self.user.id,
                    ms_calendar_id=getattr(ms_cal, 'id', None),
                    name=getattr(ms_cal, 'name', None),
                    description=getattr(ms_cal, 'description', None),
                    is_primary=getattr(ms_cal, 'is_default', False),
                    is_active=True
                )
            return None
        except Exception as e:
            raise RuntimeError(f"Failed to get calendar {ms_calendar_id} for user {self.user.id} via MS Graph: {e}") from e

    def add(self, calendar: Calendar) -> None:
        """Add a new calendar for the current user via MS Graph."""
        try:
            from msgraph.generated.models.calendar import Calendar as MsCalendar
            ms_cal = MsCalendar()
            ms_cal.name = str(calendar.name) if hasattr(calendar, 'name') else None
            ms_cal.description = str(calendar.description) if hasattr(calendar, 'description') else None
            self.client.users.by_user_id(self.user.email).calendars.post(body=ms_cal)
        except Exception as e:
            raise RuntimeError(f"Failed to add calendar for user {self.user.id} via MS Graph: {e}") from e

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
        """Update an existing calendar for the current user via MS Graph."""
        try:
            from msgraph.generated.models.calendar import Calendar as MsCalendar
            ms_cal = MsCalendar()
            ms_cal.name = str(calendar.name) if hasattr(calendar, 'name') else None
            ms_cal.description = str(calendar.description) if hasattr(calendar, 'description') else None
            self.client.users.by_user_id(self.user.email).calendars.by_calendar_id(calendar.ms_calendar_id).patch(body=ms_cal)
        except Exception as e:
            raise RuntimeError(f"Failed to update calendar {calendar.ms_calendar_id} for user {self.user.id} via MS Graph: {e}") from e

    def delete(self, ms_calendar_id: str) -> None:
        """Delete a calendar by its MS Graph ID for the current user."""
        try:
            self.client.users.by_user_id(self.user.email).calendars.by_calendar_id(ms_calendar_id).delete()
        except Exception as e:
            raise RuntimeError(f"Failed to delete calendar {ms_calendar_id} for user {self.user.id} via MS Graph: {e}") from e 