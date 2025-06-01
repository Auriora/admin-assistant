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
        return ActionLogRepository(session=db_session)

    @pytest.fixture
    def test_action_log(self, db_session, test_user):
        """Create a test action log entry."""
        action_log = ActionLog(
            user_id=test_user.id,
            event_type="overlap_resolution",
            state="pending",
            description="Test overlap detected",
            details={"appointment_count": 2}
        )
        db_session.add(action_log)
        db_session.commit()
        return action_log

    def test_create_action_log(self, repository, test_user):
        """Test creating a new action log entry."""
        action_log = ActionLog(
            user_id=test_user.id,
            event_type="calendar_archive",
            state="success",
            description="Archive completed successfully",
            details={"archived_count": 10}
        )

        result = repository.add(action_log)

        assert result.id is not None
        assert result.event_type == "calendar_archive"
        assert result.state == "success"
        assert result.user_id == test_user.id
        assert result.details["archived_count"] == 10

    def test_get_by_id(self, repository, test_action_log):
        """Test retrieving action log by ID."""
        result = repository.get_by_id(test_action_log.id)

        assert result is not None
        assert result.id == test_action_log.id
        assert result.event_type == test_action_log.event_type

    def test_get_by_id_not_found(self, repository):
        """Test retrieving non-existent action log."""
        result = repository.get_by_id(99999)
        
        assert result is None

    def test_list_for_user(self, repository, test_user, db_session):
        """Test listing action logs for a user."""
        # Create multiple action logs
        log1 = ActionLog(
            user_id=test_user.id,
            event_type="archive",
            state="success",
            description="Archive 1"
        )
        log2 = ActionLog(
            user_id=test_user.id,
            event_type="overlap",
            state="pending",
            description="Overlap 1"
        )

        db_session.add_all([log1, log2])
        db_session.commit()

        results = repository.list_for_user(test_user.id)

        assert len(results) >= 2
        event_types = [log.event_type for log in results]
        assert "archive" in event_types
        assert "overlap" in event_types

    def test_list_by_status(self, repository, test_user, db_session):
        """Test listing action logs by status."""
        # Create logs with different states
        pending_log = ActionLog(
            user_id=test_user.id,
            event_type="test",
            state="pending",
            description="Pending log"
        )
        success_log = ActionLog(
            user_id=test_user.id,
            event_type="test",
            state="success",
            description="Success log"
        )

        db_session.add_all([pending_log, success_log])
        db_session.commit()

        pending_results = repository.list_by_state("pending")
        success_results = repository.list_by_state("success")

        assert len(pending_results) >= 1
        assert len(success_results) >= 1
        assert all(log.state == "pending" for log in pending_results)
        assert all(log.state == "success" for log in success_results)

    def test_list_by_action_type(self, repository, test_user, db_session):
        """Test listing action logs by event type."""
        # Create logs with different event types
        archive_log = ActionLog(
            user_id=test_user.id,
            event_type="archive",
            state="success",
            description="Archive log"
        )
        overlap_log = ActionLog(
            user_id=test_user.id,
            event_type="overlap",
            state="pending",
            description="Overlap log"
        )

        db_session.add_all([archive_log, overlap_log])
        db_session.commit()

        archive_results = repository.list_by_event_type("archive")
        overlap_results = repository.list_by_event_type("overlap")

        assert len(archive_results) >= 1
        assert len(overlap_results) >= 1
        assert all(log.event_type == "archive" for log in archive_results)
        assert all(log.event_type == "overlap" for log in overlap_results)

    def test_update_action_log(self, repository, test_action_log):
        """Test updating an action log entry."""
        test_action_log.state = "resolved"
        test_action_log.description = "Updated message"

        repository.update(test_action_log)

        updated = repository.get_by_id(test_action_log.id)
        assert updated.state == "resolved"
        assert updated.description == "Updated message"

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
            event_type="overlap_resolution",
            state="pending",
            description="Pending overlap"
        )
        resolved_overlap = ActionLog(
            user_id=test_user.id,
            event_type="overlap_resolution",
            state="resolved",
            description="Resolved overlap"
        )
        pending_archive = ActionLog(
            user_id=test_user.id,
            event_type="archive",
            state="pending",
            description="Pending archive"
        )

        db_session.add_all([pending_overlap, resolved_overlap, pending_archive])
        db_session.commit()

        results = repository.list_pending_overlaps()

        assert len(results) >= 1
        assert all(log.event_type == "overlap_resolution" for log in results)
        assert all(log.state == "pending" for log in results)

    def test_user_isolation(self, db_session, test_user):
        """Test that users can only see their own action logs."""
        from core.models.user import User
        
        # Create another user
        other_user = User(
            email="other@example.com",
            name="Other User"
        )
        db_session.add(other_user)
        db_session.commit()
        
        # Create action logs for both users
        user1_log = ActionLog(
            user_id=test_user.id,
            event_type="test",
            state="success",
            description="User 1 log"
        )
        user2_log = ActionLog(
            user_id=other_user.id,
            event_type="test",
            state="success",
            description="User 2 log"
        )

        db_session.add_all([user1_log, user2_log])
        db_session.commit()

        # Test user 1 repository
        repo1 = ActionLogRepository(session=db_session)
        results1 = repo1.list_for_user(test_user.id)
        descriptions1 = [log.description for log in results1]

        assert "User 1 log" in descriptions1
        assert "User 2 log" not in descriptions1

        # Test user 2 repository
        repo2 = ActionLogRepository(session=db_session)
        results2 = repo2.list_for_user(other_user.id)
        descriptions2 = [log.description for log in results2]

        assert "User 2 log" in descriptions2
        assert "User 1 log" not in descriptions2
