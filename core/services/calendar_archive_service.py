from typing import List, Dict, Any, Optional
from datetime import date, datetime
from core.utilities.calendar_recurrence_utility import expand_recurring_events_range
from core.utilities.calendar_overlap_utility import merge_duplicates, detect_overlaps
from core.utilities.time_utility import to_utc
from core.models.appointment import Appointment
from sqlalchemy.orm.attributes import InstrumentedAttribute
from core.exceptions import CalendarServiceException
import logging

logger = logging.getLogger(__name__)

def prepare_appointments_for_archive(
    appointments: List[Appointment],
    start_date: date,
    end_date: date,
    user=None,
    session=None,
    logger=None,
    action_log_repository: 'Optional[Any]' = None  # Kept for backward compatibility, but not used
) -> Dict[str, Any]:
    """
    Process a list of Appointment model instances to prepare them for archiving.
    Handles time zones, recurring events, overlaps, and duplicates.
    Returns a dict with keys:
        - 'appointments': processed list of appointments ready for archiving
        - 'status': 'ok' or 'overlap'
        - 'conflicts': list of conflicts if overlaps detected
        - 'errors': list of error messages
    Note: This function no longer logs overlaps or writes to the DB. It only returns the detected overlaps.
    """
    result = {"appointments": [], "status": "ok", "conflicts": [], "errors": []}
    try:
        appts = expand_recurring_events_range(appointments, start_date, end_date)
        appts = merge_duplicates(appts)
        overlap_groups = detect_overlaps(appts)
        overlapping_appts = set()
        if overlap_groups:
            result["status"] = "overlap"
            result["conflicts"] = [
                [
                    {
                        "subject": appt.subject,
                        "start": appt.start_time.isoformat() if isinstance(appt.start_time, datetime) else None,
                        "end": appt.end_time.isoformat() if isinstance(appt.end_time, datetime) else None,
                    }
                    for appt in group
                ]
                for group in overlap_groups
            ]
            for group in overlap_groups:
                for appt in group:
                    overlapping_appts.add(appt)
        for appt in appts:
            if not isinstance(appt, Appointment):
                continue
            if appt in overlapping_appts:
                continue  # Skip archiving overlapping events
            # Ensure times are UTC, but only if not a Column object
            start_time = getattr(appt, 'start_time', None)
            end_time = getattr(appt, 'end_time', None)
            if isinstance(start_time, datetime):
                setattr(appt, 'start_time', to_utc(start_time))
            if isinstance(end_time, datetime):
                setattr(appt, 'end_time', to_utc(end_time))
            # Only allow if both are real datetimes
            if not (isinstance(start_time, datetime) and isinstance(end_time, datetime)):
                result["errors"].append(f"Skipped appointment with missing start or end time: {getattr(appt, 'subject', 'Unknown')}")
                continue
            # Always use setattr for is_archived
            setattr(appt, 'is_archived', True)  # type: ignore
            result["appointments"].append(appt)
    except Exception as e:
        if logger:
            logger.exception(f"Archiving preparation failed for range {start_date} to {end_date}: {str(e)}")
        if hasattr(e, 'add_note'):
            e.add_note(f"Error in prepare_appointments_for_archive for range {start_date} to {end_date}")
        raise CalendarServiceException(f"Archiving preparation failed for range {start_date} to {end_date}") from e
    return result

def make_appointments_immutable(appointments: List[Appointment], db_session):
    """
    Mark archived appointments as immutable (except for user).
    """
    for appt in appointments:
        setattr(appt, 'is_archived', True)  # type: ignore
    db_session.commit() 