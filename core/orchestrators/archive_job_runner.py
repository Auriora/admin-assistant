from typing import Optional, Any
from datetime import date
from core.services.user_service import UserService
from core.services.archive_configuration_service import ArchiveConfigurationService
from core.repositories.factory import get_appointment_repository
from core.orchestrators.calendar_archive_orchestrator import CalendarArchiveOrchestrator
from core.db import get_session
import logging

logger = logging.getLogger(__name__)

class ArchiveJobRunner:
    """
    Orchestrator for running a full archive job for a user, including user/config lookup,
    repository selection, event loading (mock/live), archiving, error handling, and logging.
    """
    def __init__(self):
        self.user_service = UserService()
        self.archive_config_service = ArchiveConfigurationService()
        self.orchestrator = CalendarArchiveOrchestrator()

    def run_archive_job(
        self,
        user_id: int,
        use_live: bool = False,
        local_events_file: Optional[str] = None,
        graph_client: Optional[Any] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        session: Optional[Any] = None,
        mock_events: Optional[Any] = None,
    ) -> dict:
        """
        Run the archive job for the given user.

        Args:
            user_id (int): The user ID.
            use_live (bool): Whether to use live MS Graph API.
            local_events_file (Optional[str]): Path to local events file (for mock mode).
            graph_client (Optional[Any]): MS Graph client (for live mode).
            start_date (Optional[date]): Start date for archiving.
            end_date (Optional[date]): End date for archiving.
            session (Optional[Any]): SQLAlchemy session for DB writes.
            mock_events (Optional[Any]): Mock event data (for mock mode).

        Returns:
            dict: Result of the archive operation.
        """
        try:
            user = self.user_service.get_by_id(user_id)
            if not user:
                logger.error(f"No user found with ID {user_id}.")
                return {"status": "error", "error": f"No user found with ID {user_id}."}
            archive_config = self.archive_config_service.get_active_for_user(user_id)
            if not archive_config:
                logger.error(f"No active archive configuration for user {user.email}.")
                return {"status": "error", "error": f"No active archive configuration for user {user.email}."}
            source_calendar_id = str(getattr(archive_config, 'source_calendar_id', ''))
            archive_calendar_id = str(getattr(archive_config, 'destination_calendar_id', ''))

            # Determine date range
            if not start_date or not end_date:
                from datetime import datetime, timedelta
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=7)

            # Repository selection and event loading
            if not use_live:
                if not mock_events and local_events_file:
                    from tests.utilities.calendar_utils import load_events_from_file, get_event_date_range
                    mock_events = load_events_from_file(local_events_file)
                    date_range = get_event_date_range(mock_events)
                    if date_range:
                        start_date, end_date = date_range
                fetch_repo = get_appointment_repository(
                    user=user,
                    calendar_id=source_calendar_id,
                    use_mock=True,
                    mock_data=mock_events
                )
            else:
                if not graph_client:
                    logger.error("graph_client must be provided for live mode.")
                    return {"status": "error", "error": "graph_client must be provided for live mode."}
                fetch_repo = get_appointment_repository(
                    user=user,
                    calendar_id=source_calendar_id,
                    mock_data=graph_client
                )
            # Write repo (always SQLAlchemy)
            if not session:
                session = get_session()
            write_repo = get_appointment_repository(
                user=user,
                calendar_id=archive_calendar_id,
                session=session
            )
            # Archive orchestration
            result = self.orchestrator.archive_user_appointments(
                user=user,
                start_date=start_date,
                end_date=end_date,
                fetch_repo=fetch_repo,
                write_repo=write_repo,
                logger=logger
            )
            return result
        except Exception as e:
            logger.exception(f"Archive job failed for user_id={user_id}: {e}")
            return {"status": "error", "error": str(e)} 