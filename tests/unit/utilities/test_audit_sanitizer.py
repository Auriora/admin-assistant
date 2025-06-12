"""
Tests for audit data sanitization utility.
"""

import datetime
import pytest
from unittest.mock import Mock, MagicMock

from core.utilities.audit_sanitizer import (
    sanitize_for_audit,
    sanitize_audit_data,
    _sanitize_sqlalchemy_model,
    _sanitize_appointment_model,
)


class TestSanitizeForAudit:
    """Test the main sanitization function."""

    def test_sanitize_none(self):
        """Test sanitization of None value."""
        result = sanitize_for_audit(None)
        assert result is None

    def test_sanitize_primitives(self):
        """Test sanitization of primitive types."""
        assert sanitize_for_audit("string") == "string"
        assert sanitize_for_audit(42) == 42
        assert sanitize_for_audit(3.14) == 3.14
        assert sanitize_for_audit(True) is True
        assert sanitize_for_audit(False) is False

    def test_sanitize_datetime(self):
        """Test sanitization of datetime objects."""
        dt = datetime.datetime(2024, 1, 15, 10, 30, 45)
        result = sanitize_for_audit(dt)
        assert result == "2024-01-15T10:30:45"

    def test_sanitize_date(self):
        """Test sanitization of date objects."""
        d = datetime.date(2024, 1, 15)
        result = sanitize_for_audit(d)
        assert result == "2024-01-15"

    def test_sanitize_list(self):
        """Test sanitization of lists."""
        test_list = [1, "string", datetime.date(2024, 1, 15), None]
        result = sanitize_for_audit(test_list)
        expected = [1, "string", "2024-01-15", None]
        assert result == expected

    def test_sanitize_tuple(self):
        """Test sanitization of tuples."""
        test_tuple = (1, "string", datetime.date(2024, 1, 15))
        result = sanitize_for_audit(test_tuple)
        expected = [1, "string", "2024-01-15"]
        assert result == expected

    def test_sanitize_dict(self):
        """Test sanitization of dictionaries."""
        test_dict = {
            "string_key": "value",
            "int_key": 42,
            "date_key": datetime.date(2024, 1, 15),
            123: "numeric_key"  # Non-string key
        }
        result = sanitize_for_audit(test_dict)
        expected = {
            "string_key": "value",
            "int_key": 42,
            "date_key": "2024-01-15",
            "123": "numeric_key"
        }
        assert result == expected

    def test_sanitize_set(self):
        """Test sanitization of sets."""
        test_set = {1, 2, 3}
        result = sanitize_for_audit(test_set)
        assert isinstance(result, list)
        assert set(result) == {1, 2, 3}

    def test_circular_reference_detection(self):
        """Test detection and handling of circular references."""
        # Create circular reference
        dict1 = {"name": "dict1"}
        dict2 = {"name": "dict2", "ref": dict1}
        dict1["ref"] = dict2

        result = sanitize_for_audit(dict1)
        
        # Should handle circular reference gracefully
        assert result["name"] == "dict1"
        assert result["ref"]["name"] == "dict2"
        assert "<circular_reference:dict>" in str(result["ref"]["ref"])

    def test_max_depth_limit(self):
        """Test maximum depth limit to prevent infinite recursion."""
        # Create deeply nested structure
        nested = {"level": 0}
        current = nested
        for i in range(1, 15):  # Create 15 levels deep
            current["next"] = {"level": i}
            current = current["next"]

        result = sanitize_for_audit(nested, max_depth=5)
        
        # Should stop at max depth
        current_result = result
        for i in range(5):
            assert current_result["level"] == i
            if i < 4:
                current_result = current_result["next"]
        
        # Should have max depth exceeded marker
        assert "<max_depth_exceeded:" in str(current_result.get("next", ""))

    def test_unknown_object_fallback(self):
        """Test fallback to string representation for unknown objects."""
        class CustomObject:
            def __str__(self):
                return "custom_object_string"

        obj = CustomObject()
        result = sanitize_for_audit(obj)
        assert result == "custom_object_string"

    def test_unserializable_object_fallback(self):
        """Test fallback for objects that can't be converted to string."""
        class BadObject:
            def __str__(self):
                raise Exception("Cannot convert to string")

        obj = BadObject()
        result = sanitize_for_audit(obj)
        assert result.startswith("<unserializable:BadObject>")


class TestSQLAlchemyModelSanitization:
    """Test sanitization of SQLAlchemy model instances."""

    def test_sanitize_mock_appointment(self):
        """Test sanitization of mock Appointment model."""
        # Create mock appointment
        appointment = Mock()
        appointment.__class__.__name__ = "Appointment"
        appointment.__table__ = Mock()
        appointment.__table__.name = "appointments"
        appointment.id = 123
        appointment.subject = "Test Meeting"
        appointment.start_time = datetime.datetime(2024, 1, 15, 10, 0)
        appointment.end_time = datetime.datetime(2024, 1, 15, 11, 0)
        appointment.location = "Conference Room"
        appointment.show_as = "busy"
        appointment.is_archived = False
        appointment.calendar_id = "cal-123"
        appointment.user_id = 456

        result = sanitize_for_audit(appointment)
        
        assert result["_model_type"] == "Appointment"
        assert result["_table_name"] == "appointments"
        assert result["id"] == 123
        assert result["subject"] == "Test Meeting"
        assert result["start_time"] == "2024-01-15T10:00:00"
        assert result["end_time"] == "2024-01-15T11:00:00"
        assert result["location"] == "Conference Room"
        assert result["show_as"] == "busy"
        assert result["is_archived"] is False
        assert result["calendar_id"] == "cal-123"
        assert result["user_id"] == 456

    def test_sanitize_mock_user(self):
        """Test sanitization of mock User model."""
        user = Mock()
        user.__class__.__name__ = "User"
        user.__table__ = Mock()
        user.__table__.name = "users"
        user.id = 789
        user.email = "test@example.com"
        user.name = "Test User"
        user.is_active = True

        result = sanitize_for_audit(user)
        
        assert result["_model_type"] == "User"
        assert result["_table_name"] == "users"
        assert result["id"] == 789
        assert result["email"] == "test@example.com"
        assert result["name"] == "Test User"
        assert result["is_active"] is True

    def test_sanitize_generic_model(self):
        """Test sanitization of generic SQLAlchemy model."""
        model = Mock()
        model.__class__.__name__ = "GenericModel"
        model.__table__ = Mock()
        model.__table__.name = "generic_table"
        model.id = 999
        model.name = "Generic Name"
        model.title = "Generic Title"

        result = sanitize_for_audit(model)
        
        assert result["_model_type"] == "GenericModel"
        assert result["_table_name"] == "generic_table"
        assert result["id"] == 999
        assert result["name"] == "Generic Name"
        assert result["title"] == "Generic Title"


class TestSanitizeAuditData:
    """Test the convenience function for sanitizing audit data."""

    def test_sanitize_dict_data(self):
        """Test sanitizing dictionary audit data."""
        data = {
            "operation": "test",
            "timestamp": datetime.datetime(2024, 1, 15, 10, 0),
            "details": {
                "nested": True,
                "count": 42
            }
        }
        
        result = sanitize_audit_data(data)
        
        assert result["operation"] == "test"
        assert result["timestamp"] == "2024-01-15T10:00:00"
        assert result["details"]["nested"] is True
        assert result["details"]["count"] == 42

    def test_sanitize_non_dict_data(self):
        """Test sanitizing non-dictionary data."""
        data = ["item1", datetime.date(2024, 1, 15), 42]
        result = sanitize_audit_data(data)
        expected = ["item1", "2024-01-15", 42]
        assert result == expected


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    def test_appointment_conflicts_list(self):
        """Test sanitizing a list of appointment conflicts (the original issue)."""
        # Create mock appointments similar to the failing test scenario
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

        conflicts = [appointment1, appointment2]
        
        # This is the scenario that was causing the JSON serialization error
        result_dict = {
            "status": "success",
            "conflicts": conflicts,
            "archived_count": 5,
            "processing_stats": {
                "overlap_groups": 1,
                "overlapping_appointments": 2
            }
        }
        
        sanitized = sanitize_for_audit(result_dict)
        
        # Verify the structure is preserved but appointments are sanitized
        assert sanitized["status"] == "success"
        assert sanitized["archived_count"] == 5
        assert sanitized["processing_stats"]["overlap_groups"] == 1
        assert sanitized["processing_stats"]["overlapping_appointments"] == 2
        
        # Verify conflicts are properly sanitized
        assert len(sanitized["conflicts"]) == 2
        assert sanitized["conflicts"][0]["_model_type"] == "Appointment"
        assert sanitized["conflicts"][0]["id"] == 1
        assert sanitized["conflicts"][0]["subject"] == "Meeting 1"
        assert sanitized["conflicts"][1]["_model_type"] == "Appointment"
        assert sanitized["conflicts"][1]["id"] == 2
        assert sanitized["conflicts"][1]["subject"] == "Meeting 2"

    def test_nested_model_objects(self):
        """Test sanitizing deeply nested structures with model objects."""
        appointment = Mock()
        appointment.__class__.__name__ = "Appointment"
        appointment.__table__ = Mock()
        appointment.__table__.name = "appointments"
        appointment.id = 123
        appointment.subject = "Nested Meeting"

        complex_structure = {
            "level1": {
                "level2": {
                    "appointments": [appointment],
                    "metadata": {
                        "created": datetime.datetime(2024, 1, 15, 10, 0),
                        "count": 1
                    }
                }
            }
        }
        
        result = sanitize_for_audit(complex_structure)
        
        # Verify deep nesting is handled correctly
        nested_appointment = result["level1"]["level2"]["appointments"][0]
        assert nested_appointment["_model_type"] == "Appointment"
        assert nested_appointment["id"] == 123
        assert nested_appointment["subject"] == "Nested Meeting"
        
        # Verify other nested data is preserved
        assert result["level1"]["level2"]["metadata"]["created"] == "2024-01-15T10:00:00"
        assert result["level1"]["level2"]["metadata"]["count"] == 1
