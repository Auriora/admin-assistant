"""
Tests for AuditContext sanitization integration.
"""

import datetime
import pytest
from unittest.mock import Mock, MagicMock, patch

from core.utilities.audit_logging_utility import AuditContext
from core.services.audit_log_service import AuditLogService


class TestAuditContextSanitization:
    """Test that AuditContext properly sanitizes data before storing."""

    @pytest.fixture
    def mock_audit_service(self):
        """Create a mock audit service."""
        service = Mock(spec=AuditLogService)
        service.log_operation.return_value = Mock()
        return service

    def test_add_detail_with_appointment_object(self, mock_audit_service):
        """Test that add_detail sanitizes Appointment objects."""
        # Create mock appointment
        appointment = Mock()
        appointment.__class__.__name__ = "Appointment"
        appointment.__table__ = Mock()
        appointment.__table__.name = "appointments"
        appointment.id = 123
        appointment.subject = "Test Meeting"
        appointment.start_time = datetime.datetime(2024, 1, 15, 10, 0)
        appointment.end_time = datetime.datetime(2024, 1, 15, 11, 0)

        with AuditContext(
            audit_service=mock_audit_service,
            user_id=1,
            action_type="test",
            operation="test_operation"
        ) as audit_ctx:
            # This should not raise a JSON serialization error
            audit_ctx.add_detail("appointment", appointment)
            
            # Verify the appointment was sanitized
            assert "appointment" in audit_ctx.details
            sanitized_appointment = audit_ctx.details["appointment"]
            assert sanitized_appointment["_model_type"] == "Appointment"
            assert sanitized_appointment["id"] == 123
            assert sanitized_appointment["subject"] == "Test Meeting"
            assert sanitized_appointment["start_time"] == "2024-01-15T10:00:00"

    def test_add_detail_with_conflicts_list(self, mock_audit_service):
        """Test that add_detail sanitizes lists of Appointment objects (the original issue)."""
        # Create mock appointments
        appointment1 = Mock()
        appointment1.__class__.__name__ = "Appointment"
        appointment1.__table__ = Mock()
        appointment1.__table__.name = "appointments"
        appointment1.id = 1
        appointment1.subject = "Meeting 1"

        appointment2 = Mock()
        appointment2.__class__.__name__ = "Appointment"
        appointment2.__table__ = Mock()
        appointment2.__table__.name = "appointments"
        appointment2.id = 2
        appointment2.subject = "Meeting 2"

        conflicts = [appointment1, appointment2]

        with AuditContext(
            audit_service=mock_audit_service,
            user_id=1,
            action_type="archive",
            operation="calendar_archive"
        ) as audit_ctx:
            # This was causing the original JSON serialization error
            audit_ctx.add_detail("conflicts", conflicts)
            
            # Verify the conflicts were sanitized
            assert "conflicts" in audit_ctx.details
            sanitized_conflicts = audit_ctx.details["conflicts"]
            assert len(sanitized_conflicts) == 2
            assert sanitized_conflicts[0]["_model_type"] == "Appointment"
            assert sanitized_conflicts[0]["id"] == 1
            assert sanitized_conflicts[0]["subject"] == "Meeting 1"
            assert sanitized_conflicts[1]["_model_type"] == "Appointment"
            assert sanitized_conflicts[1]["id"] == 2
            assert sanitized_conflicts[1]["subject"] == "Meeting 2"

    def test_add_detail_with_complex_result_dict(self, mock_audit_service):
        """Test sanitizing complex result dictionaries like those from archive operations."""
        # Create mock appointments for conflicts
        appointment = Mock()
        appointment.__class__.__name__ = "Appointment"
        appointment.__table__ = Mock()
        appointment.__table__.name = "appointments"
        appointment.id = 123
        appointment.subject = "Conflicted Meeting"

        # Create the complex result structure that was causing issues
        result = {
            "status": "success",
            "archive_type": "general",
            "correlation_id": "test-123",
            "total_appointments_fetched": 10,
            "appointments_archived": 8,
            "conflicts": [appointment],  # This was the problematic field
            "processing_stats": {
                "overlap_groups": 1,
                "overlapping_appointments": 2
            },
            "operation_duration": 1.5
        }

        with AuditContext(
            audit_service=mock_audit_service,
            user_id=1,
            action_type="archive",
            operation="calendar_archive"
        ) as audit_ctx:
            # This should not raise a JSON serialization error
            audit_ctx.add_detail("final_result", result)
            
            # Verify the result was sanitized
            sanitized_result = audit_ctx.details["final_result"]
            assert sanitized_result["status"] == "success"
            assert sanitized_result["archive_type"] == "general"
            assert sanitized_result["total_appointments_fetched"] == 10
            assert sanitized_result["appointments_archived"] == 8
            assert sanitized_result["operation_duration"] == 1.5
            
            # Verify conflicts were sanitized
            assert len(sanitized_result["conflicts"]) == 1
            sanitized_appointment = sanitized_result["conflicts"][0]
            assert sanitized_appointment["_model_type"] == "Appointment"
            assert sanitized_appointment["id"] == 123
            assert sanitized_appointment["subject"] == "Conflicted Meeting"

    def test_set_request_data_with_model_objects(self, mock_audit_service):
        """Test that set_request_data sanitizes model objects."""
        user = Mock()
        user.__class__.__name__ = "User"
        user.__table__ = Mock()
        user.__table__.name = "users"
        user.id = 456
        user.email = "test@example.com"

        request_data = {
            "user": user,
            "start_date": datetime.date(2024, 1, 15),
            "operation": "test"
        }

        with AuditContext(
            audit_service=mock_audit_service,
            user_id=1,
            action_type="test",
            operation="test_operation"
        ) as audit_ctx:
            audit_ctx.set_request_data(request_data)
            
            # Verify sanitization
            sanitized_data = audit_ctx.request_data
            assert sanitized_data["operation"] == "test"
            assert sanitized_data["start_date"] == "2024-01-15"
            assert sanitized_data["user"]["_model_type"] == "User"
            assert sanitized_data["user"]["id"] == 456
            assert sanitized_data["user"]["email"] == "test@example.com"

    def test_set_response_data_with_model_objects(self, mock_audit_service):
        """Test that set_response_data sanitizes model objects."""
        appointment = Mock()
        appointment.__class__.__name__ = "Appointment"
        appointment.__table__ = Mock()
        appointment.__table__.name = "appointments"
        appointment.id = 789
        appointment.subject = "Response Meeting"

        response_data = {
            "created_appointment": appointment,
            "success": True,
            "timestamp": datetime.datetime(2024, 1, 15, 10, 0)
        }

        with AuditContext(
            audit_service=mock_audit_service,
            user_id=1,
            action_type="create",
            operation="create_appointment"
        ) as audit_ctx:
            audit_ctx.set_response_data(response_data)
            
            # Verify sanitization
            sanitized_data = audit_ctx.response_data
            assert sanitized_data["success"] is True
            assert sanitized_data["timestamp"] == "2024-01-15T10:00:00"
            assert sanitized_data["created_appointment"]["_model_type"] == "Appointment"
            assert sanitized_data["created_appointment"]["id"] == 789
            assert sanitized_data["created_appointment"]["subject"] == "Response Meeting"

    def test_sanitization_error_handling(self, mock_audit_service):
        """Test that sanitization errors are handled gracefully."""
        # Create an object that will cause sanitization to fail
        class ProblematicObject:
            def __getattribute__(self, name):
                raise Exception("Cannot access attributes")

        problematic_obj = ProblematicObject()

        with AuditContext(
            audit_service=mock_audit_service,
            user_id=1,
            action_type="test",
            operation="test_operation"
        ) as audit_ctx:
            # This should not raise an exception, but should log a warning
            with patch('logging.getLogger') as mock_logger:
                audit_ctx.add_detail("problematic", problematic_obj)

                # Should have logged a warning
                mock_logger.return_value.warning.assert_called()

                # Should have stored a safe fallback
                assert "problematic" in audit_ctx.details
                assert audit_ctx.details["problematic"].startswith("<sanitization_failed:")

    def test_audit_context_passes_sanitized_data_to_service(self, mock_audit_service):
        """Test that the audit service receives sanitized data."""
        appointment = Mock()
        appointment.__class__.__name__ = "Appointment"
        appointment.__table__ = Mock()
        appointment.__table__.name = "appointments"
        appointment.id = 999
        appointment.subject = "Service Test Meeting"

        with AuditContext(
            audit_service=mock_audit_service,
            user_id=1,
            action_type="test",
            operation="test_operation"
        ) as audit_ctx:
            audit_ctx.add_detail("test_appointment", appointment)

        # Verify the service was called with sanitized data
        mock_audit_service.log_operation.assert_called_once()
        call_kwargs = mock_audit_service.log_operation.call_args[1]
        
        # Check that details contain sanitized appointment
        details = call_kwargs["details"]
        assert "test_appointment" in details
        sanitized_appointment = details["test_appointment"]
        assert sanitized_appointment["_model_type"] == "Appointment"
        assert sanitized_appointment["id"] == 999
        assert sanitized_appointment["subject"] == "Service Test Meeting"
