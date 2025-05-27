from core.repositories.appointment_repository_base import BaseAppointmentRepository
from core.models.appointment import Appointment
from typing import List, Optional

class MSGraphAppointmentRepository(BaseAppointmentRepository):
    def __init__(self, msgraph_client):
        self.client = msgraph_client

    def get_by_id(self, appointment_id: int) -> Optional[Appointment]:
        data = self.client.get_event(appointment_id)
        return self._map_api_to_model(data) if data else None

    def add(self, appointment: Appointment) -> None:
        data = self._map_model_to_api(appointment)
        self.client.create_event(data)

    def list_for_user(self, user_id: int, page: int = 1, page_size: int = 100) -> List[Appointment]:
        # Assume filters can be passed to the client
        events, _ = self.client.list_events(filters={"user_id": user_id}, page=page, page_size=page_size)
        return [self._map_api_to_model(e) for e in events]

    def update(self, appointment: Appointment) -> None:
        data = self._map_model_to_api(appointment)
        self.client.update_event(data)

    def delete(self, appointment_id: int) -> None:
        self.client.delete_event(appointment_id)

    def _map_api_to_model(self, data) -> Appointment:
        # Stub: Map MS Graph event dict to Appointment model
        return Appointment(
            id=data.get('id'),
            user_id=data.get('user_id'),
            start_time=data.get('start_time'),
            end_time=data.get('end_time'),
            subject=data.get('subject'),
            is_private=data.get('is_private', False),
            is_archived=data.get('is_archived', False),
            is_out_of_office=data.get('is_out_of_office', False)
        )

    def _map_model_to_api(self, appointment: Appointment) -> dict:
        # Stub: Map Appointment model to MS Graph event dict
        return {
            'id': appointment.id,
            'user_id': appointment.user_id,
            'start_time': appointment.start_time,
            'end_time': appointment.end_time,
            'subject': appointment.subject,
            'is_private': appointment.is_private,
            'is_archived': appointment.is_archived,
            'is_out_of_office': appointment.is_out_of_office
        } 