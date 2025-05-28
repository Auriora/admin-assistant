from typing import List, Dict, Any
from datetime import date, datetime
from core.utilities.calendar_recurrence_utility import expand_recurring_events_range
from core.utilities.calendar_overlap_utility import merge_duplicates, detect_overlaps
from core.utilities.time_utility import to_utc
from core.models.appointment import Appointment
from sqlalchemy.orm.attributes import InstrumentedAttribute
from core.exceptions import CalendarServiceException
from core.models.action_log import ActionLog
import logging

logger = logging.getLogger(__name__)

def prepare_appointments_for_archive(
    appointments: List[Appointment],
    start_date: date,
    end_date: date,
    user=None,
    session=None,
    logger=None
) -> Dict[str, Any]:
    """
    Process a list of Appointment model instances to prepare them for archiving.
    Handles time zones, recurring events, overlaps, and duplicates.
    Returns a dict with keys:
        - 'appointments': processed list of appointments ready for archiving
        - 'status': 'ok' (always, now)
        - 'conflicts': list of conflicts if overlaps detected
        - 'errors': list of error messages
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
            # Log each overlap as an ActionLog entry and collect overlapping appts
            if session is not None and user is not None:
                for group in overlap_groups:
                    for appt in group:
                        overlapping_appts.add(appt)
                        # Prevent duplicate ActionLog entries
                        existing_log = session.query(ActionLog).filter_by(
                            user_id=user.id,
                            event_id=getattr(appt, 'ms_event_id', None),
                            action_type='overlap',
                            status='needs_user_action'
                        ).first()
                        if not existing_log:
                            log = ActionLog(
                                user_id=user.id,
                                event_id=getattr(appt, 'ms_event_id', None),
                                event_subject=getattr(appt, 'subject', None),
                                action_type='overlap',
                                status='needs_user_action',
                                message=f"Overlapping event detected: {getattr(appt, 'subject', None)} ({getattr(appt, 'start_time', None)} - {getattr(appt, 'end_time', None)})"
                            )
                            session.add(log)
                session.commit()
        for appt in appts:
            if not isinstance(appt, Appointment):
                continue
            if appt in overlapping_appts:
                continue  # Skip archiving overlapping events
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
