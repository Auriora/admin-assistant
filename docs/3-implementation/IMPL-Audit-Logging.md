---
title: "Implementation: Audit Logging"
id: "IMPL-Audit-Logging"
type: [ implementation ]
status: [ draft ]
owner: "Auriora Team"
last_reviewed: "DD-MM-YYYY"
tags: [implementation, audit, logging, security, compliance]
links:
  tooling: []
---

# Implementation Guide: Audit Logging

- **Owner**: Auriora Team
- **Status**: Draft
- **Created Date**: DD-MM-YYYY
- **Last Updated**: DD-MM-YYYY
- **Audience**: [Developers, SRE, Compliance]
- **Scope**: Root

## 1. Purpose

This document details the comprehensive audit logging implementation for the Admin Assistant system. The audit logging system provides complete traceability for all archiving actions, overlap resolutions, and re-archiving operations, ensuring compliance, enabling troubleshooting, and supporting security requirements.

## 2. Key Concepts

### 2.1. Architecture Components

1.  **AuditLog Model** (`core/models/audit_log.py`): A dedicated database table for audit entries, distinct from `ActionLog` (which is for task management). It includes comprehensive fields for traceability and compliance.
2.  **AuditLogRepository** (`core/repositories/audit_log_repository.py`): The data access layer for audit log operations, optimized for performance with proper indexing.
3.  **AuditLogService** (`core/services/audit_log_service.py`): Provides business logic for audit logging, including convenient methods for different operation types and correlation ID management for tracing.
4.  **Audit Utilities** (`core/utilities/audit_logging_utility.py`): Offers an `AuditContext` context manager for automatic logging and decorators for function-level audit logging.

### 2.2. Database Schema (`AuditLog` Table)

```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    action_type VARCHAR(64) NOT NULL,     -- e.g., 'archive', 'overlap_resolution', 'api_call'
    operation VARCHAR(128) NOT NULL,      -- e.g., 'calendar_archive', 'resolve_overlap', 'msgraph_api_call'
    resource_type VARCHAR(64),            -- e.g., 'appointment', 'calendar', 'user'
    resource_id VARCHAR(128),             -- ID of the affected resource
    status VARCHAR(32) NOT NULL,          -- e.g., 'success', 'failure', 'partial'
    message TEXT,                         -- Human-readable description
    details JSON,                         -- Operation-specific details
    request_data JSON,                    -- Input parameters/data
    response_data JSON,                   -- Output/results
    duration_ms FLOAT,                    -- Operation duration in milliseconds
    ip_address VARCHAR(45),               -- IPv4/IPv6 address
    user_agent VARCHAR(512),              -- Browser/client info
    correlation_id VARCHAR(128),          -- For tracking related operations
    parent_audit_id INTEGER REFERENCES audit_log(id), -- For nested operations
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### 2.3. Indexes

Key indexes are defined for efficient querying, including `ix_audit_log_user_id`, `ix_audit_log_action_type`, `ix_audit_log_correlation_id`, and composite indexes for common query patterns.

### 2.4. Security and Privacy

-   **Data Sanitization**: Sensitive data is sanitized before logging.
-   **Access Control**: Audit logs are protected by user-based access control.
-   **Encryption**: Consideration for encryption of sensitive audit data.
-   **Anonymization**: Personal data can be anonymized for long-term retention.

## 3. Usage

### 3.1. Basic Audit Logging

```python
from core.services.audit_log_service import AuditLogService

audit_service = AuditLogService()

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

### 3.2. Using `AuditContext`

```python
from core.utilities.audit_logging_utility import AuditContext

with AuditContext(
    audit_service=audit_service,
    user_id=1,
    action_type='archive',
    operation='calendar_archive',
    resource_type='calendar',
    resource_id='msgraph://calendar'
) as audit_ctx:
    audit_ctx.add_detail('phase', 'initialization')
    result = perform_archive_operation()
    audit_ctx.set_response_data(result)
    # Context manager automatically logs success/failure with duration
```

### 3.3. Using Audit Decorator

```python
from core.utilities.audit_logging_utility import audit_operation

@audit_operation('archive', 'calendar_archive', 'calendar')
def archive_appointments(user_id, calendar_id, start_date, end_date):
    # Function implementation
    # Audit logging happens automatically
    return {'archived_count': 25, 'overlap_count': 3}
```

### 3.4. Querying Audit Logs

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

# Get complete audit trail for a correlation ID
correlation_id = 'uuid-correlation-id'
audit_trail = audit_service.get_audit_trail(correlation_id)
```

## 4. Internal Behaviour

### 4.1. Integration Points

-   **`CalendarArchiveOrchestrator`**: Enhanced with comprehensive audit logging for operation start, phase tracking, error handling, performance metrics, and correlation.
-   **`OverlapResolutionOrchestrator`**: Includes detailed audit logging for resolution actions, data changes, user decisions, and traceability to original overlap detection.

### 4.2. Performance Considerations

-   **Indexing**: Comprehensive indexes are crucial for common query patterns.
-   **Partitioning**: Consider table partitioning for very large datasets.
-   **Archiving**: Regular archival of old audit logs to separate storage.
-   **Async Logging**: Consider asynchronous logging for high-volume operations.

### 4.3. Compliance and Retention

-   **Data Retention**: Provides functionality to clean up old audit logs (e.g., older than 7 years for compliance).
-   **Export**: Audit logs can be exported for compliance reporting in various formats (CSV, Excel, PDF).

### 4.4. Testing

A comprehensive test suite covers model creation, repository operations, service business logic, context manager, decorator behavior, and integration with orchestrators.

### 4.5. Migration

Database changes for audit logging are applied via Alembic migrations. Commands like `alembic upgrade head` are used to apply pending migrations.

### 4.6. Monitoring and Alerting

Monitoring should be set up for high failure rates, unusual user activity patterns, performance degradation, and storage growth of the audit log table.

## 5. Extension Points

-   **Real-time Dashboards**: Audit log visualization for immediate insights.
-   **Anomaly Detection**: Machine learning-based detection of unusual patterns.
-   **Integration**: Export to external Security Information and Event Management (SIEM) systems.
-   **Advanced Analytics**: Trend analysis and reporting capabilities.
-   **Compliance Automation**: Automated generation of compliance reports.

# References

-   [System Architecture](../2-architecture/ARCH-001-System-Architecture.md)
-   [Observability Design](../2-architecture/ARCH-002-Observability.md)
-   [Current Database Schema](../2-architecture/DATA-002-Current-Schema.md)