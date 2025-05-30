from core.repositories.appointment_repository_base import BaseAppointmentRepository
from core.models.appointment import Appointment
from typing import List, NoReturn, Optional, Dict, Any, TYPE_CHECKING
from dateutil import parser
import pytz
import asyncio
from core.exceptions import AppointmentRepositoryException
import logging
import sys
import nest_asyncio
from sqlalchemy.orm.attributes import InstrumentedAttribute

logger = logging.getLogger(__name__)
if TYPE_CHECKING:
    from msgraph.graph_service_client import GraphServiceClient
    from msgraph.generated.models.event import Event
    from core.models.user import User

DEFAULT_TIMEOUT = 30  # seconds

def _run_async(coro, timeout=DEFAULT_TIMEOUT):
    try:
        loop = asyncio.get_running_loop()
        # If already in an event loop, use nest_asyncio to allow nested run
        nest_asyncio.apply()
        return loop.run_until_complete(asyncio.wait_for(coro, timeout=timeout))
    except RuntimeError:
        # No running event loop
        return asyncio.run(asyncio.wait_for(coro, timeout=timeout))

# TODO extend repositories to handle bulk operations so that updates and deletes are not done one by one
# TODO add caching to the repositories
# TODO add lazy loading to the repositories
class MSGraphAppointmentRepository(BaseAppointmentRepository):
    """
    Repository for managing appointments via the Microsoft Graph API for a specific user's calendar.
    Handles conversion between MS Graph event dicts and Appointment models,
    ensuring correct timezone handling.
    Expects an instance of msgraph.core.GraphClient as msgraph_client and a user_email (UPN).
    """
    def __init__(self, msgraph_client: 'GraphServiceClient', user: 'User', calendar_id: str = ""):
        """
        Initialize the repository with a Microsoft GraphClient instance, User model, and calendar_id.
        :param msgraph_client: Authenticated msgraph.core.GraphClient instance.
        :param user: User model instance (must have .email).
        :param calendar_id: The calendar identifier (string). If empty, use the user's primary calendar.
        """
        self.client = msgraph_client
        self.user = user
        self.calendar_id = calendar_id or ""

    def _get_calendar(self):
        """Return the calendar object for the given user and calendar_id."""
        if self.calendar_id:
            return self.client.users.by_user_id(self.get_user_email()).calendars.by_calendar_id(self.calendar_id)
        else:
            return self.client.users.by_user_id(self.get_user_email()).calendar

    async def aget_by_id(self, ms_event_id: str) -> Optional[Appointment]:
        """
        Async: Retrieve an appointment by its MS Graph event id for this user's calendar.
        :param ms_event_id: The MS Graph event id.
        :return: Appointment instance or None if not found.
        """
        if not ms_event_id or not isinstance(ms_event_id, str):
            raise ValueError("ms_event_id (Graph event id) must be provided as a string.")
        try:
            event = await self._get_calendar().events.by_event_id(ms_event_id).get()
            if event:
                # msgraph-sdk Event does not have to_dict; use vars(event) to get a dict
                event_dict = vars(event)
                return self._map_api_to_model(event_dict)
            return None
        except Exception as e:
            logger.exception(f"Failed to get appointment by id {ms_event_id} for user {self.get_user_email()}")
            if hasattr(e, 'add_note'):
                e.add_note(f"Error in aget_by_id for user {self.get_user_email()} and event {ms_event_id}")
            raise AppointmentRepositoryException(f"Failed to get appointment by id {ms_event_id}") from e

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
            await self._get_calendar().events.post(body=event_body)
        except Exception as e:
            logger.exception(f"Failed to add appointment for user {self.get_user_email()}")
            if hasattr(e, 'add_note'):
                e.add_note(f"Error in aadd for user {self.get_user_email()} and appointment {getattr(appointment, 'subject', None)}")
            raise AppointmentRepositoryException("Failed to add appointment") from e

    async def alist_for_user(self, start_date=None, end_date=None) -> List[Appointment]:
        """
        Async: List appointments for this user's calendar from MS Graph, optionally filtered by date range.
        :param start_date: Optional start date (date or datetime) for filtering events.
        :param end_date: Optional end date (date or datetime) for filtering events.
        :return: List of Appointment instances.
        """
        try:
            if start_date is not None and end_date is not None:
                from datetime import datetime, time
                if isinstance(start_date, datetime):
                    start_str = start_date.isoformat()
                else:
                    start_str = datetime.combine(start_date, time.min).isoformat()
                if isinstance(end_date, datetime):
                    end_str = end_date.isoformat()
                else:
                    end_str = datetime.combine(end_date, time.max).isoformat()
                logger.debug(f"MSGraphAppointmentRepository.alist_for_user: Querying calendar_view from {start_str} to {end_str}")
                # Use absolute URL for MS Graph SDK compatibility
                user_id = self.get_user_email()
                url = f"https://graph.microsoft.com/v1.0/users/{user_id}/calendar/calendarView?startDateTime={start_str}&endDateTime={end_str}"
                logger.debug(f"Querying with URL: {url}")
                # Paging support: fetch all pages using odata_next_link/@odata.nextLink
                events = []
                page = await self._get_calendar().calendar_view.with_url(url).get()
                while page:
                    page_events = getattr(page, 'value', [])
                    events.extend(page_events)
                    # Try both odata_next_link and @odata.nextLink for compatibility
                    next_link = getattr(page, 'odata_next_link', None) or getattr(page, '@odata.nextLink', None)
                    if next_link:
                        page = await self._get_calendar().calendar_view.with_url(next_link).get()
                    else:
                        break
                return [self._map_api_to_model(vars(e)) for e in events]
            else:
                logger.debug("MSGraphAppointmentRepository.alist_for_user: Querying all events (no date range)")
                events_page = await self._get_calendar().events.get()
                events = getattr(events_page, 'value', [])
                return [self._map_api_to_model(vars(e)) for e in events]
        except Exception as e:
            logger.exception(f"Failed to list appointments for user {self.get_user_email()} from {start_date} to {end_date}")
            if hasattr(e, 'add_note'):
                e.add_note(f"Error in alist_for_user for user {self.get_user_email()} and range {start_date} to {end_date}")
            raise AppointmentRepositoryException("Failed to list appointments") from e

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
            await self._get_calendar().events.by_event_id(ms_event_id).patch(body=event_body)
        except Exception as e:
            logger.exception(f"Failed to update appointment {ms_event_id} for user {self.get_user_email()}")
            if hasattr(e, 'add_note'):
                e.add_note(f"Error in aupdate for user {self.get_user_email()} and event {ms_event_id}")
            raise AppointmentRepositoryException(f"Failed to update appointment {ms_event_id}") from e

    async def adelete(self, ms_event_id: str) -> None:
        """
        Async: Delete an appointment from MS Graph for this user's calendar.
        :param ms_event_id: The MS Graph event id.
        """
        if not ms_event_id or not isinstance(ms_event_id, str):
            raise ValueError("ms_event_id (Graph event id) must be provided as a string.")
        try:
            await self._get_calendar().events.by_event_id(ms_event_id).delete()
        except Exception as e:
            logger.exception(f"Failed to delete appointment {ms_event_id} for user {self.get_user_email()}")
            if hasattr(e, 'add_note'):
                e.add_note(f"Error in adelete for user {self.get_user_email()} and event {ms_event_id}")
            raise AppointmentRepositoryException(f"Failed to delete appointment {ms_event_id}") from e

    def get_user_email(self) -> str:
        """
        Get the user's email as a string.
        """
        return str(self.user.email)

    def to_json_safe_value(self, value):
        """
        Convert a value to a JSON-serializable form. For dicts/lists, recurse. For unknown types, use str().
        """
        import datetime
        if isinstance(value, dict):
            return {k: self.to_json_safe_value(v) for k, v in value.items() if isinstance(k, str)}
        elif isinstance(value, (list, tuple, set)):
            return [self.to_json_safe_value(v) for v in value]
        elif isinstance(value, (str, int, float, bool)) or value is None:
            return value
        elif isinstance(value, datetime.datetime):
            return value.isoformat()
        elif hasattr(value, '__dict__'):
            return self.to_json_safe_value(vars(value))
        elif hasattr(value, '__slots__'):
            return {slot: self.to_json_safe_value(getattr(value, slot)) for slot in value.__slots__ if hasattr(value, slot)}
        else:
            return str(value)

    def _map_api_to_model(self, data: Dict[str, Any]) -> Appointment:
        """
        Map an MS Graph event dict to an Appointment model instance, converting all fields to JSON-serializable types.
        Non-serializable fields are converted to string. Lists of objects are converted to lists of strings/dicts.
        """
        start_dt = self._parse_msgraph_datetime(data.get('start'))
        end_dt = self._parse_msgraph_datetime(data.get('end'))
        # Handle location: always assign a string
        location_val = data.get('location')
        if isinstance(location_val, dict):
            location_str = location_val.get('displayName', '')
        else:
            location_str = location_val if isinstance(location_val, str) else ''
        return Appointment(
            ms_event_id=self.to_json_safe_value(data.get('id')),
            user_id=self.user.id,
            start_time=start_dt,
            end_time=end_dt,
            subject=self.to_json_safe_value(data.get('subject')),
            show_as=self.to_json_safe_value(data.get('showAs')),
            sensitivity=self.to_json_safe_value(data.get('sensitivity')),
            location=location_str,
            attendees=self.to_json_safe_value(data.get('attendees')),
            organizer=self.to_json_safe_value(data.get('organizer')),
            categories=self.to_json_safe_value(data.get('categories')),
            importance=self.to_json_safe_value(data.get('importance')),
            reminder_minutes_before_start=self.to_json_safe_value(data.get('reminderMinutesBeforeStart')),
            is_all_day=self.to_json_safe_value(data.get('isAllDay')),
            response_status=self.to_json_safe_value(data.get('responseStatus')),
            series_master_id=self.to_json_safe_value(data.get('seriesMasterId')),
            online_meeting=self.to_json_safe_value(data.get('onlineMeeting')),
            body_content=self.to_json_safe_value(data.get('body', {}).get('content') if isinstance(data.get('body'), dict) else None),
            body_content_type=self.to_json_safe_value(data.get('body', {}).get('contentType') if isinstance(data.get('body'), dict) else None),
            body_preview=self.to_json_safe_value(data.get('bodyPreview')),
            recurrence=self.to_json_safe_value(data.get('recurrence')),
            ms_event_data=self.to_json_safe_value(data)
        )

    def _map_model_to_api(self, appointment: Appointment) -> dict:
        """
        Convert an Appointment model instance to a dict suitable for the MS Graph API, mirroring the serialization logic of _map_api_to_model.
        Fields that were stored as strings/dicts are converted back to the expected MS Graph format where possible.
        """
        def from_json_safe_value(val):
            # For now, just return as-is; further logic can be added if needed for MS Graph SDK compatibility
            return val
        def to_msgraph_time(dt):
            import pytz
            if not dt:
                return None
            tz = dt.tzinfo.zone if dt and hasattr(dt, 'tzinfo') and hasattr(dt.tzinfo, 'zone') else 'UTC'
            return {
                'dateTime': dt.isoformat() if hasattr(dt, 'isoformat') else str(dt),
                'timeZone': tz
            }
        # Helper to get a safe value (not a SQLAlchemy Column or subclass)
        def safe_val(val, default):
            if val is None:
                return default
            if isinstance(val, InstrumentedAttribute) or hasattr(val, 'expression'):
                return default
            if isinstance(val, (str, int, float, bool)):
                return val
            if isinstance(val, dict):
                return {k: safe_val(v, '') for k, v in val.items()}
            if isinstance(val, list):
                return [safe_val(v, '') for v in val]
            return str(val)
        # Helper for lists
        def safe_list(val):
            if val is None or isinstance(val, InstrumentedAttribute) or hasattr(val, 'expression'):
                return []
            if isinstance(val, list):
                return [safe_val(v, '') for v in val]
            return [safe_val(val, '')]
        # Helper for dict fields
        def safe_dict(dct, keys):
            if not isinstance(dct, dict):
                return {k: '' for k in keys}
            return {k: safe_val(dct.get(k), '') for k in keys}

        def ensure_json_serializable(val, default=None):
            from sqlalchemy.orm.attributes import InstrumentedAttribute
            import datetime
            if val is None:
                return default
            if isinstance(val, InstrumentedAttribute) or hasattr(val, 'expression'):
                return default
            if isinstance(val, bool):
                return val
            if isinstance(val, int):
                return val
            if isinstance(val, str):
                return val
            if isinstance(val, datetime.datetime):
                return val.isoformat()
            if isinstance(val, list):
                return [ensure_json_serializable(v, default) for v in val if not isinstance(v, InstrumentedAttribute) and not hasattr(v, 'expression')]
            if isinstance(val, dict):
                return {str(k): ensure_json_serializable(v, default) for k, v in val.items() if not isinstance(v, InstrumentedAttribute) and not hasattr(v, 'expression')}
            return str(val)

        def to_bool(val, default=False):
            try:
                if isinstance(val, bool):
                    return val
                if isinstance(val, (int, float)):
                    return bool(val)
                if isinstance(val, str):
                    return val.lower() in ("true", "1", "yes", "y")
            except Exception:
                pass
            return default

        def to_int(val, default=0):
            try:
                if isinstance(val, int):
                    return val
                if isinstance(val, str):
                    return int(val)
            except Exception:
                pass
            return default

        api_dict = {}
        api_dict['id'] = str(ensure_json_serializable(appointment.ms_event_id, ''))
        api_dict['subject'] = str(ensure_json_serializable(appointment.subject, ''))
        api_dict['start'] = ensure_json_serializable(to_msgraph_time(appointment.start_time), None)
        api_dict['end'] = ensure_json_serializable(to_msgraph_time(appointment.end_time), None)
        api_dict['showAs'] = str(ensure_json_serializable(appointment.show_as, ''))
        api_dict['sensitivity'] = str(ensure_json_serializable(appointment.sensitivity, ''))
        api_dict['location'] = {'displayName': str(ensure_json_serializable(appointment.location, ''))}
        api_dict['attendees'] = ensure_json_serializable(appointment.attendees, [])
        api_dict['categories'] = ensure_json_serializable(appointment.categories, [])
        api_dict['organizer'] = str(ensure_json_serializable(appointment.organizer, ''))
        api_dict['importance'] = str(ensure_json_serializable(appointment.importance, ''))
        # reminderMinutesBeforeStart: must be int
        api_dict['reminderMinutesBeforeStart'] = to_int(ensure_json_serializable(appointment.reminder_minutes_before_start, 0), 0)
        api_dict['isAllDay'] = to_bool(ensure_json_serializable(appointment.is_all_day, False), False)
        api_dict['responseStatus'] = str(ensure_json_serializable(appointment.response_status, ''))
        api_dict['seriesMasterId'] = str(ensure_json_serializable(appointment.series_master_id, ''))
        api_dict['onlineMeeting'] = str(ensure_json_serializable(appointment.online_meeting, ''))
        api_dict['body'] = {
            'contentType': str(ensure_json_serializable(appointment.body_content_type, '')),
            'content': str(ensure_json_serializable(appointment.body_content, ''))
        }
        api_dict['bodyPreview'] = str(ensure_json_serializable(appointment.body_preview, ''))
        api_dict['recurrence'] = ensure_json_serializable(getattr(appointment, 'recurrence', None), '')
        # Remove readonly fields if present
        readonly_fields = [
            'webLink', 'onlineMeetingUrl', 'onlineMeeting',
            'changeKey', 'createdDateTime', 'lastModifiedDateTime', 'calendar',
            'exceptionOccurrences', 'extensions', 'instances',
            'multiValueExtendedProperties', 'singleValueExtendedProperties',
            'cancelledOccurrences', 'seriesMasterId'
        ]
        for field in readonly_fields:
            api_dict.pop(field, None)
        return api_dict

    def _parse_msgraph_datetime(self, dt_obj: Optional[object]):
        """
        Parse a MS Graph API datetime dict or DateTimeTimeZone object to a timezone-aware datetime object.
        :param dt_obj: Dict with 'dateTime' and 'timeZone' keys, or DateTimeTimeZone object.
        :return: timezone-aware datetime object or None.
        """
        if dt_obj is None:
            return None
        # Handle dict (JSON) format
        if isinstance(dt_obj, dict):
            date_time = dt_obj.get('dateTime')
            tz_name = dt_obj.get('timeZone', 'UTC')
        # Handle MS Graph SDK object (DateTimeTimeZone)
        else:
            date_time = getattr(dt_obj, 'date_time', None)
            tz_name = getattr(dt_obj, 'time_zone', 'UTC')
        if not date_time:
            return None
        dt = parser.parse(date_time)
        try:
            import pytz
            tz = pytz.timezone(tz_name)
            if dt.tzinfo is None:
                dt = tz.localize(dt)
            else:
                dt = dt.astimezone(tz)
        except Exception:
            dt = dt.replace(tzinfo=pytz.UTC)
        return dt

    # Synchronous wrappers for compatibility with sync interface (if needed)
    def get_by_id(self, ms_event_id: str) -> Optional[Appointment]:
        """Sync wrapper for aget_by_id."""
        return _run_async(self.aget_by_id(ms_event_id))

    def add(self, appointment: Appointment) -> None:
        """Sync wrapper for aadd."""
        return _run_async(self.aadd(appointment))

    def list_for_user(self, start_date=None, end_date=None) -> List[Appointment]:
        """Sync wrapper for alist_for_user."""
        return _run_async(self.alist_for_user(start_date, end_date))

    def update(self, appointment: Appointment) -> None:
        """Sync wrapper for aupdate."""
        return _run_async(self.aupdate(appointment))

    def delete(self, ms_event_id: str) -> None:
        """Sync wrapper for adelete."""
        return _run_async(self.adelete(ms_event_id)) 