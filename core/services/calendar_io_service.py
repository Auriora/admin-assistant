from typing import List
from datetime import date
from core.models.appointment import Appointment

def fetch_appointments(
    user,
    start_date: date,
    end_date: date,
    appointment_repo,
    logger=None
) -> List[Appointment]:
    """
    Fetch appointments for the given user and date range (inclusive) from the provided AppointmentRepository.
    Returns a list of Appointment model instances.
    """
    try:
        # The repository is responsible for filtering by user and date range
        appointments = appointment_repo.list_for_user(user.id)
        # Filter by date range (inclusive)
        filtered = [
            appt for appt in appointments
            if hasattr(appt, 'start_time') and hasattr(appt, 'end_time') and
               appt.start_time is not None and appt.end_time is not None and
               appt.start_time.date() >= start_date and appt.end_time.date() <= end_date
        ]
        if logger:
            logger.info(f"Fetched {len(filtered)} appointments for {user.email} from {start_date} to {end_date}")
        return filtered
    except Exception as e:
        if logger:
            logger.exception(f"Failed to fetch appointments: {str(e)}")
        return []

def store_appointments(
    appointments: List[Appointment],
    appointment_repo,
    logger=None
) -> dict:
    """
    Store a list of Appointment instances using the provided AppointmentRepository.
    Returns a dict with the number of stored appointments and any errors encountered.
    """
    stored_count = 0
    errors = []
    for appt in appointments:
        try:
            appointment_repo.add(appt)
            stored_count += 1
        except Exception as e:
            msg = f"Failed to store appointment {getattr(appt, 'subject', 'Unknown')}: {str(e)}"
            errors.append(msg)
            if logger:
                logger.error(msg)
    return {"stored": stored_count, "errors": errors} 
