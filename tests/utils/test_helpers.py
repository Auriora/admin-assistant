"""
Test utilities and helpers for improved test isolation and mock validation.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from contextlib import contextmanager
from typing import Any, Dict, List, Optional
import logging


class MockValidator:
    """Utility class to validate mock calls and expectations."""
    
    def __init__(self, mock_obj: Mock):
        self.mock = mock_obj
        self.expected_calls = []
        
    def expect_call(self, method_name: str, *args, **kwargs):
        """Add an expected call to validate later."""
        self.expected_calls.append((method_name, args, kwargs))
        return self
        
    def validate(self):
        """Validate that all expected calls were made."""
        for method_name, args, kwargs in self.expected_calls:
            method = getattr(self.mock, method_name)
            try:
                method.assert_called_with(*args, **kwargs)
            except AssertionError as e:
                pytest.fail(f"Mock validation failed for {method_name}: {e}")


class DatabaseTestHelper:
    """Helper for database test isolation and cleanup."""
    
    @staticmethod
    @contextmanager
    def isolated_transaction(session):
        """Context manager for isolated database transactions in tests."""
        # Start a savepoint for nested transaction
        savepoint = session.begin_nested()
        try:
            yield session
        except Exception:
            savepoint.rollback()
            raise
        finally:
            # Always rollback the savepoint to ensure isolation
            if savepoint.is_active:
                savepoint.rollback()


class ServiceMockHelper:
    """Helper for creating consistent service mocks."""
    
    @staticmethod
    def create_user_service_mock(users: Optional[List[Dict[str, Any]]] = None):
        """Create a mock user service with predefined users."""
        mock = MagicMock()
        users = users or [{"id": 1, "email": "test@example.com", "name": "Test User"}]
        
        def get_by_id(user_id):
            for user in users:
                if user["id"] == user_id:
                    user_obj = Mock()
                    for key, value in user.items():
                        setattr(user_obj, key, value)
                    return user_obj
            return None
            
        mock.get_by_id.side_effect = get_by_id
        return mock
    
    @staticmethod
    def create_archive_config_service_mock(configs: Optional[List[Dict[str, Any]]] = None):
        """Create a mock archive configuration service."""
        mock = MagicMock()
        configs = configs or [{"id": 1, "is_active": True, "name": "Test Config"}]
        
        def get_by_id(config_id):
            for config in configs:
                if config["id"] == config_id:
                    config_obj = Mock()
                    for key, value in config.items():
                        setattr(config_obj, key, value)
                    return config_obj
            return None
            
        mock.get_by_id.side_effect = get_by_id
        return mock


class LogCapture:
    """Utility for capturing and validating log messages in tests."""
    
    def __init__(self, logger_name: str = None, level: int = logging.DEBUG):
        self.logger_name = logger_name
        self.level = level
        self.records = []
        self.handler = None
        
    def __enter__(self):
        # Create a custom handler to capture log records
        class TestLogHandler(logging.Handler):
            def __init__(self, records_list):
                super().__init__()
                self.records = records_list
                
            def emit(self, record):
                self.records.append(record)
        
        self.handler = TestLogHandler(self.records)
        self.handler.setLevel(self.level)
        
        # Add handler to the specified logger or root logger
        if self.logger_name:
            logger = logging.getLogger(self.logger_name)
        else:
            logger = logging.getLogger()
            
        logger.addHandler(self.handler)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.handler:
            if self.logger_name:
                logger = logging.getLogger(self.logger_name)
            else:
                logger = logging.getLogger()
            logger.removeHandler(self.handler)
    
    def assert_log_contains(self, message: str, level: int = None):
        """Assert that a log message was captured."""
        for record in self.records:
            if level and record.levelno != level:
                continue
            if message in record.getMessage():
                return
        pytest.fail(f"Log message '{message}' not found in captured logs")
    
    def assert_log_count(self, count: int, level: int = None):
        """Assert the number of log messages captured."""
        if level:
            filtered_records = [r for r in self.records if r.levelno == level]
            actual_count = len(filtered_records)
        else:
            actual_count = len(self.records)
            
        assert actual_count == count, f"Expected {count} log messages, got {actual_count}"


@pytest.fixture
def mock_validator():
    """Fixture that provides a MockValidator factory."""
    def _create_validator(mock_obj):
        return MockValidator(mock_obj)
    return _create_validator


@pytest.fixture
def db_helper():
    """Fixture that provides database test helpers."""
    return DatabaseTestHelper()


@pytest.fixture
def service_mocks():
    """Fixture that provides service mock helpers."""
    return ServiceMockHelper()


@pytest.fixture
def log_capture():
    """Fixture that provides log capture utility."""
    def _create_capture(logger_name=None, level=logging.DEBUG):
        return LogCapture(logger_name, level)
    return _create_capture


class AsyncMockHelper:
    """Helper for creating async mocks for testing async code."""
    
    @staticmethod
    def create_async_mock(return_value=None, side_effect=None):
        """Create an async mock with proper async behavior."""
        from unittest.mock import AsyncMock
        mock = AsyncMock()
        if return_value is not None:
            mock.return_value = return_value
        if side_effect is not None:
            mock.side_effect = side_effect
        return mock


@pytest.fixture
def async_mock_helper():
    """Fixture that provides async mock helpers."""
    return AsyncMockHelper()


def assert_mock_called_with_subset(mock_obj, **expected_kwargs):
    """Assert that a mock was called with at least the specified keyword arguments."""
    if not mock_obj.called:
        pytest.fail("Mock was not called")
    
    # Get the last call's kwargs
    last_call = mock_obj.call_args
    if not last_call:
        pytest.fail("Mock was called but no call args found")
    
    actual_kwargs = last_call.kwargs if last_call.kwargs else {}
    
    # Check that all expected kwargs are present with correct values
    for key, expected_value in expected_kwargs.items():
        if key not in actual_kwargs:
            pytest.fail(f"Expected keyword argument '{key}' not found in mock call")
        if actual_kwargs[key] != expected_value:
            pytest.fail(f"Expected {key}={expected_value}, got {key}={actual_kwargs[key]}")


def create_test_appointment(subject="Test Appointment", **kwargs):
    """Factory function for creating test appointments with sensible defaults."""
    from datetime import datetime, timezone, timedelta
    from core.models.appointment import Appointment
    
    defaults = {
        "user_id": 1,
        "calendar_id": "test-calendar",
        "start_time": datetime.now(timezone.utc),
        "end_time": datetime.now(timezone.utc) + timedelta(hours=1),
        "subject": subject,
        "is_archived": False
    }
    defaults.update(kwargs)
    return Appointment(**defaults)
