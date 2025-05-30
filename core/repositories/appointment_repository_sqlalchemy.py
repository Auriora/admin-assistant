from core.repositories.appointment_repository_base import BaseAppointmentRepository
from core.models.appointment import Appointment
from typing import List, Optional
from core.db import SessionLocal
from core.exceptions import DuplicateAppointmentException
import json
import logging

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

    @staticmethod
    def _to_json_safe(val):
        import datetime
        from sqlalchemy.orm.attributes import InstrumentedAttribute
        if val is None:
            return None
        if isinstance(val, InstrumentedAttribute) or hasattr(val, 'expression'):
            return None
        if isinstance(val, (str, int, float, bool)):
            return val
        if isinstance(val, datetime.datetime):
            return val.isoformat()
        if isinstance(val, list):
            return [SQLAlchemyAppointmentRepository._to_json_safe(v) for v in val]
        if isinstance(val, dict):
            return {str(k): SQLAlchemyAppointmentRepository._to_json_safe(v) for k, v in val.items()}
        return str(val)

    @staticmethod
    def _sanitize_appointment_json_fields(appt):
        import json
        import logging
        logger = logging.getLogger(__name__)
        def to_json_str(val):
            # Only convert dict/list to JSON string, leave strings as-is
            if isinstance(val, (dict, list)):
                return json.dumps(val)
            return val
        # List of all JSON fields to sanitize and validate
        json_fields = [
            'ms_event_data', 'attendees', 'organizer', 'categories', 'response_status', 'online_meeting'
        ]
        # Sanitize JSON fields
        for field in json_fields:
            value = getattr(appt, field, None)
            safe_value = SQLAlchemyAppointmentRepository._to_json_safe(value)
            json_str = to_json_str(safe_value)
            setattr(appt, field, json_str)
            logger.debug(f"[SANITIZE] {field}: type={type(json_str)}, value={str(json_str)[:200]}")
            # Validation: must be str or None
            if json_str is not None and not isinstance(json_str, str):
                raise ValueError(f"Field '{field}' must be a string or None after sanitization, got {type(json_str)}: {json_str}")
        # Validate all fields for dict/list except allowed JSON fields
        for field in appt.__table__.columns.keys():
            value = getattr(appt, field, None)
            logger.debug(f"[VALIDATE] {field}: type={type(value)}, value={str(value)[:200]}")
            if field not in json_fields:
                if isinstance(value, (dict, list)):
                    raise ValueError(f"Field '{field}' must not be a dict or list (got {type(value)}: {value})")
        return appt

    @staticmethod
    def safe_str(val):
        from sqlalchemy.orm.attributes import InstrumentedAttribute
        if hasattr(val, 'expression') or isinstance(val, InstrumentedAttribute):
            return ''
        return str(val) if val is not None else ''

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
        appointment.calendar_id = self.safe_str(self.calendar_id)  # type: ignore
        appointment = self._sanitize_appointment_json_fields(appointment)
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
        appointment.calendar_id = self.safe_str(self.calendar_id)  # type: ignore
        appointment = self._sanitize_appointment_json_fields(appointment)
        self.session.merge(appointment)
        self.session.commit()

    def delete(self, appointment_id: int) -> None:
        appt = self.get_by_id(appointment_id)
        # Only delete if appt is not None and calendar_id matches
        if appt is not None and self.safe_str(appt.calendar_id) == self.safe_str(self.calendar_id):
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