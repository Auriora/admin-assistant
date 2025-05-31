"""
Enhanced unit tests for BackgroundJobService.
"""
import pytest
from unittest.mock import MagicMock, patch
from core.services.background_job_service import BackgroundJobService


@pytest.mark.unit
class TestBackgroundJobServiceEnhanced:
    """Enhanced test cases for BackgroundJobService."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return BackgroundJobService()

    def test_service_initialization(self, service):
        """Test service initialization."""
        assert service is not None
        assert hasattr(service, 'schedule_archive_job')
        assert hasattr(service, 'get_job_status')

    @patch('core.services.background_job_service.scheduler')
    def test_schedule_archive_job(self, mock_scheduler, service, test_user, test_archive_config):
        """Test scheduling an archive job."""
        mock_job = MagicMock()
        mock_job.id = "test-job-123"
        mock_scheduler.add_job.return_value = mock_job
        
        job_id = service.schedule_archive_job(
            user_id=test_user.id,
            archive_config_id=test_archive_config.id,
            schedule_time="2025-06-01 09:00:00"
        )
        
        assert job_id == "test-job-123"
        mock_scheduler.add_job.assert_called_once()

    @patch('core.services.background_job_service.scheduler')
    def test_get_job_status(self, mock_scheduler, service):
        """Test getting job status."""
        mock_job = MagicMock()
        mock_job.id = "test-job-123"
        mock_job.next_run_time = "2025-06-01 09:00:00"
        mock_scheduler.get_job.return_value = mock_job
        
        status = service.get_job_status("test-job-123")
        
        assert status is not None
        assert status["job_id"] == "test-job-123"
        mock_scheduler.get_job.assert_called_once_with("test-job-123")

    @patch('core.services.background_job_service.scheduler')
    def test_get_job_status_not_found(self, mock_scheduler, service):
        """Test getting status for non-existent job."""
        mock_scheduler.get_job.return_value = None
        
        status = service.get_job_status("non-existent-job")
        
        assert status is None
        mock_scheduler.get_job.assert_called_once_with("non-existent-job")

    @patch('core.services.background_job_service.scheduler')
    def test_cancel_job(self, mock_scheduler, service):
        """Test canceling a scheduled job."""
        result = service.cancel_job("test-job-123")
        
        assert result is True
        mock_scheduler.remove_job.assert_called_once_with("test-job-123")

    @patch('core.services.background_job_service.scheduler')
    def test_cancel_job_not_found(self, mock_scheduler, service):
        """Test canceling a non-existent job."""
        from apscheduler.jobstores.base import JobLookupError
        mock_scheduler.remove_job.side_effect = JobLookupError("Job not found")
        
        result = service.cancel_job("non-existent-job")
        
        assert result is False
        mock_scheduler.remove_job.assert_called_once_with("non-existent-job")

    @patch('core.services.background_job_service.scheduler')
    def test_list_jobs(self, mock_scheduler, service):
        """Test listing all scheduled jobs."""
        mock_job1 = MagicMock()
        mock_job1.id = "job-1"
        mock_job1.name = "Archive Job 1"
        
        mock_job2 = MagicMock()
        mock_job2.id = "job-2"
        mock_job2.name = "Archive Job 2"
        
        mock_scheduler.get_jobs.return_value = [mock_job1, mock_job2]
        
        jobs = service.list_jobs()
        
        assert len(jobs) == 2
        assert jobs[0]["job_id"] == "job-1"
        assert jobs[1]["job_id"] == "job-2"
        mock_scheduler.get_jobs.assert_called_once()

    @patch('core.services.background_job_service.scheduler')
    def test_schedule_recurring_job(self, mock_scheduler, service, test_user, test_archive_config):
        """Test scheduling a recurring archive job."""
        mock_job = MagicMock()
        mock_job.id = "recurring-job-123"
        mock_scheduler.add_job.return_value = mock_job
        
        job_id = service.schedule_recurring_archive_job(
            user_id=test_user.id,
            archive_config_id=test_archive_config.id,
            cron_expression="0 9 * * 1"  # Every Monday at 9 AM
        )
        
        assert job_id == "recurring-job-123"
        mock_scheduler.add_job.assert_called_once()
        
        # Verify cron trigger was used
        call_args = mock_scheduler.add_job.call_args
        assert call_args[1]["trigger"] == "cron"

    @patch('core.services.background_job_service.ArchiveJobRunner')
    def test_execute_archive_job(self, mock_runner_class, service, test_user, test_archive_config):
        """Test executing an archive job."""
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner
        mock_runner.run_archive_job.return_value = {
            "status": "success",
            "archived_count": 10,
            "overlap_count": 0
        }
        
        result = service.execute_archive_job(
            user_id=test_user.id,
            archive_config_id=test_archive_config.id
        )
        
        assert result["status"] == "success"
        assert result["archived_count"] == 10
        mock_runner.run_archive_job.assert_called_once()

    @patch('core.services.background_job_service.ArchiveJobRunner')
    def test_execute_archive_job_with_error(self, mock_runner_class, service, test_user, test_archive_config):
        """Test executing an archive job that fails."""
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner
        mock_runner.run_archive_job.side_effect = Exception("Job execution failed")
        
        result = service.execute_archive_job(
            user_id=test_user.id,
            archive_config_id=test_archive_config.id
        )
        
        assert result["status"] == "error"
        assert "Job execution failed" in result["error"]

    def test_job_id_generation(self, service, test_user, test_archive_config):
        """Test job ID generation."""
        job_id = service._generate_job_id(test_user.id, test_archive_config.id)
        
        assert job_id is not None
        assert str(test_user.id) in job_id
        assert str(test_archive_config.id) in job_id

    @patch('core.services.background_job_service.scheduler')
    def test_pause_job(self, mock_scheduler, service):
        """Test pausing a scheduled job."""
        result = service.pause_job("test-job-123")
        
        assert result is True
        mock_scheduler.pause_job.assert_called_once_with("test-job-123")

    @patch('core.services.background_job_service.scheduler')
    def test_resume_job(self, mock_scheduler, service):
        """Test resuming a paused job."""
        result = service.resume_job("test-job-123")
        
        assert result is True
        mock_scheduler.resume_job.assert_called_once_with("test-job-123")

    @patch('core.services.background_job_service.scheduler')
    def test_modify_job(self, mock_scheduler, service):
        """Test modifying a scheduled job."""
        result = service.modify_job(
            job_id="test-job-123",
            next_run_time="2025-06-02 10:00:00"
        )
        
        assert result is True
        mock_scheduler.modify_job.assert_called_once()

    @patch('core.services.background_job_service.scheduler')
    def test_get_job_history(self, mock_scheduler, service):
        """Test getting job execution history."""
        # This would typically require a job store that supports history
        # For now, test the method exists and handles empty history
        history = service.get_job_history("test-job-123")
        
        assert isinstance(history, list)

    def test_validate_cron_expression(self, service):
        """Test cron expression validation."""
        # Valid expressions
        assert service.validate_cron_expression("0 9 * * 1") is True
        assert service.validate_cron_expression("*/15 * * * *") is True
        
        # Invalid expressions
        assert service.validate_cron_expression("invalid") is False
        assert service.validate_cron_expression("") is False

    @patch('core.services.background_job_service.scheduler')
    def test_get_jobs_by_user(self, mock_scheduler, service, test_user):
        """Test getting jobs for a specific user."""
        mock_job1 = MagicMock()
        mock_job1.id = f"archive_{test_user.id}_1"
        mock_job1.name = "User Archive Job 1"
        
        mock_job2 = MagicMock()
        mock_job2.id = "archive_999_1"
        mock_job2.name = "Other User Job"
        
        mock_scheduler.get_jobs.return_value = [mock_job1, mock_job2]
        
        user_jobs = service.get_jobs_by_user(test_user.id)
        
        assert len(user_jobs) == 1
        assert user_jobs[0]["job_id"] == f"archive_{test_user.id}_1"
