from datetime import datetime, UTC, date
from typing import Optional
from core.services.calendar_fetch_service import fetch_appointments_from_ms365
from core.services.calendar_archive_service import archive_appointments

def scheduled_archive_job(db_session, user_model, msgraph_session_factory, logger=None) -> None:
    """
    Scheduled job to archive today's appointments for the first user in the database.
    Args:
        db_session: SQLAlchemy session for DB operations.
        user_model: The User model class to query users.
        msgraph_session_factory: Callable that takes a user and returns an authenticated MS Graph session.
        logger: Optional logger for logging.
    Returns:
        None
    """
    user = db_session.query(user_model).first()
    if not user:
        if logger:
            logger.warning("No user found for scheduled archive job.")
        return
    today = datetime.now(UTC).date()
    msgraph_session = msgraph_session_factory(user)
    appointments = fetch_appointments_from_ms365(user, today, today, msgraph_session, logger=logger)
    result = archive_appointments(user, appointments, today, today, db_session, logger=logger)
    if result.get("errors"):
        if logger:
            logger.error(f"Scheduled archive job errors: {result['errors']}")
    else:
        if logger:
            logger.info(f"Scheduled archive job completed for {user.email}") 