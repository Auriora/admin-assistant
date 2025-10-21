---
title: "Architecture: Current Database Schema"
id: "DATA-002"
type: [ data, schema, architecture ]
status: [ accepted ]
owner: "Auriora Team"
last_reviewed: "DD-MM-YYYY"
tags: [database, schema, data-model]
links:
  tooling: []
---

# Current Database Schema

- **Owner**: Auriora Team
- **Status**: Accepted
- **Created Date**: 2024-12-19
- **Last Updated**: 2024-12-19
- **Audience**: [Developers, Architects, SRE]

## 1. Purpose

This document provides a detailed description of the current database schema for the Admin Assistant system. It is generated from the actual implementation and serves as the authoritative reference for all data models, relationships, and constraints.

## 2. Context

The system uses two separate databases for modularity and security: a **Core Database** for business-critical entities and a **Flask/Web Database** for user-facing and integration-specific entities. This document details the Core Database.

## 3. Details

### 3.1. Core Database Models

#### User Model (`users`)
**Purpose**: Manages system users and authentication tokens.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | Primary Key | Unique user identifier |
| email | String | Unique, Not Null | User email address |
| username | String | Unique, Nullable | Username for CLI/OS mapping |
| name | String | Nullable | User display name |
| role | String | Nullable | User role/permissions |
| is_active | Boolean | Default: True | Account status |
| ms_access_token | String | Nullable | Encrypted MS Graph access token |
| ms_refresh_token | String | Nullable | Encrypted MS Graph refresh token |
| ms_token_expires_at | UTCDateTime | Nullable | Token expiration timestamp |
| profile_photo_url | String | Nullable | User profile photo URL |
| ms_token_cache | String | Nullable | Encrypted MS Graph token cache |

#### Appointment Model (`appointments`)
**Purpose**: Stores and manages all calendar events.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | Primary Key | Unique appointment ID |
| ms_event_id | String | Nullable | Original MS Graph event ID |
| user_id | Integer | Foreign Key (users.id) | Owner of the appointment |
| start_time | UTCDateTime | Not Null | Appointment start time |
| end_time | UTCDateTime | Not Null | Appointment end time |
| subject | String | Nullable | Appointment subject/title |
| location_id | Integer | Foreign Key (locations.id) | Associated location |
| category_id | Integer | Foreign Key (categories.id) | Associated category |
| timesheet_id | Integer | Foreign Key (timesheets.id) | Associated timesheet |
| recurrence | String | Nullable | RFC 5545 RRULE string |
| ms_event_data | JSON | Nullable | Full MS Graph event data |
| is_private | Boolean | Default: False | Privacy flag |
| is_archived | Boolean | Default: False | Archive status |
| is_out_of_office | Boolean | Default: False | Out-of-office flag |
| created_at | UTCDateTime | Not Null | Creation timestamp |
| updated_at | UTCDateTime | Not Null | Last update timestamp |

#### Other Core Models

- **Location (`locations`)**: Manages appointment locations.
- **Category (`categories`)**: Manages appointment categories for billing.
- **Timesheet (`timesheets`)**: Tracks generated timesheet exports.
- **Calendar (`calendars`)**: Manages user calendars for archiving.
- **ArchiveConfiguration (`archive_configurations`)**: Stores calendar archiving configurations.
- **JobConfiguration (`job_configurations`)**: Manages background job schedules.
- **AuditLog (`audit_log`)**: Provides a comprehensive audit trail.
- **ActionLog (`action_log`)**: Manages tasks requiring user attention.

### 3.2. Relationships

- **User** has a one-to-many relationship with Appointments, Locations, Categories, Timesheets, Calendars, ArchiveConfigurations, and JobConfigurations.
- **Appointment** has many-to-one relationships with Location, Category, and Timesheet.
- **JobConfiguration** has a many-to-one relationship with ArchiveConfiguration.
- **AuditLog** has a self-referencing relationship for parent-child operations.

### 3.3. Indexes and Performance

Recommended indexes are in place for frequently queried columns, including user lookups, appointment time ranges, and audit log searches.

```sql
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_appointments_user_time ON appointments(user_id, start_time, end_time);
CREATE INDEX idx_audit_log_user_time ON audit_log(user_id, created_at);
```

### 3.4. Migration Status

- **Alembic Version**: The database is kept up-to-date with the latest migration.
- **Migration Path**: `src/core/migrations/versions/`
- **Commands**: Migrations are managed via the `./dev db` command-line wrapper.

### 3.5. Data Integrity and Security

- **Constraints**: All foreign key relationships and business logic constraints (e.g., email uniqueness) are enforced at the database level.
- **Security**: Sensitive data like tokens are encrypted. Data is isolated by `user_id`, and a full audit trail is maintained.

# References

- [Application Data Model](DATA-001-Application-Data-Model.md)
- [System Architecture](ARCH-001-System-Architecture.md)
