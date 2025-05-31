import pytest
import uuid
from datetime import date, datetime
from unittest.mock import Mock, patch
from core.models.audit_log import AuditLog
from core.models.user import User
from core.repositories.audit_log_repository import AuditLogRepository
from core.services.audit_log_service import AuditLogService
from core.utilities.audit_logging_utility import AuditContext, AuditLogHelper, audit_operation


class TestAuditLogModel:
    """Test the AuditLog model."""
    
    def test_audit_log_creation(self):
        """Test creating an AuditLog instance."""
        audit_log = AuditLog(
            user_id=1,
            action_type='archive',
            operation='calendar_archive',
            resource_type='calendar',
            resource_id='test-calendar-123',
            status='success',
            message='Successfully archived 10 appointments',
            details={'archived_count': 10},
            duration_ms=1500.5,
            correlation_id=str(uuid.uuid4())
        )
        
        assert audit_log.user_id == 1
        assert audit_log.action_type == 'archive'
        assert audit_log.operation == 'calendar_archive'
        assert audit_log.resource_type == 'calendar'
        assert audit_log.resource_id == 'test-calendar-123'
        assert audit_log.status == 'success'
        assert audit_log.message == 'Successfully archived 10 appointments'
        assert audit_log.details == {'archived_count': 10}
        assert audit_log.duration_ms == 1500.5
        assert audit_log.correlation_id is not None


class TestAuditLogRepository:
    """Test the AuditLogRepository."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return Mock()
    
    @pytest.fixture
    def repository(self, mock_session):
        """Create an AuditLogRepository with mock session."""
        return AuditLogRepository(session=mock_session)
    
    def test_add_audit_log(self, repository, mock_session):
        """Test adding an audit log entry."""
        audit_log = AuditLog(
            user_id=1,
            action_type='test',
            operation='test_operation',
            status='success'
        )
        
        mock_session.refresh = Mock()
        result = repository.add(audit_log)
        
        mock_session.add.assert_called_once_with(audit_log)
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(audit_log)
        assert result == audit_log
    
    def test_search_with_filters(self, repository, mock_session):
        """Test searching audit logs with filters."""
        filters = {
            'user_id': 1,
            'action_type': 'archive',
            'status': 'success'
        }
        
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        
        repository.search(filters)
        
        mock_session.query.assert_called_once()
        assert mock_query.filter_by.call_count >= 3  # Called for each filter
        mock_query.order_by.assert_called_once()
        mock_query.all.assert_called_once()


class TestAuditLogService:
    """Test the AuditLogService."""
    
    @pytest.fixture
    def mock_repository(self):
        """Create a mock AuditLogRepository."""
        return Mock(spec=AuditLogRepository)
    
    @pytest.fixture
    def service(self, mock_repository):
        """Create an AuditLogService with mock repository."""
        return AuditLogService(repository=mock_repository)
    
    def test_log_operation(self, service, mock_repository):
        """Test logging a general operation."""
        mock_repository.add.return_value = Mock(id=1)
        
        result = service.log_operation(
            user_id=1,
            action_type='test',
            operation='test_operation',
            status='success',
            message='Test message'
        )
        
        mock_repository.add.assert_called_once()
        audit_log_arg = mock_repository.add.call_args[0][0]
        assert audit_log_arg.user_id == 1
        assert audit_log_arg.action_type == 'test'
        assert audit_log_arg.operation == 'test_operation'
        assert audit_log_arg.status == 'success'
        assert audit_log_arg.message == 'Test message'
    
    def test_log_archive_operation(self, service, mock_repository):
        """Test logging an archive operation."""
        mock_repository.add.return_value = Mock(id=1)
        
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        
        result = service.log_archive_operation(
            user_id=1,
            operation='calendar_archive',
            status='success',
            source_calendar_uri='msgraph://calendar',
            archive_calendar_id='archive-123',
            start_date=start_date,
            end_date=end_date,
            archived_count=25,
            overlap_count=3
        )
        
        mock_repository.add.assert_called_once()
        audit_log_arg = mock_repository.add.call_args[0][0]
        assert audit_log_arg.action_type == 'archive'
        assert audit_log_arg.operation == 'calendar_archive'
        assert audit_log_arg.status == 'success'
        assert 'Archived 25 appointments' in audit_log_arg.message
        assert '3 overlaps detected' in audit_log_arg.message
        assert audit_log_arg.details['archived_count'] == 25
        assert audit_log_arg.details['overlap_count'] == 3
    
    def test_log_overlap_resolution(self, service, mock_repository):
        """Test logging an overlap resolution operation."""
        mock_repository.add.return_value = Mock(id=1)
        
        result = service.log_overlap_resolution(
            user_id=1,
            action_log_id=123,
            resolution_type='merge',
            status='success',
            appointments_affected=['appt1', 'appt2', 'appt3'],
            resolution_data={'merge': {'into': 'appt1', 'from': ['appt2', 'appt3']}}
        )
        
        mock_repository.add.assert_called_once()
        audit_log_arg = mock_repository.add.call_args[0][0]
        assert audit_log_arg.action_type == 'overlap_resolution'
        assert audit_log_arg.operation == 'resolve_overlap'
        assert audit_log_arg.status == 'success'
        assert 'Resolved overlap for 3 appointments using merge' in audit_log_arg.message
        assert audit_log_arg.details['action_log_id'] == 123
        assert audit_log_arg.details['resolution_type'] == 'merge'
    
    def test_generate_correlation_id(self, service):
        """Test generating a correlation ID."""
        correlation_id = service.generate_correlation_id()
        
        assert correlation_id is not None
        assert len(correlation_id) > 0
        # Should be a valid UUID string
        uuid.UUID(correlation_id)  # This will raise ValueError if invalid


class TestAuditContext:
    """Test the AuditContext context manager."""
    
    @pytest.fixture
    def mock_audit_service(self):
        """Create a mock AuditLogService."""
        return Mock(spec=AuditLogService)
    
    def test_audit_context_success(self, mock_audit_service):
        """Test AuditContext with successful operation."""
        mock_audit_service.log_operation.return_value = Mock(id=1)
        
        with AuditContext(
            audit_service=mock_audit_service,
            user_id=1,
            action_type='test',
            operation='test_operation'
        ) as ctx:
            ctx.add_detail('test_key', 'test_value')
            ctx.set_request_data({'input': 'test'})
            ctx.set_response_data({'output': 'success'})
        
        mock_audit_service.log_operation.assert_called_once()
        call_args = mock_audit_service.log_operation.call_args[1]
        assert call_args['user_id'] == 1
        assert call_args['action_type'] == 'test'
        assert call_args['operation'] == 'test_operation'
        assert call_args['status'] == 'success'
        assert call_args['details']['test_key'] == 'test_value'
        assert call_args['request_data']['input'] == 'test'
        assert call_args['response_data']['output'] == 'success'
        assert call_args['duration_ms'] is not None
    
    def test_audit_context_failure(self, mock_audit_service):
        """Test AuditContext with failed operation."""
        mock_audit_service.log_operation.return_value = Mock(id=1)
        
        with pytest.raises(ValueError):
            with AuditContext(
                audit_service=mock_audit_service,
                user_id=1,
                action_type='test',
                operation='test_operation'
            ) as ctx:
                raise ValueError("Test error")
        
        mock_audit_service.log_operation.assert_called_once()
        call_args = mock_audit_service.log_operation.call_args[1]
        assert call_args['status'] == 'failure'
        assert 'Test error' in call_args['message']
        assert 'error' in call_args['details']


class TestAuditDecorator:
    """Test the audit_operation decorator."""
    
    def test_audit_decorator_with_user_id(self):
        """Test the audit decorator with user_id parameter."""
        with patch('core.utilities.audit_logging_utility.AuditLogService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            @audit_operation('test', 'test_operation')
            def test_function(user_id, data):
                return {'result': 'success'}
            
            result = test_function(user_id=123, data='test_data')
            
            assert result == {'result': 'success'}
            mock_service_class.assert_called_once()
    
    def test_audit_decorator_without_user_id(self):
        """Test the audit decorator when user_id cannot be extracted."""
        with patch('core.utilities.audit_logging_utility.AuditLogService') as mock_service_class:
            
            @audit_operation('test', 'test_operation')
            def test_function(data):
                return {'result': 'success'}
            
            result = test_function(data='test_data')
            
            assert result == {'result': 'success'}
            # Should not create audit service if no user_id found
            mock_service_class.assert_not_called()


class TestAuditLogHelper:
    """Test the AuditLogHelper utility class."""
    
    def test_create_correlation_id(self):
        """Test creating a correlation ID."""
        with patch('core.utilities.audit_logging_utility.AuditLogService') as mock_service_class:
            mock_service = Mock()
            mock_service.generate_correlation_id.return_value = 'test-correlation-id'
            mock_service_class.return_value = mock_service
            
            correlation_id = AuditLogHelper.create_correlation_id()
            
            assert correlation_id == 'test-correlation-id'
            mock_service.generate_correlation_id.assert_called_once()
    
    def test_log_data_modification(self):
        """Test logging data modification."""
        with patch('core.utilities.audit_logging_utility.AuditLogService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            old_values = {'name': 'old_name', 'status': 'active'}
            new_values = {'name': 'new_name', 'status': 'inactive'}
            
            AuditLogHelper.log_data_modification(
                user_id=1,
                operation='update_appointment',
                resource_type='appointment',
                resource_id='123',
                old_values=old_values,
                new_values=new_values
            )
            
            mock_service.log_operation.assert_called_once()
            call_args = mock_service.log_operation.call_args[1]
            assert call_args['user_id'] == 1
            assert call_args['action_type'] == 'data_modification'
            assert call_args['operation'] == 'update_appointment'
            assert call_args['resource_type'] == 'appointment'
            assert call_args['resource_id'] == '123'
            assert 'changes' in call_args['details']
            assert 'name' in call_args['details']['changes']
            assert 'status' in call_args['details']['changes']
