import asyncio
import logging
import sys
from typing import TYPE_CHECKING, Any, Dict, List, NoReturn, Optional

import nest_asyncio
import pytz
from dateutil import parser
from sqlalchemy.orm.attributes import InstrumentedAttribute

from core.exceptions import (
    AppointmentRepositoryException,
    ImmutableAppointmentException,
)
from core.models.appointment import Appointment
from core.repositories.appointment_repository_base import BaseAppointmentRepository

logger = logging.getLogger(__name__)
if TYPE_CHECKING:
    from msgraph.generated.models.event import Event
    from msgraph.graph_service_client import GraphServiceClient

    from core.models.user import User

DEFAULT_TIMEOUT = 30  # seconds


# Global event loop management for MSGraph operations
_global_loop = None
_loop_lock = None

def _get_or_create_event_loop():
    """
    Get or create a persistent event loop for MSGraph operations.
    This avoids the overhead and issues of creating/destroying loops for each operation.
    """
    global _global_loop, _loop_lock

    if _loop_lock is None:
        import threading
        _loop_lock = threading.Lock()

    with _loop_lock:
        if _global_loop is None or _global_loop.is_closed():
            _global_loop = asyncio.new_event_loop()
            # Apply nest_asyncio to allow nested event loops
            nest_asyncio.apply(_global_loop)
        return _global_loop

def _run_async(coro, timeout=DEFAULT_TIMEOUT):
    """
    Run an async coroutine in a sync context with proper event loop handling.
    Uses a persistent event loop to avoid creation/destruction overhead and issues.
    """
    try:
        # Try to get the current running event loop
        try:
            current_loop = asyncio.get_running_loop()
            # If we're already in an event loop, use nest_asyncio
            nest_asyncio.apply()
            # Create a task and run it
            task = asyncio.create_task(asyncio.wait_for(coro, timeout=timeout))
            return current_loop.run_until_complete(task)
        except RuntimeError:
            # No running event loop, use our persistent loop
            pass
    except Exception as e:
        logger.debug(f"Failed to use current event loop: {e}")

    # Use our persistent event loop
    try:
        loop = _get_or_create_event_loop()

        # Check if we need to start the loop in a thread
        if loop.is_running():
            # Loop is already running, use nest_asyncio
            nest_asyncio.apply(loop)
            task = asyncio.create_task(asyncio.wait_for(coro, timeout=timeout))
            return loop.run_until_complete(task)
        else:
            # Loop is not running, run the coroutine
            return loop.run_until_complete(asyncio.wait_for(coro, timeout=timeout))

    except Exception as e:
        logger.exception(f"Error in persistent event loop: {e}")
        # Fallback: create a new temporary loop
        try:
            return asyncio.run(asyncio.wait_for(coro, timeout=timeout))
        except Exception as fallback_e:
            logger.exception(f"Fallback event loop also failed: {fallback_e}")
            raise


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

    def __init__(
        self, msgraph_client: "GraphServiceClient", user: "User", calendar_id: str = ""
    ):
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
            return self.client.users.by_user_id(
                self.get_user_email()
            ).calendars.by_calendar_id(self.calendar_id)
        else:
            return self.client.users.by_user_id(self.get_user_email()).calendar

    async def aget_by_id(self, ms_event_id: str) -> Optional[Appointment]:
        """
        Async: Retrieve an appointment by its MS Graph event id for this user's calendar.
        :param ms_event_id: The MS Graph event id.
        :return: Appointment instance or None if not found.
        """
        if not ms_event_id or not isinstance(ms_event_id, str):
            raise ValueError(
                "ms_event_id (Graph event id) must be provided as a string."
            )
        try:
            event = await self._get_calendar().events.by_event_id(ms_event_id).get()
            if event:
                # msgraph-sdk Event does not have to_dict; use vars(event) to get a dict
                event_dict = vars(event)
                return self._map_api_to_model(event_dict)
            return None
        except Exception as e:
            logger.exception(
                f"Failed to get appointment by id {ms_event_id} for user {self.get_user_email()}"
            )
            if hasattr(e, "add_note"):
                e.add_note(
                    f"Error in aget_by_id for user {self.get_user_email()} and event {ms_event_id}"
                )
            raise AppointmentRepositoryException(
                f"Failed to get appointment by id {ms_event_id}"
            ) from e

    async def aadd(self, appointment: Appointment) -> None:
        """
        Async: Add a new appointment to MS Graph for this user's calendar.
        :param appointment: Appointment model instance.
        """
        try:
            from msgraph.generated.models.event import Event

            # Create Event object with minimal required fields to debug the issue
            event_body = Event()
            data = self._map_model_to_api(appointment)

            # Debug: Log what data we're trying to send (can be removed after testing)
            # print(f"[DEBUG] Creating event with data keys: {list(data.keys())}")
            # print(f"[DEBUG] Subject: {data.get('subject', '')}")
            # print(f"[DEBUG] Start: {data.get('start')}")
            # print(f"[DEBUG] End: {data.get('end')}")

            # Set required fields
            event_body.subject = data.get("subject", "")
            event_body.start = data.get("start")
            event_body.end = data.get("end")

            # Set optional fields (only if they have valid values)
            if data.get("body"):
                event_body.body = data.get("body")
            if data.get("location"):
                event_body.location = data.get("location")
            if data.get("categories"):
                event_body.categories = data.get("categories", [])
            if data.get("attendees"):
                event_body.attendees = data.get("attendees", [])
            if data.get("showAs"):
                event_body.show_as = data.get("showAs")
            if data.get("sensitivity"):
                event_body.sensitivity = data.get("sensitivity")
            if data.get("importance"):
                event_body.importance = data.get("importance")
            if data.get("reminderMinutesBeforeStart") is not None:
                event_body.reminder_minutes_before_start = data.get("reminderMinutesBeforeStart", 0)
            if data.get("isAllDay") is not None:
                event_body.is_all_day = data.get("isAllDay", False)

            # Don't set organizer - MS Graph sets this automatically for new events

            await self._get_calendar().events.post(body=event_body)
        except Exception as e:
            logger.exception(
                f"Failed to add appointment for user {self.get_user_email()}"
            )
            if hasattr(e, "add_note"):
                e.add_note(
                    f"Error in aadd for user {self.get_user_email()} and appointment {getattr(appointment, 'subject', None)}"
                )
            raise AppointmentRepositoryException("Failed to add appointment") from e

    async def aadd_bulk(self, appointments: List[Appointment]) -> List[str]:
        """
        Async: Add multiple appointments to MS Graph for this user's calendar.
        Returns a list of error messages for failed appointments.
        :param appointments: List of Appointment model instances.
        :return: List of error messages (empty if all successful).
        """
        errors = []
        for i, appointment in enumerate(appointments):
            try:
                await self.aadd(appointment)
            except Exception as e:
                error_msg = f"Failed to add appointment {getattr(appointment, 'subject', f'#{i+1}')}: {str(e)}"
                errors.append(error_msg)
                logger.exception(f"Bulk add error for appointment {i+1}: {e}")
        return errors

    def add_bulk(self, appointments: List[Appointment]) -> List[str]:
        """Sync wrapper for aadd_bulk."""
        return _run_async(self.aadd_bulk(appointments))

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
                logger.debug(
                    f"MSGraphAppointmentRepository.alist_for_user: Querying calendar_view from {start_str} to {end_str}"
                )
                # Use absolute URL for MS Graph SDK compatibility
                user_id = self.get_user_email()
                url = f"https://graph.microsoft.com/v1.0/users/{user_id}/calendar/calendarView?startDateTime={start_str}&endDateTime={end_str}"
                logger.debug(f"Querying with URL: {url}")
                # Paging support: fetch all pages using odata_next_link/@odata.nextLink
                events = []
                page = await self._get_calendar().calendar_view.with_url(url).get()
                while page:
                    page_events = getattr(page, "value", [])
                    events.extend(page_events)
                    # Try both odata_next_link and @odata.nextLink for compatibility
                    next_link = getattr(page, "odata_next_link", None) or getattr(
                        page, "@odata.nextLink", None
                    )
                    if next_link:
                        page = (
                            await self._get_calendar()
                            .calendar_view.with_url(next_link)
                            .get()
                        )
                    else:
                        break
                return [self._map_api_to_model(vars(e)) for e in events]
            else:
                logger.debug(
                    "MSGraphAppointmentRepository.alist_for_user: Querying all events (no date range)"
                )
                events_page = await self._get_calendar().events.get()
                events = getattr(events_page, "value", [])
                return [self._map_api_to_model(vars(e)) for e in events]
        except Exception as e:
            logger.exception(
                f"Failed to list appointments for user {self.get_user_email()} from {start_date} to {end_date}"
            )
            if hasattr(e, "add_note"):
                e.add_note(
                    f"Error in alist_for_user for user {self.get_user_email()} and range {start_date} to {end_date}"
                )
            raise AppointmentRepositoryException("Failed to list appointments") from e

    async def aupdate(self, appointment: Appointment) -> None:
        """
        Async: Update an existing appointment in MS Graph for this user's calendar.
        :param appointment: Appointment model instance.
        """
        # Check if appointment is immutable before updating
        appointment.validate_modification_allowed(self.user)

        data = self._map_model_to_api(appointment)
        ms_event_id = appointment.ms_event_id
        if ms_event_id is None or not isinstance(ms_event_id, str):
            raise ValueError(
                "Appointment must have a valid ms_event_id (string) for update."
            )
        try:
            from msgraph.generated.models.event import Event

            # Create Event object and set properties directly from the mapped data
            event_body = Event()
            data = self._map_model_to_api(appointment)

            # Set only writable properties for updates (exclude all readonly fields)
            event_body.subject = data.get("subject", "")
            event_body.start = data.get("start")
            event_body.end = data.get("end")
            event_body.show_as = data.get("showAs", "")
            event_body.sensitivity = data.get("sensitivity", "")
            event_body.location = data.get("location")
            event_body.attendees = data.get("attendees", [])
            event_body.categories = data.get("categories", [])
            event_body.importance = data.get("importance", "")
            event_body.reminder_minutes_before_start = data.get("reminderMinutesBeforeStart", 0)
            event_body.is_all_day = data.get("isAllDay", False)
            event_body.body = data.get("body")
            # Don't set bodyPreview - it's readonly and computed by MS Graph
            # Don't set responseStatus - it's readonly and represents user's response
            # Don't set seriesMasterId - it's readonly and only for recurring instances

            await self._get_calendar().events.by_event_id(ms_event_id).patch(
                body=event_body
            )
        except Exception as e:
            logger.exception(
                f"Failed to update appointment {ms_event_id} for user {self.get_user_email()}"
            )
            if hasattr(e, "add_note"):
                e.add_note(
                    f"Error in aupdate for user {self.get_user_email()} and event {ms_event_id}"
                )
            raise AppointmentRepositoryException(
                f"Failed to update appointment {ms_event_id}"
            ) from e

    async def adelete(self, ms_event_id: str) -> None:
        """
        Async: Delete an appointment from MS Graph for this user's calendar.
        :param ms_event_id: The MS Graph event id.
        """
        if not ms_event_id or not isinstance(ms_event_id, str):
            raise ValueError(
                "ms_event_id (Graph event id) must be provided as a string."
            )

        # First get the appointment to check immutability
        try:
            appointment = await self.aget_by_id(ms_event_id)
            if appointment:
                appointment.validate_modification_allowed(self.user)
        except Exception as e:
            # If we can't get the appointment, log but continue with deletion attempt
            logger.warning(
                f"Could not validate immutability for appointment {ms_event_id}: {e}"
            )

        try:
            await self._get_calendar().events.by_event_id(ms_event_id).delete()
        except Exception as e:
            logger.exception(
                f"Failed to delete appointment {ms_event_id} for user {self.get_user_email()}"
            )
            if hasattr(e, "add_note"):
                e.add_note(
                    f"Error in adelete for user {self.get_user_email()} and event {ms_event_id}"
                )
            raise AppointmentRepositoryException(
                f"Failed to delete appointment {ms_event_id}"
            ) from e

    def get_user_email(self) -> str:
        """
        Get the user's email as a string.
        """
        return str(self.user.email)

    def to_json_safe_value(self, value, _seen=None):
        """
        Convert a value to a JSON-serializable form. For dicts/lists, recurse. For unknown types, use str().
        Includes cycle detection to prevent infinite recursion.
        """
        import datetime

        if _seen is None:
            _seen = set()

        # Prevent infinite recursion by tracking seen objects
        if id(value) in _seen:
            return f"<circular reference to {type(value).__name__}>"

        if isinstance(value, dict):
            _seen.add(id(value))
            try:
                return {
                    k: self.to_json_safe_value(v, _seen)
                    for k, v in value.items()
                    if isinstance(k, str)
                }
            finally:
                _seen.discard(id(value))
        elif isinstance(value, (list, tuple, set)):
            _seen.add(id(value))
            try:
                return [self.to_json_safe_value(v, _seen) for v in value]
            finally:
                _seen.discard(id(value))
        elif isinstance(value, (str, int, float, bool)) or value is None:
            return value
        elif isinstance(value, datetime.datetime):
            return value.isoformat()
        elif hasattr(value, "__dict__"):
            _seen.add(id(value))
            try:
                return self.to_json_safe_value(vars(value), _seen)
            finally:
                _seen.discard(id(value))
        elif hasattr(value, "__slots__"):
            _seen.add(id(value))
            try:
                return {
                    slot: self.to_json_safe_value(getattr(value, slot), _seen)
                    for slot in value.__slots__
                    if hasattr(value, slot)
                }
            finally:
                _seen.discard(id(value))
        else:
            return str(value)

    def _map_api_to_model(self, data: Dict[str, Any]) -> Appointment:
        """
        Map an MS Graph event dict to an Appointment model instance, converting all fields to JSON-serializable types.
        Non-serializable fields are converted to string. Lists of objects are converted to lists of strings/dicts.
        """
        start_dt = self._parse_msgraph_datetime(data.get("start"))
        end_dt = self._parse_msgraph_datetime(data.get("end"))
        # Handle location: always assign a string
        location_val = data.get("location")
        if isinstance(location_val, dict):
            location_str = location_val.get("displayName", "")
        else:
            location_str = location_val if isinstance(location_val, str) else ""
        return Appointment(
            ms_event_id=self.to_json_safe_value(data.get("id")),
            user_id=self.user.id,
            start_time=start_dt,
            end_time=end_dt,
            subject=self.to_json_safe_value(data.get("subject")),
            show_as=self.to_json_safe_value(data.get("showAs")),
            sensitivity=self.to_json_safe_value(data.get("sensitivity")),
            location=location_str,
            attendees=self.to_json_safe_value(data.get("attendees")),
            organizer=self.to_json_safe_value(data.get("organizer")),
            categories=self.to_json_safe_value(data.get("categories")),
            importance=self.to_json_safe_value(data.get("importance")),
            reminder_minutes_before_start=self.to_json_safe_value(
                data.get("reminderMinutesBeforeStart")
            ),
            is_all_day=self.to_json_safe_value(data.get("isAllDay")),
            response_status=self.to_json_safe_value(data.get("responseStatus")),
            series_master_id=self.to_json_safe_value(data.get("seriesMasterId")),
            online_meeting=self.to_json_safe_value(data.get("onlineMeeting")),
            body_content=self.to_json_safe_value(
                data.get("body", {}).get("content")
                if isinstance(data.get("body"), dict)
                else None
            ),
            body_content_type=self.to_json_safe_value(
                data.get("body", {}).get("contentType")
                if isinstance(data.get("body"), dict)
                else None
            ),
            body_preview=self.to_json_safe_value(data.get("bodyPreview")),
            recurrence=self.to_json_safe_value(data.get("recurrence")),
            ms_event_data=self.to_json_safe_value(data),
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
            from msgraph.generated.models.date_time_time_zone import DateTimeTimeZone

            if not dt:
                return None
            tz = (
                dt.tzinfo.zone
                if dt and hasattr(dt, "tzinfo") and hasattr(dt.tzinfo, "zone")
                else "UTC"
            )
            # Return proper DateTimeTimeZone object instead of dict
            dt_tz = DateTimeTimeZone()
            dt_tz.date_time = dt.isoformat() if hasattr(dt, "isoformat") else str(dt)
            dt_tz.time_zone = tz
            return dt_tz

        # Helper to get a safe value (not a SQLAlchemy Column or subclass)
        def safe_val(val, default):
            if val is None:
                return default
            if isinstance(val, InstrumentedAttribute) or hasattr(val, "expression"):
                return default
            if isinstance(val, (str, int, float, bool)):
                return val
            if isinstance(val, dict):
                return {k: safe_val(v, "") for k, v in val.items()}
            if isinstance(val, list):
                return [safe_val(v, "") for v in val]
            return str(val)

        # Helper for lists
        def safe_list(val):
            if (
                val is None
                or isinstance(val, InstrumentedAttribute)
                or hasattr(val, "expression")
            ):
                return []
            if isinstance(val, list):
                return [safe_val(v, "") for v in val]
            return [safe_val(val, "")]

        # Helper for dict fields
        def safe_dict(dct, keys):
            if not isinstance(dct, dict):
                return {k: "" for k in keys}
            return {k: safe_val(dct.get(k), "") for k in keys}

        def ensure_json_serializable(val, default=None):
            import datetime

            from sqlalchemy.orm.attributes import InstrumentedAttribute

            if val is None:
                return default
            if isinstance(val, InstrumentedAttribute) or hasattr(val, "expression"):
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
                return [
                    ensure_json_serializable(v, default)
                    for v in val
                    if not isinstance(v, InstrumentedAttribute)
                    and not hasattr(v, "expression")
                ]
            if isinstance(val, dict):
                return {
                    str(k): ensure_json_serializable(v, default)
                    for k, v in val.items()
                    if not isinstance(v, InstrumentedAttribute)
                    and not hasattr(v, "expression")
                }
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
        # Don't include ID for new events - it will be assigned by MS Graph
        # api_dict["id"] = str(ensure_json_serializable(appointment.ms_event_id, ""))
        api_dict["subject"] = str(ensure_json_serializable(appointment.subject, ""))
        # Don't apply ensure_json_serializable to DateTimeTimeZone objects
        api_dict["start"] = to_msgraph_time(appointment.start_time)
        api_dict["end"] = to_msgraph_time(appointment.end_time)

        # Only set showAs if it has a valid value
        show_as_val = ensure_json_serializable(appointment.show_as, "")
        if show_as_val and str(show_as_val).strip():
            api_dict["showAs"] = str(show_as_val)

        # Only set sensitivity if it has a valid value
        sensitivity_val = ensure_json_serializable(appointment.sensitivity, "")
        if sensitivity_val and str(sensitivity_val).strip():
            api_dict["sensitivity"] = str(sensitivity_val)
        # Create proper Location object
        from msgraph.generated.models.location import Location
        location_obj = Location()
        location_obj.display_name = str(ensure_json_serializable(appointment.location, ""))
        api_dict["location"] = location_obj

        # Create proper Attendee objects
        from msgraph.generated.models.attendee import Attendee
        from msgraph.generated.models.email_address import EmailAddress
        from msgraph.generated.models.attendee_type import AttendeeType

        attendees_list = []
        raw_attendees = ensure_json_serializable(appointment.attendees, [])
        if isinstance(raw_attendees, list):
            for attendee_data in raw_attendees:
                if isinstance(attendee_data, dict):
                    # Only create attendee if we have valid email address data
                    if "emailAddress" in attendee_data:
                        email_data = attendee_data["emailAddress"]
                        if isinstance(email_data, dict) and email_data.get("address"):
                            attendee_obj = Attendee()

                            # Set email address
                            email_addr = EmailAddress()
                            email_addr.address = email_data.get("address", "")
                            email_addr.name = email_data.get("name", "")
                            attendee_obj.email_address = email_addr

                            # Set attendee type
                            attendee_type_str = attendee_data.get("type", "required").lower()
                            if attendee_type_str == "required":
                                attendee_obj.type = AttendeeType.Required
                            elif attendee_type_str == "optional":
                                attendee_obj.type = AttendeeType.Optional
                            else:
                                attendee_obj.type = AttendeeType.Required  # default

                            attendees_list.append(attendee_obj)

        api_dict["attendees"] = attendees_list
        api_dict["categories"] = ensure_json_serializable(appointment.categories, [])

        # Don't set organizer for new events - MS Graph will set it automatically
        # The organizer field is readonly for new events and causes ErrorInvalidIdMalformed
        # api_dict["organizer"] = str(ensure_json_serializable(appointment.organizer, ""))

        # Don't set importance if it's empty/None to avoid validation issues
        importance_val = ensure_json_serializable(appointment.importance, "")
        if importance_val and str(importance_val).strip():
            api_dict["importance"] = str(importance_val)
        # reminderMinutesBeforeStart: must be int
        api_dict["reminderMinutesBeforeStart"] = to_int(
            ensure_json_serializable(appointment.reminder_minutes_before_start, 0), 0
        )
        api_dict["isAllDay"] = to_bool(
            ensure_json_serializable(appointment.is_all_day, False), False
        )
        # Don't include readonly fields in API dict
        # api_dict["responseStatus"] = str(ensure_json_serializable(appointment.response_status, ""))
        # api_dict["seriesMasterId"] = str(ensure_json_serializable(appointment.series_master_id, ""))
        # api_dict["onlineMeeting"] = str(ensure_json_serializable(appointment.online_meeting, ""))

        # Create proper ItemBody object
        from msgraph.generated.models.item_body import ItemBody
        from msgraph.generated.models.body_type import BodyType

        body_obj = ItemBody()
        content_type_str = str(ensure_json_serializable(appointment.body_content_type, "text")).lower()
        if content_type_str == "html":
            body_obj.content_type = BodyType.Html
        else:
            body_obj.content_type = BodyType.Text
        body_obj.content = str(ensure_json_serializable(appointment.body_content, ""))
        api_dict["body"] = body_obj
        # Don't include bodyPreview - it's readonly and computed by MS Graph
        # api_dict["bodyPreview"] = str(ensure_json_serializable(appointment.body_preview, ""))
        api_dict["recurrence"] = ensure_json_serializable(
            getattr(appointment, "recurrence", None), ""
        )
        # Remove readonly fields if present
        readonly_fields = [
            "id",  # Auto-generated unique identifier
            "webLink",  # Computed URL
            "onlineMeetingUrl",  # Deprecated readonly field
            "onlineMeeting",  # Readonly after initialization
            "changeKey",  # Version identifier
            "createdDateTime",  # Auto-generated timestamp
            "lastModifiedDateTime",  # Auto-generated timestamp
            "bodyPreview",  # Computed preview
            "responseStatus",  # User's response, not organizer setting
            "seriesMasterId",  # Only for recurring instances
            "type",  # Computed event type
            "hasAttachments",  # Computed field
            "isCancelled",  # Computed field
            "isDraft",  # Computed field
            "isOrganizer",  # Computed field
            "originalStart",  # Only for recurring instances
            "originalStartTimeZone",  # Only for recurring instances
            "originalEndTimeZone",  # Only for recurring instances
            "cancelledOccurrences",  # Only for series masters
            "calendar",  # Navigation property
            "exceptionOccurrences",  # Navigation property
            "extensions",  # Navigation property
            "instances",  # Navigation property
            "multiValueExtendedProperties",  # Navigation property
            "singleValueExtendedProperties",  # Navigation property
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
            date_time = dt_obj.get("dateTime")
            tz_name = dt_obj.get("timeZone", "UTC")
        # Handle MS Graph SDK object (DateTimeTimeZone)
        else:
            date_time = getattr(dt_obj, "date_time", None)
            tz_name = getattr(dt_obj, "time_zone", "UTC")
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
        # Check immutability before async call for better error handling
        appointment.validate_modification_allowed(self.user)
        return _run_async(self.aupdate(appointment))

    def delete(self, ms_event_id: str) -> None:
        """Sync wrapper for adelete."""
        return _run_async(self.adelete(ms_event_id))
