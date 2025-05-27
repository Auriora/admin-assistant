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
        if backend == 'sqlalchemy':
            session: Session = kwargs['session']
            return SQLAlchemyAppointmentRepository(session)
        elif backend == 'msgraph':
            msgraph_client = kwargs['msgraph_client']
            return MSGraphAppointmentRepository(msgraph_client)
        else:
            raise ValueError(f"Unknown backend: {backend}") 