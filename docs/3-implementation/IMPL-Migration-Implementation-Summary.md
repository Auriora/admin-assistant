---
title: "Implementation: Database Migration Implementation Summary"
id: "IMPL-Migration-Implementation-Summary"
type: [ implementation, migration ]
status: [ accepted ]
owner: "Auriora Team"
last_reviewed: "DD-MM-YYYY"
tags: [implementation, migration, database, alembic]
links:
  tooling: []
---

# Implementation Guide: Database Migration Implementation Summary

- **Owner**: Auriora Team
- **Status**: Accepted
- **Created Date**: DD-MM-YYYY
- **Last Updated**: DD-MM-YYYY
- **Audience**: [Developers, Database Administrators]
- **Scope**: Root

## 1. Purpose

This document summarizes the implementation of a proper Alembic migration for the restoration configuration tables. This change aligns with the project's established database migration patterns, ensuring proper version control, rollback capabilities, and consistency across environments.

## 2. Key Concepts

### 2.1. Overview of Changes

-   **Removed Standalone Script**: The `scripts/create_restoration_tables.py` script was removed as it did not conform to the project's Alembic migration pattern.
-   **Created Alembic Migration**: A new Alembic migration file, `src/core/migrations/versions/add_restoration_configurations_table.py`, was created.
    -   **Revision ID**: `add_restoration_configurations_table`
    -   **Revises**: `migrate_calendar_uris_user_friendly`

### 2.2. Migration Features

#### Table Creation

```sql
CREATE TABLE restoration_configurations (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    source_type VARCHAR(50) NOT NULL,
    source_config JSON NOT NULL,
    destination_type VARCHAR(50) NOT NULL,
    destination_config JSON NOT NULL,
    restoration_policy JSON,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

#### Indexes for Performance

-   `ix_restoration_configurations_user_id`
-   `ix_restoration_configurations_source_type`
-   `ix_restoration_configurations_destination_type`
-   `ix_restoration_configurations_is_active`
-   `ix_restoration_configurations_user_active`

#### Foreign Key Constraints

-   `fk_restoration_configurations_user_id` references `users.id` with CASCADE delete.

#### Sample Data

The migration automatically inserts three sample restoration configurations: Audit Log Recovery, Backup to MSGraph, and Import from CSV (inactive by default).

### 2.3. Benefits of Proper Migration

-   **Version Control Integration**: Migration files are tracked in Git, providing a clear revision history and consistent database state across environments.
-   **Rollback Capabilities**: The migration is fully reversible using `alembic downgrade`, ensuring safe rollbacks and data protection.
-   **Environment Consistency**: Ensures the same migration runs in all environments (development, testing, production).
-   **Performance Optimization**: Proper indexes and foreign key constraints are applied from creation.
-   **Integration with Existing Patterns**: Follows project standards and integrates with existing Alembic and CLI infrastructure.

## 3. Usage

### 3.1. Usage Instructions

#### For New Installations

```bash
# Initialize database with all migrations
./dev db init

# Or apply all migrations to an existing database
./dev db upgrade
```

#### For Existing Installations

```bash
# Check current migration status
./dev db current

# Apply pending migrations (including restoration tables)
./dev db upgrade
```

### 3.2. Verification Steps

1.  **Check Migration Applied**:
    ```bash
    ./dev db current
    # Should show: add_restoration_configurations_table
    ```
2.  **Verify Table Creation**:
    ```bash
    admin-assistant restore list-configs --user 1
    # Should show 3 sample configurations
    ```
3.  **Test CLI Integration**:
    ```bash
    admin-assistant restore --help
    admin-assistant restore from-audit-logs --user 1 --dry-run
    ```

## 4. Internal Behaviour

### 4.1. Migration File Structure

```python
"""Add restoration_configurations table

Revision ID: add_restoration_configurations_table
Revises: migrate_calendar_uris_user_friendly
Create Date: 2025-01-27 15:00:00.000000
"""

def upgrade() -> None:
    """Add restoration_configurations table."""
    # ... table creation, indexes, constraints, sample data ...

def downgrade() -> None:
    """Remove restoration_configurations table."""
    # ... drop constraints, indexes, table ...
```

### 4.2. Migration Safety Features

-   **Upgrade Safety**: Creates the table with proper constraints and indexes, handles missing users gracefully for sample data, and is non-destructive.
-   **Downgrade Safety**: Properly removes foreign key constraints, indexes, and the table, ensuring a complete cleanup of all migration artifacts.
-   **Error Handling**: Sample data creation failures do not stop the entire migration, and detailed error reporting is provided.

### 4.3. Migration Chain

The restoration migration fits into the existing migration chain:

`... → migrate_calendar_uris_user_friendly → add_restoration_configurations_table → (future migrations)`

This ensures proper dependencies, a clean chain, and future compatibility.

### 4.4. Rollback Plan

If issues arise, the migration can be safely rolled back:

```bash
# Rollback the restoration migration
alembic downgrade migrate_calendar_uris_user_friendly
```

### 4.5. Success Criteria

-   ✅ Migration file created and versioned.
-   ✅ Table structure, indexes, and constraints are correct.
-   ✅ Working sample configurations are created.
-   ✅ Documentation is updated.
-   ✅ Rollback is clean and tested.
-   ✅ CLI integration works with migrated tables.

## 5. Extension Points

### 5.1. Next Steps

-   Update any dependent services that use restoration configurations.

# References

-   [Current Database Schema](DATA-002-Current-Schema.md)
-   [System Architecture](ARCH-001-System-Architecture.md)
