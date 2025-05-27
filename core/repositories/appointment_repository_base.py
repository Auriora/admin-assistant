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
    def list_for_user(self, user_id: int, page: int = 1, page_size: int = 100) -> List[Appointment]:
        pass

    @abstractmethod
    def update(self, appointment: Appointment) -> None:
        pass

    @abstractmethod
    def delete(self, appointment_id: int) -> None:
        pass 