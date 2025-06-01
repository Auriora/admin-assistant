"""
Unit tests for AuditLogService

Tests the business logic for managing audit logging including
operation logging, specialized logging methods, search functionality,
and audit trail management.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import date, datetime
from core.services.audit_log_service import AuditLogService
from core.models.audit_log import AuditLog
from core.repositories.audit_log_repository import AuditLogRepository


class TestAuditLogService:
    """Test suite for AuditLogService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_repository = Mock(spec=AuditLogRepository)
        self.service = AuditLogService(repository=self.mock_repository)
    
    def test_init_with_repository(self):
        """Test service initialization with provided repository"""
        service = AuditLogService(repository=self.mock_repository)
        assert service.repository == self.mock_repository
    
    def test_init_with_default_repository(self):
        """Test service initialization with default repository"""
        service = AuditLogService()
        assert service.repository is not None
    
    @patch('core.services.audit_log_service.AuditLog')
    def test_log_operation_basic(self, mock_audit_log_class):
        """Test basic operation logging"""
        # Arrange
        mock_audit_log = Mock(spec=AuditLog)
        mock_audit_log_class.return_value = mock_audit_log
        self.mock_repository.add.return_value = mock_audit_log
        
        # Act
        result = self.service.log_operation(
            user_id=123,
            action_type="test_action",
            operation="test_operation",
            status="success",
            message="Test message"
        )
        
        # Assert
        mock_audit_log_class.assert_called_once()
        call_kwargs = mock_audit_log_class.call_args[1]
        assert call_kwargs['user_id'] == 123
        assert call_kwargs['action_type'] == "test_action"
        assert call_kwargs['operation'] == "test_operation"
        assert call_kwargs['status'] == "success"
        assert call_kwargs['message'] == "Test message"
        
        self.mock_repository.add.assert_called_once_with(mock_audit_log)
        assert result == mock_audit_log
    
    @patch('core.services.audit_log_service.AuditLog')
    def test_log_operation_with_all_parameters(self, mock_audit_log_class):
        """Test operation logging with all optional parameters"""
        # Arrange
        mock_audit_log = Mock(spec=AuditLog)
        mock_audit_log_class.return_value = mock_audit_log
        self.mock_repository.add.return_value = mock_audit_log
        
        details = {"key": "value"}
        request_data = {"input": "data"}
        response_data = {"output": "result"}
        
        # Act
        result = self.service.log_operation(
            user_id=123,
            action_type="test_action",
            operation="test_operation",
            status="success",
            message="Test message",
            resource_type="appointment",
            resource_id="456",
            details=details,
            request_data=request_data,
            response_data=response_data,
            duration_ms=150.5,
            correlation_id="corr-123",
            parent_audit_id=789,
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0"
        )
        
        # Assert
        call_kwargs = mock_audit_log_class.call_args[1]
        assert call_kwargs['resource_type'] == "appointment"
        assert call_kwargs['resource_id'] == "456"
        assert call_kwargs['details'] == details
        assert call_kwargs['request_data'] == request_data
        assert call_kwargs['response_data'] == response_data
        assert call_kwargs['duration_ms'] == 150.5
        assert call_kwargs['correlation_id'] == "corr-123"
        assert call_kwargs['parent_audit_id'] == 789
        assert call_kwargs['ip_address'] == "192.168.1.1"
        assert call_kwargs['user_agent'] == "TestAgent/1.0"
        
        assert result == mock_audit_log
    
    @patch('core.services.audit_log_service.AuditLogService.log_operation')
    def test_log_archive_operation(self, mock_log_operation):
        """Test archive operation logging"""
        # Arrange
        mock_audit_log = Mock(spec=AuditLog)
        mock_log_operation.return_value = mock_audit_log
        
        start_date = date(2025, 1, 1)
        end_date = date(2025, 1, 31)
        
        # Act
        result = self.service.log_archive_operation(
            user_id=123,
            operation="calendar_archive",
            status="success",
            source_calendar_uri="msgraph://source-cal",
            archive_calendar_id="archive-cal-123",
            start_date=start_date,
            end_date=end_date,
            archived_count=25,
            overlap_count=3,
            errors=["Error 1", "Error 2"],
            duration_ms=5000.0,
            correlation_id="corr-456"
        )
        
        # Assert
        mock_log_operation.assert_called_once()
        call_kwargs = mock_log_operation.call_args[1]
        
        assert call_kwargs['user_id'] == 123
        assert call_kwargs['action_type'] == "archive"
        assert call_kwargs['operation'] == "calendar_archive"
        assert call_kwargs['status'] == "success"
        assert call_kwargs['resource_type'] == "calendar"
        assert call_kwargs['resource_id'] == "msgraph://source-cal"
        assert call_kwargs['duration_ms'] == 5000.0
        assert call_kwargs['correlation_id'] == "corr-456"
        
        # Check details structure
        details = call_kwargs['details']
        assert details['source_calendar_uri'] == "msgraph://source-cal"
        assert details['archive_calendar_id'] == "archive-cal-123"
        assert details['start_date'] == "2025-01-01"
        assert details['end_date'] == "2025-01-31"
        assert details['archived_count'] == 25
        assert details['overlap_count'] == 3
        assert details['errors'] == ["Error 1", "Error 2"]
        
        assert "Archived 25 appointments from 2025-01-01 to 2025-01-31" in call_kwargs['message']
        assert result == mock_audit_log
    
    @patch('core.services.audit_log_service.AuditLogService.log_operation')
    def test_log_overlap_resolution(self, mock_log_operation):
        """Test overlap resolution operation logging"""
        # Arrange
        mock_audit_log = Mock(spec=AuditLog)
        mock_log_operation.return_value = mock_audit_log

        appointments_affected = ["appt-1", "appt-2"]
        resolution_data = {
            "action": "keep_first",
            "deleted_appointments": ["appt-2"]
        }

        # Act
        result = self.service.log_overlap_resolution(
            user_id=123,
            action_log_id=456,
            resolution_type="automatic",
            status="success",
            appointments_affected=appointments_affected,
            resolution_data=resolution_data,
            ai_recommendations={"confidence": 0.85},
            duration_ms=2500.0,
            correlation_id="corr-789"
        )

        # Assert
        mock_log_operation.assert_called_once()
        call_kwargs = mock_log_operation.call_args[1]

        assert call_kwargs['user_id'] == 123
        assert call_kwargs['action_type'] == "overlap_resolution"
        assert call_kwargs['operation'] == "resolve_overlap"
        assert call_kwargs['status'] == "success"
        assert call_kwargs['resource_type'] == "action_log"
        assert call_kwargs['resource_id'] == "456"

        # Check details structure
        details = call_kwargs['details']
        assert details['action_log_id'] == 456
        assert details['resolution_type'] == "automatic"
        assert details['appointments_affected'] == appointments_affected
        assert details['resolution_data'] == resolution_data
        assert details['ai_recommendations'] == {"confidence": 0.85}

        assert "Resolved overlap for 2 appointments using automatic" in call_kwargs['message']
        assert result == mock_audit_log
    
    @patch('core.services.audit_log_service.AuditLogService.log_operation')
    def test_log_re_archive_operation(self, mock_log_operation):
        """Test re-archive operation logging"""
        # Arrange
        mock_audit_log = Mock(spec=AuditLog)
        mock_log_operation.return_value = mock_audit_log

        start_date = date(2025, 1, 1)
        end_date = date(2025, 1, 31)

        # Act
        result = self.service.log_re_archive_operation(
            user_id=123,
            status="success",
            source_calendar_uri="msgraph://source-cal",
            archive_calendar_id="archive-cal-123",
            start_date=start_date,
            end_date=end_date,
            replaced_count=10,
            new_archived_count=15,
            duration_ms=3000.0,
            correlation_id="corr-999"
        )

        # Assert
        mock_log_operation.assert_called_once()
        call_kwargs = mock_log_operation.call_args[1]

        assert call_kwargs['user_id'] == 123
        assert call_kwargs['action_type'] == "re_archive"
        assert call_kwargs['operation'] == "calendar_re_archive"
        assert call_kwargs['status'] == "success"
        assert call_kwargs['resource_type'] == "calendar"
        assert call_kwargs['resource_id'] == "msgraph://source-cal"

        # Check details structure
        details = call_kwargs['details']
        assert details['replaced_count'] == 10
        assert details['new_archived_count'] == 15

        expected_message = "Re-archived period 2025-01-01 to 2025-01-31: replaced 10, archived 15"
        assert call_kwargs['message'] == expected_message
        assert result == mock_audit_log

    @patch('core.services.audit_log_service.AuditLogService.log_operation')
    def test_log_api_call(self, mock_log_operation):
        """Test API call logging"""
        # Arrange
        mock_audit_log = Mock(spec=AuditLog)
        mock_log_operation.return_value = mock_audit_log

        request_data = {"param1": "value1"}
        response_data = {"result": "success"}

        # Act
        result = self.service.log_api_call(
            user_id=123,
            api_name="msgraph",
            endpoint="/me/calendars",
            method="GET",
            status="success",
            status_code=200,
            request_data=request_data,
            response_data=response_data,
            duration_ms=150.0,
            correlation_id="corr-api-123"
        )

        # Assert
        mock_log_operation.assert_called_once()
        call_kwargs = mock_log_operation.call_args[1]

        assert call_kwargs['user_id'] == 123
        assert call_kwargs['action_type'] == "api_call"
        assert call_kwargs['operation'] == "msgraph_api_call"
        assert call_kwargs['status'] == "success"
        assert call_kwargs['resource_type'] == "api_endpoint"
        assert call_kwargs['resource_id'] == "/me/calendars"
        assert call_kwargs['request_data'] == request_data
        assert call_kwargs['response_data'] == response_data
        assert call_kwargs['duration_ms'] == 150.0
        assert call_kwargs['correlation_id'] == "corr-api-123"

        # Check details structure
        details = call_kwargs['details']
        assert details['api_name'] == "msgraph"
        assert details['endpoint'] == "/me/calendars"
        assert details['method'] == "GET"
        assert details['status_code'] == 200

        assert call_kwargs['message'] == "GET /me/calendars - 200"
        assert result == mock_audit_log

    @patch('core.services.audit_log_service.uuid')
    def test_generate_correlation_id(self, mock_uuid):
        """Test correlation ID generation"""
        # Arrange
        mock_uuid.uuid4.return_value.return_value = "test-uuid-123"
        mock_uuid.uuid4.return_value.__str__ = lambda x: "test-uuid-123"
        
        # Act
        result = self.service.generate_correlation_id()
        
        # Assert
        mock_uuid.uuid4.assert_called_once()
        assert result == "test-uuid-123"
    
    def test_get_audit_trail(self):
        """Test getting audit trail by correlation ID"""
        # Arrange
        correlation_id = "corr-123"
        expected_logs = [Mock(spec=AuditLog), Mock(spec=AuditLog)]
        self.mock_repository.list_by_correlation_id.return_value = expected_logs
        
        # Act
        result = self.service.get_audit_trail(correlation_id)
        
        # Assert
        assert result == expected_logs
        self.mock_repository.list_by_correlation_id.assert_called_once_with(correlation_id)
    
    def test_search_audit_logs(self):
        """Test searching audit logs with filters"""
        # Arrange
        filters = {"user_id": 123, "action_type": "archive"}
        limit = 50
        offset = 10
        expected_logs = [Mock(spec=AuditLog)]
        self.mock_repository.search.return_value = expected_logs
        
        # Act
        result = self.service.search_audit_logs(filters, limit, offset)
        
        # Assert
        assert result == expected_logs
        self.mock_repository.search.assert_called_once_with(filters, limit, offset)
    
    @patch('core.services.audit_log_service.date')
    def test_get_audit_summary(self, mock_date):
        """Test getting audit summary for a user"""
        # Arrange
        user_id = 123
        days = 30
        
        # Mock date calculations
        mock_end_date = date(2025, 1, 31)
        mock_start_date = date(2025, 1, 1)
        mock_date.today.return_value = mock_end_date
        mock_date.fromordinal.return_value = mock_start_date
        
        # Mock audit logs
        mock_log1 = Mock(spec=AuditLog)
        mock_log1.action_type = "archive"
        mock_log1.status = "success"
        mock_log1.operation = "calendar_archive"
        
        mock_log2 = Mock(spec=AuditLog)
        mock_log2.action_type = "archive"
        mock_log2.status = "failure"
        mock_log2.operation = "calendar_archive"
        
        mock_log3 = Mock(spec=AuditLog)
        mock_log3.action_type = "overlap_resolution"
        mock_log3.status = "success"
        mock_log3.operation = "resolve_overlap"
        
        self.mock_repository.list_by_date_range.return_value = [mock_log1, mock_log2, mock_log3]
        
        # Act
        result = self.service.get_audit_summary(user_id, days)
        
        # Assert
        self.mock_repository.list_by_date_range.assert_called_once_with(
            mock_start_date, mock_end_date, user_id
        )
        
        assert result['total_operations'] == 3
        assert result['date_range']['start'] == "2025-01-01"
        assert result['date_range']['end'] == "2025-01-31"
        assert result['by_action_type']['archive'] == 2
        assert result['by_action_type']['overlap_resolution'] == 1
        assert result['by_status']['success'] == 2
        assert result['by_status']['failure'] == 1
        assert result['by_operation']['calendar_archive'] == 2
        assert result['by_operation']['resolve_overlap'] == 1
    
    @patch('core.services.audit_log_service.date')
    def test_cleanup_old_logs(self, mock_date):
        """Test cleaning up old audit logs"""
        # Arrange
        older_than_days = 90
        user_id = 123
        
        # Mock date calculation
        mock_today = date(2025, 1, 31)
        mock_cutoff_date = date(2024, 11, 2)  # 90 days ago
        mock_date.today.return_value = mock_today
        mock_date.fromordinal.return_value = mock_cutoff_date
        
        self.mock_repository.delete_old_entries.return_value = 25
        
        # Act
        result = self.service.cleanup_old_logs(older_than_days, user_id)
        
        # Assert
        self.mock_repository.delete_old_entries.assert_called_once_with(mock_cutoff_date, user_id)
        assert result == 25
    
    @patch('core.services.audit_log_service.date')
    def test_cleanup_old_logs_all_users(self, mock_date):
        """Test cleaning up old audit logs for all users"""
        # Arrange
        older_than_days = 365
        
        mock_today = date(2025, 1, 31)
        mock_cutoff_date = date(2024, 1, 31)  # 365 days ago
        mock_date.today.return_value = mock_today
        mock_date.fromordinal.return_value = mock_cutoff_date
        
        self.mock_repository.delete_old_entries.return_value = 100
        
        # Act
        result = self.service.cleanup_old_logs(older_than_days)
        
        # Assert
        self.mock_repository.delete_old_entries.assert_called_once_with(mock_cutoff_date, None)
        assert result == 100
