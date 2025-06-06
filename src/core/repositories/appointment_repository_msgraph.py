import asyncio
import logging
import sys
from typing import TYPE_CHECKING, Any, Dict, List, NoReturn, Optional

# Removed nest_asyncio - using enhanced async runner instead
import pytz
from dateutil import parser
from sqlalchemy.orm.attributes import InstrumentedAttribute

from core.exceptions import (
    AppointmentRepositoryException,
    ImmutableAppointmentException,
)
from core.models.appointment import Appointment
from core.repositories.appointment_repository_base import BaseAppointmentRepository
from core.utilities.async_runner import run_async

logger = logging.getLogger(__name__)
if TYPE_CHECKING:
    from msgraph.generated.models.event import Event
    from msgraph.graph_service_client import GraphServiceClient

    from core.models.user import User

DEFAULT_TIMEOUT = 30  # seconds


# Using enhanced async runner to resolve event loop issues


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
        Uses direct HTTP requests to avoid event loop issues with the MS Graph SDK.
        Returns a list of error messages for failed appointments.
        :param appointments: List of Appointment model instances.
        :return: List of error messages (empty if all successful).
        """
        if not appointments:
            return []

        # Use direct HTTP implementation to avoid event loop issues
        try:
            return await self.aadd_bulk_direct(appointments)
        except Exception as e:
            logger.exception(f"Direct HTTP bulk add failed, falling back to individual operations: {e}")

            # Fallback to individual operations with fresh HTTP clients
            errors = []
            for i, appointment in enumerate(appointments):
                try:
                    await self.aadd_direct(appointment)
                except Exception as individual_e:
                    error_msg = f"Failed to add appointment {getattr(appointment, 'subject', f'#{i+1}')}: {str(individual_e)}"
                    errors.append(error_msg)
                    logger.exception(f"Individual add error for appointment {i+1}: {individual_e}")
            return errors

    def add_bulk(self, appointments: List[Appointment]) -> List[str]:
        """Sync wrapper for aadd_bulk."""
        return run_async(self.aadd_bulk(appointments))

    async def aadd_direct(self, appointment: Appointment) -> None:
        """
        Async: Add a single appointment using direct HTTP requests to avoid event loop issues.
        This completely bypasses the MS Graph SDK.

        :param appointment: Appointment model instance to add
        """
        import httpx

        try:
            access_token = await self._get_fresh_access_token()

            # Convert appointment to JSON-serializable format for direct HTTP
            event_data = self._map_model_to_json(appointment)

            # Prepare headers
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "User-Agent": "admin-assistant/1.0"
            }

            # Determine the calendar endpoint
            if self.calendar_id and self.calendar_id != "primary":
                calendar_endpoint = f"/users/{self.get_user_email()}/calendars/{self.calendar_id}/events"
            else:
                calendar_endpoint = f"/users/{self.get_user_email()}/calendar/events"

            # Make the request with a fresh HTTP client
            timeout = httpx.Timeout(30.0, connect=10.0)
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as http_client:
                response = await http_client.post(
                    f"https://graph.microsoft.com/v1.0{calendar_endpoint}",
                    json=event_data,
                    headers=headers
                )

            if response.status_code not in [200, 201]:
                error_text = response.text if hasattr(response, 'text') else str(response.content)
                raise Exception(f"Failed to create event: HTTP {response.status_code} - {error_text}")

            logger.debug(f"Successfully created appointment via direct HTTP: {getattr(appointment, 'subject', 'Unknown')}")

        except Exception as e:
            logger.exception(f"Failed to add appointment via direct HTTP for user {self.get_user_email()}")
            raise AppointmentRepositoryException(f"Failed to add appointment: {str(e)}") from e

    async def aadd_bulk_direct(self, appointments: List[Appointment]) -> List[str]:
        """
        Async: Add multiple appointments using direct HTTP requests.
        This completely bypasses the MS Graph SDK to avoid event loop issues.

        :param appointments: List of Appointment model instances to add
        :return: List of error messages for failed appointments
        """
        if not appointments:
            return []

        errors = []

        # Process appointments individually with fresh HTTP clients
        for i, appointment in enumerate(appointments):
            try:
                await self.aadd_direct(appointment)
            except Exception as e:
                error_msg = f"Failed to add appointment {getattr(appointment, 'subject', f'#{i+1}')}: {str(e)}"
                errors.append(error_msg)
                logger.exception(f"Direct HTTP add error for appointment {i+1}: {e}")

        return errors

    async def acheck_for_duplicates(self, appointments: List[Appointment], start_date=None, end_date=None) -> List[Appointment]:
        """
        Async: Check for appointments that already exist in this calendar.
        Returns a list of appointments that do NOT exist in the destination (safe to add).

        :param appointments: List of appointments to check
        :param start_date: Optional start date for filtering existing appointments
        :param end_date: Optional end date for filtering existing appointments
        :return: List of appointments that don't exist in destination
        """
        try:
            # Try direct HTTP approach first to avoid event loop issues
            try:
                existing_appointments = await self.alist_for_user_direct(start_date, end_date)
                logger.debug(f"Successfully retrieved {len(existing_appointments)} existing appointments via direct HTTP")
            except Exception as direct_e:
                logger.warning(f"Direct HTTP approach failed, trying SDK approach: {direct_e}")
                # Fallback to SDK approach
                existing_appointments = await self.alist_for_user(start_date, end_date)
                logger.debug(f"Successfully retrieved {len(existing_appointments)} existing appointments via SDK")

            # Create a set of existing appointment signatures for fast lookup
            existing_signatures = set()
            for existing in existing_appointments:
                signature = self._create_appointment_signature(existing)
                if signature:
                    existing_signatures.add(signature)

            # Filter out appointments that already exist
            unique_appointments = []
            duplicate_count = 0

            for appointment in appointments:
                signature = self._create_appointment_signature(appointment)
                if signature and signature not in existing_signatures:
                    unique_appointments.append(appointment)
                else:
                    duplicate_count += 1

            logger.debug(f"Duplicate check: {duplicate_count} duplicates found, {len(unique_appointments)} unique appointments to add")
            return unique_appointments

        except Exception as e:
            logger.exception(f"Error checking for duplicates in destination calendar: {e}")
            # If duplicate checking fails, return all appointments to avoid data loss
            logger.warning("Duplicate checking failed completely - proceeding with all appointments to avoid data loss")
            return appointments

    def check_for_duplicates(self, appointments: List[Appointment], start_date=None, end_date=None) -> List[Appointment]:
        """Sync wrapper for acheck_for_duplicates."""
        return run_async(self.acheck_for_duplicates(appointments, start_date, end_date))

    def _create_appointment_signature(self, appointment: Appointment) -> Optional[str]:
        """
        Create a unique signature for an appointment based on key fields.
        Used for duplicate detection.

        :param appointment: Appointment to create signature for
        :return: Unique signature string or None if appointment is invalid
        """
        try:
            subject = getattr(appointment, 'subject', '') or ''
            start_time = getattr(appointment, 'start_time', None)
            end_time = getattr(appointment, 'end_time', None)

            if not start_time or not end_time:
                return None

            # Create signature from subject, start time, and end time
            # Use ISO format for consistent time comparison
            start_str = start_time.isoformat() if hasattr(start_time, 'isoformat') else str(start_time)
            end_str = end_time.isoformat() if hasattr(end_time, 'isoformat') else str(end_time)

            signature = f"{subject}|{start_str}|{end_str}"
            return signature

        except Exception as e:
            logger.debug(f"Error creating appointment signature: {e}")
            return None

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

    async def adelete_bulk(self, ms_event_ids: List[str]) -> Dict[str, Any]:
        """
        Async: Delete multiple appointments from MS Graph using batch API.
        Returns information about the deletion results for audit/reversal purposes.

        :param ms_event_ids: List of MS Graph event IDs to delete
        :return: Dict with 'successful_deletes', 'failed_deletes', and 'errors'
        """
        if not ms_event_ids:
            return {"successful_deletes": [], "failed_deletes": [], "errors": []}

        # Validate all event IDs first
        valid_event_ids = []
        for event_id in ms_event_ids:
            if event_id and isinstance(event_id, str):
                valid_event_ids.append(event_id)
            else:
                logger.warning(f"Invalid event ID skipped: {event_id}")

        if not valid_event_ids:
            return {"successful_deletes": [], "failed_deletes": [], "errors": ["No valid event IDs provided"]}

        # MS Graph batch API supports up to 20 requests per batch
        batch_size = 20
        all_successful = []
        all_failed = []
        all_errors = []

        # Process in batches of 20
        for i in range(0, len(valid_event_ids), batch_size):
            batch_event_ids = valid_event_ids[i:i + batch_size]
            try:
                batch_result = await self._delete_batch(batch_event_ids)
                all_successful.extend(batch_result["successful_deletes"])
                all_failed.extend(batch_result["failed_deletes"])
                all_errors.extend(batch_result["errors"])
            except Exception as e:
                logger.exception(f"Batch delete failed for batch starting at index {i}: {e}")
                # Mark all events in this batch as failed
                all_failed.extend(batch_event_ids)
                all_errors.append(f"Batch delete failed: {str(e)}")

        return {
            "successful_deletes": all_successful,
            "failed_deletes": all_failed,
            "errors": all_errors
        }

    async def _delete_batch(self, event_ids: List[str]) -> Dict[str, Any]:
        """
        Delete a batch of appointments using MS Graph batch API.
        Uses a fresh HTTP client to avoid event loop issues.

        :param event_ids: List of event IDs to delete (max 20)
        :return: Dict with successful/failed deletes and errors
        """
        import json
        import httpx

        if len(event_ids) > 20:
            raise ValueError("Batch size cannot exceed 20 events")

        # Build batch request payload
        batch_requests = []
        for i, event_id in enumerate(event_ids):
            # Use the correct calendar endpoint based on calendar_id
            if self.calendar_id:
                calendar_endpoint = f"/users/{self.get_user_email()}/calendars/{self.calendar_id}/events/{event_id}"
            else:
                calendar_endpoint = f"/users/{self.get_user_email()}/calendar/events/{event_id}"

            batch_requests.append({
                "id": str(i + 1),  # Batch request IDs must be strings
                "method": "DELETE",
                "url": calendar_endpoint
            })

        batch_payload = {"requests": batch_requests}

        try:
            # Get access token using a more robust method
            access_token = await self._get_fresh_access_token()

            # Make the batch request with a fresh HTTP client
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "User-Agent": "admin-assistant/1.0"
            }

            # Use a fresh HTTP client with proper timeout and connection settings
            timeout = httpx.Timeout(30.0, connect=10.0)
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as http_client:
                response = await http_client.post(
                    "https://graph.microsoft.com/v1.0/$batch",
                    json=batch_payload,
                    headers=headers
                )

            if response.status_code != 200:
                error_text = response.text if hasattr(response, 'text') else str(response.content)
                raise Exception(f"Batch request failed with status {response.status_code}: {error_text}")

            # Parse batch response
            batch_response = response.json()
            return self._parse_batch_delete_response(batch_response, event_ids)

        except Exception as e:
            logger.exception(f"Failed to execute batch delete: {e}")
            return {
                "successful_deletes": [],
                "failed_deletes": event_ids,
                "errors": [f"Batch delete failed: {str(e)}"]
            }

    async def _get_fresh_access_token(self) -> str:
        """
        Get a fresh access token using multiple fallback methods.
        """
        # Method 1: Try to get from cached MSAL token (CLI context)
        try:
            from core.utilities.auth_utility import get_cached_access_token
            cached_token = get_cached_access_token()
            if cached_token:
                logger.debug("Using cached MSAL token")
                return cached_token
        except Exception as e:
            logger.debug(f"Failed to get cached MSAL token: {e}")

        # Method 2: Try to get from user's stored credentials (web context)
        if hasattr(self.user, 'ms_access_token') and self.user.ms_access_token:
            # Check if token is still valid
            if hasattr(self.user, 'ms_token_expires_at') and self.user.ms_token_expires_at:
                from datetime import datetime, UTC
                if self.user.ms_token_expires_at > datetime.now(UTC):
                    logger.debug("Using valid stored user token")
                    return self.user.ms_access_token
                else:
                    logger.debug("User token is expired, attempting refresh")
                    # Try to refresh the token
                    try:
                        from web.app.services.msgraph import refresh_token
                        refreshed_token = refresh_token(self.user)
                        if refreshed_token:
                            logger.debug("Successfully refreshed user token")
                            return refreshed_token
                    except Exception as refresh_error:
                        logger.warning(f"Failed to refresh user token: {refresh_error}")

            # Token might be expired, but try anyway as a last resort
            logger.warning("Using potentially expired user token as fallback")
            return self.user.ms_access_token

        # Method 3: Try to extract from Graph client (if structure allows)
        try:
            # Try different possible client structures
            if hasattr(self.client, '_request_adapter'):
                auth_provider = self.client._request_adapter.authentication_provider
                access_token_result = await auth_provider.get_authorization_token("https://graph.microsoft.com/.default")
                return access_token_result.token
            elif hasattr(self.client, 'credentials'):
                # Try the credentials approach
                token = self.client.credentials.get_token("https://graph.microsoft.com/.default")
                return token.token
        except Exception as e:
            logger.debug(f"Failed to get token from Graph client: {e}")

        raise Exception("No valid access token available from any source")

    async def adelete_for_period_direct(self, start_date, end_date) -> List[Dict[str, Any]]:
        """
        Alternative implementation that uses direct HTTP requests to avoid event loop issues.
        This method completely bypasses the MS Graph SDK.

        :param start_date: Start date for deletion range
        :param end_date: End date for deletion range
        :return: List of deleted appointment information
        """
        import httpx

        try:
            access_token = await self._get_fresh_access_token()

            # Step 1: Get all appointments in the date range using direct HTTP
            appointments_to_delete = await self.alist_for_user_direct(start_date, end_date)

            if not appointments_to_delete:
                logger.info(f"No appointments found to delete for period {start_date} to {end_date}")
                return []

            # Step 2: Prepare appointment data for audit before deletion
            appointment_data_map = {}
            event_ids_to_delete = []

            for appointment in appointments_to_delete:
                ms_event_id = getattr(appointment, "ms_event_id", None)
                if ms_event_id:
                    # Capture appointment state before deletion for audit
                    appointment_data = {
                        "ms_event_id": ms_event_id,
                        "subject": getattr(appointment, "subject", None),
                        "start_time": getattr(appointment, "start_time", None),
                        "end_time": getattr(appointment, "end_time", None),
                        "categories": getattr(appointment, "categories", None),
                        "body": getattr(appointment, "body", None),
                        "location": getattr(appointment, "location", None),
                        "sensitivity": getattr(appointment, "sensitivity", None),
                        "show_as": getattr(appointment, "show_as", None),
                        "importance": getattr(appointment, "importance", None),
                        "is_all_day": getattr(appointment, "is_all_day", None),
                        "attendees": getattr(appointment, "attendees", None),
                    }
                    appointment_data_map[ms_event_id] = appointment_data
                    event_ids_to_delete.append(ms_event_id)

            if not event_ids_to_delete:
                logger.info(f"No valid event IDs found to delete for period {start_date} to {end_date}")
                return []

            # Step 3: Use bulk delete with direct HTTP
            logger.info(f"Attempting to delete {len(event_ids_to_delete)} appointments using direct HTTP bulk operations")
            bulk_result = await self._delete_bulk_direct(event_ids_to_delete, access_token)

            # Step 4: Prepare the return data for successfully deleted appointments
            deleted_appointments = []
            for event_id in bulk_result["successful_deletes"]:
                if event_id in appointment_data_map:
                    deleted_appointments.append(appointment_data_map[event_id])
                    logger.debug(f"Deleted appointment: {appointment_data_map[event_id]['subject']} ({event_id})")

            # Log any failures
            if bulk_result["failed_deletes"]:
                logger.warning(f"Failed to delete {len(bulk_result['failed_deletes'])} appointments: {bulk_result['failed_deletes']}")

            if bulk_result["errors"]:
                for error in bulk_result["errors"]:
                    logger.error(f"Bulk delete error: {error}")

            logger.info(f"Successfully deleted {len(deleted_appointments)} out of {len(event_ids_to_delete)} appointments from calendar for period {start_date} to {end_date}")
            return deleted_appointments

        except Exception as e:
            logger.exception(f"Failed to delete appointments for period {start_date} to {end_date} using direct HTTP")
            raise AppointmentRepositoryException(f"Failed to delete appointments for period") from e

    async def _delete_bulk_direct(self, event_ids: List[str], access_token: str) -> Dict[str, Any]:
        """
        Delete a batch of appointments using direct HTTP requests to MS Graph batch API.
        This completely bypasses the MS Graph SDK to avoid event loop issues.

        :param event_ids: List of event IDs to delete
        :param access_token: Valid access token for MS Graph
        :return: Dict with successful/failed deletes and errors
        """
        import httpx

        if not event_ids:
            return {"successful_deletes": [], "failed_deletes": [], "errors": []}

        # MS Graph batch API supports up to 20 requests per batch
        batch_size = 20
        all_successful = []
        all_failed = []
        all_errors = []

        # Process in batches of 20
        for i in range(0, len(event_ids), batch_size):
            batch_event_ids = event_ids[i:i + batch_size]
            try:
                batch_result = await self._delete_single_batch_direct(batch_event_ids, access_token)
                all_successful.extend(batch_result["successful_deletes"])
                all_failed.extend(batch_result["failed_deletes"])
                all_errors.extend(batch_result["errors"])
            except Exception as e:
                logger.exception(f"Direct HTTP batch delete failed for batch starting at index {i}: {e}")
                # Mark all events in this batch as failed
                all_failed.extend(batch_event_ids)
                all_errors.append(f"Direct HTTP batch delete failed: {str(e)}")

        return {
            "successful_deletes": all_successful,
            "failed_deletes": all_failed,
            "errors": all_errors
        }

    async def _delete_single_batch_direct(self, event_ids: List[str], access_token: str) -> Dict[str, Any]:
        """
        Delete a single batch of appointments using direct HTTP requests.

        :param event_ids: List of event IDs to delete (max 20)
        :param access_token: Valid access token for MS Graph
        :return: Dict with successful/failed deletes and errors
        """
        import httpx

        if len(event_ids) > 20:
            raise ValueError("Batch size cannot exceed 20 events")

        # Build batch request payload
        batch_requests = []
        for i, event_id in enumerate(event_ids):
            # Use the correct calendar endpoint based on calendar_id
            if self.calendar_id:
                calendar_endpoint = f"/users/{self.get_user_email()}/calendars/{self.calendar_id}/events/{event_id}"
            else:
                calendar_endpoint = f"/users/{self.get_user_email()}/calendar/events/{event_id}"

            batch_requests.append({
                "id": str(i + 1),  # Batch request IDs must be strings
                "method": "DELETE",
                "url": calendar_endpoint
            })

        batch_payload = {"requests": batch_requests}

        try:
            # Make the batch request with a fresh HTTP client
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "User-Agent": "admin-assistant/1.0"
            }

            # Use a fresh HTTP client with proper timeout and connection settings
            timeout = httpx.Timeout(30.0, connect=10.0)
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as http_client:
                response = await http_client.post(
                    "https://graph.microsoft.com/v1.0/$batch",
                    json=batch_payload,
                    headers=headers
                )

            if response.status_code != 200:
                error_text = response.text if hasattr(response, 'text') else str(response.content)
                raise Exception(f"Direct HTTP batch request failed with status {response.status_code}: {error_text}")

            # Parse batch response
            batch_response = response.json()
            return self._parse_batch_delete_response(batch_response, event_ids)

        except Exception as e:
            logger.exception(f"Failed to execute direct HTTP batch delete: {e}")
            return {
                "successful_deletes": [],
                "failed_deletes": event_ids,
                "errors": [f"Direct HTTP batch delete failed: {str(e)}"]
            }

    async def alist_for_user_direct(self, start_date=None, end_date=None) -> List[Appointment]:
        """
        Alternative implementation of alist_for_user using direct HTTP requests.
        This avoids event loop issues with the MS Graph SDK.

        :param start_date: Optional start date for filtering events
        :param end_date: Optional end date for filtering events
        :return: List of Appointment instances
        """
        import httpx

        try:
            access_token = await self._get_fresh_access_token()

            # Build the URL
            user_email = self.get_user_email()
            if self.calendar_id:
                base_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/calendars/{self.calendar_id}"
            else:
                base_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/calendar"

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

                url = f"{base_url}/calendarView?startDateTime={start_str}&endDateTime={end_str}"
            else:
                url = f"{base_url}/events"

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "User-Agent": "admin-assistant/1.0"
            }

            events = []
            timeout = httpx.Timeout(30.0, connect=10.0)

            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as http_client:
                while url:
                    response = await http_client.get(url, headers=headers)

                    if response.status_code != 200:
                        error_text = response.text if hasattr(response, 'text') else str(response.content)
                        raise Exception(f"Failed to fetch events: HTTP {response.status_code} - {error_text}")

                    data = response.json()
                    page_events = data.get("value", [])
                    events.extend(page_events)

                    # Check for next page
                    url = data.get("@odata.nextLink")

            # Convert to Appointment objects
            appointments = []
            for event_data in events:
                try:
                    appointment = self._map_api_to_model(event_data)
                    appointments.append(appointment)
                except Exception as e:
                    logger.warning(f"Failed to map event to appointment: {e}")
                    continue

            logger.debug(f"Fetched {len(appointments)} appointments using direct HTTP")
            return appointments

        except Exception as e:
            logger.exception(f"Failed to list appointments using direct HTTP: {e}")
            raise AppointmentRepositoryException("Failed to list appointments") from e

    def _parse_batch_delete_response(self, batch_response: Dict[str, Any], event_ids: List[str]) -> Dict[str, Any]:
        """
        Parse the batch response and categorize successful/failed deletions.

        :param batch_response: The JSON response from the batch API
        :param event_ids: Original list of event IDs in the same order as batch requests
        :return: Dict with successful/failed deletes and errors
        """
        successful_deletes = []
        failed_deletes = []
        errors = []

        responses = batch_response.get("responses", [])

        # Create a mapping from batch request ID to event ID
        id_to_event = {}
        for i, event_id in enumerate(event_ids):
            id_to_event[str(i + 1)] = event_id

        for response in responses:
            request_id = response.get("id")
            status = response.get("status")
            event_id = id_to_event.get(request_id)

            if not event_id:
                errors.append(f"Unknown request ID in batch response: {request_id}")
                continue

            if status == 204:  # HTTP 204 No Content - successful deletion
                successful_deletes.append(event_id)
                logger.debug(f"Successfully deleted appointment: {event_id}")
            else:
                failed_deletes.append(event_id)
                error_body = response.get("body", {})
                error_message = "Unknown error"

                if isinstance(error_body, dict) and "error" in error_body:
                    error_info = error_body["error"]
                    error_message = error_info.get("message", "Unknown error")

                errors.append(f"Failed to delete {event_id}: HTTP {status} - {error_message}")
                logger.warning(f"Failed to delete appointment {event_id}: HTTP {status} - {error_message}")

        # Check for any event IDs that weren't in the response
        responded_events = set(id_to_event[resp.get("id")] for resp in responses if resp.get("id") in id_to_event)
        missing_events = set(event_ids) - responded_events

        for missing_event in missing_events:
            failed_deletes.append(missing_event)
            errors.append(f"No response received for event {missing_event}")

        return {
            "successful_deletes": successful_deletes,
            "failed_deletes": failed_deletes,
            "errors": errors
        }

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

    def _map_model_to_json(self, appointment: Appointment) -> dict:
        """
        Convert an Appointment model instance to a JSON-serializable dict for direct HTTP requests.
        This method returns plain Python dictionaries instead of MS Graph SDK objects.
        """
        def to_json_time(dt):
            """Convert datetime to JSON-serializable format for MS Graph API."""
            if not dt:
                return None

            tz = (
                dt.tzinfo.zone
                if dt and hasattr(dt, "tzinfo") and hasattr(dt.tzinfo, "zone")
                else "UTC"
            )

            return {
                "dateTime": dt.isoformat() if hasattr(dt, "isoformat") else str(dt),
                "timeZone": tz
            }

        def ensure_json_serializable(val, default=None):
            """Ensure value is JSON serializable."""
            if val is None:
                return default
            if isinstance(val, (str, int, float, bool, list, dict)):
                return val
            return str(val)

        def to_int(val, default=0):
            """Convert value to int with fallback."""
            try:
                return int(val) if val is not None else default
            except (ValueError, TypeError):
                return default

        def to_bool(val, default=False):
            """Convert value to bool with fallback."""
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                return val.lower() in ('true', '1', 'yes', 'on')
            return bool(val) if val is not None else default

        # Build the JSON-serializable dictionary
        api_dict = {}

        # Basic fields
        api_dict["subject"] = str(ensure_json_serializable(appointment.subject, ""))
        api_dict["start"] = to_json_time(appointment.start_time)
        api_dict["end"] = to_json_time(appointment.end_time)

        # Optional fields - only include if they have valid values
        show_as_val = ensure_json_serializable(appointment.show_as, "")
        if show_as_val and str(show_as_val).strip():
            # Convert enum-style values to lowercase
            show_as_clean = str(show_as_val).lower()
            if "." in show_as_clean:
                show_as_clean = show_as_clean.split(".")[-1]
            api_dict["showAs"] = show_as_clean

        sensitivity_val = ensure_json_serializable(appointment.sensitivity, "")
        if sensitivity_val and str(sensitivity_val).strip():
            # Convert enum-style values to lowercase
            sensitivity_clean = str(sensitivity_val).lower()
            if "." in sensitivity_clean:
                sensitivity_clean = sensitivity_clean.split(".")[-1]
            api_dict["sensitivity"] = sensitivity_clean

        # Location as simple dict
        location_str = str(ensure_json_serializable(appointment.location, ""))
        if location_str:
            api_dict["location"] = {
                "displayName": location_str
            }

        # Attendees as list of dicts
        attendees_list = []
        raw_attendees = ensure_json_serializable(appointment.attendees, [])
        if isinstance(raw_attendees, list):
            for attendee_data in raw_attendees:
                if isinstance(attendee_data, dict) and "emailAddress" in attendee_data:
                    email_data = attendee_data["emailAddress"]
                    if isinstance(email_data, dict) and email_data.get("address"):
                        attendee_dict = {
                            "emailAddress": {
                                "address": email_data.get("address", ""),
                                "name": email_data.get("name", "")
                            }
                        }
                        # Add type if present
                        if "type" in attendee_data:
                            attendee_dict["type"] = attendee_data["type"]
                        attendees_list.append(attendee_dict)

        api_dict["attendees"] = attendees_list
        api_dict["categories"] = ensure_json_serializable(appointment.categories, [])

        # Importance - only if valid
        importance_val = ensure_json_serializable(appointment.importance, "")
        if importance_val and str(importance_val).strip():
            # Convert enum-style values to lowercase
            importance_clean = str(importance_val).lower()
            if "." in importance_clean:
                importance_clean = importance_clean.split(".")[-1]
            api_dict["importance"] = importance_clean

        # Reminder and all-day settings
        api_dict["reminderMinutesBeforeStart"] = to_int(
            ensure_json_serializable(appointment.reminder_minutes_before_start, 0), 0
        )
        api_dict["isAllDay"] = to_bool(
            ensure_json_serializable(appointment.is_all_day, False), False
        )

        # Body content
        content_type_str = str(ensure_json_serializable(appointment.body_content_type, "text")).lower()
        body_content = str(ensure_json_serializable(appointment.body_content, ""))

        api_dict["body"] = {
            "contentType": "html" if content_type_str == "html" else "text",
            "content": body_content
        }

        # Recurrence if present
        recurrence_val = ensure_json_serializable(getattr(appointment, "recurrence", None), "")
        if recurrence_val:
            api_dict["recurrence"] = recurrence_val

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
        return run_async(self.aget_by_id(ms_event_id))

    def add(self, appointment: Appointment) -> None:
        """Sync wrapper for aadd."""
        return run_async(self.aadd(appointment))

    def list_for_user(self, start_date=None, end_date=None) -> List[Appointment]:
        """Sync wrapper for alist_for_user."""
        return run_async(self.alist_for_user(start_date, end_date))

    def update(self, appointment: Appointment) -> None:
        """Sync wrapper for aupdate."""
        # Check immutability before async call for better error handling
        appointment.validate_modification_allowed(self.user)
        return run_async(self.aupdate(appointment))

    def delete(self, ms_event_id: str) -> None:
        """Sync wrapper for adelete."""
        return run_async(self.adelete(ms_event_id))

    def delete_bulk(self, ms_event_ids: List[str]) -> Dict[str, Any]:
        """Sync wrapper for adelete_bulk."""
        return run_async(self.adelete_bulk(ms_event_ids))

    async def adelete_for_period(self, start_date, end_date) -> List[Dict[str, Any]]:
        """
        Async: Delete all appointments in the specified date range from this calendar using bulk operations.
        Returns information about deleted appointments for audit/reversal purposes.

        :param start_date: Start date for deletion range
        :param end_date: End date for deletion range
        :return: List of deleted appointment information
        """
        try:
            # Use the direct HTTP implementation as primary method to avoid event loop issues
            logger.debug("Using direct HTTP implementation for delete operation")
            return await self.adelete_for_period_direct(start_date, end_date)

        except Exception as e:
            logger.exception(f"Direct HTTP delete failed, attempting fallback to SDK method: {e}")

            # Fallback to original SDK-based implementation
            try:
                # First, get all appointments in the date range
                appointments_to_delete = await self.alist_for_user(start_date, end_date)

                if not appointments_to_delete:
                    logger.info(f"No appointments found to delete for period {start_date} to {end_date}")
                    return []

                # Prepare appointment data for audit before deletion
                appointment_data_map = {}
                event_ids_to_delete = []

                for appointment in appointments_to_delete:
                    ms_event_id = getattr(appointment, "ms_event_id", None)
                    if ms_event_id:
                        # Capture appointment state before deletion for audit
                        appointment_data = {
                            "ms_event_id": ms_event_id,
                            "subject": getattr(appointment, "subject", None),
                            "start_time": getattr(appointment, "start_time", None),
                            "end_time": getattr(appointment, "end_time", None),
                            "categories": getattr(appointment, "categories", None),
                            "body": getattr(appointment, "body", None),
                            "location": getattr(appointment, "location", None),
                            "sensitivity": getattr(appointment, "sensitivity", None),
                            "show_as": getattr(appointment, "show_as", None),
                            "importance": getattr(appointment, "importance", None),
                            "is_all_day": getattr(appointment, "is_all_day", None),
                            "attendees": getattr(appointment, "attendees", None),
                        }
                        appointment_data_map[ms_event_id] = appointment_data
                        event_ids_to_delete.append(ms_event_id)

                if not event_ids_to_delete:
                    logger.info(f"No valid event IDs found to delete for period {start_date} to {end_date}")
                    return []

                # Use bulk delete for efficiency
                logger.info(f"Attempting to delete {len(event_ids_to_delete)} appointments using SDK bulk operations")
                bulk_result = await self.adelete_bulk(event_ids_to_delete)

                # Prepare the return data for successfully deleted appointments
                deleted_appointments = []
                for event_id in bulk_result["successful_deletes"]:
                    if event_id in appointment_data_map:
                        deleted_appointments.append(appointment_data_map[event_id])
                        logger.debug(f"Deleted appointment: {appointment_data_map[event_id]['subject']} ({event_id})")

                # Log any failures
                if bulk_result["failed_deletes"]:
                    logger.warning(f"Failed to delete {len(bulk_result['failed_deletes'])} appointments: {bulk_result['failed_deletes']}")

                if bulk_result["errors"]:
                    for error in bulk_result["errors"]:
                        logger.error(f"Bulk delete error: {error}")

                logger.info(f"Successfully deleted {len(deleted_appointments)} out of {len(event_ids_to_delete)} appointments from calendar for period {start_date} to {end_date}")
                return deleted_appointments

            except Exception as fallback_e:
                logger.exception(f"Both direct HTTP and SDK fallback methods failed for period {start_date} to {end_date}")
                raise AppointmentRepositoryException(f"Failed to delete appointments for period") from fallback_e

    def delete_for_period(self, start_date, end_date) -> List[Dict[str, Any]]:
        """Sync wrapper for adelete_for_period."""
        return run_async(self.adelete_for_period(start_date, end_date))
