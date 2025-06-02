# Database Schema Documentation

## Document Information
- **Document ID**: DATABASE-SCHEMA-001
- **Document Name**: Current Database Schema
- **Created By**: Admin Assistant System
- **Creation Date**: 2024-12-19
- **Status**: ACTIVE - Generated from actual implementation
- **Related Documents**: [Data Model](data-model.md), [System Architecture](ARCH-001-System-Architecture.md)

## Overview

The Admin Assistant system uses two separate databases to support modularity, security, and integration with external services:

1. **Core Database**: Business-critical, backend-agnostic entities
2. **Flask/Web Database**: User-facing, web-specific, and integration-related entities

## Core Database Models

### User Model
**Table**: `users`
**Purpose**: System user management and authentication

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | Primary Key | Unique user identifier |
| email | String | Unique, Not Null | User email address |
| name | String | Nullable | User display name |
| role | String | Nullable | User role/permissions |
| is_active | Boolean | Default: True | Account status |
| ms_access_token | String | Nullable | Microsoft Graph access token |
| ms_refresh_token | String | Nullable | Microsoft Graph refresh token |
| ms_token_expires_at | UTCDateTime | Nullable | Token expiration timestamp |
| profile_photo_url | String | Nullable | User profile photo URL |
| ms_token_cache | String | Nullable | Encrypted MS Graph token cache |

### Appointment Model
**Table**: `appointments`
**Purpose**: Calendar event storage and management

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | Primary Key | Unique appointment identifier |
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

### Location Model
**Table**: `locations`
**Purpose**: Location management for appointments

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | Primary Key | Unique location identifier |
| name | String | Not Null | Location name |
| address | String | Nullable | Location address |
| user_id | Integer | Foreign Key (users.id) | Owner of the location |

### Category Model
**Table**: `categories`
**Purpose**: Appointment categorization for billing and organization

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | Primary Key | Unique category identifier |
| name | String | Not Null | Category name |
| description | String | Nullable | Category description |
| user_id | Integer | Foreign Key (users.id) | Owner of the category |
| ms_category_id | String | Nullable | MS Graph category ID |
| color | String | Nullable | Category color |

### Timesheet Model
**Table**: `timesheets`
**Purpose**: Generated timesheet tracking and export management

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | Primary Key | Unique timesheet identifier |
| user_id | Integer | Foreign Key (users.id) | Owner of the timesheet |
| start_date | Date | Not Null | Timesheet period start |
| end_date | Date | Not Null | Timesheet period end |
| pdf_path | String | Nullable | Generated PDF file path |
| csv_path | String | Nullable | Generated CSV file path |
| excel_path | String | Nullable | Generated Excel file path |
| uploaded_to_onedrive | Boolean | Default: False | OneDrive upload status |
| uploaded_to_xero | Boolean | Default: False | Xero upload status |
| created_at | UTCDateTime | Not Null | Creation timestamp |

### Calendar Model
**Table**: `calendars`
**Purpose**: Calendar management for archiving and organization

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | Primary Key | Unique calendar identifier |
| name | String | Not Null | Calendar name |
| description | String | Nullable | Calendar description |
| user_id | Integer | Foreign Key (users.id) | Owner of the calendar |
| ms_calendar_id | String | Nullable | MS Graph calendar ID |
| is_archive | Boolean | Default: False | Archive calendar flag |
| created_at | UTCDateTime | Not Null | Creation timestamp |
| updated_at | UTCDateTime | Not Null | Last update timestamp |

### ArchiveConfiguration Model
**Table**: `archive_configurations`
**Purpose**: Calendar archiving configuration management

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | Primary Key | Unique configuration identifier |
| user_id | Integer | Foreign Key (users.id) | Owner of the configuration |
| name | String | Not Null | Configuration name |
| source_calendar_uri | String | Not Null | Source calendar URI |
| destination_calendar_uri | String | Not Null | Destination calendar URI |
| is_active | Boolean | Default: True | Configuration status |
| timezone | String | Not Null | Timezone for operations |
| created_at | UTCDateTime | Not Null | Creation timestamp |
| updated_at | UTCDateTime | Not Null | Last update timestamp |

### JobConfiguration Model
**Table**: `job_configurations`
**Purpose**: Background job scheduling configuration

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | Primary Key | Unique job configuration identifier |
| user_id | Integer | Foreign Key (users.id) | Owner of the job |
| archive_configuration_id | Integer | Foreign Key (archive_configurations.id) | Associated archive config |
| archive_window_days | Integer | Default: 1 | Days to look back for archiving |
| schedule_type | String | Not Null | Schedule type (daily/weekly/manual) |
| schedule_hour | Integer | Default: 23 | Hour to run (0-23) |
| schedule_minute | Integer | Default: 59 | Minute to run (0-59) |
| schedule_day_of_week | Integer | Nullable | Day of week for weekly jobs |
| is_active | Boolean | Default: True | Job status |
| created_at | UTCDateTime | Not Null | Creation timestamp |
| updated_at | UTCDateTime | Not Null | Last update timestamp |

### AuditLog Model
**Table**: `audit_log`
**Purpose**: Comprehensive audit trail for compliance and troubleshooting

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | Primary Key | Unique audit log identifier |
| user_id | Integer | Foreign Key (users.id) | User performing the action |
| action_type | String(64) | Not Null | Type of action performed |
| operation | String(128) | Not Null | Specific operation |
| resource_type | String(64) | Nullable | Type of resource affected |
| resource_id | String(128) | Nullable | ID of affected resource |
| status | String(32) | Not Null | Operation status |
| message | Text | Nullable | Human-readable description |
| details | JSON | Nullable | Operation-specific details |
| request_data | JSON | Nullable | Input parameters |
| response_data | JSON | Nullable | Output/results |
| duration_ms | Float | Nullable | Operation duration |
| ip_address | String(45) | Nullable | Client IP address |
| user_agent | String(512) | Nullable | Client user agent |
| correlation_id | String(128) | Nullable | Related operations tracking |
| parent_audit_id | Integer | Foreign Key (audit_log.id) | Parent operation |
| created_at | UTCDateTime | Not Null | Creation timestamp |

### ActionLog Model
**Table**: `action_log`
**Purpose**: Task management and user attention tracking

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | Primary Key | Unique action log identifier |
| user_id | Integer | Foreign Key (users.id) | User requiring attention |
| event_type | String | Not Null | Type of event/task |
| state | String | Default: 'open' | Task state |
| description | String | Nullable | Task description |
| details | JSON | Nullable | Additional context |
| recommendations | JSON | Nullable | AI recommendations |
| created_at | UTCDateTime | Not Null | Creation timestamp |
| updated_at | UTCDateTime | Not Null | Last update timestamp |

## Relationships

### Primary Relationships
- **User** → **Appointments** (One-to-Many)
- **User** → **Locations** (One-to-Many)
- **User** → **Categories** (One-to-Many)
- **User** → **Timesheets** (One-to-Many)
- **User** → **Calendars** (One-to-Many)
- **User** → **ArchiveConfigurations** (One-to-Many)
- **User** → **JobConfigurations** (One-to-Many)

### Secondary Relationships
- **Appointment** → **Location** (Many-to-One)
- **Appointment** → **Category** (Many-to-One)
- **Appointment** → **Timesheet** (Many-to-One)
- **JobConfiguration** → **ArchiveConfiguration** (Many-to-One)
- **AuditLog** → **AuditLog** (Self-referencing for parent operations)

## Indexes and Performance

### Recommended Indexes
```sql
-- User lookups
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active);

-- Appointment queries
CREATE INDEX idx_appointments_user_time ON appointments(user_id, start_time, end_time);
CREATE INDEX idx_appointments_archived ON appointments(is_archived);
CREATE INDEX idx_appointments_ms_event ON appointments(ms_event_id);

-- Audit log queries
CREATE INDEX idx_audit_log_user_time ON audit_log(user_id, created_at);
CREATE INDEX idx_audit_log_correlation ON audit_log(correlation_id);
CREATE INDEX idx_audit_log_operation ON audit_log(action_type, operation);

-- Job configuration queries
CREATE INDEX idx_job_config_active ON job_configurations(is_active);
CREATE INDEX idx_job_config_user ON job_configurations(user_id);
```

## Migration Status

### Current Migration Version
- **Core Database**: Latest migration applied
- **Alembic Version**: Current with all models
- **Migration Path**: `src/core/migrations/versions/`

### Migration Commands
```bash
# Apply all pending migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "Description"

# Check current version
alembic current
```

## Data Integrity Constraints

### Foreign Key Constraints
- All foreign key relationships enforced at database level
- Cascade delete policies defined for dependent records
- Referential integrity maintained across all relationships

### Business Logic Constraints
- User email uniqueness enforced
- Appointment time validation (end_time > start_time)
- Archive configuration URI format validation
- Job schedule parameter validation

## Security Considerations

### Data Protection
- Sensitive tokens encrypted using Fernet encryption
- User data isolated by user_id foreign key constraints
- Audit trail for all data modifications
- Secure token cache storage

### Access Control
- User-based data isolation
- Role-based access control ready for implementation
- Audit logging for all operations
- Secure session management

---

*This schema documentation reflects the current state of the Admin Assistant database implementation as of 2024-12-19.*
