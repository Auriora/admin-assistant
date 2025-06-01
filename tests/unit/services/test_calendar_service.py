"""
Tests for CalendarService class.
"""

import pytest
from unittest.mock import Mock, MagicMock

from core.services.calendar_service import CalendarService
from core.models.calendar import Calendar
from core.repositories.calendar_repository_base import BaseCalendarRepository

class TestCalendarService:
    """Test cases for CalendarService class."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock calendar repository."""
        return Mock(spec=BaseCalendarRepository)

    @pytest.fixture
    def calendar_service(self, mock_repository):
        """Create a CalendarService instance with mock repository."""
        return CalendarService(mock_repository)

    @pytest.fixture
    def sample_calendar(self):
        """Create a sample calendar for testing."""
        return Calendar(
            id=1,
            name="Test Calendar",
            user_id=1,
            description="A test calendar"
        )

    def test_init_with_repository(self, mock_repository):
        """Test CalendarService initialization with repository."""
        service = CalendarService(mock_repository)
        assert service.repository == mock_repository

    def test_get_by_id_success(self, calendar_service, mock_repository, sample_calendar):
        """Test successful calendar retrieval by ID."""
        # Arrange
        mock_repository.get_by_id.return_value = sample_calendar

        # Act
        result = calendar_service.get_by_id(1)

        # Assert
        assert result == sample_calendar
        mock_repository.get_by_id.assert_called_once_with(1)

    def test_get_by_id_not_found(self, calendar_service, mock_repository):
        """Test calendar retrieval when calendar not found."""
        # Arrange
        mock_repository.get_by_id.return_value = None

        # Act
        result = calendar_service.get_by_id(999)

        # Assert
        assert result is None
        mock_repository.get_by_id.assert_called_once_with(999)

    def test_create_valid_calendar(self, calendar_service, mock_repository, sample_calendar):
        """Test successful calendar creation."""
        # Act
        calendar_service.create(sample_calendar)

        # Assert
        mock_repository.add.assert_called_once_with(sample_calendar)

    def test_create_invalid_calendar_empty_name(self, calendar_service, mock_repository):
        """Test calendar creation with empty name raises ValueError."""
        # Arrange
        invalid_calendar = Calendar(id=1, name="", user_id=1)

        # Act & Assert
        with pytest.raises(ValueError, match="Calendar name is required"):
            calendar_service.create(invalid_calendar)

        # Verify repository was not called
        mock_repository.add.assert_not_called()

    def test_create_invalid_calendar_whitespace_name(self, calendar_service, mock_repository):
        """Test calendar creation with whitespace-only name raises ValueError."""
        # Arrange
        invalid_calendar = Calendar(id=1, name="   ", user_id=1)

        # Act & Assert
        with pytest.raises(ValueError, match="Calendar name is required"):
            calendar_service.create(invalid_calendar)

        # Verify repository was not called
        mock_repository.add.assert_not_called()

    def test_create_invalid_calendar_none_name(self, calendar_service, mock_repository):
        """Test calendar creation with None name raises ValueError."""
        # Arrange
        invalid_calendar = Calendar(id=1, name=None, user_id=1)

        # Act & Assert
        with pytest.raises(ValueError, match="Calendar name is required"):
            calendar_service.create(invalid_calendar)

        # Verify repository was not called
        mock_repository.add.assert_not_called()

    def test_list_calendars(self, calendar_service, mock_repository):
        """Test listing all calendars."""
        # Arrange
        calendars = [
            Calendar(id=1, name="Calendar 1", user_id=1),
            Calendar(id=2, name="Calendar 2", user_id=1)
        ]
        mock_repository.list.return_value = calendars

        # Act
        result = calendar_service.list()

        # Assert
        assert result == calendars
        mock_repository.list.assert_called_once()

    def test_list_calendars_empty(self, calendar_service, mock_repository):
        """Test listing calendars when none exist."""
        # Arrange
        mock_repository.list.return_value = []

        # Act
        result = calendar_service.list()

        # Assert
        assert result == []
        mock_repository.list.assert_called_once()

    def test_update_valid_calendar(self, calendar_service, mock_repository, sample_calendar):
        """Test successful calendar update."""
        # Act
        calendar_service.update(sample_calendar)

        # Assert
        mock_repository.update.assert_called_once_with(sample_calendar)

    def test_update_invalid_calendar(self, calendar_service, mock_repository):
        """Test calendar update with invalid data raises ValueError."""
        # Arrange
        invalid_calendar = Calendar(id=1, name="", user_id=1)

        # Act & Assert
        with pytest.raises(ValueError, match="Calendar name is required"):
            calendar_service.update(invalid_calendar)

        # Verify repository was not called
        mock_repository.update.assert_not_called()

    def test_delete_calendar(self, calendar_service, mock_repository):
        """Test successful calendar deletion."""
        # Act
        calendar_service.delete(1)

        # Assert
        mock_repository.delete.assert_called_once_with(1)

    def test_validate_valid_calendar(self, calendar_service, sample_calendar):
        """Test validation of valid calendar."""
        # Act & Assert - should not raise any exception
        calendar_service.validate(sample_calendar)

    def test_validate_calendar_without_name_attribute(self, calendar_service):
        """Test validation of calendar without name attribute."""
        # Arrange
        calendar_without_name = Mock()
        del calendar_without_name.name  # Remove name attribute

        # Act & Assert
        with pytest.raises(ValueError, match="Calendar name is required"):
            calendar_service.validate(calendar_without_name)
        