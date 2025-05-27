from core.repositories.appointment_repository_base import BaseAppointmentRepository
from core.models.appointment import Appointment
from typing import List, Optional, Dict, Any
from dateutil import parser
import pytz

class MSGraphAppointmentRepository(BaseAppointmentRepository):
    """
    Repository for managing appointments via the Microsoft Graph API.
    Handles conversion between MS Graph event dicts and Appointment models,
    ensuring correct timezone handling.
    """
    def __init__(self, msgraph_client):
        """
        Initialize the repository with an MS Graph client.
        :param msgraph_client: Authenticated MS Graph client instance.
        """
        self.client = msgraph_client

    def get_by_id(self, appointment_id: int) -> Optional[Appointment]:
        """
        Retrieve an appointment by its ID from MS Graph.
        :param appointment_id: The appointment's unique identifier.
        :return: Appointment instance or None if not found.
        """
        data = self.client.get_event(appointment_id)
        return self._map_api_to_model(data) if data else None

    def add(self, appointment: Appointment) -> None:
        """
        Add a new appointment to MS Graph.
        :param appointment: Appointment model instance.
        """
        data = self._map_model_to_api(appointment)
        self.client.create_event(data)

    def list_for_user(self, user_id: int, page: int = 1, page_size: int = 100) -> List[Appointment]:
        """
        List appointments for a user from MS Graph.
        :param user_id: User's unique identifier.
        :param page: Page number for pagination.
        :param page_size: Number of items per page.
        :return: List of Appointment instances.
        """
        events, _ = self.client.list_events(filters={"user_id": user_id}, page=page, page_size=page_size)
        return [self._map_api_to_model(e) for e in events]

    def update(self, appointment: Appointment) -> None:
        """
        Update an existing appointment in MS Graph.
        :param appointment: Appointment model instance.
        """
        data = self._map_model_to_api(appointment)
        self.client.update_event(data)

    def delete(self, appointment_id: int) -> None:
        """
        Delete an appointment from MS Graph.
        :param appointment_id: The appointment's unique identifier.
        """
        self.client.delete_event(appointment_id)

    def _map_api_to_model(self, data: Dict[str, Any]) -> Appointment:
        """
        Map an MS Graph event dict to an Appointment model instance.
        Handles timezone-aware datetime conversion using 'dateTime' and 'timeZone'.
        Assigns MS Graph event 'id' to ms_event_id (not id).
        :param data: MS Graph event dict.
        :return: Appointment model instance.
        """
        start_dt = self._parse_msgraph_datetime(data.get('start'))
        end_dt = self._parse_msgraph_datetime(data.get('end'))
        return Appointment(
            ms_event_id=data.get('id'),
            user_id=data.get('user_id'),
            start_time=start_dt,
            end_time=end_dt,
            subject=data.get('subject'),
            is_private=data.get('sensitivity', '').lower() == 'private',
            is_archived=True,
            is_out_of_office=data.get('showAs', '').lower() == 'oof',
            recurrence=data.get('recurrence'),
            ms_event_data=data,
        )

    def _map_model_to_api(self, appointment: Appointment) -> dict:
        """
        Map an Appointment model instance to an MS Graph event dict.
        Includes both 'dateTime' and 'timeZone' for start and end.
        :param appointment: Appointment model instance.
        :return: MS Graph event dict.
        """
        def to_msgraph_time(dt):
            tz = dt.tzinfo.zone if dt.tzinfo and hasattr(dt.tzinfo, 'zone') else 'UTC'
            return {
                'dateTime': dt.isoformat(),
                'timeZone': tz
            }
        return {
            'id': appointment.id,
            'user_id': appointment.user_id,
            'start': to_msgraph_time(appointment.start_time),
            'end': to_msgraph_time(appointment.end_time),
            'subject': appointment.subject,
            'is_private': appointment.is_private,
            'is_archived': appointment.is_archived,
            'is_out_of_office': appointment.is_out_of_office
        }

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