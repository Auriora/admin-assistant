"""
Unit tests for ActionLogRepository.
"""
import pytest
from datetime import datetime, UTC
from core.models.action_log import ActionLog
from core.repositories.action_log_repository import ActionLogRepository


@pytest.mark.unit
@pytest.mark.db
class TestActionLogRepository:
    """Test cases for ActionLogRepository."""

    @pytest.fixture
    def repository(self, db_session, test_user):
        """Create repository instance."""
        return ActionLogRepository(session=db_session, user=test_user)

    @pytest.fixture
    def test_action_log(self, db_session, test_user):
        """Create a test action log entry."""
        action_log = ActionLog(
            user_id=test_user.id,
            action_type="overlap_resolution",
            status="pending",
            message="Test overlap detected",
            details={"appointment_count": 2}
        )
        db_session.add(action_log)
        db_session.commit()
        return action_log

    def test_create_action_log(self, repository, test_user):
        """Test creating a new action log entry."""
        action_log = ActionLog(
            user_id=test_user.id,
            action_type="calendar_archive",
            status="success",
            message="Archive completed successfully",
            details={"archived_count": 10}
        )
        
        result = repository.add(action_log)
        
        assert result.id is not None
        assert result.action_type == "calendar_archive"
        assert result.status == "success"
        assert result.user_id == test_user.id
        assert result.details["archived_count"] == 10

    def test_get_by_id(self, repository, test_action_log):
        """Test retrieving action log by ID."""
        result = repository.get_by_id(test_action_log.id)
        
        assert result is not None
        assert result.id == test_action_log.id
        assert result.action_type == test_action_log.action_type

    def test_get_by_id_not_found(self, repository):
        """Test retrieving non-existent action log."""
        result = repository.get_by_id(99999)
        
        assert result is None

    def test_list_for_user(self, repository, test_user, db_session):
        """Test listing action logs for a user."""
        # Create multiple action logs
        log1 = ActionLog(
            user_id=test_user.id,
            action_type="archive",
            status="success",
            message="Archive 1"
        )
        log2 = ActionLog(
            user_id=test_user.id,
            action_type="overlap",
            status="pending",
            message="Overlap 1"
        )
        
        db_session.add_all([log1, log2])
        db_session.commit()
        
        results = repository.list()
        
        assert len(results) >= 2
        action_types = [log.action_type for log in results]
        assert "archive" in action_types
        assert "overlap" in action_types

    def test_list_by_status(self, repository, test_user, db_session):
        """Test listing action logs by status."""
        # Create logs with different statuses
        pending_log = ActionLog(
            user_id=test_user.id,
            action_type="test",
            status="pending",
            message="Pending log"
        )
        success_log = ActionLog(
            user_id=test_user.id,
            action_type="test",
            status="success",
            message="Success log"
        )
        
        db_session.add_all([pending_log, success_log])
        db_session.commit()
        
        pending_results = repository.list_by_status("pending")
        success_results = repository.list_by_status("success")
        
        assert len(pending_results) >= 1
        assert len(success_results) >= 1
        assert all(log.status == "pending" for log in pending_results)
        assert all(log.status == "success" for log in success_results)

    def test_list_by_action_type(self, repository, test_user, db_session):
        """Test listing action logs by action type."""
        # Create logs with different action types
        archive_log = ActionLog(
            user_id=test_user.id,
            action_type="archive",
            status="success",
            message="Archive log"
        )
        overlap_log = ActionLog(
            user_id=test_user.id,
            action_type="overlap",
            status="pending",
            message="Overlap log"
        )
        
        db_session.add_all([archive_log, overlap_log])
        db_session.commit()
        
        archive_results = repository.list_by_action_type("archive")
        overlap_results = repository.list_by_action_type("overlap")
        
        assert len(archive_results) >= 1
        assert len(overlap_results) >= 1
        assert all(log.action_type == "archive" for log in archive_results)
        assert all(log.action_type == "overlap" for log in overlap_results)

    def test_update_action_log(self, repository, test_action_log):
        """Test updating an action log entry."""
        test_action_log.status = "resolved"
        test_action_log.message = "Updated message"
        
        repository.update(test_action_log)
        
        updated = repository.get_by_id(test_action_log.id)
        assert updated.status == "resolved"
        assert updated.message == "Updated message"

    def test_delete_action_log(self, repository, test_action_log):
        """Test deleting an action log entry."""
        log_id = test_action_log.id
        
        repository.delete(log_id)
        
        result = repository.get_by_id(log_id)
        assert result is None

    def test_list_pending_overlaps(self, repository, test_user, db_session):
        """Test listing pending overlap resolution tasks."""
        # Create various action logs
        pending_overlap = ActionLog(
            user_id=test_user.id,
            action_type="overlap_resolution",
            status="pending",
            message="Pending overlap"
        )
        resolved_overlap = ActionLog(
            user_id=test_user.id,
            action_type="overlap_resolution",
            status="resolved",
            message="Resolved overlap"
        )
        pending_archive = ActionLog(
            user_id=test_user.id,
            action_type="archive",
            status="pending",
            message="Pending archive"
        )
        
        db_session.add_all([pending_overlap, resolved_overlap, pending_archive])
        db_session.commit()
        
        results = repository.list_pending_overlaps()
        
        assert len(results) >= 1
        assert all(log.action_type == "overlap_resolution" for log in results)
        assert all(log.status == "pending" for log in results)

    def test_user_isolation(self, db_session, test_user):
        """Test that users can only see their own action logs."""
        from core.models.user import User
        
        # Create another user
        other_user = User(
            email="other@example.com",
            name="Other User",
            ms_user_id="other-ms-user-id"
        )
        db_session.add(other_user)
        db_session.commit()
        
        # Create action logs for both users
        user1_log = ActionLog(
            user_id=test_user.id,
            action_type="test",
            status="success",
            message="User 1 log"
        )
        user2_log = ActionLog(
            user_id=other_user.id,
            action_type="test",
            status="success",
            message="User 2 log"
        )
        
        db_session.add_all([user1_log, user2_log])
        db_session.commit()
        
        # Test user 1 repository
        repo1 = ActionLogRepository(session=db_session, user=test_user)
        results1 = repo1.list()
        messages1 = [log.message for log in results1]
        
        assert "User 1 log" in messages1
        assert "User 2 log" not in messages1
        
        # Test user 2 repository
        repo2 = ActionLogRepository(session=db_session, user=other_user)
        results2 = repo2.list()
        messages2 = [log.message for log in results2]
        
        assert "User 2 log" in messages2
        assert "User 1 log" not in messages2
