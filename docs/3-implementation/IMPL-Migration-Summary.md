---
title: "Implementation: Account Context URI Migration Summary"
id: "IMPL-Migration-Summary"
type: [ implementation, migration ]
status: [ accepted ]
owner: "Auriora Team"
last_reviewed: "DD-MM-YYYY"
tags: [implementation, migration, uri, database, alembic]
links:
  tooling: []
---

# Implementation Guide: Account Context URI Migration Summary

- **Owner**: Auriora Team
- **Status**: Accepted
- **Created Date**: DD-MM-YYYY
- **Last Updated**: DD-MM-YYYY
- **Audience**: [Developers, Database Administrators]
- **Scope**: Root

## 1. Purpose

This document summarizes the Alembic migration `20250610_add_account_context_to_uris.py`, which adds account context to existing calendar URIs and introduces new columns to the `archive_configurations` table. This migration is crucial for enhancing URI management, supporting flexible archiving purposes, and controlling overlap behavior.

## 2. Key Concepts

### 2.1. Migration Details

-   **File Location**: `src/core/migrations/versions/20250610_add_account_context_to_uris.py`
-   **Revision ID**: `20250610_add_account_context_to_uris`
-   **Revises**: `add_restoration_configurations_table`
-   **Create Date**: 2025-06-10 00:00:00.000000

### 2.2. `archive_configurations` Table Updates

#### `allow_overlaps` Column
-   **Type**: Boolean
-   **Default**: `True`
-   **Purpose**: Controls whether overlapping appointments are allowed in archive operations.

#### `archive_purpose` Column
-   **Type**: `String(50)`
-   **Default**: `'general'`
-   **Purpose**: Categorizes the purpose of the archive configuration (e.g., `'Billable - [Customer Name]'`, `'Travel'`).

### 2.3. URI Account Context Migration

This migration updates existing calendar URIs to include account context, ensuring better organization and user-specific data handling.

-   **Before (Legacy Format)**:
    ```
    msgraph://calendars/primary
    local://calendars/personal
    ```
-   **After (New Format with Account Context)**:
    ```
    msgraph://user@example.com/calendars/primary
    local://user@example.com/calendars/personal
    ```

-   **Account Context Priority**: The migration determines account context using user email (preferred), username (fallback), or user ID (last resort).
-   **Edge Case Handling**: The migration gracefully handles missing users, null/empty emails/usernames, already migrated URIs, and malformed URIs.

### 2.4. Model Updates

The `ArchiveConfiguration` SQLAlchemy model (`src/core/models/archive_configuration.py`) has been updated to include the `allow_overlaps` and `archive_purpose` attributes.

## 3. Usage

### 3.1. Business Billing Categories

The `archive_purpose` column enables the creation of configurations tailored for specific billing needs, such as:

```
archive_purpose = 'Billable - Modena'
archive_purpose = 'Non-billable - Modena'
archive_purpose = 'Travel'
```

### 3.2. Overlap Control

The `allow_overlaps` column provides granular control over archiving behavior, allowing for filtering appointments by categories and preventing overlap conflicts in specific scenarios.

## 4. Internal Behaviour

### 4.1. Migration Features

-   **Comprehensive Error Handling**: Individual configuration errors do not halt the entire migration, with detailed logging for troubleshooting.
-   **Migration Statistics**: Provides statistics on processed, updated, skipped, and error configurations, as well as user contexts created.
-   **Validation**: Post-migration validation ensures all configurations have proper account context and URI formatting.
-   **Reversibility**: A comprehensive `downgrade()` function is provided to remove account context and drop new columns, ensuring full rollback capability.

### 4.2. Testing

-   **URI Transformation Logic Testing**: Extensive tests cover adding/removing account context, roundtrip transformations, and edge case handling for various URI formats.
-   **Test Results**: All URI transformation tests pass, confirming correct handling of legacy formats, proper account context addition, and robust edge case management.

### 4.3. Migration Safety

-   **Backup Compatibility**: The migration preserves all existing data and is fully reversible.
-   **Production Readiness**: Tested URI transformation logic, comprehensive error handling, detailed validation, and safe fallback mechanisms ensure production readiness.

### 4.4. Performance Considerations

-   **Indexing**: Comprehensive indexes are in place for common query patterns.
-   **Partitioning**: Consideration for table partitioning for large datasets.
-   **Archiving**: Regular archival of old audit logs to separate storage.

### 4.5. Security and Privacy

-   **Data Sanitization**: Sensitive data is sanitized before logging.
-   **Access Control**: Audit logs are protected by user-based access control.

## 5. Extension Points

### 5.1. Next Steps

1.  Run the migration in a development environment first.
2.  Review migration output and statistics.
3.  Test the new columns in application code.
4.  Update any dependent services that use archive configurations.
5.  Deploy to production after thorough testing.

### 5.2. Monitoring and Alerting

Consider setting up monitoring for high failure rates, unusual patterns in user activity, performance degradation, and storage growth of the audit log table.

# References

-   [URI Transformation Functions](./IMPL-URI-Transformation-Functions.md)
-   [Current Database Schema](../2-architecture/DATA-002-Current-Schema.md)
-   [System Architecture](../2-architecture/ARCH-001-System-Architecture.md)