from typing import List, Dict, Any, Optional
from datetime import date, datetime
from core.utilities.calendar_recurrence_utility import expand_recurring_events_range
from core.utilities.calendar_overlap_utility import merge_duplicates, detect_overlaps
from core.utilities.time_utility import to_utc
from core.models.appointment import Appointment
from sqlalchemy.orm.attributes import InstrumentedAttribute
from core.exceptions import CalendarServiceException
from core.models.action_log import ActionLog
from core.repositories.action_log_repository import ActionLogRepository
import logging

logger = logging.getLogger(__name__)

def prepare_appointments_for_archive(
    appointments: List[Appointment],
    start_date: date,
    end_date: date,
    user=None,
    session=None,
    logger=None,
    action_log_repository: 'Optional[ActionLogRepository]' = None
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
            if user is not None and action_log_repository is not None:
                for group in overlap_groups:
                    for appt in group:
                        overlapping_appts.add(appt)
                        # Prevent duplicate ActionLog entries
                        existing_logs = action_log_repository.list_for_user(user.id)
                        exists = any(
                            getattr(log, 'event_id', None) == getattr(appt, 'ms_event_id', None) and
                            getattr(log, 'action_type', None) == 'overlap' and
                            getattr(log, 'status', None) == 'needs_user_action'
                            for log in existing_logs
                        )
                        if not exists:
                            log = ActionLog(
                                user_id=user.id,
                                event_id=getattr(appt, 'ms_event_id', None),
                                event_subject=getattr(appt, 'subject', None),
                                action_type='overlap',
                                status='needs_user_action',
                                message=f"Overlapping event detected: {getattr(appt, 'subject', None)} ({getattr(appt, 'start_time', None)} - {getattr(appt, 'end_time', None)})"
                            )
                            action_log_repository.add(log)
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


def archive_appointments(user, appointments, start_date, end_date, session, logger=None):
    """
    Archive appointments for a user, ensuring all action logging uses ActionLogRepository.
    """
    action_log_repository = ActionLogRepository(session=session)
    return prepare_appointments_for_archive(
        appointments=appointments,
        start_date=start_date,
        end_date=end_date,
        user=user,
        session=session,
        logger=logger,
        action_log_repository=action_log_repository
    ) 

def rearchive_period(user, archive_config, start_date, end_date, session, logger=None):
    """
    Re-archive (replace) all appointments for a specified period.
    Deletes all appointments in the archive calendar for the period, then archives the current source appointments.
    Args:
        user: User model instance.
        archive_config: ArchiveConfiguration instance (must have destination_calendar_id, source_calendar_id).
        start_date: Start of the period (datetime/date).
        end_date: End of the period (datetime/date).
        session: SQLAlchemy session.
        logger: Optional logger.
    Returns:
        dict: Summary of the operation (deleted_count, archived_count, errors).
    """
    from core.repositories.appointment_repository_sqlalchemy import SQLAlchemyAppointmentRepository
    from core.repositories.factory import get_appointment_repository
    import logging
    logger = logger or logging.getLogger(__name__)
    result = {"deleted_count": 0, "archived_count": 0, "errors": []}
    try:
        # 1. Delete all appointments in the archive calendar for the period
        archive_repo = SQLAlchemyAppointmentRepository(user, archive_config.destination_calendar_id, session=session)
        deleted_count = archive_repo.delete_for_period(start_date, end_date)
        logger.info(f"Re-archiving: Deleted {deleted_count} appointments for user {user.id} in archive calendar {archive_config.destination_calendar_id} for period {start_date} to {end_date}.")
        result["deleted_count"] = deleted_count
        # 2. Fetch source appointments for the period
        source_repo = get_appointment_repository(user, archive_config.source_calendar_id, session=session)
        source_appointments = source_repo.list_for_user(start_date, end_date)
        logger.info(f"Re-archiving: Fetched {len(source_appointments)} source appointments for user {user.id} from calendar {archive_config.source_calendar_id}.")
        # 3. Archive them to the destination calendar
        archive_result = archive_appointments(user, source_appointments, start_date, end_date, session, logger=logger)
        archived_count = len(archive_result.get("appointments", []))
        result["archived_count"] = archived_count
        result["errors"] = archive_result.get("errors", [])
        logger.info(f"Re-archiving: Archived {archived_count} appointments for user {user.id} to archive calendar {archive_config.destination_calendar_id}.")
    except Exception as e:
        logger.exception(f"Re-archiving failed for user {user.id} period {start_date} to {end_date}: {str(e)}")
        result["errors"].append(str(e))
    return result 