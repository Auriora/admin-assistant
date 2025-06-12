"""
Test to verify that the JSON serialization issue is fixed.
This test specifically reproduces the original error scenario and verifies it's resolved.
"""

import json
import datetime
import pytest
from unittest.mock import Mock

from core.utilities.audit_sanitizer import sanitize_for_audit
from core.utilities.audit_logging_utility import AuditContext
from core.services.audit_log_service import AuditLogService


class TestJSONSerializationFix:
    """Test that the original JSON serialization issue is resolved."""

    def test_original_error_scenario_fixed(self):
        """
        Test the exact scenario that was causing the original error:
        'TypeError: Object of type Appointment is not JSON serializable'
        """
        # Create mock appointments that would cause the original error
        appointment1 = Mock()
        appointment1.__class__.__name__ = "Appointment"
        appointment1.__table__ = Mock()
        appointment1.__table__.name = "appointments"
        appointment1.id = 1
        appointment1.subject = "Meeting 1"
        appointment1.start_time = datetime.datetime(2024, 1, 15, 10, 0)
        appointment1.end_time = datetime.datetime(2024, 1, 15, 11, 0)

        appointment2 = Mock()
        appointment2.__class__.__name__ = "Appointment"
        appointment2.__table__ = Mock()
        appointment2.__table__.name = "appointments"
        appointment2.id = 2
        appointment2.subject = "Meeting 2"
        appointment2.start_time = datetime.datetime(2024, 1, 15, 10, 30)
        appointment2.end_time = datetime.datetime(2024, 1, 15, 11, 30)

        # Create the exact result structure that was causing the error
        result = {
            "status": "success",
            "archive_type": "general",
            "archive_purpose": "general",
            "correlation_id": "test-correlation-id",
            "total_appointments_fetched": 5,
            "appointments_archived": 3,
            "allow_overlaps": False,
            "overlap_handling": "full",
            "processing_stats": {
                "original_count": 5,
                "expanded_count": 5,
                "deduplicated_count": 4,
                "overlap_groups": 1,
                "overlapping_appointments": 2,
                "processing_mode": "full"
            },
            "conflicts": [appointment1, appointment2],  # This was the problematic field
            "archive_errors": [],
            "archived_count": 3,
            "operation_duration": 1.234,
            "overlap_count": 1,
            "errors": []
        }

        # Before the fix, this would raise:
        # TypeError: Object of type Appointment is not JSON serializable
        # After the fix, this should work without error
        sanitized_result = sanitize_for_audit(result)

        # Verify the result can be JSON serialized
        json_string = json.dumps(sanitized_result)
        assert json_string is not None
        assert len(json_string) > 0

        # Verify the structure is preserved
        assert sanitized_result["status"] == "success"
        assert sanitized_result["archive_type"] == "general"
        assert sanitized_result["total_appointments_fetched"] == 5
        assert sanitized_result["appointments_archived"] == 3

        # Verify conflicts are properly sanitized
        assert len(sanitized_result["conflicts"]) == 2
        conflict1 = sanitized_result["conflicts"][0]
        conflict2 = sanitized_result["conflicts"][1]

        assert conflict1["_model_type"] == "Appointment"
        assert conflict1["id"] == 1
        assert conflict1["subject"] == "Meeting 1"
        assert conflict1["start_time"] == "2024-01-15T10:00:00"

        assert conflict2["_model_type"] == "Appointment"
        assert conflict2["id"] == 2
        assert conflict2["subject"] == "Meeting 2"
        assert conflict2["start_time"] == "2024-01-15T10:30:00"

    def test_audit_context_with_original_error_scenario(self):
        """
        Test that AuditContext can handle the original error scenario without throwing.
        """
        # Create mock audit service
        mock_audit_service = Mock(spec=AuditLogService)
        mock_audit_service.log_operation.return_value = Mock()

        # Create mock appointment
        appointment = Mock()
        appointment.__class__.__name__ = "Appointment"
        appointment.__table__ = Mock()
        appointment.__table__.name = "appointments"
        appointment.id = 123
        appointment.subject = "Problematic Meeting"
        appointment.start_time = datetime.datetime(2024, 1, 15, 10, 0)

        # Create the problematic result structure
        problematic_result = {
            "status": "success",
            "conflicts": [appointment],
            "processing_stats": {
                "overlap_groups": 1
            }
        }

        # This should not raise any JSON serialization errors
        with AuditContext(
            audit_service=mock_audit_service,
            user_id=1,
            action_type="archive",
            operation="general_archive",
            resource_type="calendar",
            resource_id="test-calendar"
        ) as audit_ctx:
            # This was the line causing the original error
            audit_ctx.add_detail("final_result", problematic_result)

        # Verify the audit service was called successfully
        mock_audit_service.log_operation.assert_called_once()
        
        # Verify the details were sanitized properly
        call_kwargs = mock_audit_service.log_operation.call_args[1]
        details = call_kwargs["details"]
        
        assert "final_result" in details
        final_result = details["final_result"]
        assert final_result["status"] == "success"
        assert len(final_result["conflicts"]) == 1
        assert final_result["conflicts"][0]["_model_type"] == "Appointment"
        assert final_result["conflicts"][0]["id"] == 123

    def test_deeply_nested_appointment_objects(self):
        """Test that deeply nested structures with appointments are handled correctly."""
        appointment = Mock()
        appointment.__class__.__name__ = "Appointment"
        appointment.__table__ = Mock()
        appointment.__table__.name = "appointments"
        appointment.id = 456
        appointment.subject = "Nested Meeting"

        # Create a deeply nested structure
        deeply_nested = {
            "level1": {
                "level2": {
                    "level3": {
                        "appointments": [appointment],
                        "metadata": {
                            "conflicts": [appointment],
                            "timestamp": datetime.datetime(2024, 1, 15, 10, 0)
                        }
                    }
                }
            }
        }

        # This should not raise any errors
        sanitized = sanitize_for_audit(deeply_nested)

        # Verify JSON serialization works
        json_string = json.dumps(sanitized)
        assert json_string is not None

        # Verify structure is preserved and appointments are sanitized
        nested_appointment = sanitized["level1"]["level2"]["level3"]["appointments"][0]
        assert nested_appointment["_model_type"] == "Appointment"
        assert nested_appointment["id"] == 456
        assert nested_appointment["subject"] == "Nested Meeting"

        conflict_appointment = sanitized["level1"]["level2"]["level3"]["metadata"]["conflicts"][0]
        assert conflict_appointment["_model_type"] == "Appointment"
        assert conflict_appointment["id"] == 456

    def test_mixed_object_types_serialization(self):
        """Test serialization of mixed object types including appointments."""
        appointment = Mock()
        appointment.__class__.__name__ = "Appointment"
        appointment.__table__ = Mock()
        appointment.__table__.name = "appointments"
        appointment.id = 789
        appointment.subject = "Mixed Meeting"

        user = Mock()
        user.__class__.__name__ = "User"
        user.__table__ = Mock()
        user.__table__.name = "users"
        user.id = 101
        user.email = "test@example.com"

        # Create structure with mixed object types
        mixed_data = {
            "appointment": appointment,
            "user": user,
            "datetime": datetime.datetime(2024, 1, 15, 10, 0),
            "date": datetime.date(2024, 1, 15),
            "list_with_objects": [appointment, user, "string", 42],
            "primitive_data": {
                "string": "value",
                "number": 123,
                "boolean": True,
                "null": None
            }
        }

        # Should handle all types correctly
        sanitized = sanitize_for_audit(mixed_data)

        # Verify JSON serialization
        json_string = json.dumps(sanitized)
        assert json_string is not None

        # Verify each type was handled correctly
        assert sanitized["appointment"]["_model_type"] == "Appointment"
        assert sanitized["user"]["_model_type"] == "User"
        assert sanitized["datetime"] == "2024-01-15T10:00:00"
        assert sanitized["date"] == "2024-01-15"
        assert len(sanitized["list_with_objects"]) == 4
        assert sanitized["list_with_objects"][0]["_model_type"] == "Appointment"
        assert sanitized["list_with_objects"][1]["_model_type"] == "User"
        assert sanitized["list_with_objects"][2] == "string"
        assert sanitized["list_with_objects"][3] == 42
        assert sanitized["primitive_data"]["string"] == "value"
        assert sanitized["primitive_data"]["number"] == 123
        assert sanitized["primitive_data"]["boolean"] is True
        assert sanitized["primitive_data"]["null"] is None
