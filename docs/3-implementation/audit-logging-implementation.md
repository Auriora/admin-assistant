# Audit Logging Implementation

## Overview

This document describes the comprehensive audit logging implementation for the Admin Assistant system. The audit logging system provides complete traceability for all archiving actions, overlap resolutions, and re-archiving operations, ensuring compliance and enabling troubleshooting.

## Architecture

### Components

1. **AuditLog Model** (`core/models/audit_log.py`)
   - Dedicated database table for audit entries
   - Separate from ActionLog (which is for task management)
   - Comprehensive fields for traceability and compliance

2. **AuditLogRepository** (`core/repositories/audit_log_repository.py`)
   - Data access layer for audit log operations
   - Advanced querying and filtering capabilities
   - Optimized for performance with proper indexing

3. **AuditLogService** (`core/services/audit_log_service.py`)
   - Business logic for audit logging
   - Convenient methods for different operation types
   - Correlation ID management for operation tracing

4. **Audit Utilities** (`core/utilities/audit_logging_utility.py`)
   - AuditContext context manager for automatic logging
   - Decorators for function-level audit logging
   - Helper functions for common audit patterns

## Database Schema

### AuditLog Table

```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    
    -- Core audit fields
    action_type VARCHAR(64) NOT NULL,     -- 'archive', 'overlap_resolution', 're_archive', 'api_call'
    operation VARCHAR(128) NOT NULL,      -- 'calendar_archive', 'resolve_overlap', 'msgraph_api_call'
    resource_type VARCHAR(64),            -- 'appointment', 'calendar', 'user'
    resource_id VARCHAR(128),             -- ID of the affected resource
    
    -- Status and outcome
    status VARCHAR(32) NOT NULL,          -- 'success', 'failure', 'partial'
    message TEXT,                         -- Human-readable description
    
    -- Detailed context and metadata
    details JSON,                         -- Operation-specific details
    request_data JSON,                    -- Input parameters/data
    response_data JSON,                   -- Output/results
    
    -- Performance and technical details
    duration_ms FLOAT,                    -- Operation duration in milliseconds
    ip_address VARCHAR(45),               -- IPv4/IPv6 address
    user_agent VARCHAR(512),              -- Browser/client info
    
    -- Traceability
    correlation_id VARCHAR(128),          -- For tracking related operations
    parent_audit_id INTEGER REFERENCES audit_log(id), -- For nested operations
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### Indexes

- `ix_audit_log_user_id` - For user-specific queries
- `ix_audit_log_action_type` - For filtering by action type
- `ix_audit_log_operation` - For filtering by operation
- `ix_audit_log_status` - For filtering by status
- `ix_audit_log_correlation_id` - For tracing related operations
- `ix_audit_log_created_at` - For date-based queries
- `ix_audit_log_user_action_type` - Composite index for common queries
- `ix_audit_log_user_created_at` - Composite index for user activity over time

## Usage Examples

### Basic Audit Logging

```python
from core.services.audit_log_service import AuditLogService

audit_service = AuditLogService()

# Log a simple operation
audit_log = audit_service.log_operation(
    user_id=1,
    action_type='archive',
    operation='calendar_archive',
    status='success',
    message='Successfully archived 25 appointments',
    resource_type='calendar',
    resource_id='msgraph://calendar',
    details={'archived_count': 25, 'overlap_count': 3}
)
```

### Archive Operation Logging

```python
# Log archive operation with specific context
audit_log = audit_service.log_archive_operation(
    user_id=1,
    operation='calendar_archive',
    status='success',
    source_calendar_uri='msgraph://calendar',
    archive_calendar_id='archive-123',
    start_date=date(2024, 1, 1),
    end_date=date(2024, 1, 31),
    archived_count=25,
    overlap_count=3,
    duration_ms=1500.5
)
```

### Overlap Resolution Logging

```python
# Log overlap resolution
audit_log = audit_service.log_overlap_resolution(
    user_id=1,
    action_log_id=123,
    resolution_type='merge',
    status='success',
    appointments_affected=['appt1', 'appt2', 'appt3'],
    resolution_data={'merge': {'into': 'appt1', 'from': ['appt2', 'appt3']}},
    ai_recommendations={'suggested_action': 'merge', 'confidence': 0.85}
)
```

### Using AuditContext

```python
from core.utilities.audit_logging_utility import AuditContext

# Automatic audit logging with context manager
with AuditContext(
    audit_service=audit_service,
    user_id=1,
    action_type='archive',
    operation='calendar_archive',
    resource_type='calendar',
    resource_id='msgraph://calendar'
) as audit_ctx:
    
    # Add operation details
    audit_ctx.add_detail('phase', 'initialization')
    audit_ctx.set_request_data({'start_date': '2024-01-01', 'end_date': '2024-01-31'})
    
    # Perform the operation
    result = perform_archive_operation()
    
    # Add response data
    audit_ctx.set_response_data(result)
    
    # Context manager automatically logs success/failure with duration
```

### Using Audit Decorator

```python
from core.utilities.audit_logging_utility import audit_operation

@audit_operation('archive', 'calendar_archive', 'calendar')
def archive_appointments(user_id, calendar_id, start_date, end_date):
    # Function implementation
    # Audit logging happens automatically
    return {'archived_count': 25, 'overlap_count': 3}
```

### Correlation ID for Operation Tracing

```python
# Generate correlation ID for related operations
correlation_id = audit_service.generate_correlation_id()

# Use same correlation ID across related operations
audit_service.log_operation(
    user_id=1,
    action_type='archive',
    operation='fetch_appointments',
    status='success',
    correlation_id=correlation_id
)

audit_service.log_operation(
    user_id=1,
    action_type='archive',
    operation='process_overlaps',
    status='success',
    correlation_id=correlation_id
)

# Later, retrieve all related operations
audit_trail = audit_service.get_audit_trail(correlation_id)
```

## Integration Points

### CalendarArchiveOrchestrator

The `CalendarArchiveOrchestrator` has been enhanced with comprehensive audit logging:

- **Operation Start**: Logs the beginning of archiving with parameters
- **Phase Tracking**: Logs each phase (fetching, processing, archiving, etc.)
- **Error Handling**: Automatically logs failures with stack traces
- **Performance Metrics**: Tracks operation duration
- **Correlation**: Links all related operations with correlation ID

### OverlapResolutionOrchestrator

The `OverlapResolutionOrchestrator` includes detailed audit logging for:

- **Resolution Actions**: Logs each type of resolution (keep, edit, merge, create, delete)
- **Data Changes**: Tracks before/after values for modified appointments
- **User Decisions**: Records user choices and AI recommendations
- **Traceability**: Links resolution actions to original overlap detection

## Querying and Analysis

### Search Audit Logs

```python
# Search with filters
filters = {
    'user_id': 1,
    'action_type': 'archive',
    'start_date': date(2024, 1, 1),
    'end_date': date(2024, 1, 31),
    'status': 'success'
}

audit_logs = audit_service.search_audit_logs(filters, limit=100)
```

### Get Audit Summary

```python
# Get activity summary for a user
summary = audit_service.get_audit_summary(user_id=1, days=30)
# Returns:
# {
#     'total_operations': 150,
#     'by_action_type': {'archive': 45, 'overlap_resolution': 12, ...},
#     'by_status': {'success': 140, 'failure': 8, 'partial': 2},
#     'by_operation': {'calendar_archive': 30, 'resolve_overlap': 12, ...}
# }
```

### Trace Operation Chain

```python
# Get complete audit trail for a correlation ID
correlation_id = 'uuid-correlation-id'
audit_trail = audit_service.get_audit_trail(correlation_id)

# Shows all related operations in chronological order
for audit_log in audit_trail:
    print(f"{audit_log.created_at}: {audit_log.operation} - {audit_log.status}")
```

## Compliance and Retention

### Data Retention

```python
# Clean up old audit logs (e.g., older than 7 years for compliance)
deleted_count = audit_service.cleanup_old_logs(older_than_days=2555)  # 7 years
print(f"Deleted {deleted_count} old audit log entries")
```

### Export for Compliance

```python
# Export audit logs for compliance reporting
filters = {
    'start_date': date(2024, 1, 1),
    'end_date': date(2024, 12, 31),
    'action_type': 'archive'
}

audit_logs = audit_service.search_audit_logs(filters)
# Export to CSV, Excel, or PDF as needed
```

## Performance Considerations

1. **Indexing**: Comprehensive indexes for common query patterns
2. **Partitioning**: Consider table partitioning for large datasets
3. **Archiving**: Regular archival of old audit logs to separate storage
4. **Async Logging**: Consider async logging for high-volume operations
5. **Batch Operations**: Use correlation IDs to group related operations

## Security and Privacy

1. **Data Sanitization**: Sensitive data is sanitized before logging
2. **Access Control**: Audit logs are protected by user-based access control
3. **Encryption**: Consider encryption for sensitive audit data
4. **Anonymization**: Personal data can be anonymized for long-term retention

## Testing

Comprehensive test suite covers:

- Model creation and validation
- Repository operations and querying
- Service business logic
- Context manager functionality
- Decorator behavior
- Integration with orchestrators

Run tests with:
```bash
pytest tests/test_audit_logging.py -v
```

## Migration

To apply the audit logging database changes:

```bash
# Run the migration
alembic upgrade head

# Or apply specific migration
alembic upgrade add_audit_log_table
```

## Monitoring and Alerting

Consider setting up monitoring for:

- High failure rates in audit logs
- Unusual patterns in user activity
- Performance degradation in audit operations
- Storage growth of audit log table

## Future Enhancements

1. **Real-time Dashboards**: Audit log visualization
2. **Anomaly Detection**: ML-based detection of unusual patterns
3. **Integration**: Export to external SIEM systems
4. **Advanced Analytics**: Trend analysis and reporting
5. **Compliance Automation**: Automated compliance report generation
