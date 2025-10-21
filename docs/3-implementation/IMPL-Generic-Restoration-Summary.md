---
title: "Implementation: Generic Appointment Restoration Feature"
id: "IMPL-Generic-Restoration-Summary"
type: [ implementation, feature ]
status: [ accepted ]
owner: "Auriora Team"
last_reviewed: "DD-MM-YYYY"
tags: [implementation, restoration, calendar, cli]
links:
  tooling: []
---

# Implementation Guide: Generic Appointment Restoration Feature

- **Owner**: Auriora Team
- **Status**: Accepted
- **Created Date**: DD-MM-YYYY
- **Last Updated**: DD-MM-YYYY
- **Audience**: [Developers, Maintainers]
- **Scope**: Root

## 1. Purpose

This document summarizes the implementation of a generic, configurable appointment restoration feature. It details the conversion of previous restoration scripts into a unified system capable of restoring appointments from multiple sources (audit logs, backup calendars, export files) to various destinations (local calendars, MSGraph calendars, export files).

## 2. Key Concepts

### 2.1. Core Components

#### Models
-   **`src/core/models/restoration_configuration.py`**: New model for `RestorationConfiguration`, defining source/destination types and policies, including validation.

#### Repositories
-   **`src/core/repositories/restoration_configuration_repository.py`**: New repository for CRUD operations on restoration configurations, with advanced search and user-specific management.

#### Services
-   **`src/core/services/appointment_restoration_service.py`**: The main restoration service, offering generic restoration from any source to any destination, configurable policies, comprehensive audit logging, and dry-run capabilities.
-   **`src/core/services/appointment_restoration_service_helpers.py`**: Helper methods for applying policies (duplicate detection, date filtering) and destination-specific restoration logic.
-   **`src/core/services/calendar_backup_service.py`**: New backup service for backing up calendars to files (CSV, JSON, ICS) or other calendars, integrating with the restoration service.

### 2.2. Key Features Implemented

-   **Multiple Source Types**: Supports restoration from Audit Logs, Backup Calendars, and Export Files (CSV, JSON, ICS).
-   **Multiple Destination Types**: Supports restoration to Local Calendars, MSGraph Calendars, and Export Files.
-   **Configurable Restoration Policies**: Includes duplicate detection, date range filtering, and subject/category filtering.
-   **Comprehensive Audit Logging**: All restoration operations are logged for compliance, with detailed metadata and error tracking.
-   **Backward Compatibility**: New CLI provides equivalent functionality while existing audit logs and backup calendars remain compatible.

## 3. Usage

### 3.1. CLI Usage Examples

#### Quick Restoration from Audit Logs

```bash
# Dry run to see what would be restored
python scripts/appointment_restoration_cli.py audit-logs --dry-run

# Restore failed appointments from specific date range
python scripts/appointment_restoration_cli.py audit-logs \
  --start-date 2025-05-29 --end-date 2025-06-06
```

#### Restore from Backup Calendars

```bash
# Consolidate multiple backup calendars
python scripts/appointment_restoration_cli.py backup-calendars \
  --source-calendars "Recovered" "Recovered Missing" \
  --destination-calendar "Consolidated Recovery"
```

#### Create Calendar Backups

```bash
# Backup to CSV file
python scripts/appointment_restoration_cli.py backup \
  --source-calendar "Main Calendar" \
  --backup-destination "backup.csv" \
  --backup-format csv
```

### 3.2. Programmatic Usage

```python
from core.services.appointment_restoration_service import AppointmentRestorationService

service = AppointmentRestorationService(user_id=1)

# Restore from audit logs
result = service.restore_from_audit_logs(
    start_date=date(2025, 5, 29),
    end_date=date(2025, 6, 6),
    destination_calendar="Recovered"
)

print(f"Restored {result['restored']} appointments")
```

### 3.3. Migration from Old Scripts

| Old Script                       | New Command        | Notes                                  |
|----------------------------------|--------------------|----------------------------------------|
| `restore_lost_appointments.py`   | `audit-logs`       | Direct replacement with more options   |
| `restore_missing_appointments.py`| `audit-logs`       | Use custom date ranges                 |
| `restore_to_msgraph_recovery.py` | `backup-calendars` | With MSGraph destination               |
| `export_appointments_for_msgraph.py` | `backup`           | With appropriate format                |

### 3.4. Setup Instructions

1.  **Create Database Tables**:
    ```bash
    python scripts/create_restoration_tables.py
    ```
2.  **Test the Implementation**:
    ```bash
    python scripts/test_restoration_service.py
    ```
3.  **List Available Configurations**:
    ```bash
    python scripts/appointment_restoration_cli.py list-configs
    ```
4.  **Try a Dry Run Restoration**:
    ```bash
    python scripts/appointment_restoration_cli.py audit-logs --dry-run
    ```

## 4. Internal Behaviour

### 4.1. Benefits of the New System

-   **Unified Interface**: A single CLI tool replaces multiple disparate scripts.
-   **Configurable**: Flexible policies allow for diverse restoration scenarios.
-   **Extensible**: Designed for easy addition of new source and destination types.
-   **Auditable**: Comprehensive logging ensures traceability for all operations.
-   **Testable**: Dry-run capabilities provide a safe way to test restoration logic.
-   **Future-Ready**: Includes a built-in backup service for proactive data protection.

### 4.2. Compliance and Audit

-   All restoration operations are logged in the `audit_log` table.
-   Supports reversible operations as per existing audit requirements.
-   Detailed operation metadata is captured for compliance reporting.
-   User-specific operation tracking and permissions are enforced.

## 5. Extension Points

### 5.1. Future Enhancements

The new architecture is designed to easily accommodate:

-   New source types (e.g., Google Calendar, Outlook).
-   New destination types (e.g., cloud storage, other calendar systems).
-   Advanced restoration policies (e.g., AI-based duplicate detection).
-   Scheduled backup operations.
-   A dedicated Web UI for configuration management.

# References

-   [Current Database Schema](../2-architecture/DATA-002-Current-Schema.md)
-   [System Architecture](../2-architecture/ARCH-001-System-Architecture.md)
-   [Audit Logging Implementation](./IMPL-Audit-Logging.md)