import time
import functools
import traceback
from typing import Any, Callable, Optional, Dict, Union
from datetime import datetime
from core.services.audit_log_service import AuditLogService


class AuditContext:
    """
    Context manager for audit logging that automatically tracks operation duration
    and handles success/failure logging.
    """
    
    def __init__(self, 
                 audit_service: AuditLogService,
                 user_id: int,
                 action_type: str,
                 operation: str,
                 resource_type: Optional[str] = None,
                 resource_id: Optional[str] = None,
                 correlation_id: Optional[str] = None,
                 parent_audit_id: Optional[int] = None):
        self.audit_service = audit_service
        self.user_id = user_id
        self.action_type = action_type
        self.operation = operation
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.correlation_id = correlation_id
        self.parent_audit_id = parent_audit_id
        self.start_time = None
        self.audit_log = None
        self.details = {}
        self.request_data = {}
        self.response_data = {}
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000 if self.start_time else None
        
        if exc_type is None:
            # Success case
            status = 'success'
            message = f"Operation {self.operation} completed successfully"
        else:
            # Failure case
            status = 'failure'
            message = f"Operation {self.operation} failed: {str(exc_val)}"
            self.details['error'] = {
                'type': exc_type.__name__ if exc_type else None,
                'message': str(exc_val) if exc_val else None,
                'traceback': traceback.format_exc() if exc_tb else None
            }
        
        self.audit_log = self.audit_service.log_operation(
            user_id=self.user_id,
            action_type=self.action_type,
            operation=self.operation,
            status=status,
            message=message,
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            details=self.details,
            request_data=self.request_data,
            response_data=self.response_data,
            duration_ms=duration_ms,
            correlation_id=self.correlation_id,
            parent_audit_id=self.parent_audit_id
        )
        
        # Don't suppress exceptions
        return False
    
    def add_detail(self, key: str, value: Any):
        """Add a detail to the audit log."""
        self.details[key] = value
    
    def set_request_data(self, data: Dict[str, Any]):
        """Set the request data for the audit log."""
        self.request_data = data
    
    def set_response_data(self, data: Dict[str, Any]):
        """Set the response data for the audit log."""
        self.response_data = data
    
    def update_resource(self, resource_type: str, resource_id: str):
        """Update the resource information."""
        self.resource_type = resource_type
        self.resource_id = resource_id


def audit_operation(action_type: str, 
                   operation: str,
                   resource_type: Optional[str] = None,
                   auto_extract_user_id: bool = True,
                   correlation_id_param: Optional[str] = None):
    """
    Decorator for automatically auditing function calls.
    
    Args:
        action_type: High-level action category
        operation: Specific operation name
        resource_type: Type of resource being operated on
        auto_extract_user_id: Whether to automatically extract user_id from function args
        correlation_id_param: Name of parameter containing correlation_id
    
    Usage:
        @audit_operation('archive', 'calendar_archive', 'calendar')
        def archive_appointments(user_id, calendar_id, ...):
            # Function implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract user_id
            user_id = None
            if auto_extract_user_id:
                # Try to find user_id in kwargs first
                if 'user_id' in kwargs:
                    user_id = kwargs['user_id']
                # Try to find user object and extract id
                elif 'user' in kwargs:
                    user = kwargs['user']
                    user_id = getattr(user, 'id', None)
                # Try first positional argument if it looks like a user_id
                elif args and isinstance(args[0], int):
                    user_id = args[0]
                # Try second positional argument if first is user object
                elif len(args) > 1 and hasattr(args[0], 'id'):
                    user_id = getattr(args[0], 'id')
            
            if user_id is None:
                # If we can't extract user_id, just call the function without auditing
                return func(*args, **kwargs)
            
            # Extract correlation_id if specified
            correlation_id = None
            if correlation_id_param and correlation_id_param in kwargs:
                correlation_id = kwargs[correlation_id_param]
            
            # Create audit service
            audit_service = AuditLogService()
            
            # Extract resource_id if possible
            resource_id = None
            if 'calendar_id' in kwargs:
                resource_id = kwargs['calendar_id']
            elif 'appointment_id' in kwargs:
                resource_id = kwargs['appointment_id']
            elif 'action_log_id' in kwargs:
                resource_id = str(kwargs['action_log_id'])
            
            with AuditContext(
                audit_service=audit_service,
                user_id=user_id,
                action_type=action_type,
                operation=operation,
                resource_type=resource_type,
                resource_id=resource_id,
                correlation_id=correlation_id
            ) as audit_ctx:
                # Add function arguments to request data
                audit_ctx.set_request_data({
                    'args': [str(arg) for arg in args],  # Convert to strings for JSON serialization
                    'kwargs': {k: str(v) for k, v in kwargs.items()}
                })
                
                # Call the original function
                result = func(*args, **kwargs)
                
                # Add result to response data if it's serializable
                try:
                    if isinstance(result, (dict, list, str, int, float, bool, type(None))):
                        audit_ctx.set_response_data({'result': result})
                    elif hasattr(result, '__dict__'):
                        audit_ctx.set_response_data({'result_type': type(result).__name__})
                except Exception:
                    # If we can't serialize the result, just log the type
                    audit_ctx.set_response_data({'result_type': type(result).__name__})
                
                return result
        
        return wrapper
    return decorator


class AuditLogHelper:
    """
    Helper class for common audit logging patterns.
    """
    
    @staticmethod
    def create_correlation_id() -> str:
        """Create a new correlation ID."""
        audit_service = AuditLogService()
        return audit_service.generate_correlation_id()
    
    @staticmethod
    def log_batch_operation_start(user_id: int, 
                                 operation: str, 
                                 batch_size: int,
                                 correlation_id: str) -> int:
        """
        Log the start of a batch operation and return the audit log ID.
        """
        audit_service = AuditLogService()
        audit_log = audit_service.log_operation(
            user_id=user_id,
            action_type='batch_operation',
            operation=f'{operation}_batch_start',
            status='in_progress',
            message=f"Started batch operation {operation} with {batch_size} items",
            details={'batch_size': batch_size, 'phase': 'start'},
            correlation_id=correlation_id
        )
        return audit_log.id
    
    @staticmethod
    def log_batch_operation_end(user_id: int,
                               operation: str,
                               parent_audit_id: int,
                               success_count: int,
                               failure_count: int,
                               correlation_id: str):
        """
        Log the completion of a batch operation.
        """
        audit_service = AuditLogService()
        total_count = success_count + failure_count
        status = 'success' if failure_count == 0 else ('partial' if success_count > 0 else 'failure')
        
        audit_service.log_operation(
            user_id=user_id,
            action_type='batch_operation',
            operation=f'{operation}_batch_end',
            status=status,
            message=f"Completed batch operation {operation}: {success_count}/{total_count} successful",
            details={
                'success_count': success_count,
                'failure_count': failure_count,
                'total_count': total_count,
                'phase': 'end'
            },
            correlation_id=correlation_id,
            parent_audit_id=parent_audit_id
        )
    
    @staticmethod
    def log_data_modification(user_id: int,
                            operation: str,
                            resource_type: str,
                            resource_id: str,
                            old_values: Dict[str, Any],
                            new_values: Dict[str, Any],
                            correlation_id: Optional[str] = None):
        """
        Log data modification operations with before/after values.
        """
        audit_service = AuditLogService()
        
        changes = {}
        for key in set(old_values.keys()) | set(new_values.keys()):
            old_val = old_values.get(key)
            new_val = new_values.get(key)
            if old_val != new_val:
                changes[key] = {'old': old_val, 'new': new_val}
        
        audit_service.log_operation(
            user_id=user_id,
            action_type='data_modification',
            operation=operation,
            status='success',
            message=f"Modified {resource_type} {resource_id}: {len(changes)} fields changed",
            resource_type=resource_type,
            resource_id=resource_id,
            details={
                'changes': changes,
                'fields_modified': list(changes.keys())
            },
            correlation_id=correlation_id
        )
