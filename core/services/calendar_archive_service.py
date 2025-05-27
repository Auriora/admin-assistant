from typing import List
from datetime import date
from core.services.calendar_recurrence_utils import expand_recurring_events_range
from core.services.calendar_overlap_utils import merge_duplicates, detect_overlaps
from core.services.calendar_time_utils import to_utc
from core.models.appointment import Appointment


def event_to_appointment_fields(event: dict, user_id: int) -> dict:
    """
    (DEPRECATED) Map a Microsoft Graph event dict to Appointment model fields.
    """
    from dateutil import parser
    start = event.get('start', {})
    end = event.get('end', {})
    if isinstance(start, dict):
        dt = start.get('dateTime')
        start_time = parser.parse(dt) if isinstance(dt, str) else None
    elif hasattr(start, 'isoformat'):
        start_time = start
    else:
        start_time = None
    if isinstance(end, dict):
        dt = end.get('dateTime')
        end_time = parser.parse(dt) if isinstance(dt, str) else None
    elif hasattr(end, 'isoformat'):
        end_time = end
    else:
        end_time = None
    if start_time is not None:
        start_time = to_utc(start_time)
    if end_time is not None:
        end_time = to_utc(end_time)
    return {
        'user_id': user_id,
        'subject': event.get('subject'),
        'start_time': start_time,
        'end_time': end_time,
        'is_private': event.get('sensitivity', '').lower() == 'private',
        'is_out_of_office': event.get('showAs', '').lower() == 'oof',
        'is_archived': True,
    }


def archive_appointments(
    user,
    appointments: List[Appointment],
    start_date: date,
    end_date: date,
    db_session,
    logger=None
) -> dict:
    """
    Archive the given Appointment model instances to the archive calendar for the given date range (inclusive).
    Handles time zones, recurring, overlaps, and duplicates.
    Returns a result dict with status and errors.
    """
    result = {"archived": 0, "errors": []}
    try:
        # TODO: Refactor expand_recurring_events_range, merge_duplicates, detect_overlaps to support Appointment instances
        appointments = expand_recurring_events_range(appointments, start_date, end_date)  # May need refactor
        appointments = merge_duplicates(appointments)  # May need refactor
        overlap_groups = detect_overlaps(appointments)  # May need refactor
        if overlap_groups:
            return {
                "status": "overlap",
                "conflicts": [
                    [
                        {
                            "subject": appt.subject,
                            "start": appt.start_time.isoformat() if appt.start_time else None,
                            "end": appt.end_time.isoformat() if appt.end_time else None,
                        }
                        for appt in group
                    ]
                    for group in overlap_groups
                ]
            }
        for appt in appointments:
            # Ensure times are UTC
            if appt.start_time:
                appt.start_time = to_utc(appt.start_time)
            if appt.end_time:
                appt.end_time = to_utc(appt.end_time)
        for appt in appointments:
            try:
                if appt.start_time is None or appt.end_time is None:
                    result["errors"].append(f"Skipped appointment with missing start or end time: {getattr(appt, 'subject', 'Unknown')}")
                    continue
                appt.user_id = user.id  # Ensure correct user assignment
                appt.is_archived = True
                db_session.add(appt)
            except Exception as e:
                result["errors"].append(f"Failed to archive {getattr(appt, 'subject', 'Unknown')}: {str(e)}")
        try:
            db_session.commit()
            result["archived"] = len([
                a for a in appointments if a.start_time is not None and a.end_time is not None
            ])
        except Exception as e:
            db_session.rollback()
            result["errors"].append(f"DB commit failed: {str(e)}")
    except Exception as e:
        if logger:
            logger.exception(f"Archiving failed: {str(e)}")
        result["errors"].append(str(e))
    return result


def make_appointments_immutable(appointments: List[Appointment], db_session):
    """
    Mark archived appointments as immutable (except for user).
    """
    for appt in appointments:
        appt.is_archived = True
    db_session.commit() 