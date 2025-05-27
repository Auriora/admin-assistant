from typing import List, Dict
from datetime import date
from core.services.calendar_recurrence_utils import expand_recurring_events_range
from core.services.calendar_overlap_utils import merge_duplicates, detect_overlaps
from core.services.calendar_time_utils import to_utc


def event_to_appointment_fields(event: dict, user_id: int) -> dict:
    """
    Map a Microsoft Graph event dict to Appointment model fields.
    Ensures all datetimes are UTC and timezone-aware.
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

def archive_appointments(user, appointments: List[dict], start_date: date, end_date: date, db_session, logger=None) -> dict:
    """
    Archive the given appointments to the archive calendar for the given date range (inclusive).
    Handles time zones, recurring, overlaps, and duplicates.
    Returns a result dict with status and errors.
    """
    result = {"archived": 0, "errors": []}
    try:
        from core.models.appointment import Appointment
        appointments = expand_recurring_events_range(appointments, start_date, end_date)
        appointments = merge_duplicates(appointments)
        overlap_groups = detect_overlaps(appointments)
        if overlap_groups:
            return {
                "status": "overlap",
                "conflicts": [
                    [
                        {
                            "subject": appt["subject"],
                            "start": appt["start"].isoformat(),
                            "end": appt["end"].isoformat(),
                        }
                        for appt in group
                    ]
                    for group in overlap_groups
                ]
            }
        for appt in appointments:
            appt['start'] = to_utc(appt['start'])
            appt['end'] = to_utc(appt['end'])
        for appt in appointments:
            try:
                appt_fields = event_to_appointment_fields(appt, user.id)
                if appt_fields['start_time'] is None or appt_fields['end_time'] is None:
                    result["errors"].append(f"Skipped appointment with missing start or end time: {appt.get('subject', 'Unknown')}")
                    continue
                archived = Appointment(**appt_fields)
                db_session.add(archived)
            except Exception as e:
                result["errors"].append(f"Failed to archive {appt.get('subject', 'Unknown')}: {str(e)}")
        try:
            db_session.commit()
            result["archived"] = len([a for a in appointments if event_to_appointment_fields(a, user.id)['start_time'] is not None and event_to_appointment_fields(a, user.id)['end_time'] is not None])
        except Exception as e:
            db_session.rollback()
            result["errors"].append(f"DB commit failed: {str(e)}")
    except Exception as e:
        if logger:
            logger.exception(f"Archiving failed: {str(e)}")
        result["errors"].append(str(e))
    return result

def make_appointments_immutable(appointments, db_session):
    """
    Mark archived appointments as immutable (except for user).
    """
    for appt in appointments:
        appt.is_archived = True
    db_session.commit() 