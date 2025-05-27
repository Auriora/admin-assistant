from core.repositories.appointment_repository_base import BaseAppointmentRepository
from core.models.appointment import Appointment
from typing import List, NoReturn, Optional, Dict, Any, TYPE_CHECKING
from dateutil import parser
import pytz
import asyncio
if TYPE_CHECKING:
    from msgraph.graph_service_client import GraphServiceClient
    from msgraph.generated.models.event import Event
    from core.models.user import User

class MSGraphAppointmentRepository(BaseAppointmentRepository):
    """
    Repository for managing appointments via the Microsoft Graph API for a specific user's calendar.
    Handles conversion between MS Graph event dicts and Appointment models,
    ensuring correct timezone handling.
    Expects an instance of msgraph.core.GraphClient as msgraph_client and a user_email (UPN).
    """
    def __init__(self, msgraph_client: 'GraphServiceClient', user: 'User'):
        """
        Initialize the repository with a Microsoft GraphClient instance and User model.
        :param msgraph_client: Authenticated msgraph.core.GraphClient instance.
        :param user: User model instance (must have .email).
        """
        self.client = msgraph_client
        self.user = user

    async def aget_by_id(self, ms_event_id: str) -> Optional[Appointment]:
        """
        Async: Retrieve an appointment by its MS Graph event id for this user's calendar.
        :param ms_event_id: The MS Graph event id.
        :return: Appointment instance or None if not found.
        """
        if not ms_event_id or not isinstance(ms_event_id, str):
            raise ValueError("ms_event_id (Graph event id) must be provided as a string.")
        try:
            event = await self.client.users.by_user_id(self.get_user_email()).events.by_event_id(ms_event_id).get()
            if event:
                # msgraph-sdk Event does not have to_dict; use vars(event) to get a dict
                event_dict = vars(event)
                return self._map_api_to_model(event_dict)
            return None
        except Exception:
            return None

    async def aadd(self, appointment: Appointment) -> None:
        """
        Async: Add a new appointment to MS Graph for this user's calendar.
        :param appointment: Appointment model instance.
        """
        data = self._map_model_to_api(appointment)
        try:
            from msgraph.generated.models.event import Event
            # Event.from_dict is not always available; fallback to manual assignment
            event_body = Event()
            for k, v in data.items():
                if hasattr(event_body, k):
                    setattr(event_body, k, v)
            await self.client.users.by_user_id(self.get_user_email()).calendar.events.post(body=event_body)
        except Exception as e:
            raise

    async def alist_for_user(self, user_id: int, page: int = 1, page_size: int = 100) -> List[Appointment]:
        """
        Async: List appointments for this user's calendar from MS Graph.
        :param user_id: User's unique identifier (ignored).
        :param page: Page number for pagination.
        :param page_size: Number of items per page.
        :return: List of Appointment instances.
        """
        try:
            # msgraph-sdk may require request_configuration for query params
            # If not supported, remove and fetch all events (TODO: add paging if needed)
            events_page = await self.client.users.by_user_id(self.get_user_email()).calendar.events.get()
            events = getattr(events_page, 'value', [])
            # Each event is an Event object; use vars() to get dict
            return [self._map_api_to_model(vars(e)) for e in events]
        except Exception:
            return []

    async def aupdate(self, appointment: Appointment) -> None:
        """
        Async: Update an existing appointment in MS Graph for this user's calendar.
        :param appointment: Appointment model instance.
        """
        data = self._map_model_to_api(appointment)
        ms_event_id = appointment.ms_event_id
        if ms_event_id is None or not isinstance(ms_event_id, str):
            raise ValueError("Appointment must have a valid ms_event_id (string) for update.")
        try:
            from msgraph.generated.models.event import Event
            event_body = Event()
            for k, v in data.items():
                if hasattr(event_body, k):
                    setattr(event_body, k, v)
            await self.client.users.by_user_id(self.get_user_email()).events.by_event_id(ms_event_id).patch(body=event_body)
        except Exception as e:
            raise

    async def adelete(self, ms_event_id: str) -> None:
        """
        Async: Delete an appointment from MS Graph for this user's calendar.
        :param ms_event_id: The MS Graph event id.
        """
        if not ms_event_id or not isinstance(ms_event_id, str):
            raise ValueError("ms_event_id (Graph event id) must be provided as a string.")
        try:
            await self.client.users.by_user_id(self.get_user_email()).events.by_event_id(ms_event_id).delete()
        except Exception as e:
            raise

    def get_user_email(self) -> str:
        """
        Get the user's email as a string.
        """
        return str(self.user.email)

    def _map_api_to_model(self, data: Dict[str, Any]) -> Appointment:
        """
        Map an MS Graph event dict to an Appointment model instance, including all relevant fields for round-trip safety.
        """
        start_dt = self._parse_msgraph_datetime(data.get('start'))
        end_dt = self._parse_msgraph_datetime(data.get('end'))
        return Appointment(
            ms_event_id=data.get('id'),
            user_id=self.user.id,
            start_time=start_dt,
            end_time=end_dt,
            subject=data.get('subject'),
            show_as=data.get('showAs'),
            sensitivity=data.get('sensitivity'),
            location=(data.get('location', {}).get('displayName') if isinstance(data.get('location'), dict) else data.get('location')),
            attendees=data.get('attendees'),
            organizer=data.get('organizer'),
            categories=data.get('categories'),
            importance=data.get('importance'),
            reminder_minutes_before_start=data.get('reminderMinutesBeforeStart'),
            is_all_day=data.get('isAllDay'),
            response_status=data.get('responseStatus'),
            series_master_id=data.get('seriesMasterId'),
            online_meeting=data.get('onlineMeeting'),
            body_content=(data.get('body', {}).get('content') if isinstance(data.get('body'), dict) else None),
            body_content_type=(data.get('body', {}).get('contentType') if isinstance(data.get('body'), dict) else None),
            body_preview=data.get('bodyPreview'),
            recurrence=data.get('recurrence'),
            ms_event_data=data
        )

    def _map_model_to_api(self, appointment: Appointment) -> dict:
        """
        Map an Appointment model instance to an MS Graph event dict, including all relevant fields for round-trip safety.
        """
        def to_msgraph_time(dt):
            tz = dt.tzinfo.zone if dt.tzinfo and hasattr(dt.tzinfo, 'zone') else 'UTC'
            return {
                'dateTime': dt.isoformat(),
                'timeZone': tz
            }
        def safe_value(val):
            from sqlalchemy.orm.attributes import InstrumentedAttribute
            if hasattr(val, 'expression') or isinstance(val, InstrumentedAttribute):
                return None
            return val
        ms_event_data = getattr(appointment, 'ms_event_data', None)
        base = dict(ms_event_data) if isinstance(ms_event_data, dict) else {}
        base.update({
            'id': safe_value(appointment.ms_event_id),
            'subject': safe_value(appointment.subject),
            'start': to_msgraph_time(safe_value(appointment.start_time)),
            'end': to_msgraph_time(safe_value(appointment.end_time)),
            'showAs': safe_value(appointment.show_as),
            'sensitivity': safe_value(appointment.sensitivity),
            'location': {'displayName': safe_value(appointment.location)} if appointment.location is not NoReturn else None,
            'attendees': safe_value(appointment.attendees),
            'organizer': safe_value(appointment.organizer),
            'categories': safe_value(appointment.categories),
            'importance': safe_value(appointment.importance),
            'reminderMinutesBeforeStart': safe_value(appointment.reminder_minutes_before_start),
            'isAllDay': safe_value(appointment.is_all_day),
            'responseStatus': safe_value(appointment.response_status),
            'seriesMasterId': safe_value(appointment.series_master_id),
            'onlineMeeting': safe_value(appointment.online_meeting),
            'body': {
                'contentType': safe_value(appointment.body_content_type),
                'content': safe_value(appointment.body_content)
            },
            'bodyPreview': safe_value(appointment.body_preview),
            'recurrence': safe_value(getattr(appointment, 'recurrence', None)),
        })
        readonly_fields = [
            'webLink', 'onlineMeetingUrl', 'onlineMeeting',
            'changeKey', 'createdDateTime', 'lastModifiedDateTime', 'calendar',
            'exceptionOccurrences', 'extensions', 'instances',
            'multiValueExtendedProperties', 'singleValueExtendedProperties',
            'cancelledOccurrences', 'seriesMasterId'
        ]
        for field in readonly_fields:
            base.pop(field, None)
        return base

    def _parse_msgraph_datetime(self, dt_dict: Optional[Dict[str, str]]):
        """
        Parse a MS Graph API datetime dict to a timezone-aware datetime object.
        :param dt_dict: Dict with 'dateTime' and 'timeZone' keys.
        :return: timezone-aware datetime object or None.
        """
        if not dt_dict or 'dateTime' not in dt_dict:
            return None
        dt = parser.parse(dt_dict['dateTime'])
        tz_name = dt_dict.get('timeZone', 'UTC')
        try:
            tz = pytz.timezone(tz_name)
            if dt.tzinfo is None:
                dt = tz.localize(dt)
            else:
                dt = dt.astimezone(tz)
        except Exception:
            # Fallback to UTC if timezone is invalid
            dt = dt.replace(tzinfo=pytz.UTC)
        return dt 

    # Synchronous wrappers for compatibility with sync interface (if needed)
    def get_by_id(self, ms_event_id: str) -> Optional[Appointment]:
        """Sync wrapper for aget_by_id."""
        return asyncio.run(self.aget_by_id(ms_event_id))

    def add(self, appointment: Appointment) -> None:
        """Sync wrapper for aadd."""
        return asyncio.run(self.aadd(appointment))

    def list_for_user(self, user_id: int, page: int = 1, page_size: int = 100) -> List[Appointment]:
        """Sync wrapper for alist_for_user."""
        return asyncio.run(self.alist_for_user(user_id, page, page_size))

    def update(self, appointment: Appointment) -> None:
        """Sync wrapper for aupdate."""
        return asyncio.run(self.aupdate(appointment))

    def delete(self, ms_event_id: str) -> None:
        """Sync wrapper for adelete."""
        return asyncio.run(self.adelete(ms_event_id)) 