import logging
from datetime import date
from typing import Any, Optional

from core.db import get_session
from core.orchestrators.calendar_archive_orchestrator import CalendarArchiveOrchestrator
from core.repositories.factory import get_appointment_repository
from core.services.archive_configuration_service import ArchiveConfigurationService
from core.services.user_service import UserService

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
        archive_config_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        replace_mode: bool = False,
    ) -> dict:
        """
        Run the archive job for the given user and archive configuration.

        Args:
            user_id (int): The user ID.
            archive_config_id (int): The archive configuration ID.
            start_date (Optional[date]): Start date for archiving.
            end_date (Optional[date]): End date for archiving.

        Returns:
            dict: Result of the archive operation.
        """
        try:
            user = self.user_service.get_by_id(user_id)
            if not user:
                logger.error(f"No user found with ID {user_id}.")
                return {"status": "error", "error": f"No user found with ID {user_id}."}
            archive_config = self.archive_config_service.get_by_id(archive_config_id)
            if not archive_config:
                logger.error(
                    f"No archive configuration with ID {archive_config_id} for user {user.email}."
                )
                return {
                    "status": "error",
                    "error": f"No archive configuration with ID {archive_config_id} for user {user.email}.",
                }
            source_calendar_uri = str(
                getattr(archive_config, "source_calendar_uri", "")
            )
            archive_calendar_uri = str(
                getattr(archive_config, "destination_calendar_uri", "")
            )

            # Determine date range
            if start_date and not end_date:
                end_date = start_date
            if end_date and not start_date:
                start_date = end_date
            if not start_date or not end_date:
                from datetime import datetime, timedelta

                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=7)

            # Fetch graph client and session internally
            from core.utilities import get_graph_client
            from core.utilities.auth_utility import get_cached_access_token

            access_token = get_cached_access_token()
            if not access_token:
                logger.error(
                    "No valid MS Graph token found. Please login with 'admin-assistant login msgraph'."
                )
                return {
                    "status": "error",
                    "error": "No valid MS Graph token found. Please login with 'admin-assistant login msgraph'.",
                }
            graph_client = get_graph_client(user=user, access_token=access_token)

            from core.db import get_session

            session = get_session()

            # Use the new configuration-based method for better archive type support
            result = self.orchestrator.archive_user_appointments_with_config(
                user=user,
                msgraph_client=graph_client,
                archive_config=archive_config,
                start_date=start_date,
                end_date=end_date,
                db_session=session,
                logger=logger,
                replace_mode=replace_mode,
            )
            return result
        except Exception as e:
            logger.exception(
                f"Archive job failed for user_id={user_id}, archive_config_id={archive_config_id}: {e}"
            )
            return {"status": "error", "error": str(e)}
