from datetime import date
from typing import Any, Callable, List, Optional
from core.models.appointment import Appointment
from core.repositories.appointment_repository_base import BaseAppointmentRepository
from core.services.calendar_io_service import fetch_appointments, store_appointments
from core.services.calendar_archive_service import prepare_appointments_for_archive
from core.exceptions import OrchestrationException
import logging

logger = logging.getLogger(__name__)

class CalendarArchiveOrchestrator:
    """
    Orchestrator for archiving user appointments. Coordinates fetching, processing, and writing.
    """
    def archive_user_appointments(
        self,
        user: Any,
        start_date: date,
        end_date: date,
        fetch_repo: BaseAppointmentRepository,
        write_repo: BaseAppointmentRepository,
        logger: Optional[Any] = None
    ) -> dict:
        """
        Fetches, processes, and writes appointments for archiving.
        fetch_repo: repository to fetch appointments from
        write_repo: repository to store appointments to
        Returns a dict with status, errors, and count.
        """
        try:
            appointments = fetch_repo.list_for_user(start_date=start_date, end_date=end_date)
            process_result = prepare_appointments_for_archive(appointments, start_date, end_date, logger=logger)
            if process_result.get("status") == "overlap":
                return {
                    "status": "overlap",
                    "conflicts": process_result.get("conflicts", []),
                    "archived": 0,
                    "errors": process_result.get("errors", [])
                }
            store_result = store_appointments(process_result.get("appointments", []), write_repo, logger=logger)
            return {
                "status": "ok",
                "archived": store_result.get("stored", 0),
                "errors": process_result.get("errors", []) + store_result.get("errors", [])
            }
        except Exception as e:
            if logger:
                logger.exception(f"Orchestration failed for user {getattr(user, 'email', None)} from {start_date} to {end_date}: {str(e)}")
            if hasattr(e, 'add_note'):
                e.add_note(f"Error in archive_user_appointments for user {getattr(user, 'email', None)} and range {start_date} to {end_date}")
            raise OrchestrationException(f"Failed to archive appointments for user {getattr(user, 'email', None)}") from e 