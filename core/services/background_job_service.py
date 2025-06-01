"""
Background Job Service

This service manages background job scheduling and execution for the admin-assistant system.
It provides functionality for:
- Scheduling recurring archive jobs
- Managing manual job triggers
- Job status monitoring and logging
- Job configuration management

Key Features:
- Flask-APScheduler integration
- Job persistence and recovery
- Error handling and retry logic
- Job status tracking
- Manual job triggering
"""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from flask_apscheduler import APScheduler

from core.services.archive_configuration_service import \
    ArchiveConfigurationService
from core.services.job_configuration_service import JobConfigurationService
from core.services.user_service import UserService

logger = logging.getLogger(__name__)


class BackgroundJobService:
    """Service for managing background jobs and scheduling."""

    def __init__(self, scheduler: Optional[APScheduler] = None):
        """
        Initialize the background job service.

        Args:
            scheduler: Flask-APScheduler instance (optional, will be set later if not provided)
        """
        self.scheduler = scheduler
        self.user_service = UserService()
        self.archive_config_service = ArchiveConfigurationService()
        self.job_config_service = JobConfigurationService()
        self._archive_runner = None

    def set_scheduler(self, scheduler: APScheduler):
        """Set the scheduler instance (used when initializing from Flask app)."""
        self.scheduler = scheduler

    @property
    def archive_runner(self):
        """Lazy initialization of ArchiveJobRunner to avoid circular imports."""
        if self._archive_runner is None:
            from core.orchestrators.archive_job_runner import ArchiveJobRunner

            self._archive_runner = ArchiveJobRunner()
        return self._archive_runner

    def schedule_daily_archive_job(
        self, user_id: int, archive_config_id: int, hour: int = 23, minute: int = 59
    ) -> str:
        """
        Schedule a daily archive job for a user.

        Args:
            user_id: User ID to schedule archiving for
            archive_config_id: Archive configuration ID to use
            hour: Hour to run the job (0-23, default 23)
            minute: Minute to run the job (0-59, default 59)

        Returns:
            Job ID for the scheduled job

        Raises:
            ValueError: If scheduler is not initialized or user/config not found
        """
        if not self.scheduler:
            raise ValueError("Scheduler not initialized")

        # Validate user and config exist
        user = self.user_service.get_by_id(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        archive_config = self.archive_config_service.get_by_id(archive_config_id)
        if not archive_config:
            raise ValueError(
                f"Archive configuration with ID {archive_config_id} not found"
            )

        if not archive_config.is_active:
            raise ValueError(f"Archive configuration {archive_config_id} is not active")

        job_id = f"daily_archive_user_{user_id}_config_{archive_config_id}"

        # Remove existing job if it exists
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed existing job {job_id}")

        # Schedule new job
        self.scheduler.add_job(
            id=job_id,
            func=self._run_scheduled_archive,
            args=[user_id, archive_config_id],
            trigger="cron",
            hour=hour,
            minute=minute,
            timezone="UTC",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

        logger.info(
            f"Scheduled daily archive job {job_id} for user {user.email} at {hour:02d}:{minute:02d} UTC"
        )
        return job_id

    def schedule_weekly_archive_job(
        self,
        user_id: int,
        archive_config_id: int,
        day_of_week: int = 6,
        hour: int = 23,
        minute: int = 59,
    ) -> str:
        """
        Schedule a weekly archive job for a user.

        Args:
            user_id: User ID to schedule archiving for
            archive_config_id: Archive configuration ID to use
            day_of_week: Day of week (0=Monday, 6=Sunday, default 6)
            hour: Hour to run the job (0-23, default 23)
            minute: Minute to run the job (0-59, default 59)

        Returns:
            Job ID for the scheduled job
        """
        if not self.scheduler:
            raise ValueError("Scheduler not initialized")

        # Validate user and config exist
        user = self.user_service.get_by_id(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        archive_config = self.archive_config_service.get_by_id(archive_config_id)
        if not archive_config:
            raise ValueError(
                f"Archive configuration with ID {archive_config_id} not found"
            )

        if not archive_config.is_active:
            raise ValueError(f"Archive configuration {archive_config_id} is not active")

        job_id = f"weekly_archive_user_{user_id}_config_{archive_config_id}"

        # Remove existing job if it exists
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed existing job {job_id}")

        # Schedule new job
        self.scheduler.add_job(
            id=job_id,
            func=self._run_scheduled_archive,
            args=[user_id, archive_config_id],
            trigger="cron",
            day_of_week=day_of_week,
            hour=hour,
            minute=minute,
            timezone="UTC",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

        logger.info(
            f"Scheduled weekly archive job {job_id} for user {user.email} on day {day_of_week} at {hour:02d}:{minute:02d} UTC"
        )
        return job_id

    def trigger_manual_archive(
        self,
        user_id: int,
        archive_config_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> str:
        """
        Trigger a manual archive job immediately.

        Args:
            user_id: User ID to run archiving for
            archive_config_id: Archive configuration ID to use
            start_date: Start date for archiving (optional, defaults to yesterday)
            end_date: End date for archiving (optional, defaults to yesterday)

        Returns:
            Job ID for the manual job
        """
        if not self.scheduler:
            raise ValueError("Scheduler not initialized")

        # Default to yesterday if no dates provided
        if not start_date and not end_date:
            yesterday = date.today() - timedelta(days=1)
            start_date = yesterday
            end_date = yesterday
        elif start_date and not end_date:
            end_date = start_date
        elif end_date and not start_date:
            start_date = end_date

        job_id = f"manual_archive_{user_id}_{archive_config_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Schedule immediate job
        self.scheduler.add_job(
            id=job_id,
            func=self._run_manual_archive,
            args=[user_id, archive_config_id, start_date, end_date],
            trigger="date",
            run_date=datetime.now(),
            max_instances=1,
        )

        logger.info(
            f"Triggered manual archive job {job_id} for user {user_id} from {start_date} to {end_date}"
        )
        return job_id

    def remove_job(self, job_id: str) -> bool:
        """
        Remove a scheduled job.

        Args:
            job_id: ID of the job to remove

        Returns:
            True if job was removed, False if job not found
        """
        if not self.scheduler:
            raise ValueError("Scheduler not initialized")

        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed job {job_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to remove job {job_id}: {e}")
            return False

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status information for a job.

        Args:
            job_id: ID of the job to check

        Returns:
            Dictionary with job status information or None if job not found
        """
        if not self.scheduler:
            raise ValueError("Scheduler not initialized")

        job = self.scheduler.get_job(job_id)
        if not job:
            return None

        return {
            "id": job.id,
            "name": job.name,
            "func": str(job.func),
            "trigger": str(job.trigger),
            "next_run_time": job.next_run_time,
            "args": job.args,
            "kwargs": job.kwargs,
        }

    def list_jobs(self) -> List[Dict[str, Any]]:
        """
        List all scheduled jobs.

        Returns:
            List of job status dictionaries
        """
        if not self.scheduler:
            raise ValueError("Scheduler not initialized")

        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "func": str(job.func),
                    "trigger": str(job.trigger),
                    "next_run_time": job.next_run_time,
                    "args": job.args,
                    "kwargs": job.kwargs,
                }
            )
        return jobs

    def _run_scheduled_archive(self, user_id: int, archive_config_id: int):
        """
        Internal method to run scheduled archive job.
        Archives appointments based on JobConfiguration settings.
        """
        try:
            # Get job configuration to determine archive window
            job_config = None
            job_configs = self.job_config_service.get_by_archive_config_id(
                archive_config_id
            )
            if job_configs:
                # Find the active job config for this user
                job_config = next(
                    (
                        jc
                        for jc in job_configs
                        if jc.user_id == user_id and jc.is_active
                    ),
                    None,
                )

            # Determine archive window (default to 1 day if no job config found)
            archive_window_days = job_config.archive_window_days if job_config else 1

            # Calculate date range
            end_date = date.today() - timedelta(days=1)  # Yesterday
            start_date = end_date - timedelta(days=archive_window_days - 1)

            logger.info(
                f"Starting scheduled archive for user {user_id}, config {archive_config_id}, "
                f"dates {start_date} to {end_date} (window: {archive_window_days} days)"
            )

            result = self.archive_runner.run_archive_job(
                user_id=user_id,
                archive_config_id=archive_config_id,
                start_date=start_date,
                end_date=end_date,
            )

            if result.get("status") == "error":
                logger.error(
                    f"Scheduled archive failed for user {user_id}: {result.get('error')}"
                )
            else:
                logger.info(
                    f"Scheduled archive completed for user {user_id}: {result.get('archived_count', 0)} appointments archived"
                )

        except Exception as e:
            logger.exception(
                f"Scheduled archive job failed for user {user_id}, config {archive_config_id}: {e}"
            )

    def _run_manual_archive(
        self, user_id: int, archive_config_id: int, start_date: date, end_date: date
    ):
        """
        Internal method to run manual archive job.
        """
        try:
            logger.info(
                f"Starting manual archive for user {user_id}, config {archive_config_id}, dates {start_date} to {end_date}"
            )

            result = self.archive_runner.run_archive_job(
                user_id=user_id,
                archive_config_id=archive_config_id,
                start_date=start_date,
                end_date=end_date,
            )

            if result.get("status") == "error":
                logger.error(
                    f"Manual archive failed for user {user_id}: {result.get('error')}"
                )
            else:
                logger.info(
                    f"Manual archive completed for user {user_id}: {result.get('archived_count', 0)} appointments archived"
                )

        except Exception as e:
            logger.exception(
                f"Manual archive job failed for user {user_id}, config {archive_config_id}: {e}"
            )

    def schedule_job_from_configuration(self, job_config_id: int) -> str:
        """
        Schedule a job based on a JobConfiguration.

        Args:
            job_config_id: ID of the JobConfiguration to schedule

        Returns:
            Job ID for the scheduled job

        Raises:
            ValueError: If job configuration not found or invalid
        """
        job_config = self.job_config_service.get_by_id(job_config_id)
        if not job_config:
            raise ValueError(f"JobConfiguration with ID {job_config_id} not found")

        if not job_config.is_active:
            raise ValueError(f"JobConfiguration {job_config_id} is not active")

        if job_config.schedule_type == "daily":
            return self.schedule_daily_archive_job(
                user_id=job_config.user_id,
                archive_config_id=job_config.archive_configuration_id,
                hour=job_config.schedule_hour,
                minute=job_config.schedule_minute,
            )
        elif job_config.schedule_type == "weekly":
            return self.schedule_weekly_archive_job(
                user_id=job_config.user_id,
                archive_config_id=job_config.archive_configuration_id,
                day_of_week=job_config.schedule_day_of_week,
                hour=job_config.schedule_hour,
                minute=job_config.schedule_minute,
            )
        elif job_config.schedule_type == "manual":
            # Manual jobs are not scheduled, they are triggered on demand
            raise ValueError("Manual job configurations cannot be scheduled")
        else:
            raise ValueError(f"Unknown schedule type: {job_config.schedule_type}")

    def schedule_all_job_configurations(
        self, user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Schedule jobs for all active JobConfigurations.

        Args:
            user_id: Optional user ID to filter by (if None, schedules for all users)

        Returns:
            Dictionary with scheduling results
        """
        results = {
            "scheduled_jobs": [],
            "failed_jobs": [],
            "skipped_jobs": [],
            "total_configs": 0,
        }

        # Get job configurations to schedule
        if user_id:
            job_configs = self.job_config_service.get_active_by_user_id(user_id)
        else:
            job_configs = self.job_config_service.get_scheduled_configs()

        results["total_configs"] = len(job_configs)

        for job_config in job_configs:
            try:
                if job_config.schedule_type == "manual":
                    results["skipped_jobs"].append(
                        {
                            "job_config_id": job_config.id,
                            "user_id": job_config.user_id,
                            "reason": "Manual job configurations are not scheduled",
                        }
                    )
                    continue

                job_id = self.schedule_job_from_configuration(job_config.id)
                results["scheduled_jobs"].append(
                    {
                        "job_id": job_id,
                        "job_config_id": job_config.id,
                        "user_id": job_config.user_id,
                        "archive_config_id": job_config.archive_configuration_id,
                        "schedule_type": job_config.schedule_type,
                        "schedule_description": job_config.get_schedule_description(),
                    }
                )

            except Exception as e:
                logger.error(
                    f"Failed to schedule job for configuration {job_config.id}: {e}"
                )
                results["failed_jobs"].append(
                    {
                        "job_config_id": job_config.id,
                        "user_id": job_config.user_id,
                        "error": str(e),
                    }
                )

        return results

    def remove_jobs_for_user(self, user_id: int) -> Dict[str, Any]:
        """
        Remove all scheduled jobs for a user.

        Args:
            user_id: User ID to remove jobs for

        Returns:
            Dictionary with removal results
        """
        results = {"removed_jobs": [], "failed_removals": []}

        if not self.scheduler:
            raise ValueError("Scheduler not initialized")

        # Get all jobs and filter by user
        all_jobs = self.scheduler.get_jobs()
        user_jobs = [job for job in all_jobs if f"user_{user_id}" in job.id]

        for job in user_jobs:
            try:
                self.scheduler.remove_job(job.id)
                results["removed_jobs"].append({"job_id": job.id, "user_id": user_id})
                logger.info(f"Removed job {job.id} for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to remove job {job.id} for user {user_id}: {e}")
                results["failed_removals"].append(
                    {"job_id": job.id, "user_id": user_id, "error": str(e)}
                )

        return results

    def get_jobs_for_user(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all scheduled jobs for a user.

        Args:
            user_id: User ID to get jobs for

        Returns:
            List of job status dictionaries for the user
        """
        if not self.scheduler:
            raise ValueError("Scheduler not initialized")

        all_jobs = self.scheduler.get_jobs()
        user_jobs = [job for job in all_jobs if f"user_{user_id}" in job.id]

        jobs = []
        for job in user_jobs:
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "func": str(job.func),
                    "trigger": str(job.trigger),
                    "next_run_time": job.next_run_time,
                    "args": job.args,
                    "kwargs": job.kwargs,
                }
            )

        return jobs
