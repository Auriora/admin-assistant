"""
Tests for calendar_archive_service module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime, timezone
from typing import List

from core.services.calendar_archive_service import (
    prepare_appointments_for_archive,
    _prepare_appointments_for_archive_impl,
    make_appointments_immutable,
    OTEL_AVAILABLE
)
from core.models.appointment import Appointment
from core.exceptions import CalendarServiceException


class TestCalendarArchiveService:
    """Test cases for calendar archive service functions."""

    @pytest.fixture
    def sample_appointments(self):
        """Create sample appointments for testing."""
        return [
            Appointment(
                id=1,
                user_id=1,
                subject="Meeting 1",
                start_time=datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 15, 11, 0, tzinfo=timezone.utc),
                is_archived=False
            ),
            Appointment(
                id=2,
                user_id=1,
                subject="Meeting 2",
                start_time=datetime(2024, 1, 15, 14, 0, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 15, 15, 0, tzinfo=timezone.utc),
                is_archived=False
            )
        ]

    @pytest.fixture
    def overlapping_appointments(self):
        """Create overlapping appointments for testing."""
        return [
            Appointment(
                id=1,
                user_id=1,
                subject="Meeting 1",
                start_time=datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 15, 11, 0, tzinfo=timezone.utc),
                is_archived=False
            ),
            Appointment(
                id=2,
                user_id=1,
                subject="Meeting 2",
                start_time=datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 15, 11, 30, tzinfo=timezone.utc),
                is_archived=False
            )
        ]

    @pytest.fixture
    def mock_user(self):
        """Create a mock user."""
        user = Mock()
        user.id = 1
        return user

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return Mock()

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return Mock()

    def test_prepare_appointments_for_archive_success(self, sample_appointments, mock_user, mock_session, mock_logger):
        """Test successful appointment preparation."""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 15)
        
        with patch('core.services.calendar_archive_service.expand_recurring_events_range') as mock_expand, \
             patch('core.services.calendar_archive_service.merge_duplicates') as mock_merge, \
             patch('core.services.calendar_archive_service.detect_overlaps') as mock_detect:
            
            mock_expand.return_value = sample_appointments
            mock_merge.return_value = sample_appointments
            mock_detect.return_value = []  # No overlaps
            
            result = prepare_appointments_for_archive(
                sample_appointments, start_date, end_date, mock_user, mock_session, mock_logger
            )
            
            assert result["status"] == "ok"
            assert len(result["appointments"]) == 2
            assert result["conflicts"] == []
            assert result["errors"] == []
            
            # Verify appointments are marked as archived
            for appt in result["appointments"]:
                assert appt.is_archived is True

    def test_prepare_appointments_for_archive_with_overlaps(self, overlapping_appointments, mock_user, mock_session, mock_logger):
        """Test appointment preparation with overlaps detected."""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 15)
        
        with patch('core.services.calendar_archive_service.expand_recurring_events_range') as mock_expand, \
             patch('core.services.calendar_archive_service.merge_duplicates') as mock_merge, \
             patch('core.services.calendar_archive_service.detect_overlaps') as mock_detect:
            
            mock_expand.return_value = overlapping_appointments
            mock_merge.return_value = overlapping_appointments
            mock_detect.return_value = [overlapping_appointments]  # Return overlap group
            
            result = prepare_appointments_for_archive(
                overlapping_appointments, start_date, end_date, mock_user, mock_session, mock_logger
            )
            
            assert result["status"] == "overlap"
            assert len(result["appointments"]) == 0  # No appointments archived due to overlaps
            assert len(result["conflicts"]) == 1
            assert len(result["conflicts"][0]) == 2  # Two overlapping appointments
            assert result["errors"] == []

    def test_prepare_appointments_for_archive_with_invalid_times(self, mock_user, mock_session, mock_logger):
        """Test appointment preparation with invalid start/end times."""
        # Create appointment with missing end time
        invalid_appointment = Appointment(
            id=1,
            user_id=1,
            subject="Invalid Meeting",
            start_time=datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),
            end_time=None,  # Missing end time
            is_archived=False
        )
        
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 15)
        
        with patch('core.services.calendar_archive_service.expand_recurring_events_range') as mock_expand, \
             patch('core.services.calendar_archive_service.merge_duplicates') as mock_merge, \
             patch('core.services.calendar_archive_service.detect_overlaps') as mock_detect:
            
            mock_expand.return_value = [invalid_appointment]
            mock_merge.return_value = [invalid_appointment]
            mock_detect.return_value = []
            
            result = prepare_appointments_for_archive(
                [invalid_appointment], start_date, end_date, mock_user, mock_session, mock_logger
            )
            
            assert result["status"] == "ok"
            assert len(result["appointments"]) == 0  # No valid appointments
            assert len(result["errors"]) == 1
            assert "missing start or end time" in result["errors"][0]

    def test_prepare_appointments_for_archive_exception_handling(self, sample_appointments, mock_user, mock_session, mock_logger):
        """Test exception handling in appointment preparation."""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 15)
        
        with patch('core.services.calendar_archive_service.expand_recurring_events_range') as mock_expand:
            mock_expand.side_effect = Exception("Test error")
            
            with pytest.raises(CalendarServiceException, match="Archiving preparation failed"):
                prepare_appointments_for_archive(
                    sample_appointments, start_date, end_date, mock_user, mock_session, mock_logger
                )
            
            # Verify logger was called
            mock_logger.exception.assert_called_once()

    def test_make_appointments_immutable_success(self, sample_appointments, mock_session):
        """Test successful marking of appointments as immutable."""
        # Reset archived status
        for appt in sample_appointments:
            appt.is_archived = False
        
        make_appointments_immutable(sample_appointments, mock_session)
        
        # Verify all appointments are marked as archived
        for appt in sample_appointments:
            assert appt.is_archived is True
        
        # Verify session commit was called
        mock_session.commit.assert_called_once()

    def test_make_appointments_immutable_exception_handling(self, sample_appointments, mock_session):
        """Test exception handling in make_appointments_immutable."""
        mock_session.commit.side_effect = Exception("Database error")
        
        with pytest.raises(Exception, match="Database error"):
            make_appointments_immutable(sample_appointments, mock_session)

    def test_prepare_appointments_empty_list(self, mock_user, mock_session, mock_logger):
        """Test preparation with empty appointment list."""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 15)
        
        result = prepare_appointments_for_archive(
            [], start_date, end_date, mock_user, mock_session, mock_logger
        )
        
        assert result["status"] == "ok"
        assert result["appointments"] == []
        assert result["conflicts"] == []
        assert result["errors"] == []

    def test_make_appointments_immutable_empty_list(self, mock_session):
        """Test make_appointments_immutable with empty list."""
        make_appointments_immutable([], mock_session)
        
        # Should still commit
        mock_session.commit.assert_called_once()

    @patch('core.services.calendar_archive_service.OTEL_AVAILABLE', False)
    def test_prepare_appointments_without_otel(self, sample_appointments, mock_user, mock_session, mock_logger):
        """Test appointment preparation when OpenTelemetry is not available."""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 15)
        
        with patch('core.services.calendar_archive_service.expand_recurring_events_range') as mock_expand, \
             patch('core.services.calendar_archive_service.merge_duplicates') as mock_merge, \
             patch('core.services.calendar_archive_service.detect_overlaps') as mock_detect:
            
            mock_expand.return_value = sample_appointments
            mock_merge.return_value = sample_appointments
            mock_detect.return_value = []
            
            result = prepare_appointments_for_archive(
                sample_appointments, start_date, end_date, mock_user, mock_session, mock_logger
            )
            
            assert result["status"] == "ok"
            assert len(result["appointments"]) == 2

    @patch('core.services.calendar_archive_service.OTEL_AVAILABLE', False)
    def test_make_appointments_immutable_without_otel(self, sample_appointments, mock_session):
        """Test make_appointments_immutable when OpenTelemetry is not available."""
        for appt in sample_appointments:
            appt.is_archived = False
        
        make_appointments_immutable(sample_appointments, mock_session)
        
        for appt in sample_appointments:
            assert appt.is_archived is True
        
        mock_session.commit.assert_called_once()

    def test_prepare_appointments_with_non_appointment_objects(self, mock_user, mock_session, mock_logger):
        """Test preparation with non-Appointment objects in the list."""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 15)

        # Mix of valid appointments and non-appointment objects
        mixed_list = [
            Appointment(
                id=1,
                user_id=1,
                subject="Valid Meeting",
                start_time=datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 15, 11, 0, tzinfo=timezone.utc),
                is_archived=False
            ),
            "not an appointment",  # This should be skipped
            Mock(),  # This should be skipped
        ]

        with patch('core.services.calendar_archive_service.expand_recurring_events_range') as mock_expand, \
             patch('core.services.calendar_archive_service.merge_duplicates') as mock_merge, \
             patch('core.services.calendar_archive_service.detect_overlaps') as mock_detect:

            mock_expand.return_value = mixed_list
            mock_merge.return_value = mixed_list
            mock_detect.return_value = []

            result = prepare_appointments_for_archive(
                mixed_list, start_date, end_date, mock_user, mock_session, mock_logger
            )

            assert result["status"] == "ok"
            assert len(result["appointments"]) == 1  # Only the valid appointment
            assert result["appointments"][0].subject == "Valid Meeting"

    def test_prepare_appointments_with_user_none(self, sample_appointments, mock_session, mock_logger):
        """Test preparation with user=None."""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 15)

        with patch('core.services.calendar_archive_service.expand_recurring_events_range') as mock_expand, \
             patch('core.services.calendar_archive_service.merge_duplicates') as mock_merge, \
             patch('core.services.calendar_archive_service.detect_overlaps') as mock_detect:

            mock_expand.return_value = sample_appointments
            mock_merge.return_value = sample_appointments
            mock_detect.return_value = []

            result = prepare_appointments_for_archive(
                sample_appointments, start_date, end_date, None, mock_session, mock_logger
            )

            assert result["status"] == "ok"
            assert len(result["appointments"]) == 2

    def test_prepare_appointments_with_logger_none(self, sample_appointments, mock_user, mock_session):
        """Test preparation with logger=None."""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 15)

        with patch('core.services.calendar_archive_service.expand_recurring_events_range') as mock_expand:
            mock_expand.side_effect = Exception("Test error")

            with pytest.raises(CalendarServiceException):
                prepare_appointments_for_archive(
                    sample_appointments, start_date, end_date, mock_user, mock_session, None
                )

    @patch('core.services.calendar_archive_service.OTEL_AVAILABLE', True)
    @patch('core.services.calendar_archive_service.tracer')
    def test_prepare_appointments_with_otel_span(self, mock_tracer, sample_appointments, mock_user, mock_session, mock_logger):
        """Test appointment preparation with OpenTelemetry span."""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 15)

        # Mock the span context manager
        mock_span = Mock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_tracer.start_as_current_span.return_value.__exit__.return_value = None

        with patch('core.services.calendar_archive_service.expand_recurring_events_range') as mock_expand, \
             patch('core.services.calendar_archive_service.merge_duplicates') as mock_merge, \
             patch('core.services.calendar_archive_service.detect_overlaps') as mock_detect:

            mock_expand.return_value = sample_appointments
            mock_merge.return_value = sample_appointments
            mock_detect.return_value = []

            result = prepare_appointments_for_archive(
                sample_appointments, start_date, end_date, mock_user, mock_session, mock_logger
            )

            assert result["status"] == "ok"
            # Verify span was started
            mock_tracer.start_as_current_span.assert_called_once()
            # Verify span attributes were set
            mock_span.set_attributes.assert_called()
            mock_span.set_status.assert_called()

    @patch('core.services.calendar_archive_service.OTEL_AVAILABLE', True)
    @patch('core.services.calendar_archive_service.tracer')
    def test_make_appointments_immutable_with_otel_span(self, mock_tracer, sample_appointments, mock_session):
        """Test make_appointments_immutable with OpenTelemetry span."""
        # Mock the span context manager
        mock_span = Mock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_tracer.start_as_current_span.return_value.__exit__.return_value = None

        for appt in sample_appointments:
            appt.is_archived = False

        make_appointments_immutable(sample_appointments, mock_session)

        # Verify span was started
        mock_tracer.start_as_current_span.assert_called_once()
        # Verify span attributes were set
        mock_span.set_attributes.assert_called()
        mock_span.set_status.assert_called()

        for appt in sample_appointments:
            assert appt.is_archived is True

    @patch('core.services.calendar_archive_service.OTEL_AVAILABLE', True)
    @patch('core.services.calendar_archive_service.tracer')
    def test_make_appointments_immutable_with_otel_exception(self, mock_tracer, sample_appointments, mock_session):
        """Test make_appointments_immutable exception handling with OpenTelemetry."""
        # Mock the span context manager
        mock_span = Mock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_tracer.start_as_current_span.return_value.__exit__.return_value = None

        mock_session.commit.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            make_appointments_immutable(sample_appointments, mock_session)

        # Verify error span attributes were set
        mock_span.set_attributes.assert_called()
        mock_span.set_status.assert_called()

    def test_prepare_appointments_for_archive_with_allow_overlaps_true(self, overlapping_appointments, mock_user, mock_session, mock_logger):
        """Test appointment preparation with allow_overlaps=True."""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 15)

        with patch('core.services.calendar_archive_service.expand_recurring_events_range') as mock_expand, \
             patch('core.services.calendar_archive_service.merge_duplicates') as mock_merge, \
             patch('core.services.calendar_archive_service.detect_overlaps') as mock_detect:

            mock_expand.return_value = overlapping_appointments
            mock_merge.return_value = overlapping_appointments
            mock_detect.return_value = [overlapping_appointments]  # Return overlap group

            result = prepare_appointments_for_archive(
                overlapping_appointments, start_date, end_date, mock_user, mock_session, mock_logger, allow_overlaps=True
            )

            assert result["status"] == "ok_with_overlaps"
            assert len(result["appointments"]) == 2  # Both overlapping appointments archived
            assert len(result["conflicts"]) == 1  # Conflicts still reported for transparency
            assert len(result["conflicts"][0]) == 2  # Two overlapping appointments in conflict
            assert result["errors"] == []

            # Verify all appointments are marked as archived
            for appt in result["appointments"]:
                assert appt.is_archived is True

    def test_prepare_appointments_for_archive_with_allow_overlaps_false(self, overlapping_appointments, mock_user, mock_session, mock_logger):
        """Test appointment preparation with allow_overlaps=False (default behavior)."""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 15)

        with patch('core.services.calendar_archive_service.expand_recurring_events_range') as mock_expand, \
             patch('core.services.calendar_archive_service.merge_duplicates') as mock_merge, \
             patch('core.services.calendar_archive_service.detect_overlaps') as mock_detect:

            mock_expand.return_value = overlapping_appointments
            mock_merge.return_value = overlapping_appointments
            mock_detect.return_value = [overlapping_appointments]  # Return overlap group

            result = prepare_appointments_for_archive(
                overlapping_appointments, start_date, end_date, mock_user, mock_session, mock_logger, allow_overlaps=False
            )

            assert result["status"] == "overlap"
            assert len(result["appointments"]) == 0  # No appointments archived due to overlaps
            assert len(result["conflicts"]) == 1
            assert len(result["conflicts"][0]) == 2  # Two overlapping appointments
            assert result["errors"] == []

    def test_prepare_appointments_for_archive_allow_overlaps_default_false(self, overlapping_appointments, mock_user, mock_session, mock_logger):
        """Test that allow_overlaps defaults to False for backward compatibility."""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 15)

        with patch('core.services.calendar_archive_service.expand_recurring_events_range') as mock_expand, \
             patch('core.services.calendar_archive_service.merge_duplicates') as mock_merge, \
             patch('core.services.calendar_archive_service.detect_overlaps') as mock_detect:

            mock_expand.return_value = overlapping_appointments
            mock_merge.return_value = overlapping_appointments
            mock_detect.return_value = [overlapping_appointments]  # Return overlap group

            # Call without allow_overlaps parameter (should default to False)
            result = prepare_appointments_for_archive(
                overlapping_appointments, start_date, end_date, mock_user, mock_session, mock_logger
            )

            assert result["status"] == "overlap"
            assert len(result["appointments"]) == 0  # No appointments archived due to overlaps

    def test_prepare_appointments_for_archive_mixed_overlaps_and_valid(self, mock_user, mock_session, mock_logger):
        """Test appointment preparation with mix of overlapping and non-overlapping appointments when allow_overlaps=True."""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 15)

        # Create overlapping appointments
        overlapping_appt1 = Appointment(
            id=1,
            user_id=1,
            subject="Overlapping Meeting 1",
            start_time=datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 15, 11, 0, tzinfo=timezone.utc),
            is_archived=False
        )
        overlapping_appt2 = Appointment(
            id=2,
            user_id=1,
            subject="Overlapping Meeting 2",
            start_time=datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 15, 11, 30, tzinfo=timezone.utc),
            is_archived=False
        )

        # Create non-overlapping appointment
        standalone_appt = Appointment(
            id=3,
            user_id=1,
            subject="Standalone Meeting",
            start_time=datetime(2024, 1, 15, 14, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 15, 15, 0, tzinfo=timezone.utc),
            is_archived=False
        )

        all_appointments = [overlapping_appt1, overlapping_appt2, standalone_appt]

        with patch('core.services.calendar_archive_service.expand_recurring_events_range') as mock_expand, \
             patch('core.services.calendar_archive_service.merge_duplicates') as mock_merge, \
             patch('core.services.calendar_archive_service.detect_overlaps') as mock_detect:

            mock_expand.return_value = all_appointments
            mock_merge.return_value = all_appointments
            mock_detect.return_value = [[overlapping_appt1, overlapping_appt2]]  # Only the overlapping ones

            result = prepare_appointments_for_archive(
                all_appointments, start_date, end_date, mock_user, mock_session, mock_logger, allow_overlaps=True
            )

            assert result["status"] == "ok_with_overlaps"
            assert len(result["appointments"]) == 3  # All appointments archived
            assert len(result["conflicts"]) == 1  # One overlap group reported
            assert len(result["conflicts"][0]) == 2  # Two overlapping appointments
            assert result["errors"] == []

            # Verify all appointments are marked as archived
            for appt in result["appointments"]:
                assert appt.is_archived is True

    def test_prepare_appointments_for_archive_no_overlaps_with_allow_overlaps_true(self, sample_appointments, mock_user, mock_session, mock_logger):
        """Test appointment preparation with no overlaps when allow_overlaps=True."""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 15)

        with patch('core.services.calendar_archive_service.expand_recurring_events_range') as mock_expand, \
             patch('core.services.calendar_archive_service.merge_duplicates') as mock_merge, \
             patch('core.services.calendar_archive_service.detect_overlaps') as mock_detect:

            mock_expand.return_value = sample_appointments
            mock_merge.return_value = sample_appointments
            mock_detect.return_value = []  # No overlaps

            result = prepare_appointments_for_archive(
                sample_appointments, start_date, end_date, mock_user, mock_session, mock_logger, allow_overlaps=True
            )

            assert result["status"] == "ok"  # Should be "ok", not "ok_with_overlaps" when no overlaps
            assert len(result["appointments"]) == 2
            assert result["conflicts"] == []
            assert result["errors"] == []

    def test_prepare_appointments_for_archive_logging_with_allow_overlaps(self, overlapping_appointments, mock_user, mock_session, mock_logger):
        """Test that appropriate logging occurs when allow_overlaps=True."""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 15)

        with patch('core.services.calendar_archive_service.expand_recurring_events_range') as mock_expand, \
             patch('core.services.calendar_archive_service.merge_duplicates') as mock_merge, \
             patch('core.services.calendar_archive_service.detect_overlaps') as mock_detect:

            mock_expand.return_value = overlapping_appointments
            mock_merge.return_value = overlapping_appointments
            mock_detect.return_value = [overlapping_appointments]  # Return overlap group

            prepare_appointments_for_archive(
                overlapping_appointments, start_date, end_date, mock_user, mock_session, mock_logger, allow_overlaps=True
            )

            # Verify appropriate logging calls were made
            mock_logger.info.assert_any_call(
                "Found 1 overlap groups but proceeding with archiving due to allow_overlaps=True"
            )
            # Should also log the final archiving summary
            assert any("Archive preparation complete" in str(call) for call in mock_logger.info.call_args_list)
