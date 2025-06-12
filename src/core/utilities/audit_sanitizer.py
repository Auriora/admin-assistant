"""
Audit Data Sanitization Utility

Provides functions to convert complex Python objects into JSON-serializable
representations for audit logging. Handles SQLAlchemy models, datetime objects,
and other non-serializable types while preserving meaningful information.
"""

import datetime
from typing import Any, Dict, List, Set, Union, Optional
import logging

logger = logging.getLogger(__name__)


def sanitize_for_audit(
    obj: Any, 
    max_depth: int = 10, 
    _seen: Optional[Set[int]] = None, 
    _current_depth: int = 0
) -> Any:
    """
    Convert any Python object to a JSON-serializable representation suitable for audit logging.
    
    Args:
        obj: The object to sanitize
        max_depth: Maximum recursion depth to prevent infinite loops
        _seen: Set of object IDs already processed (for cycle detection)
        _current_depth: Current recursion depth
        
    Returns:
        JSON-serializable representation of the object
        
    Raises:
        ValueError: If max_depth is exceeded
    """
    if _seen is None:
        _seen = set()
    
    # Prevent infinite recursion
    if _current_depth > max_depth:
        return f"<max_depth_exceeded:{type(obj).__name__}>"
    
    # Handle None
    if obj is None:
        return None
    
    # Handle already JSON-safe primitive types
    if isinstance(obj, (str, int, float, bool)):
        return obj
    
    # Prevent circular references
    obj_id = id(obj)
    if obj_id in _seen:
        return f"<circular_reference:{type(obj).__name__}>"
    
    # Handle datetime objects
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    
    if isinstance(obj, datetime.date):
        return obj.isoformat()
    
    # Handle lists and tuples
    if isinstance(obj, (list, tuple)):
        _seen.add(obj_id)
        try:
            result = [
                sanitize_for_audit(item, max_depth, _seen, _current_depth + 1)
                for item in obj
            ]
            return result
        finally:
            _seen.discard(obj_id)
    
    # Handle dictionaries
    if isinstance(obj, dict):
        _seen.add(obj_id)
        try:
            result = {}
            for key, value in obj.items():
                # Ensure keys are strings
                safe_key = str(key) if not isinstance(key, str) else key
                result[safe_key] = sanitize_for_audit(
                    value, max_depth, _seen, _current_depth + 1
                )
            return result
        finally:
            _seen.discard(obj_id)
    
    # Handle SQLAlchemy model instances
    if hasattr(obj, '__table__'):
        return _sanitize_sqlalchemy_model(obj, max_depth, _seen, _current_depth)
    
    # Handle sets (convert to lists)
    if isinstance(obj, set):
        _seen.add(obj_id)
        try:
            return [
                sanitize_for_audit(item, max_depth, _seen, _current_depth + 1)
                for item in obj
            ]
        finally:
            _seen.discard(obj_id)
    
    # Handle other iterables (but not strings)
    if hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
        try:
            _seen.add(obj_id)
            return [
                sanitize_for_audit(item, max_depth, _seen, _current_depth + 1)
                for item in obj
            ]
        except Exception:
            # If iteration fails, fall back to string representation
            return str(obj)
        finally:
            _seen.discard(obj_id)
    
    # For any other object, try to get a meaningful string representation
    try:
        return str(obj)
    except Exception as e:
        logger.warning(f"Failed to convert object {type(obj)} to string: {e}")
        return f"<unserializable:{type(obj).__name__}>"


def _sanitize_sqlalchemy_model(
    model: Any, 
    max_depth: int, 
    _seen: Set[int], 
    _current_depth: int
) -> Dict[str, Any]:
    """
    Convert a SQLAlchemy model instance to a sanitized dictionary.
    
    Args:
        model: SQLAlchemy model instance
        max_depth: Maximum recursion depth
        _seen: Set of seen object IDs
        _current_depth: Current recursion depth
        
    Returns:
        Dictionary with model's key attributes
    """
    from sqlalchemy.orm.attributes import InstrumentedAttribute
    from sqlalchemy.inspection import inspect
    
    result = {
        "_model_type": type(model).__name__,
        "_table_name": getattr(model.__table__, 'name', 'unknown') if hasattr(model, '__table__') else 'unknown'
    }
    
    # Add primary key if available
    try:
        mapper = inspect(model.__class__)
        pk_columns = [col.name for col in mapper.primary_key]
        for pk_col in pk_columns:
            if hasattr(model, pk_col):
                pk_value = getattr(model, pk_col)
                result[f"_pk_{pk_col}"] = sanitize_for_audit(
                    pk_value, max_depth, _seen, _current_depth + 1
                )
    except Exception:
        pass
    
    # Add model-specific key fields
    if type(model).__name__ == 'Appointment':
        return _sanitize_appointment_model(model, result, max_depth, _seen, _current_depth)
    elif type(model).__name__ == 'User':
        return _sanitize_user_model(model, result, max_depth, _seen, _current_depth)
    elif type(model).__name__ == 'Calendar':
        return _sanitize_calendar_model(model, result, max_depth, _seen, _current_depth)
    
    # For other models, include basic identifying information
    identifying_fields = ['id', 'name', 'title', 'subject', 'email']
    for field in identifying_fields:
        if hasattr(model, field):
            try:
                value = getattr(model, field)
                if not isinstance(value, InstrumentedAttribute):
                    result[field] = sanitize_for_audit(
                        value, max_depth, _seen, _current_depth + 1
                    )
            except Exception:
                continue
    
    return result


def _sanitize_appointment_model(
    appointment: Any, 
    base_result: Dict[str, Any], 
    max_depth: int, 
    _seen: Set[int], 
    _current_depth: int
) -> Dict[str, Any]:
    """Sanitize Appointment model with relevant fields for audit logging."""
    key_fields = [
        'id', 'subject', 'start_time', 'end_time', 'location', 
        'show_as', 'sensitivity', 'is_archived', 'calendar_id',
        'user_id', 'category_id', 'ms_event_id'
    ]
    
    for field in key_fields:
        if hasattr(appointment, field):
            try:
                value = getattr(appointment, field)
                base_result[field] = sanitize_for_audit(
                    value, max_depth, _seen, _current_depth + 1
                )
            except Exception:
                continue
    
    return base_result


def _sanitize_user_model(
    user: Any, 
    base_result: Dict[str, Any], 
    max_depth: int, 
    _seen: Set[int], 
    _current_depth: int
) -> Dict[str, Any]:
    """Sanitize User model with relevant fields for audit logging."""
    key_fields = ['id', 'email', 'name', 'is_active']
    
    for field in key_fields:
        if hasattr(user, field):
            try:
                value = getattr(user, field)
                base_result[field] = sanitize_for_audit(
                    value, max_depth, _seen, _current_depth + 1
                )
            except Exception:
                continue
    
    return base_result


def _sanitize_calendar_model(
    calendar: Any, 
    base_result: Dict[str, Any], 
    max_depth: int, 
    _seen: Set[int], 
    _current_depth: int
) -> Dict[str, Any]:
    """Sanitize Calendar model with relevant fields for audit logging."""
    key_fields = ['id', 'name', 'calendar_id', 'user_id', 'is_default']
    
    for field in key_fields:
        if hasattr(calendar, field):
            try:
                value = getattr(calendar, field)
                base_result[field] = sanitize_for_audit(
                    value, max_depth, _seen, _current_depth + 1
                )
            except Exception:
                continue
    
    return base_result


def sanitize_audit_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to sanitize a dictionary of audit data.
    
    Args:
        data: Dictionary containing audit data
        
    Returns:
        Sanitized dictionary safe for JSON serialization
    """
    if not isinstance(data, dict):
        return sanitize_for_audit(data)
    
    return sanitize_for_audit(data)
