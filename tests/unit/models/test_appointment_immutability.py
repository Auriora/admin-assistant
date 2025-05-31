"""
Tests for appointment immutability enforcement.
"""
import pytest
from datetime import datetime, timezone
from core.models.appointment import Appointment
from core.models.user import User
from core.exceptions import ImmutableAppointmentException


class TestAppointmentImmutability:
    """Test cases for appointment immutability logic."""

    def test_non_archived_appointment_is_mutable(self):
        """Test that non-archived appointments are mutable."""
        appointment = Appointment(
            user_id=1,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            subject="Test Meeting",
            calendar_id="test-calendar",
            is_archived=False
        )
        
        # Should not be immutable
        assert not appointment.is_immutable()
        
        # Should not raise exception
        appointment.validate_modification_allowed()

    def test_archived_appointment_is_immutable_for_other_users(self):
        """Test that archived appointments are immutable for other users."""
        appointment = Appointment(
            user_id=1,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            subject="Test Meeting",
            calendar_id="test-calendar",
            is_archived=True
        )
        
        # Create a different user
        other_user = User(id=2, email="other@example.com", name="Other User")
        
        # Should be immutable for other user
        assert appointment.is_immutable(other_user)
        
        # Should raise exception
        with pytest.raises(ImmutableAppointmentException):
            appointment.validate_modification_allowed(other_user)

    def test_archived_appointment_is_mutable_for_owner(self):
        """Test that archived appointments are mutable for the owner."""
        appointment = Appointment(
            user_id=1,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            subject="Test Meeting",
            calendar_id="test-calendar",
            is_archived=True
        )
        
        # Create the owner user
        owner_user = User(id=1, email="owner@example.com", name="Owner User")
        
        # Should not be immutable for owner
        assert not appointment.is_immutable(owner_user)
        
        # Should not raise exception
        appointment.validate_modification_allowed(owner_user)

    def test_archived_appointment_is_immutable_without_user(self):
        """Test that archived appointments are immutable when no user is provided."""
        appointment = Appointment(
            user_id=1,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            subject="Test Meeting",
            calendar_id="test-calendar",
            is_archived=True
        )
        
        # Should be immutable when no user provided (safety default)
        assert appointment.is_immutable()
        
        # Should raise exception
        with pytest.raises(ImmutableAppointmentException):
            appointment.validate_modification_allowed()

    def test_immutable_appointment_exception_message(self):
        """Test that the exception message contains useful information."""
        appointment = Appointment(
            id=123,
            user_id=1,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            subject="Important Meeting",
            calendar_id="test-calendar",
            is_archived=True
        )
        
        other_user = User(id=2, email="other@example.com", name="Other User")
        
        with pytest.raises(ImmutableAppointmentException) as exc_info:
            appointment.validate_modification_allowed(other_user)
        
        error_message = str(exc_info.value)
        assert "Important Meeting" in error_message
        assert "123" in error_message
        assert "immutable" in error_message.lower()
