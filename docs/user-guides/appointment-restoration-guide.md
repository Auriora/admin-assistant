# Appointment Restoration Guide

This guide covers the new generic appointment restoration feature that replaces the individual restoration scripts with a unified, configurable system.

## Overview

The appointment restoration system provides a flexible way to restore appointments from various sources to various destinations:

### Sources
- **Audit Logs**: Restore failed appointments from audit log entries
- **Backup Calendars**: Restore from local backup calendars
- **Export Files**: Import from CSV, JSON, or ICS files

### Destinations
- **Local Calendars**: Restore to SQLite-based local calendars
- **MSGraph Calendars**: Restore to Microsoft 365 calendars
- **Export Files**: Export to CSV, JSON, or ICS files

## Quick Start

### 1. Set Up the Database Tables

First, run the database migration to create the restoration configuration tables:

```bash
# Apply all pending migrations
./dev db upgrade

# Or using alembic directly
alembic upgrade head
```

This will create the `restoration_configurations` table with proper indexes, foreign key constraints, and some sample configurations.

### 2. List Available Configurations

```bash
python scripts/appointment_restoration_cli.py list-configs
```

### 3. Restore from Audit Logs (Most Common Use Case)

```bash
# Dry run to see what would be restored
python scripts/appointment_restoration_cli.py audit-logs --dry-run

# Actually restore appointments
python scripts/appointment_restoration_cli.py audit-logs --start-date 2025-05-29 --end-date 2025-06-06
```

### 4. Restore from Backup Calendars

```bash
# Restore from multiple backup calendars
python scripts/appointment_restoration_cli.py backup-calendars \
  --source-calendars "Recovered" "Recovered Missing" \
  --destination-calendar "Consolidated Recovery"
```

## CLI Reference

### Global Options

- `--user-id`: User ID to perform operations for (default: 1)
- `--verbose`: Enable verbose output and error tracebacks

### Commands

#### `audit-logs` - Restore from Audit Logs

Restore appointments from audit log entries (typically failed operations).

```bash
python scripts/appointment_restoration_cli.py audit-logs [OPTIONS]
```

**Options:**
- `--start-date`: Start date for restoration (YYYY-MM-DD, default: 2025-05-29)
- `--end-date`: End date for restoration (YYYY-MM-DD, default: today)
- `--destination-calendar`: Destination calendar name (default: Recovered)
- `--action-types`: Action types to restore from (default: archive restore)
- `--dry-run`: Perform analysis without actually restoring appointments

**Examples:**
```bash
# Restore failed appointments from May 29 to June 6
python scripts/appointment_restoration_cli.py audit-logs \
  --start-date 2025-05-29 --end-date 2025-06-06

# Dry run with custom destination
python scripts/appointment_restoration_cli.py audit-logs \
  --destination-calendar "My Recovery" --dry-run

# Restore only archive failures
python scripts/appointment_restoration_cli.py audit-logs \
  --action-types archive
```

#### `backup-calendars` - Restore from Backup Calendars

Restore appointments from existing backup calendars.

```bash
python scripts/appointment_restoration_cli.py backup-calendars [OPTIONS]
```

**Options:**
- `--source-calendars`: Source calendar names to restore from (required)
- `--destination-calendar`: Destination calendar name (required)
- `--start-date`: Start date for filtering (YYYY-MM-DD, optional)
- `--end-date`: End date for filtering (YYYY-MM-DD, optional)
- `--dry-run`: Perform analysis without actually restoring appointments

**Examples:**
```bash
# Restore from multiple calendars
python scripts/appointment_restoration_cli.py backup-calendars \
  --source-calendars "Recovered" "Recovered Missing" \
  --destination-calendar "Consolidated"

# Restore with date filtering
python scripts/appointment_restoration_cli.py backup-calendars \
  --source-calendars "Backup Calendar" \
  --destination-calendar "Restored" \
  --start-date 2025-06-01 --end-date 2025-06-30
```

#### `backup` - Backup a Calendar

Create backups of calendars for future restoration.

```bash
python scripts/appointment_restoration_cli.py backup [OPTIONS]
```

**Options:**
- `--source-calendar`: Source calendar name to backup (required)
- `--backup-destination`: Backup destination (file path or calendar name) (required)
- `--backup-format`: Backup format: csv, json, ics, local_calendar (default: csv)
- `--start-date`: Start date for filtering (YYYY-MM-DD, optional)
- `--end-date`: End date for filtering (YYYY-MM-DD, optional)
- `--include-metadata`: Include metadata in backup (default: True)

**Examples:**
```bash
# Backup to CSV file
python scripts/appointment_restoration_cli.py backup \
  --source-calendar "Main Calendar" \
  --backup-destination "backups/main_calendar_backup.csv" \
  --backup-format csv

# Backup to another local calendar
python scripts/appointment_restoration_cli.py backup \
  --source-calendar "Work Calendar" \
  --backup-destination "Work Calendar Backup" \
  --backup-format local_calendar

# Backup with date range to JSON
python scripts/appointment_restoration_cli.py backup \
  --source-calendar "Personal" \
  --backup-destination "backups/personal_june.json" \
  --backup-format json \
  --start-date 2025-06-01 --end-date 2025-06-30
```

#### `list-configs` - List Restoration Configurations

List all restoration configurations for the current user.

```bash
python scripts/appointment_restoration_cli.py list-configs
```

## Programmatic Usage

### Using the Restoration Service

```python
from core.services.appointment_restoration_service import AppointmentRestorationService
from datetime import date

# Initialize service
service = AppointmentRestorationService(user_id=1)

# Restore from audit logs
result = service.restore_from_audit_logs(
    start_date=date(2025, 5, 29),
    end_date=date(2025, 6, 6),
    destination_calendar="Recovered",
    dry_run=False
)

print(f"Restored {result['restored']} appointments")
```

### Creating Custom Configurations

```python
from core.models.restoration_configuration import RestorationType, DestinationType

# Create a custom configuration
config = service.create_configuration(
    name="Custom Audit Recovery",
    source_type=RestorationType.AUDIT_LOG.value,
    source_config={
        "action_types": ["archive"],
        "date_range": {"start": "2025-05-29", "end": "2025-06-30"},
        "status": "failure"
    },
    destination_type=DestinationType.LOCAL_CALENDAR.value,
    destination_config={
        "calendar_name": "Custom Recovery"
    },
    restoration_policy={
        "skip_duplicates": True,
        "subject_filters": {
            "exclude": ["test", "debug"]
        }
    }
)

# Use the configuration
result = service.restore_from_configuration(config, dry_run=False)
```

### Using the Backup Service

```python
from core.services.calendar_backup_service import CalendarBackupService, BackupFormat
from datetime import date

# Initialize backup service
backup_service = CalendarBackupService(user_id=1)

# Backup to file
result = backup_service.backup_calendar_to_file(
    calendar_name="Main Calendar",
    backup_path="backups/main_calendar.csv",
    backup_format=BackupFormat.CSV,
    start_date=date(2025, 6, 1),
    end_date=date(2025, 6, 30)
)

# Backup to another calendar
result = backup_service.backup_calendar_to_local_calendar(
    source_calendar_name="Work Calendar",
    backup_calendar_name="Work Calendar Backup"
)
```

## Migration from Old Scripts

The new system replaces these old scripts:

- `restore_lost_appointments.py` → Use `audit-logs` command
- `restore_missing_appointments.py` → Use `audit-logs` command with custom date range
- `restore_to_msgraph_recovery.py` → Use `backup-calendars` command with MSGraph destination
- `export_appointments_for_msgraph.py` → Use `backup` command with appropriate format

### Migration Examples

**Old:**
```bash
./scripts/run_appointment_restoration.sh --dry-run
```

**New:**
```bash
python scripts/appointment_restoration_cli.py audit-logs --dry-run
```

**Old:**
```bash
python scripts/restore_to_msgraph_recovery.py --dry-run
```

**New:**
```bash
python scripts/appointment_restoration_cli.py backup-calendars \
  --source-calendars "Recovered" "Recovered Missing" \
  --destination-calendar "MSGraph Recovery" --dry-run
```

## Configuration Reference

### Source Types

#### `audit_log`
```json
{
  "action_types": ["archive", "restore"],
  "date_range": {
    "start": "2025-05-29",
    "end": "2025-06-30"
  },
  "status": "failure"
}
```

#### `backup_calendar`
```json
{
  "calendar_names": ["Recovered", "Backup Calendar"],
  "date_range": {
    "start": "2025-06-01",
    "end": "2025-06-30"
  }
}
```

#### `export_file`
```json
{
  "file_path": "/path/to/backup.csv",
  "file_format": "csv"
}
```

### Destination Types

#### `local_calendar`
```json
{
  "calendar_name": "Restored Appointments"
}
```

#### `msgraph_calendar`
```json
{
  "calendar_name": "MSGraph Recovery"
}
```

#### `export_file`
```json
{
  "file_path": "/path/to/export.json",
  "file_format": "json"
}
```

### Restoration Policies

```json
{
  "skip_duplicates": true,
  "date_range": {
    "start": "2025-05-29",
    "end": "2025-12-31"
  },
  "subject_filters": {
    "include": ["meeting", "appointment"],
    "exclude": ["test", "debug"]
  },
  "category_filters": {
    "include": ["Work", "Personal"],
    "exclude": ["Archived"]
  }
}
```

## Troubleshooting

### Common Issues

1. **"No appointments found to restore"**
   - Check date ranges in your configuration
   - Verify audit logs exist for the specified period
   - Use `--verbose` flag for detailed output

2. **"Calendar not found"**
   - Ensure source calendars exist
   - Check calendar name spelling (case-sensitive)
   - List available calendars first

3. **"Permission denied" for MSGraph operations**
   - Verify Microsoft 365 authentication
   - Check MSGraph API permissions
   - Ensure user has calendar access

### Debug Mode

Use the `--verbose` flag for detailed error information:

```bash
python scripts/appointment_restoration_cli.py audit-logs --verbose --dry-run
```

### Logs

Check the application logs for detailed operation information:

```bash
tail -f logs/app.log
```
