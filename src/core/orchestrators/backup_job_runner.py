"""
Orchestrator for running backup jobs.
"""

import logging
from datetime import date
from typing import Any, Optional

from core.db import get_session
from core.services.backup_configuration_service import BackupConfigurationService
from core.services.calendar_backup_service import CalendarBackupService, BackupFormat
from core.services.user_service import UserService
from core.utilities.uri_utility import parse_resource_uri, URIParseError
from core.utilities.calendar_resolver import CalendarResolver
from core.utilities.auth_utility import get_cached_access_token

logger = logging.getLogger(__name__)


class BackupJobRunner:
    """
    Orchestrator for running a full backup job for a user, including user/config lookup,
    URI resolution, backup execution, error handling, and logging.
    """

    def __init__(self):
        self.user_service = UserService()
        self.backup_config_service = BackupConfigurationService()

    def run_backup_job(
        self,
        user_id: int,
        backup_config_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        replace_mode: bool = False,
    ) -> dict:
        """
        Run the backup job for the given user and backup configuration.

        Args:
            user_id (int): The user ID.
            backup_config_id (int): The backup configuration ID.
            start_date (Optional[date]): Start date for backup.
            end_date (Optional[date]): End date for backup.
            replace_mode (bool): Whether to replace existing backup data.

        Returns:
            dict: Result of the backup operation.
        """
        try:
            # Get user and backup configuration
            user = self.user_service.get_by_id(user_id)
            if not user:
                logger.error(f"No user found with ID {user_id}.")
                return {"status": "error", "error": f"No user found with ID {user_id}."}

            backup_config = self.backup_config_service.get_by_id(backup_config_id)
            if not backup_config:
                logger.error(
                    f"No backup configuration with ID {backup_config_id} for user {user.email}."
                )
                return {
                    "status": "error",
                    "error": f"No backup configuration with ID {backup_config_id} for user {user.email}.",
                }

            if not backup_config.is_active:
                logger.error(f"Backup configuration {backup_config_id} is not active.")
                return {
                    "status": "error",
                    "error": f"Backup configuration {backup_config_id} is not active.",
                }

            source_calendar_uri = backup_config.source_calendar_uri
            destination_uri = backup_config.destination_uri

            logger.info(
                f"Starting backup job for user {user.email}, config '{backup_config.name}', "
                f"source '{source_calendar_uri}' to '{destination_uri}'"
            )

            # Parse and validate URIs
            try:
                source_parsed = parse_resource_uri(source_calendar_uri)
                dest_parsed = parse_resource_uri(destination_uri)
                
                if source_parsed.namespace != 'calendars':
                    raise ValueError(f"Source URI must be a calendar URI, got namespace: {source_parsed.namespace}")
                    
            except URIParseError as e:
                logger.error(f"Invalid URI format: {e}")
                return {"status": "error", "error": f"Invalid URI format: {e}"}

            # Resolve source calendar
            access_token = get_cached_access_token()
            resolver = CalendarResolver(user, access_token)
            
            try:
                resolved_source_id = resolver.resolve_calendar_uri(source_calendar_uri)
                source_calendar_name = source_parsed.identifier
            except Exception as e:
                logger.error(f"Failed to resolve source calendar URI '{source_calendar_uri}': {e}")
                return {"status": "error", "error": f"Failed to resolve source calendar: {e}"}

            # Initialize backup service
            backup_service = CalendarBackupService(user_id=user.id)

            # Execute backup based on destination type
            try:
                if dest_parsed.scheme == 'local' and dest_parsed.namespace == 'calendars':
                    # Backup to local calendar
                    result = backup_service.backup_calendar_to_local_calendar(
                        source_calendar_name=source_calendar_name,
                        backup_calendar_name=dest_parsed.identifier,
                        start_date=start_date,
                        end_date=end_date
                    )
                elif dest_parsed.scheme == 'file':
                    # Backup to file
                    backup_format_enum = BackupFormat(backup_config.backup_format)
                    file_path = dest_parsed.identifier
                    if dest_parsed.raw_uri.startswith('file://'):
                        # Handle file:// URIs properly
                        file_path = dest_parsed.raw_uri[7:]  # Remove 'file://' prefix
                    
                    # Handle replace mode for file backups
                    if replace_mode:
                        import os
                        if os.path.exists(file_path):
                            logger.info(f"Replace mode: removing existing backup file {file_path}")
                            os.remove(file_path)
                    
                    result = backup_service.backup_calendar_to_file(
                        calendar_name=source_calendar_name,
                        backup_path=file_path,
                        backup_format=backup_format_enum,
                        start_date=start_date,
                        end_date=end_date,
                        include_metadata=backup_config.include_metadata
                    )
                else:
                    error_msg = f"Unsupported destination URI scheme: {dest_parsed.scheme}"
                    logger.error(error_msg)
                    return {"status": "error", "error": error_msg}

                # Log results
                if result.failed > 0:
                    logger.warning(
                        f"Backup completed with errors for user {user.email}: "
                        f"{result.backed_up} backed up, {result.failed} failed"
                    )
                else:
                    logger.info(
                        f"Backup completed successfully for user {user.email}: "
                        f"{result.backed_up} appointments backed up to {result.backup_location}"
                    )

                return {
                    "status": "success",
                    "total_appointments": result.total_appointments,
                    "backed_up": result.backed_up,
                    "failed": result.failed,
                    "backup_location": result.backup_location,
                    "errors": result.errors,
                }

            except Exception as e:
                logger.exception(f"Backup execution failed: {e}")
                return {"status": "error", "error": f"Backup execution failed: {e}"}

        except Exception as e:
            logger.exception(
                f"Backup job failed for user_id={user_id}, backup_config_id={backup_config_id}: {e}"
            )
            return {"status": "error", "error": str(e)}
