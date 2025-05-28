from core.repositories.appointment_repository_sqlalchemy import SQLAlchemyAppointmentRepository
from core.repositories.appointment_repository_msgraph import MSGraphAppointmentRepository
from core.repositories.appointment_repository_base import BaseAppointmentRepository
from sqlalchemy.orm import Session

class AppointmentRepositoryFactory:
    """
    Factory for creating AppointmentRepository instances based on backend type.
    """
    @staticmethod
    def create(backend: str, **kwargs) -> BaseAppointmentRepository:
        calendar_id = kwargs.get('calendar_id')
        if not calendar_id:
            raise ValueError("calendar_id must be provided for all appointment repositories.")
        if backend == 'sqlalchemy':
            session: Session = kwargs['session']
            user = kwargs['user']
            return SQLAlchemyAppointmentRepository(user, calendar_id, session)
        elif backend == 'msgraph':
            msgraph_client = kwargs['msgraph_client']
            user = kwargs['user']
            return MSGraphAppointmentRepository(msgraph_client, user, calendar_id)
        else:
            raise ValueError(f"Unknown backend: {backend}") 