# Admin Assistant CLI Command Structure

## Document Information
- **Document ID**: CLI-001
- **Last Updated**: 2024-12-19
- **Status**: CURRENT
- **Related Documents**: [Consolidated Action Plan](../CAP-001-Consolidated-Action-Plan.md), [System Architecture](ARCH-001-System-Architecture.md)

This document provides a comprehensive overview of the Admin Assistant CLI command structure and organization. All commands documented here are implemented and tested in `cli/main.py`.

## Command Hierarchy Overview

The CLI is organized into logical groups based on functionality:

- **Operational Commands**: Direct actions on data (calendar, category)
- **Configuration Commands**: System configuration management (config)
- **System Commands**: Authentication, jobs, etc. (login, jobs)

## Complete Command Tree

```
admin-assistant
├── calendar                    # Calendar operations
│   ├── archive                # Execute calendar archiving
│   ├── travel                 # Auto-plan travel
│   ├── analyze-overlaps       # Analyze overlapping appointments
│   ├── list                   # List calendars for user
│   └── create                 # Create new calendar
├── category                   # Category management
│   ├── list                   # List categories
│   ├── add                    # Add new category
│   ├── edit                   # Edit existing category
│   ├── delete                 # Delete category
│   └── validate               # Validate appointment categories
├── config                     # Configuration management
│   └── calendar               # Calendar configurations
│       └── archive            # Archive configuration management
│           ├── list           # List archive configurations
│           ├── create         # Create archive configuration
│           ├── activate       # Activate configuration
│           ├── deactivate     # Deactivate configuration
│           ├── delete         # Delete configuration
│           └── set-default    # Set default configuration
├── timesheet                  # Timesheet operations (in development)
│   ├── export                 # Export timesheet data
│   └── upload                 # Upload timesheet to external systems
├── jobs                       # Background job management
│   ├── schedule               # Schedule recurring archive jobs
│   ├── trigger                # Trigger manual archive job
│   ├── status                 # Get job status for user
│   ├── remove                 # Remove scheduled jobs
│   └── health                 # Job scheduler health check
├── restore                    # Appointment restoration operations
│   ├── from-audit-logs        # Restore appointments from audit logs
│   ├── from-backup-calendars  # Restore from backup calendars
│   ├── backup-calendar        # Backup calendar to file or another calendar
│   └── list-configs           # List restoration configurations
└── login                      # Authentication
    ├── msgraph                # Login to Microsoft 365
    └── logout                 # Logout (remove cached tokens)
```

**Note**: Timesheet commands are implemented but functionality is in development. See [Consolidated Action Plan](../CAP-001-Consolidated-Action-Plan.md) for implementation status.

## Calendar Operations (`admin-assistant calendar`)

Calendar operations perform direct actions on calendar data.

### Archive Command
```bash
admin-assistant calendar archive --user <USER_ID> --archive-config <CONFIG_ID> [--date <DATE_RANGE>]
```

**Purpose**: Execute calendar archiving using a configured archive setup.

**Options**:
- `--user <USER_ID>`: User to operate on (required)
- `--archive-config <CONFIG_ID>`: Archive configuration to use (required)
- `--date <DATE_RANGE>`: Date range to archive (default: yesterday)

**Date Range Examples**:
- `today`, `yesterday`
- `last 7 days`, `last week`, `last 30 days`, `last month`
- Single date: `31-12-2024`, `31-Dec`, `31-12`
- Date range: `1-6 to 7-6`, `1-6-2024 - 7-6-2024`

### List Calendars
```bash
admin-assistant calendar list --user <USER_ID> [--store <STORE>]
```
List all calendars for a user across stores (local, msgraph, or all).

### Create Calendar
```bash
admin-assistant calendar create --user <USER_ID> --store <STORE> [--name <NAME>] [--description <DESC>]
```
Create a new calendar for a user in the selected store (local or msgraph).

### Travel Planning
```bash
admin-assistant calendar travel
```
Auto-plan travel appointments.

### Overlap Analysis
```bash
admin-assistant calendar analyze-overlaps --user <USER_ID> [--start-date <DATE>] [--end-date <DATE>] [--auto-resolve] [--details/--no-details]
```
Analyze overlapping appointments and optionally auto-resolve conflicts.

## Configuration Management (`admin-assistant config`)

Configuration commands manage system settings and configurations.

### Calendar Archive Configuration (`admin-assistant config calendar archive`)

Archive configuration management for setting up and maintaining archive rules.

#### List Configurations
```bash
admin-assistant config calendar archive list --user <USER_ID>
```
Lists all archive configurations for a user.

#### Create Configuration
```bash
# Interactive mode (prompts for missing fields)
admin-assistant config calendar archive create --user <USER_ID>

# Full specification
admin-assistant config calendar archive create --user <USER_ID> \
  --name "Work Archive" \
  --source-uri "msgraph://calendar" \
  --dest-uri "msgraph://archive-calendar-id" \
  --timezone "Europe/London" \
  --active
```

**Options**:
- `--name <NAME>`: Human-readable name for the configuration
- `--source-uri <URI>`: Source calendar URI (e.g., `msgraph://calendar` for primary)
- `--dest-uri <URI>`: Destination archive calendar URI
- `--timezone <TZ>`: IANA timezone (e.g., `Europe/London`)
- `--active/--inactive`: Whether the configuration is active

#### Manage Configurations
```bash
# Activate/deactivate configurations
admin-assistant config calendar archive activate --user <USER_ID> --config-id <CONFIG_ID>
admin-assistant config calendar archive deactivate --user <USER_ID> --config-id <CONFIG_ID>

# Delete configuration
admin-assistant config calendar archive delete --user <USER_ID> --config-id <CONFIG_ID>

# Set as default (informational)
admin-assistant config calendar archive set-default --user <USER_ID> --config-id <CONFIG_ID>
```

## Category Management (`admin-assistant category`)

Category operations for managing appointment, email, and contact categories.

### List Categories
```bash
admin-assistant category list --user <USER_ID> [--store <STORE>]
```
List all categories for a user from the specified store.

### Add Category
```bash
admin-assistant category add --user <USER_ID> [--store <STORE>] [--name <NAME>] [--description <DESC>]
```
Add a new category for a user in the specified store.

### Edit Category
```bash
admin-assistant category edit --user <USER_ID> --id <CATEGORY_ID> [--store <STORE>] [--name <NAME>] [--description <DESC>]
```
Edit an existing category in the specified store.

### Delete Category
```bash
admin-assistant category delete --user <USER_ID> --id <CATEGORY_ID> [--store <STORE>] [--confirm]
```
Delete a category from the specified store.

### Validate Categories
```bash
admin-assistant category validate --user <USER_ID> [--start-date <DATE>] [--end-date <DATE>] [--stats/--no-stats] [--issues/--no-issues]
```
Validate appointment categories for a user and date range, showing statistics and validation issues.

**Store Options**: `local` (default) or `msgraph`

## Timesheet Operations (`admin-assistant timesheet`)

**Status**: Commands implemented, functionality in development. See [Consolidated Action Plan](../CAP-001-Consolidated-Action-Plan.md) for implementation roadmap.

### Export Timesheet
```bash
admin-assistant timesheet export --user <USER_ID> [--output <FORMAT>]
```
Export timesheet data for a user. Options:
- `--output`: Output format (PDF or CSV, default: PDF)

### Upload Timesheet
```bash
admin-assistant timesheet upload --user <USER_ID> --destination <DEST>
```
Upload timesheet to external systems. Options:
- `--destination`: Upload destination (e.g., Xero)

## Appointment Restoration (`admin-assistant restore`)

Restore appointments from various sources (audit logs, backup calendars, export files) to various destinations.

### Restore from Audit Logs
```bash
admin-assistant restore from-audit-logs --user <USER_ID> [--start-date <DATE>] [--end-date <DATE>] [--destination <CALENDAR>] [--action-types <TYPES>] [--dry-run]
```

**Purpose**: Restore appointments from audit log entries (typically failed operations).

**Options**:
- `--user <USER_ID>`: User to restore appointments for (required)
- `--start-date <DATE>`: Start date for restoration (YYYY-MM-DD, default: 2025-05-29)
- `--end-date <DATE>`: End date for restoration (YYYY-MM-DD, default: today)
- `--destination <CALENDAR>`: Destination calendar name (default: "Recovered")
- `--action-types <TYPES>`: Action types to restore from (default: archive restore)
- `--dry-run`: Perform analysis without actually restoring appointments

**Examples**:
```bash
# Restore failed appointments from specific date range
admin-assistant restore from-audit-logs --user 1 --start-date "2025-05-29" --end-date "2025-06-06"

# Dry run to preview what would be restored
admin-assistant restore from-audit-logs --user 1 --dry-run

# Restore only archive failures to custom calendar
admin-assistant restore from-audit-logs --user 1 --action-types archive --destination "Archive Recovery"
```

### Restore from Backup Calendars
```bash
admin-assistant restore from-backup-calendars --user <USER_ID> --source <CALENDARS> --destination <CALENDAR> [--start-date <DATE>] [--end-date <DATE>] [--dry-run]
```

**Purpose**: Restore appointments from existing backup calendars.

**Options**:
- `--user <USER_ID>`: User to restore appointments for (required)
- `--source <CALENDARS>`: Source calendar names (required, can specify multiple)
- `--destination <CALENDAR>`: Destination calendar name (required)
- `--start-date <DATE>`: Start date filter (YYYY-MM-DD, optional)
- `--end-date <DATE>`: End date filter (YYYY-MM-DD, optional)
- `--dry-run`: Perform analysis without actually restoring appointments

**Examples**:
```bash
# Restore from multiple backup calendars
admin-assistant restore from-backup-calendars --user 1 --source "Recovered" "Recovered Missing" --destination "Consolidated Recovery"

# Restore with date filtering
admin-assistant restore from-backup-calendars --user 1 --source "Backup Calendar" --destination "Restored" --start-date "2025-06-01" --end-date "2025-06-30"
```

### Backup Calendar
```bash
admin-assistant restore backup-calendar --user <USER_ID> --source <CALENDAR> --destination <DEST> [--format <FORMAT>] [--start-date <DATE>] [--end-date <DATE>] [--include-metadata]
```

**Purpose**: Backup a calendar to file or another calendar for future restoration.

**Options**:
- `--user <USER_ID>`: User to backup calendar for (required)
- `--source <CALENDAR>`: Source calendar name (required)
- `--destination <DEST>`: Backup destination - file path or calendar name (required)
- `--format <FORMAT>`: Backup format: csv, json, ics, local_calendar (default: csv)
- `--start-date <DATE>`: Start date filter (YYYY-MM-DD, optional)
- `--end-date <DATE>`: End date filter (YYYY-MM-DD, optional)
- `--include-metadata/--no-metadata`: Include metadata in backup (default: include)

**Examples**:
```bash
# Backup to CSV file
admin-assistant restore backup-calendar --user 1 --source "Main Calendar" --destination "backups/main_calendar.csv" --format csv

# Backup to another local calendar
admin-assistant restore backup-calendar --user 1 --source "Work Calendar" --destination "Work Calendar Backup" --format local_calendar

# Backup with date range to JSON
admin-assistant restore backup-calendar --user 1 --source "Personal" --destination "backups/personal_june.json" --format json --start-date "2025-06-01" --end-date "2025-06-30"
```

### List Restoration Configurations
```bash
admin-assistant restore list-configs --user <USER_ID>
```

**Purpose**: List all restoration configurations for the user.

**Examples**:
```bash
# List all restoration configurations
admin-assistant restore list-configs --user 1
```

## Background Job Management (`admin-assistant jobs`)

Manage scheduled and manual background jobs.

### Schedule Recurring Jobs
```bash
admin-assistant jobs schedule --user <USER_ID> [--type daily|weekly] [--hour <HOUR>] [--minute <MINUTE>] [--day <DAY>] [--config <CONFIG_ID>]
```
Schedule a recurring archive job for a user. Options:
- `--type`: Schedule type (daily or weekly, default: daily)
- `--hour`: Hour to run (0-23, default: 23)
- `--minute`: Minute to run (0-59, default: 59)
- `--day`: Day of week for weekly jobs (0=Monday, 6=Sunday)
- `--config`: Archive configuration ID (uses active if not specified)

### Trigger Manual Archive
```bash
admin-assistant jobs trigger --user <USER_ID> [--start <DATE>] [--end <DATE>] [--config <CONFIG_ID>]
```
Trigger a manual archive job immediately with optional date range and configuration.

### Check Job Status
```bash
admin-assistant jobs status --user <USER_ID>
```
Get job status for a user, showing active configurations and scheduled jobs.

### Remove Scheduled Jobs
```bash
admin-assistant jobs remove --user <USER_ID> [--confirm]
```
Remove all scheduled jobs for a user.

### Health Check
```bash
admin-assistant jobs health
```
Perform health check on the job scheduling system.

## Authentication (`admin-assistant login`)

Authentication and token management.

### Login to Microsoft 365
```bash
admin-assistant login msgraph --user <USER_ID>
```
Log in to Microsoft 365 (MS Graph) for the given user. Uses MSAL device code flow and caches token in `~/.cache/admin-assistant/ms_token.json`.

### Logout
```bash
admin-assistant login logout --user <USER_ID>
```
Log out from Microsoft 365 (MS Graph) for the given user. Removes the token cache file.

## Common Patterns

### Environment Variables
Set `ADMIN_ASSISTANT_USER` to avoid specifying `--user` repeatedly:
```bash
export ADMIN_ASSISTANT_USER=123
admin-assistant calendar archive "Work Archive"
```

### Help System
Every command supports `--help`:
```bash
admin-assistant --help
admin-assistant calendar --help
admin-assistant config calendar archive --help
admin-assistant config calendar archive create --help
```

### Interactive Mode
Many commands support interactive prompts when required options are omitted:
```bash
# Will prompt for missing name, URIs, timezone
admin-assistant config calendar archive create --user 123
```

## Command Design Principles

1. **Contextual Organization**: Commands are grouped by their primary context
   - `calendar`: Operations on calendar data
   - `config`: System configuration management
   - `jobs`: Background processing management

2. **Hierarchical Structure**: Related commands are nested logically
   - `config calendar archive`: All archive configuration commands
   - Clear separation between execution (`calendar archive`) and configuration (`config calendar archive`)

3. **Consistent Patterns**: Similar option names and behaviors across commands
   - `--user` for user specification
   - `--help` for documentation
   - Interactive prompts for missing required fields

4. **Operational vs Configuration**: Clear distinction between:
   - **Operational**: `admin-assistant calendar archive` (execute archiving)
   - **Configuration**: `admin-assistant config calendar archive` (manage archive settings)
