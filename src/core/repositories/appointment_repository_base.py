from abc import ABC, abstractmethod
from typing import List, Optional

from core.models.appointment import Appointment


class BaseAppointmentRepository(ABC):
    @abstractmethod
    def get_by_id(self, appointment_id: int) -> Optional[Appointment]:
        pass

    @abstractmethod
    def add(self, appointment: Appointment) -> None:
        pass

    @abstractmethod
    def list_for_user(self, start_date=None, end_date=None) -> List[Appointment]:
        """
        List appointments for the user, optionally filtered by date range.
        :param start_date: Optional start date (date or datetime) for filtering events.
        :param end_date: Optional end date (date or datetime) for filtering events.
        :return: List of Appointment instances.
        """
        pass

    @abstractmethod
    def update(self, appointment: Appointment) -> None:
        pass

    @abstractmethod
    def delete(self, appointment_id: int) -> None:
        pass
