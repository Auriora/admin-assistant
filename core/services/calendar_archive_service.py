from typing import List, Dict, Any
from datetime import date, datetime
from core.utilities.calendar_recurrence_utility import expand_recurring_events_range
from core.utilities.calendar_overlap_utility import merge_duplicates, detect_overlaps
from core.utilities.time_utility import to_utc
from core.models.appointment import Appointment
from sqlalchemy.orm.attributes import InstrumentedAttribute

def prepare_appointments_for_archive(
    appointments: List[Appointment],
    start_date: date,
    end_date: date,
    logger=None
) -> Dict[str, Any]:
    """
    Process a list of Appointment model instances to prepare them for archiving.
    Handles time zones, recurring events, overlaps, and duplicates.
    Returns a dict with keys:
        - 'appointments': processed list of appointments ready for archiving
        - 'status': 'ok' or 'overlap'
        - 'conflicts': list of conflicts if overlaps detected
        - 'errors': list of error messages
    """
    result = {"appointments": [], "status": "ok", "conflicts": [], "errors": []}
    try:
        appts = expand_recurring_events_range(appointments, start_date, end_date)
        appts = merge_duplicates(appts)
        overlap_groups = detect_overlaps(appts)
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
            return result
        for appt in appts:
            if not isinstance(appt, Appointment):
                continue
            # Ensure times are UTC, but only if not a Column object
            if hasattr(appt, 'start_time') and isinstance(appt.start_time, datetime):
                setattr(appt, 'start_time', to_utc(appt.start_time))
            if hasattr(appt, 'end_time') and isinstance(appt.end_time, datetime):
                setattr(appt, 'end_time', to_utc(appt.end_time))
            if not (hasattr(appt, 'start_time') and isinstance(appt.start_time, datetime)) or not (hasattr(appt, 'end_time') and isinstance(appt.end_time, datetime)):
                result["errors"].append(f"Skipped appointment with missing start or end time: {getattr(appt, 'subject', 'Unknown')}")
                continue
            # Always use setattr for is_archived
            setattr(appt, 'is_archived', True)  # type: ignore
            result["appointments"].append(appt)
    except Exception as e:
        if logger:
            logger.exception(f"Archiving preparation failed: {str(e)}")
        result["errors"].append(str(e))
    return result


def make_appointments_immutable(appointments: List[Appointment], db_session):
    """
    Mark archived appointments as immutable (except for user).
    """
    for appt in appointments:
        setattr(appt, 'is_archived', True)  # type: ignore
    db_session.commit() 
