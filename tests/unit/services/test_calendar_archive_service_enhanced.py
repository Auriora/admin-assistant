"""
Enhanced unit tests for CalendarArchiveService.
"""
import pytest
from datetime import datetime, UTC, date
from unittest.mock import MagicMock, patch
from core.models.appointment import Appointment
from core.services.calendar_archive_service import (
    prepare_appointments_for_archive,
    make_appointments_immutable
)
from core.exceptions import CalendarServiceException


@pytest.mark.unit
class TestCalendarArchiveService:
    """Test cases for CalendarArchiveService functions."""

    def test_prepare_appointments_for_archive_success(self, test_user, db_session):
        """Test successful preparation of appointments for archiving."""
        appointments = [
            Appointment(
                user_id=test_user.id,
                subject="Meeting 1",
                start_time=datetime(2025, 6, 1, 9, 0, tzinfo=UTC),
                end_time=datetime(2025, 6, 1, 10, 0, tzinfo=UTC),
                calendar_id="test-calendar"
            ),
            Appointment(
                user_id=test_user.id,
                subject="Meeting 2",
                start_time=datetime(2025, 6, 1, 11, 0, tzinfo=UTC),
                end_time=datetime(2025, 6, 1, 12, 0, tzinfo=UTC),
                calendar_id="test-calendar"
            )
        ]
        
        start_date = date(2025, 6, 1)
        end_date = date(2025, 6, 1)
        
        result = prepare_appointments_for_archive(
            appointments=appointments,
            start_date=start_date,
            end_date=end_date,
            user=test_user,
            session=db_session
        )
        
        assert result["status"] == "ok"
        assert len(result["appointments"]) == 2
        assert len(result["conflicts"]) == 0
        assert len(result["errors"]) == 0
        
        # Check that appointments are marked as archived
        for appt in result["appointments"]:
            assert appt.is_archived is True

    def test_prepare_appointments_with_overlaps(self, test_user, db_session):
        """Test preparation with overlapping appointments."""
        appointments = [
            Appointment(
                user_id=test_user.id,
                subject="Meeting 1",
                start_time=datetime(2025, 6, 1, 9, 0, tzinfo=UTC),
                end_time=datetime(2025, 6, 1, 10, 0, tzinfo=UTC),
                calendar_id="test-calendar"
            ),
            Appointment(
                user_id=test_user.id,
                subject="Overlapping Meeting",
                start_time=datetime(2025, 6, 1, 9, 30, tzinfo=UTC),
                end_time=datetime(2025, 6, 1, 10, 30, tzinfo=UTC),
                calendar_id="test-calendar"
            )
        ]
        
        start_date = date(2025, 6, 1)
        end_date = date(2025, 6, 1)
        
        result = prepare_appointments_for_archive(
            appointments=appointments,
            start_date=start_date,
            end_date=end_date,
            user=test_user,
            session=db_session
        )
        
        assert result["status"] == "overlap"
        assert len(result["appointments"]) == 0  # Overlapping appointments are excluded
        assert len(result["conflicts"]) > 0
        assert len(result["errors"]) == 0

    def test_prepare_appointments_with_invalid_times(self, test_user, db_session):
        """Test preparation with appointments having invalid times."""
        # Create appointment with missing end time
        appointment = Appointment(
            user_id=test_user.id,
            subject="Invalid Meeting",
            start_time=datetime(2025, 6, 1, 9, 0, tzinfo=UTC),
            end_time=None,  # Invalid
            calendar_id="test-calendar"
        )
        
        start_date = date(2025, 6, 1)
        end_date = date(2025, 6, 1)
        
        result = prepare_appointments_for_archive(
            appointments=[appointment],
            start_date=start_date,
            end_date=end_date,
            user=test_user,
            session=db_session
        )
        
        assert result["status"] == "ok"
        assert len(result["appointments"]) == 0
        assert len(result["errors"]) == 1
        assert "missing start or end time" in result["errors"][0]

    @patch('core.services.calendar_archive_service.expand_recurring_events')
    @patch('core.services.calendar_archive_service.detect_overlaps')
    def test_prepare_appointments_with_mocked_utilities(
        self, mock_detect_overlaps, mock_expand_recurring, test_user, db_session
    ):
        """Test preparation with mocked utility functions."""
        appointments = [
            Appointment(
                user_id=test_user.id,
                subject="Meeting 1",
                start_time=datetime(2025, 6, 1, 9, 0, tzinfo=UTC),
                end_time=datetime(2025, 6, 1, 10, 0, tzinfo=UTC),
                calendar_id="test-calendar"
            )
        ]
        
        # Mock the utility functions
        mock_expand_recurring.return_value = appointments
        mock_detect_overlaps.return_value = []
        
        start_date = date(2025, 6, 1)
        end_date = date(2025, 6, 1)
        
        result = prepare_appointments_for_archive(
            appointments=appointments,
            start_date=start_date,
            end_date=end_date,
            user=test_user,
            session=db_session
        )
        
        assert result["status"] == "ok"
        assert len(result["appointments"]) == 1
        mock_expand_recurring.assert_called_once()
        mock_detect_overlaps.assert_called_once()

    def test_prepare_appointments_exception_handling(self, test_user, db_session):
        """Test exception handling in prepare_appointments_for_archive."""
        # Pass invalid data to trigger an exception
        with pytest.raises(CalendarServiceException):
            prepare_appointments_for_archive(
                appointments=None,  # Invalid
                start_date=date(2025, 6, 1),
                end_date=date(2025, 6, 1),
                user=test_user,
                session=db_session
            )

    def test_make_appointments_immutable(self, test_user, db_session):
        """Test making appointments immutable."""
        appointments = [
            Appointment(
                user_id=test_user.id,
                subject="Meeting 1",
                start_time=datetime(2025, 6, 1, 9, 0, tzinfo=UTC),
                end_time=datetime(2025, 6, 1, 10, 0, tzinfo=UTC),
                calendar_id="test-calendar",
                is_archived=False
            ),
            Appointment(
                user_id=test_user.id,
                subject="Meeting 2",
                start_time=datetime(2025, 6, 1, 11, 0, tzinfo=UTC),
                end_time=datetime(2025, 6, 1, 12, 0, tzinfo=UTC),
                calendar_id="test-calendar",
                is_archived=False
            )
        ]
        
        # Add appointments to session
        for appt in appointments:
            db_session.add(appt)
        db_session.commit()
        
        make_appointments_immutable(appointments, db_session)
        
        # Verify all appointments are marked as archived
        for appt in appointments:
            assert appt.is_archived is True

    def test_prepare_appointments_with_timezone_conversion(self, test_user, db_session):
        """Test that appointments are properly converted to UTC."""
        from datetime import timezone, timedelta
        
        # Create appointment with non-UTC timezone
        est = timezone(timedelta(hours=-5))
        appointment = Appointment(
            user_id=test_user.id,
            subject="EST Meeting",
            start_time=datetime(2025, 6, 1, 9, 0, tzinfo=est),
            end_time=datetime(2025, 6, 1, 10, 0, tzinfo=est),
            calendar_id="test-calendar"
        )
        
        start_date = date(2025, 6, 1)
        end_date = date(2025, 6, 1)
        
        result = prepare_appointments_for_archive(
            appointments=[appointment],
            start_date=start_date,
            end_date=end_date,
            user=test_user,
            session=db_session
        )
        
        assert result["status"] == "ok"
        assert len(result["appointments"]) == 1
        
        archived_appt = result["appointments"][0]
        # Times should be converted to UTC
        assert archived_appt.start_time.tzinfo == UTC
        assert archived_appt.end_time.tzinfo == UTC

    def test_prepare_appointments_empty_list(self, test_user, db_session):
        """Test preparation with empty appointment list."""
        result = prepare_appointments_for_archive(
            appointments=[],
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 1),
            user=test_user,
            session=db_session
        )
        
        assert result["status"] == "ok"
        assert len(result["appointments"]) == 0
        assert len(result["conflicts"]) == 0
        assert len(result["errors"]) == 0

    def test_prepare_appointments_with_logger(self, test_user, db_session):
        """Test preparation with logger provided."""
        import logging
        logger = logging.getLogger(__name__)
        
        appointments = [
            Appointment(
                user_id=test_user.id,
                subject="Meeting 1",
                start_time=datetime(2025, 6, 1, 9, 0, tzinfo=UTC),
                end_time=datetime(2025, 6, 1, 10, 0, tzinfo=UTC),
                calendar_id="test-calendar"
            )
        ]
        
        result = prepare_appointments_for_archive(
            appointments=appointments,
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 1),
            user=test_user,
            session=db_session,
            logger=logger
        )
        
        assert result["status"] == "ok"
        assert len(result["appointments"]) == 1
