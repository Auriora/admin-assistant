"""
Scheduled Archive Service

This service provides high-level management of scheduled archiving operations.
It handles:
- Auto-scheduling for all active users
- Schedule management and updates
- Job monitoring and health checks
- Configuration-based scheduling

Key Features:
- Automatic job scheduling for all active archive configurations
- Schedule updates when configurations change
- Health monitoring and job recovery
- Flexible scheduling options (daily, weekly, custom)
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, date, time
from core.services.background_job_service import BackgroundJobService
from core.services.user_service import UserService
from core.services.archive_configuration_service import ArchiveConfigurationService
from core.models.archive_configuration import ArchiveConfiguration
import logging

logger = logging.getLogger(__name__)


class ScheduledArchiveService:
    """Service for managing scheduled archive operations."""
    
    def __init__(self, background_job_service: Optional[BackgroundJobService] = None):
        """
        Initialize the scheduled archive service.
        
        Args:
            background_job_service: BackgroundJobService instance (optional)
        """
        self.background_job_service = background_job_service or BackgroundJobService()
        self.user_service = UserService()
        self.archive_config_service = ArchiveConfigurationService()
        
    def set_background_job_service(self, background_job_service: BackgroundJobService):
        """Set the background job service instance."""
        self.background_job_service = background_job_service
        
    def schedule_all_active_users(self, schedule_type: str = 'daily', 
                                hour: int = 23, minute: int = 59,
                                day_of_week: Optional[int] = None) -> Dict[str, Any]:
        """
        Schedule archive jobs for all users with active archive configurations.
        
        Args:
            schedule_type: Type of schedule ('daily' or 'weekly')
            hour: Hour to run jobs (0-23, default 23)
            minute: Minute to run jobs (0-59, default 59)
            day_of_week: Day of week for weekly jobs (0=Monday, 6=Sunday)
            
        Returns:
            Dictionary with scheduling results
        """
        results = {
            'scheduled_jobs': [],
            'failed_jobs': [],
            'skipped_jobs': [],
            'total_users': 0,
            'total_configs': 0
        }
        
        try:
            # Get all active archive configurations
            active_configs = self.archive_config_service.get_all_active()
            results['total_configs'] = len(active_configs)
            
            # Group by user
            user_configs = {}
            for config in active_configs:
                user_id = config.user_id
                if user_id not in user_configs:
                    user_configs[user_id] = []
                user_configs[user_id].append(config)
                
            results['total_users'] = len(user_configs)
            
            # Schedule jobs for each user's active configurations
            for user_id, configs in user_configs.items():
                user = self.user_service.get_by_id(user_id)
                if not user:
                    logger.warning(f"User {user_id} not found, skipping archive scheduling")
                    results['skipped_jobs'].append({
                        'user_id': user_id,
                        'reason': 'User not found'
                    })
                    continue
                    
                # Schedule job for each active configuration
                for config in configs:
                    try:
                        if schedule_type == 'daily':
                            job_id = self.background_job_service.schedule_daily_archive_job(
                                user_id=user_id,
                                archive_config_id=config.id,
                                hour=hour,
                                minute=minute
                            )
                        elif schedule_type == 'weekly':
                            if day_of_week is None:
                                day_of_week = 6  # Default to Sunday
                            job_id = self.background_job_service.schedule_weekly_archive_job(
                                user_id=user_id,
                                archive_config_id=config.id,
                                day_of_week=day_of_week,
                                hour=hour,
                                minute=minute
                            )
                        else:
                            raise ValueError(f"Unsupported schedule type: {schedule_type}")
                            
                        results['scheduled_jobs'].append({
                            'job_id': job_id,
                            'user_id': user_id,
                            'user_email': user.email,
                            'config_id': config.id,
                            'config_name': config.name,
                            'schedule_type': schedule_type
                        })
                        
                        logger.info(f"Scheduled {schedule_type} archive job {job_id} for user {user.email}")
                        
                    except Exception as e:
                        logger.error(f"Failed to schedule archive job for user {user_id}, config {config.id}: {e}")
                        results['failed_jobs'].append({
                            'user_id': user_id,
                            'user_email': user.email,
                            'config_id': config.id,
                            'config_name': config.name,
                            'error': str(e)
                        })
                        
        except Exception as e:
            logger.exception(f"Failed to schedule archive jobs for all users: {e}")
            raise
            
        logger.info(f"Archive scheduling completed: {len(results['scheduled_jobs'])} jobs scheduled, "
                   f"{len(results['failed_jobs'])} failed, {len(results['skipped_jobs'])} skipped")
        
        return results
        
    def update_user_schedule(self, user_id: int, schedule_type: str = 'daily',
                           hour: int = 23, minute: int = 59,
                           day_of_week: Optional[int] = None) -> Dict[str, Any]:
        """
        Update archive schedule for a specific user.
        
        Args:
            user_id: User ID to update schedule for
            schedule_type: Type of schedule ('daily' or 'weekly')
            hour: Hour to run jobs (0-23)
            minute: Minute to run jobs (0-59)
            day_of_week: Day of week for weekly jobs (0=Monday, 6=Sunday)
            
        Returns:
            Dictionary with update results
        """
        results = {
            'updated_jobs': [],
            'failed_jobs': [],
            'user_id': user_id
        }
        
        try:
            # Get user's active archive configurations
            user_configs = self.archive_config_service.get_active_for_user(user_id)
            if not user_configs:
                logger.warning(f"No active archive configurations found for user {user_id}")
                return results
                
            # Handle single config or list of configs
            if not isinstance(user_configs, list):
                user_configs = [user_configs]
                
            user = self.user_service.get_by_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
                
            # Update schedule for each configuration
            for config in user_configs:
                try:
                    # Remove existing jobs first
                    old_daily_job_id = f"daily_archive_user_{user_id}_config_{config.id}"
                    old_weekly_job_id = f"weekly_archive_user_{user_id}_config_{config.id}"
                    
                    self.background_job_service.remove_job(old_daily_job_id)
                    self.background_job_service.remove_job(old_weekly_job_id)
                    
                    # Schedule new job
                    if schedule_type == 'daily':
                        job_id = self.background_job_service.schedule_daily_archive_job(
                            user_id=user_id,
                            archive_config_id=config.id,
                            hour=hour,
                            minute=minute
                        )
                    elif schedule_type == 'weekly':
                        if day_of_week is None:
                            day_of_week = 6  # Default to Sunday
                        job_id = self.background_job_service.schedule_weekly_archive_job(
                            user_id=user_id,
                            archive_config_id=config.id,
                            day_of_week=day_of_week,
                            hour=hour,
                            minute=minute
                        )
                    else:
                        raise ValueError(f"Unsupported schedule type: {schedule_type}")
                        
                    results['updated_jobs'].append({
                        'job_id': job_id,
                        'config_id': config.id,
                        'config_name': config.name,
                        'schedule_type': schedule_type
                    })
                    
                    logger.info(f"Updated {schedule_type} archive schedule for user {user.email}, config {config.name}")
                    
                except Exception as e:
                    logger.error(f"Failed to update schedule for user {user_id}, config {config.id}: {e}")
                    results['failed_jobs'].append({
                        'config_id': config.id,
                        'config_name': config.name,
                        'error': str(e)
                    })
                    
        except Exception as e:
            logger.exception(f"Failed to update schedule for user {user_id}: {e}")
            raise
            
        return results
        
    def remove_user_schedule(self, user_id: int) -> Dict[str, Any]:
        """
        Remove all scheduled archive jobs for a user.
        
        Args:
            user_id: User ID to remove schedules for
            
        Returns:
            Dictionary with removal results
        """
        results = {
            'removed_jobs': [],
            'failed_removals': [],
            'user_id': user_id
        }
        
        try:
            # Get all jobs and filter for this user
            all_jobs = self.background_job_service.list_jobs()
            user_jobs = [job for job in all_jobs if f"user_{user_id}" in job['id']]
            
            for job in user_jobs:
                try:
                    success = self.background_job_service.remove_job(job['id'])
                    if success:
                        results['removed_jobs'].append(job['id'])
                        logger.info(f"Removed job {job['id']} for user {user_id}")
                    else:
                        results['failed_removals'].append({
                            'job_id': job['id'],
                            'error': 'Job removal returned False'
                        })
                except Exception as e:
                    logger.error(f"Failed to remove job {job['id']} for user {user_id}: {e}")
                    results['failed_removals'].append({
                        'job_id': job['id'],
                        'error': str(e)
                    })
                    
        except Exception as e:
            logger.exception(f"Failed to remove schedules for user {user_id}: {e}")
            raise
            
        return results
        
    def get_user_schedule_status(self, user_id: int) -> Dict[str, Any]:
        """
        Get schedule status for a user.
        
        Args:
            user_id: User ID to check
            
        Returns:
            Dictionary with schedule status information
        """
        status = {
            'user_id': user_id,
            'scheduled_jobs': [],
            'active_configs': [],
            'has_schedule': False
        }
        
        try:
            # Get user's active configurations
            user_configs = self.archive_config_service.get_active_for_user(user_id)
            if user_configs:
                if not isinstance(user_configs, list):
                    user_configs = [user_configs]
                    
                for config in user_configs:
                    status['active_configs'].append({
                        'id': config.id,
                        'name': config.name,
                        'source_calendar_uri': config.source_calendar_uri,
                        'destination_calendar_uri': config.destination_calendar_uri
                    })
                    
            # Get scheduled jobs for this user
            all_jobs = self.background_job_service.list_jobs()
            user_jobs = [job for job in all_jobs if f"user_{user_id}" in job['id']]
            
            for job in user_jobs:
                status['scheduled_jobs'].append({
                    'job_id': job['id'],
                    'trigger': job['trigger'],
                    'next_run_time': job['next_run_time'],
                    'args': job['args']
                })
                
            status['has_schedule'] = len(status['scheduled_jobs']) > 0
            
        except Exception as e:
            logger.exception(f"Failed to get schedule status for user {user_id}: {e}")
            status['error'] = str(e)
            
        return status
        
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on scheduled archive jobs.
        
        Returns:
            Dictionary with health check results
        """
        health = {
            'status': 'healthy',
            'total_jobs': 0,
            'active_jobs': 0,
            'failed_jobs': 0,
            'issues': [],
            'timestamp': datetime.now()
        }
        
        try:
            all_jobs = self.background_job_service.list_jobs()
            health['total_jobs'] = len(all_jobs)
            
            for job in all_jobs:
                if job['next_run_time']:
                    health['active_jobs'] += 1
                else:
                    health['failed_jobs'] += 1
                    health['issues'].append(f"Job {job['id']} has no next run time")
                    
            # Check if we have jobs for all active configurations
            active_configs = self.archive_config_service.get_all_active()
            expected_jobs = len(active_configs)
            
            if health['active_jobs'] < expected_jobs:
                health['status'] = 'warning'
                health['issues'].append(f"Expected {expected_jobs} jobs but only {health['active_jobs']} are active")
                
            if health['failed_jobs'] > 0:
                health['status'] = 'unhealthy'
                
        except Exception as e:
            logger.exception(f"Health check failed: {e}")
            health['status'] = 'error'
            health['issues'].append(f"Health check error: {e}")
            
        return health
