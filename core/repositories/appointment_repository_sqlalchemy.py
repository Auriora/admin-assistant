from core.repositories.appointment_repository_base import BaseAppointmentRepository
from core.models.appointment import Appointment
from typing import List, Optional
from core.db import SessionLocal
from core.exceptions import DuplicateAppointmentException

class SQLAlchemyAppointmentRepository(BaseAppointmentRepository):
    def __init__(self, user, calendar_id: str, session=None):
        """
        :param user: User model instance (must have .id)
        :param calendar_id: The calendar identifier (string)
        :param session: Optional SQLAlchemy session
        """
        self.user = user
        self.calendar_id = calendar_id
        self.session = session or SessionLocal()

    def get_by_id(self, appointment_id: int) -> Optional[Appointment]:
        return self.session.get(Appointment, appointment_id)

    def add(self, appointment: Appointment) -> None:
        # Prevent duplicate appointments for the same user, calendar, start_time, end_time, and subject
        exists = self.session.query(Appointment).filter_by(
            user_id=self.user.id,
            calendar_id=self.calendar_id,
            start_time=appointment.start_time,
            end_time=appointment.end_time,
            subject=appointment.subject
        ).first()
        if exists:
            raise DuplicateAppointmentException(
                f"Duplicate appointment for user_id={self.user.id}, calendar_id={self.calendar_id}, start_time={appointment.start_time}, end_time={appointment.end_time}, subject={appointment.subject}"
            )
        appointment.calendar_id = self.calendar_id  # Ensure calendar_id is set
        self.session.add(appointment)
        self.session.commit()

    def list_for_user(self, start_date=None, end_date=None) -> List[Appointment]:
        """
        List appointments for the current user and calendar, optionally filtered by date range.
        :param start_date: Optional start date (date or datetime) for filtering events.
        :param end_date: Optional end date (date or datetime) for filtering events.
        :return: List of Appointment instances.
        """
        query = self.session.query(Appointment).filter_by(user_id=self.user.id, calendar_id=self.calendar_id)
        if start_date is not None:
            query = query.filter(Appointment.start_time >= start_date)
        if end_date is not None:
            query = query.filter(Appointment.end_time <= end_date)
        return query.all()

    def update(self, appointment: Appointment) -> None:
        appointment.calendar_id = self.calendar_id  # Ensure calendar_id is set
        self.session.merge(appointment)
        self.session.commit()

    def delete(self, appointment_id: int) -> None:
        appt = self.get_by_id(appointment_id)
        if appt and appt.calendar_id == self.calendar_id:
            self.session.delete(appt)
            self.session.commit()

    def delete_for_period(self, start_date, end_date) -> int:
        """
        Delete all appointments for the current user in the given period.
        Args:
            start_date (datetime/date): Start of the period (inclusive).
            end_date (datetime/date): End of the period (inclusive).
        Returns:
            int: Number of deleted appointments.
        """
        query = self.session.query(Appointment).filter(
            Appointment.user_id == self.user.id,
            Appointment.start_time >= start_date,
            Appointment.end_time <= end_date
        )
        count = query.count()
        query.delete(synchronize_session=False)
        self.session.commit()
        return count 