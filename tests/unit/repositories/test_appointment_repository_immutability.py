"""
Tests for appointment repository immutability enforcement.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from core.models.appointment import Appointment
from core.models.user import User
from core.repositories.appointment_repository_sqlalchemy import SQLAlchemyAppointmentRepository
from core.exceptions import ImmutableAppointmentException


class TestAppointmentRepositoryImmutability:
    """Test cases for repository immutability enforcement."""

    @pytest.fixture
    def user(self):
        """Create a test user."""
        return User(id=1, email="test@example.com", name="Test User")

    @pytest.fixture
    def other_user(self):
        """Create another test user."""
        return User(id=2, email="other@example.com", name="Other User")

    @pytest.fixture
    def archived_appointment(self, user):
        """Create an archived appointment."""
        return Appointment(
            id=1,
            user_id=user.id,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            subject="Archived Meeting",
            calendar_id="test-calendar",
            is_archived=True
        )

    @pytest.fixture
    def non_archived_appointment(self, user):
        """Create a non-archived appointment."""
        return Appointment(
            id=2,
            user_id=user.id,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            subject="Regular Meeting",
            calendar_id="test-calendar",
            is_archived=False
        )

    def test_update_archived_appointment_by_owner_succeeds(self, user, archived_appointment):
        """Test that owner can update their archived appointment."""
        with patch('core.repositories.appointment_repository_sqlalchemy.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            
            repo = SQLAlchemyAppointmentRepository(user, "test-calendar", mock_session)
            
            # Should not raise exception for owner
            repo.update(archived_appointment)
            
            # Verify session operations were called
            mock_session.merge.assert_called_once()
            mock_session.commit.assert_called_once()

    def test_update_archived_appointment_by_other_user_fails(self, other_user, archived_appointment):
        """Test that other users cannot update archived appointments."""
        with patch('core.repositories.appointment_repository_sqlalchemy.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            
            repo = SQLAlchemyAppointmentRepository(other_user, "test-calendar", mock_session)
            
            # Should raise exception for other user
            with pytest.raises(ImmutableAppointmentException):
                repo.update(archived_appointment)
            
            # Verify session operations were NOT called
            mock_session.merge.assert_not_called()
            mock_session.commit.assert_not_called()

    def test_update_non_archived_appointment_succeeds(self, other_user, non_archived_appointment):
        """Test that any user can update non-archived appointments."""
        with patch('core.repositories.appointment_repository_sqlalchemy.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            
            repo = SQLAlchemyAppointmentRepository(other_user, "test-calendar", mock_session)
            
            # Should not raise exception for non-archived appointment
            repo.update(non_archived_appointment)
            
            # Verify session operations were called
            mock_session.merge.assert_called_once()
            mock_session.commit.assert_called_once()

    def test_delete_archived_appointment_by_owner_succeeds(self, user, archived_appointment):
        """Test that owner can delete their archived appointment."""
        with patch('core.repositories.appointment_repository_sqlalchemy.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.get.return_value = archived_appointment
            
            repo = SQLAlchemyAppointmentRepository(user, "test-calendar", mock_session)
            
            # Should not raise exception for owner
            repo.delete(archived_appointment.id)
            
            # Verify session operations were called
            mock_session.delete.assert_called_once()
            mock_session.commit.assert_called_once()

    def test_delete_archived_appointment_by_other_user_fails(self, other_user, archived_appointment):
        """Test that other users cannot delete archived appointments."""
        with patch('core.repositories.appointment_repository_sqlalchemy.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.get.return_value = archived_appointment
            
            repo = SQLAlchemyAppointmentRepository(other_user, "test-calendar", mock_session)
            
            # Should raise exception for other user
            with pytest.raises(ImmutableAppointmentException):
                repo.delete(archived_appointment.id)
            
            # Verify session operations were NOT called
            mock_session.delete.assert_not_called()
            mock_session.commit.assert_not_called()

    def test_delete_for_period_respects_immutability(self, other_user, archived_appointment, non_archived_appointment):
        """Test that delete_for_period respects immutability rules."""
        with patch('core.repositories.appointment_repository_sqlalchemy.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            
            # Mock query to return both appointments
            mock_query = Mock()
            mock_query.filter.return_value = mock_query
            mock_query.all.return_value = [archived_appointment, non_archived_appointment]
            mock_session.query.return_value = mock_query
            
            repo = SQLAlchemyAppointmentRepository(other_user, "test-calendar", mock_session)
            
            # Should only delete non-archived appointment
            deleted_count = repo.delete_for_period(
                datetime.now(timezone.utc).date(),
                datetime.now(timezone.utc).date()
            )
            
            # Should return 1 (only non-archived was deleted)
            assert deleted_count == 1
            
            # Verify only one delete call was made
            assert mock_session.delete.call_count == 1
            mock_session.commit.assert_called_once()
