"""
Unit tests for time utility

Tests the time utility functions for timezone and date handling.
"""

import pytest
import pytz
from datetime import datetime
from core.utilities.time_utility import to_utc


class TestTimeUtility:
    """Test suite for time utility functions"""

    def test_to_utc_naive_datetime(self):
        """Test converting naive datetime to UTC"""
        # Arrange
        naive_dt = datetime(2024, 1, 1, 12, 0, 0)

        # Act
        result = to_utc(naive_dt)

        # Assert
        assert isinstance(result, datetime)
        assert result.tzinfo == pytz.UTC
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 12
        assert result.minute == 0

    def test_to_utc_timezone_aware_datetime(self):
        """Test converting timezone-aware datetime to UTC"""
        # Arrange
        eastern = pytz.timezone('US/Eastern')
        eastern_dt = eastern.localize(datetime(2024, 1, 1, 12, 0, 0))

        # Act
        result = to_utc(eastern_dt)

        # Assert
        assert isinstance(result, datetime)
        assert result.tzinfo == pytz.UTC
        # Eastern time in winter is UTC-5, so 12:00 EST = 17:00 UTC
        assert result.hour == 17

    def test_to_utc_already_utc_datetime(self):
        """Test converting UTC datetime (should remain unchanged)"""
        # Arrange
        utc_dt = pytz.UTC.localize(datetime(2024, 1, 1, 12, 0, 0))

        # Act
        result = to_utc(utc_dt)

        # Assert
        assert isinstance(result, datetime)
        assert result.tzinfo == pytz.UTC
        assert result == utc_dt
