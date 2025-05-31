"""
Enhanced unit tests for ScheduledArchiveService.
"""
import pytest
from datetime import datetime, UTC, date, timedelta
from unittest.mock import MagicMock, patch
from core.services.scheduled_archive_service import ScheduledArchiveService


@pytest.mark.unit
class TestScheduledArchiveServiceEnhanced:
    """Enhanced test cases for ScheduledArchiveService."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return ScheduledArchiveService()

    def test_service_initialization(self, service):
        """Test service initialization."""
        assert service is not None
        assert hasattr(service, 'schedule_archive')
        assert hasattr(service, 'get_scheduled_archives')

    @patch('core.services.scheduled_archive_service.BackgroundJobService')
    def test_schedule_archive(self, mock_job_service_class, service, test_user, test_archive_config):
        """Test scheduling an archive operation."""
        mock_job_service = MagicMock()
        mock_job_service_class.return_value = mock_job_service
        mock_job_service.schedule_archive_job.return_value = "job-123"
        
        schedule_time = datetime.now(UTC) + timedelta(hours=1)
        
        job_id = service.schedule_archive(
            user_id=test_user.id,
            archive_config_id=test_archive_config.id,
            schedule_time=schedule_time,
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 7)
        )
        
        assert job_id == "job-123"
        mock_job_service.schedule_archive_job.assert_called_once()

    @patch('core.services.scheduled_archive_service.BackgroundJobService')
    def test_schedule_recurring_archive(self, mock_job_service_class, service, test_user, test_archive_config):
        """Test scheduling a recurring archive operation."""
        mock_job_service = MagicMock()
        mock_job_service_class.return_value = mock_job_service
        mock_job_service.schedule_recurring_archive_job.return_value = "recurring-job-123"
        
        job_id = service.schedule_recurring_archive(
            user_id=test_user.id,
            archive_config_id=test_archive_config.id,
            cron_expression="0 9 * * 1",  # Every Monday at 9 AM
            date_range_days=7
        )
        
        assert job_id == "recurring-job-123"
        mock_job_service.schedule_recurring_archive_job.assert_called_once()

    @patch('core.services.scheduled_archive_service.BackgroundJobService')
    def test_cancel_scheduled_archive(self, mock_job_service_class, service):
        """Test canceling a scheduled archive."""
        mock_job_service = MagicMock()
        mock_job_service_class.return_value = mock_job_service
        mock_job_service.cancel_job.return_value = True
        
        result = service.cancel_scheduled_archive("job-123")
        
        assert result is True
        mock_job_service.cancel_job.assert_called_once_with("job-123")

    @patch('core.services.scheduled_archive_service.BackgroundJobService')
    def test_get_scheduled_archives(self, mock_job_service_class, service, test_user):
        """Test getting scheduled archives for a user."""
        mock_job_service = MagicMock()
        mock_job_service_class.return_value = mock_job_service
        mock_job_service.get_jobs_by_user.return_value = [
            {
                "job_id": "job-1",
                "name": "Archive Job 1",
                "next_run_time": "2025-06-01 09:00:00",
                "status": "scheduled"
            },
            {
                "job_id": "job-2",
                "name": "Archive Job 2",
                "next_run_time": "2025-06-02 09:00:00",
                "status": "scheduled"
            }
        ]
        
        jobs = service.get_scheduled_archives(test_user.id)
        
        assert len(jobs) == 2
        assert jobs[0]["job_id"] == "job-1"
        assert jobs[1]["job_id"] == "job-2"
        mock_job_service.get_jobs_by_user.assert_called_once_with(test_user.id)

    @patch('core.services.scheduled_archive_service.BackgroundJobService')
    def test_pause_scheduled_archive(self, mock_job_service_class, service):
        """Test pausing a scheduled archive."""
        mock_job_service = MagicMock()
        mock_job_service_class.return_value = mock_job_service
        mock_job_service.pause_job.return_value = True
        
        result = service.pause_scheduled_archive("job-123")
        
        assert result is True
        mock_job_service.pause_job.assert_called_once_with("job-123")

    @patch('core.services.scheduled_archive_service.BackgroundJobService')
    def test_resume_scheduled_archive(self, mock_job_service_class, service):
        """Test resuming a paused archive."""
        mock_job_service = MagicMock()
        mock_job_service_class.return_value = mock_job_service
        mock_job_service.resume_job.return_value = True
        
        result = service.resume_scheduled_archive("job-123")
        
        assert result is True
        mock_job_service.resume_job.assert_called_once_with("job-123")

    @patch('core.services.scheduled_archive_service.BackgroundJobService')
    def test_modify_scheduled_archive(self, mock_job_service_class, service):
        """Test modifying a scheduled archive."""
        mock_job_service = MagicMock()
        mock_job_service_class.return_value = mock_job_service
        mock_job_service.modify_job.return_value = True
        
        new_time = datetime.now(UTC) + timedelta(hours=2)
        
        result = service.modify_scheduled_archive(
            job_id="job-123",
            next_run_time=new_time
        )
        
        assert result is True
        mock_job_service.modify_job.assert_called_once()

    def test_calculate_date_range(self, service):
        """Test date range calculation for recurring jobs."""
        base_date = date(2025, 6, 1)
        
        start_date, end_date = service._calculate_date_range(base_date, 7)
        
        assert start_date == date(2025, 5, 25)  # 7 days before
        assert end_date == base_date

    def test_validate_cron_expression(self, service):
        """Test cron expression validation."""
        # Valid expressions
        assert service.validate_cron_expression("0 9 * * 1") is True
        assert service.validate_cron_expression("*/15 * * * *") is True
        assert service.validate_cron_expression("0 0 1 * *") is True
        
        # Invalid expressions
        assert service.validate_cron_expression("invalid") is False
        assert service.validate_cron_expression("") is False
        assert service.validate_cron_expression("60 * * * *") is False  # Invalid minute

    @patch('core.services.scheduled_archive_service.BackgroundJobService')
    def test_get_archive_history(self, mock_job_service_class, service):
        """Test getting archive execution history."""
        mock_job_service = MagicMock()
        mock_job_service_class.return_value = mock_job_service
        mock_job_service.get_job_history.return_value = [
            {
                "execution_time": "2025-05-01 09:00:00",
                "status": "success",
                "archived_count": 15,
                "overlap_count": 2
            },
            {
                "execution_time": "2025-04-24 09:00:00",
                "status": "success",
                "archived_count": 12,
                "overlap_count": 0
            }
        ]
        
        history = service.get_archive_history("job-123")
        
        assert len(history) == 2
        assert history[0]["status"] == "success"
        assert history[0]["archived_count"] == 15
        mock_job_service.get_job_history.assert_called_once_with("job-123")

    def test_generate_job_name(self, service, test_archive_config):
        """Test job name generation."""
        job_name = service._generate_job_name(test_archive_config, "weekly")
        
        assert test_archive_config.name in job_name
        assert "weekly" in job_name.lower()

    @patch('core.services.scheduled_archive_service.BackgroundJobService')
    def test_schedule_archive_with_validation(self, mock_job_service_class, service, test_user, test_archive_config):
        """Test scheduling with input validation."""
        mock_job_service = MagicMock()
        mock_job_service_class.return_value = mock_job_service
        
        # Test with past schedule time
        past_time = datetime.now(UTC) - timedelta(hours=1)
        
        with pytest.raises(ValueError, match="Schedule time cannot be in the past"):
            service.schedule_archive(
                user_id=test_user.id,
                archive_config_id=test_archive_config.id,
                schedule_time=past_time,
                start_date=date(2025, 6, 1),
                end_date=date(2025, 6, 7)
            )

    @patch('core.services.scheduled_archive_service.BackgroundJobService')
    def test_schedule_recurring_with_validation(self, mock_job_service_class, service, test_user, test_archive_config):
        """Test scheduling recurring archive with validation."""
        mock_job_service = MagicMock()
        mock_job_service_class.return_value = mock_job_service
        
        # Test with invalid cron expression
        with pytest.raises(ValueError, match="Invalid cron expression"):
            service.schedule_recurring_archive(
                user_id=test_user.id,
                archive_config_id=test_archive_config.id,
                cron_expression="invalid cron",
                date_range_days=7
            )

    @patch('core.services.scheduled_archive_service.BackgroundJobService')
    def test_get_next_execution_times(self, mock_job_service_class, service):
        """Test getting next execution times for a cron expression."""
        mock_job_service = MagicMock()
        mock_job_service_class.return_value = mock_job_service
        
        # Test getting next 5 execution times
        next_times = service.get_next_execution_times("0 9 * * 1", count=5)
        
        assert len(next_times) == 5
        assert all(isinstance(time, datetime) for time in next_times)

    def test_parse_cron_expression(self, service):
        """Test parsing cron expressions into human-readable format."""
        # Test common expressions
        assert "every Monday at 09:00" in service.parse_cron_expression("0 9 * * 1").lower()
        assert "every 15 minutes" in service.parse_cron_expression("*/15 * * * *").lower()
        assert "daily at 00:00" in service.parse_cron_expression("0 0 * * *").lower()

    @patch('core.services.scheduled_archive_service.BackgroundJobService')
    def test_bulk_schedule_archives(self, mock_job_service_class, service, test_user):
        """Test bulk scheduling of archives."""
        mock_job_service = MagicMock()
        mock_job_service_class.return_value = mock_job_service
        mock_job_service.schedule_archive_job.side_effect = ["job-1", "job-2", "job-3"]
        
        archive_configs = [1, 2, 3]  # Config IDs
        schedule_time = datetime.now(UTC) + timedelta(hours=1)
        
        job_ids = service.bulk_schedule_archives(
            user_id=test_user.id,
            archive_config_ids=archive_configs,
            schedule_time=schedule_time,
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 7)
        )
        
        assert len(job_ids) == 3
        assert job_ids == ["job-1", "job-2", "job-3"]
        assert mock_job_service.schedule_archive_job.call_count == 3
