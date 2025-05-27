from core.repositories.appointment_repository_base import BaseAppointmentRepository
from core.models.appointment import Appointment
from typing import List, Optional
from core.db import SessionLocal

class SQLAlchemyAppointmentRepository(BaseAppointmentRepository):
    def __init__(self, session=None):
        self.session = session or SessionLocal()

    def get_by_id(self, appointment_id: int) -> Optional[Appointment]:
        return self.session.get(Appointment, appointment_id)

    def add(self, appointment: Appointment) -> None:
        self.session.add(appointment)
        self.session.commit()

    def list_for_user(self, user_id: int, page: int = 1, page_size: int = 100) -> List[Appointment]:
        query = self.session.query(Appointment).filter_by(user_id=user_id)
        return query.offset((page - 1) * page_size).limit(page_size).all()

    def update(self, appointment: Appointment) -> None:
        self.session.merge(appointment)
        self.session.commit()

    def delete(self, appointment_id: int) -> None:
        appt = self.get_by_id(appointment_id)
        if appt:
            self.session.delete(appt)
            self.session.commit() 