"""
Tests for calendar_io_service module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime, timezone
from typing import List

from core.services.calendar_io_service import fetch_appointments, store_appointments
from core.models.appointment import Appointment
from core.models.user import User
from core.exceptions import CalendarServiceException


class TestFetchAppointments:
    """Test cases for fetch_appointments function."""

    def test_fetch_appointments_success(self):
        """Test successful fetching of appointments with date filtering."""
        # Arrange
        user = Mock()
        user.id = 1
        user.email = "test@example.com"
        
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        
        # Create mock appointments with proper datetime objects
        appt1 = Mock(spec=Appointment)
        appt1.start_time = datetime(2024, 1, 15, 9, 0, tzinfo=timezone.utc)
        appt1.end_time = datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)
        appt1.subject = "Meeting 1"
        
        appt2 = Mock(spec=Appointment)
        appt2.start_time = datetime(2024, 1, 20, 14, 0, tzinfo=timezone.utc)
        appt2.end_time = datetime(2024, 1, 20, 15, 0, tzinfo=timezone.utc)
        appt2.subject = "Meeting 2"
        
        # Appointment outside date range
        appt3 = Mock(spec=Appointment)
        appt3.start_time = datetime(2024, 2, 1, 9, 0, tzinfo=timezone.utc)
        appt3.end_time = datetime(2024, 2, 1, 10, 0, tzinfo=timezone.utc)
        appt3.subject = "Meeting 3"
        
        mock_repo = Mock()
        mock_repo.list_for_user.return_value = [appt1, appt2, appt3]
        
        mock_logger = Mock()
        
        # Act
        result = fetch_appointments(user, start_date, end_date, mock_repo, mock_logger)
        
        # Assert
        assert len(result) == 2
        assert appt1 in result
        assert appt2 in result
        assert appt3 not in result
        
        mock_repo.list_for_user.assert_called_once_with(user.id)
        mock_logger.info.assert_called_once_with(
            f"Fetched 2 appointments for {user.email} from {start_date} to {end_date}"
        )

    def test_fetch_appointments_empty_result(self):
        """Test fetching when no appointments are found."""
        # Arrange
        user = Mock()
        user.id = 1
        user.email = "test@example.com"
        
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        
        mock_repo = Mock()
        mock_repo.list_for_user.return_value = []
        
        mock_logger = Mock()
        
        # Act
        result = fetch_appointments(user, start_date, end_date, mock_repo, mock_logger)
        
        # Assert
        assert result == []
        mock_repo.list_for_user.assert_called_once_with(user.id)
        mock_logger.info.assert_called_once_with(
            f"Fetched 0 appointments for {user.email} from {start_date} to {end_date}"
        )

    def test_fetch_appointments_filters_invalid_appointments(self):
        """Test that appointments without start_time or end_time are filtered out."""
        # Arrange
        user = Mock()
        user.id = 1
        user.email = "test@example.com"

        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)

        # Valid appointment
        valid_appt = Mock(spec=Appointment)
        valid_appt.start_time = datetime(2024, 1, 15, 9, 0, tzinfo=timezone.utc)
        valid_appt.end_time = datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)

        # Invalid appointments - use objects that don't have the attributes
        no_start_time = Mock()
        no_start_time.end_time = datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)
        del no_start_time.start_time  # Remove the attribute

        no_end_time = Mock()
        no_end_time.start_time = datetime(2024, 1, 15, 9, 0, tzinfo=timezone.utc)
        del no_end_time.end_time  # Remove the attribute

        null_start_time = Mock(spec=Appointment)
        null_start_time.start_time = None
        null_start_time.end_time = datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)

        null_end_time = Mock(spec=Appointment)
        null_end_time.start_time = datetime(2024, 1, 15, 9, 0, tzinfo=timezone.utc)
        null_end_time.end_time = None

        mock_repo = Mock()
        mock_repo.list_for_user.return_value = [
            valid_appt, no_start_time, no_end_time, null_start_time, null_end_time
        ]

        # Act
        result = fetch_appointments(user, start_date, end_date, mock_repo)

        # Assert
        assert len(result) == 1
        assert result[0] == valid_appt

    def test_fetch_appointments_without_logger(self):
        """Test fetching appointments without providing a logger."""
        # Arrange
        user = Mock()
        user.id = 1
        user.email = "test@example.com"
        
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        
        mock_repo = Mock()
        mock_repo.list_for_user.return_value = []
        
        # Act
        result = fetch_appointments(user, start_date, end_date, mock_repo)
        
        # Assert
        assert result == []
        mock_repo.list_for_user.assert_called_once_with(user.id)

    def test_fetch_appointments_repository_exception(self):
        """Test handling of repository exceptions."""
        # Arrange
        user = Mock()
        user.id = 1
        user.email = "test@example.com"

        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)

        mock_repo = Mock()
        original_exception = Exception("Database connection failed")
        mock_repo.list_for_user.side_effect = original_exception

        mock_logger = Mock()

        # Act & Assert
        with pytest.raises(CalendarServiceException) as exc_info:
            fetch_appointments(user, start_date, end_date, mock_repo, mock_logger)

        assert "Failed to fetch appointments for user test@example.com" in str(exc_info.value)
        assert exc_info.value.__cause__ == original_exception

        mock_logger.exception.assert_called_once_with(
            f"Failed to fetch appointments for user {user.email} from {start_date} to {end_date}: Database connection failed"
        )

    def test_fetch_appointments_exception_with_add_note(self):
        """Test handling of exceptions that support add_note method."""
        # Arrange
        user = Mock()
        user.id = 1
        user.email = "test@example.com"

        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)

        mock_repo = Mock()

        # Create a real exception with add_note method
        class ExceptionWithAddNote(Exception):
            def __init__(self, message):
                super().__init__(message)
                self.add_note = Mock()

        original_exception = ExceptionWithAddNote("Database error")
        mock_repo.list_for_user.side_effect = original_exception

        mock_logger = Mock()

        # Act & Assert
        with pytest.raises(CalendarServiceException):
            fetch_appointments(user, start_date, end_date, mock_repo, mock_logger)

        original_exception.add_note.assert_called_once_with(
            f"Error in fetch_appointments for user {user.email} and range {start_date} to {end_date}"
        )

    def test_fetch_appointments_exception_without_logger(self):
        """Test handling of exceptions when no logger is provided."""
        # Arrange
        user = Mock()
        user.id = 1
        user.email = "test@example.com"

        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)

        mock_repo = Mock()
        original_exception = Exception("Database connection failed")
        mock_repo.list_for_user.side_effect = original_exception

        # Act & Assert
        with pytest.raises(CalendarServiceException) as exc_info:
            fetch_appointments(user, start_date, end_date, mock_repo)

        assert "Failed to fetch appointments for user test@example.com" in str(exc_info.value)
        assert exc_info.value.__cause__ == original_exception

    def test_fetch_appointments_date_boundary_conditions(self):
        """Test date filtering boundary conditions."""
        # Arrange
        user = Mock()
        user.id = 1
        user.email = "test@example.com"

        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 15)  # Same day

        # Appointment exactly on start date
        appt_on_start = Mock(spec=Appointment)
        appt_on_start.start_time = datetime(2024, 1, 15, 9, 0, tzinfo=timezone.utc)
        appt_on_start.end_time = datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)

        # Appointment exactly on end date
        appt_on_end = Mock(spec=Appointment)
        appt_on_end.start_time = datetime(2024, 1, 15, 14, 0, tzinfo=timezone.utc)
        appt_on_end.end_time = datetime(2024, 1, 15, 15, 0, tzinfo=timezone.utc)

        # Appointment before start date
        appt_before = Mock(spec=Appointment)
        appt_before.start_time = datetime(2024, 1, 14, 9, 0, tzinfo=timezone.utc)
        appt_before.end_time = datetime(2024, 1, 14, 10, 0, tzinfo=timezone.utc)

        # Appointment after end date
        appt_after = Mock(spec=Appointment)
        appt_after.start_time = datetime(2024, 1, 16, 9, 0, tzinfo=timezone.utc)
        appt_after.end_time = datetime(2024, 1, 16, 10, 0, tzinfo=timezone.utc)

        mock_repo = Mock()
        mock_repo.list_for_user.return_value = [appt_on_start, appt_on_end, appt_before, appt_after]

        # Act
        result = fetch_appointments(user, start_date, end_date, mock_repo)

        # Assert
        assert len(result) == 2
        assert appt_on_start in result
        assert appt_on_end in result
        assert appt_before not in result
        assert appt_after not in result


class TestStoreAppointments:
    """Test cases for store_appointments function."""

    def test_store_appointments_success(self):
        """Test successful storage of all appointments."""
        # Arrange
        appt1 = Mock(spec=Appointment)
        appt1.subject = "Meeting 1"

        appt2 = Mock(spec=Appointment)
        appt2.subject = "Meeting 2"

        appointments = [appt1, appt2]

        mock_repo = Mock()
        mock_logger = Mock()

        # Act
        result = store_appointments(appointments, mock_repo, mock_logger)

        # Assert
        assert result["stored"] == 2
        assert result["errors"] == []

        assert mock_repo.add.call_count == 2
        mock_repo.add.assert_any_call(appt1)
        mock_repo.add.assert_any_call(appt2)

    def test_store_appointments_empty_list(self):
        """Test storing an empty list of appointments."""
        # Arrange
        appointments = []
        mock_repo = Mock()
        mock_logger = Mock()

        # Act
        result = store_appointments(appointments, mock_repo, mock_logger)

        # Assert
        assert result["stored"] == 0
        assert result["errors"] == []
        mock_repo.add.assert_not_called()

    def test_store_appointments_partial_failure(self):
        """Test storing appointments with some failures."""
        # Arrange
        appt1 = Mock(spec=Appointment)
        appt1.subject = "Meeting 1"

        appt2 = Mock(spec=Appointment)
        appt2.subject = "Meeting 2"

        appt3 = Mock(spec=Appointment)
        appt3.subject = "Meeting 3"

        appointments = [appt1, appt2, appt3]

        mock_repo = Mock()
        # First appointment succeeds, second fails, third succeeds
        mock_repo.add.side_effect = [None, Exception("Storage failed"), None]

        mock_logger = Mock()

        # Act
        result = store_appointments(appointments, mock_repo, mock_logger)

        # Assert
        assert result["stored"] == 2
        assert len(result["errors"]) == 1
        assert "Failed to store appointment Meeting 2: Storage failed" in result["errors"][0]

        assert mock_repo.add.call_count == 3
        mock_logger.error.assert_called_once_with(
            "Failed to store appointment Meeting 2: Storage failed"
        )

    def test_store_appointments_all_failures(self):
        """Test storing appointments when all fail."""
        # Arrange
        appt1 = Mock(spec=Appointment)
        appt1.subject = "Meeting 1"

        appt2 = Mock(spec=Appointment)
        appt2.subject = "Meeting 2"

        appointments = [appt1, appt2]

        mock_repo = Mock()
        mock_repo.add.side_effect = [
            Exception("Storage failed 1"),
            Exception("Storage failed 2")
        ]

        mock_logger = Mock()

        # Act
        result = store_appointments(appointments, mock_repo, mock_logger)

        # Assert
        assert result["stored"] == 0
        assert len(result["errors"]) == 2
        assert "Failed to store appointment Meeting 1: Storage failed 1" in result["errors"][0]
        assert "Failed to store appointment Meeting 2: Storage failed 2" in result["errors"][1]

        assert mock_repo.add.call_count == 2
        assert mock_logger.error.call_count == 2

    def test_store_appointments_without_logger(self):
        """Test storing appointments without providing a logger."""
        # Arrange
        appt1 = Mock(spec=Appointment)
        appt1.subject = "Meeting 1"

        appointments = [appt1]

        mock_repo = Mock()

        # Act
        result = store_appointments(appointments, mock_repo)

        # Assert
        assert result["stored"] == 1
        assert result["errors"] == []
        mock_repo.add.assert_called_once_with(appt1)

    def test_store_appointments_exception_with_add_note(self):
        """Test handling of exceptions that support add_note method."""
        # Arrange
        appt1 = Mock(spec=Appointment)
        appt1.subject = "Meeting 1"

        appointments = [appt1]

        mock_repo = Mock()

        # Create a real exception with add_note method
        class ExceptionWithAddNote(Exception):
            def __init__(self, message):
                super().__init__(message)
                self.add_note = Mock()

        original_exception = ExceptionWithAddNote("Storage failed")
        mock_repo.add.side_effect = original_exception

        mock_logger = Mock()

        # Act
        result = store_appointments(appointments, mock_repo, mock_logger)

        # Assert
        assert result["stored"] == 0
        assert len(result["errors"]) == 1

        original_exception.add_note.assert_called_once_with(
            "Error in store_appointments for appointment Meeting 1"
        )

    def test_store_appointments_appointment_without_subject(self):
        """Test storing appointment that doesn't have a subject attribute."""
        # Arrange
        appt1 = Mock()
        # Remove the subject attribute to simulate missing attribute
        del appt1.subject

        appointments = [appt1]

        mock_repo = Mock()
        mock_repo.add.side_effect = Exception("Storage failed")

        mock_logger = Mock()

        # Act
        result = store_appointments(appointments, mock_repo, mock_logger)

        # Assert
        assert result["stored"] == 0
        assert len(result["errors"]) == 1
        assert "Failed to store appointment Unknown: Storage failed" in result["errors"][0]

        mock_logger.error.assert_called_once_with(
            "Failed to store appointment Unknown: Storage failed"
        )
