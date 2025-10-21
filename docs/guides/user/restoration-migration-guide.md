# Appointment Restoration Migration Guide

This guide helps you migrate from the old standalone restoration scripts to the new integrated CLI commands in the admin-assistant.

## Overview of Changes

The appointment restoration functionality has been **integrated into the main admin-assistant CLI** and the standalone scripts have been **removed**. This provides:

- **Unified Interface**: All admin-assistant functionality in one place
- **Better Integration**: Consistent user management and configuration
- **Enhanced Features**: More flexible restoration policies and dry-run capabilities
- **Improved UX**: Rich console output with tables and progress indicators

## Migration Table

| Old Script | New CLI Command | Status |
|------------|-----------------|--------|
| `scripts/restore_lost_appointments.py` | `admin-assistant restore from-audit-logs` | ✅ **REPLACED** |
| `scripts/restore_missing_appointments.py` | `admin-assistant restore from-audit-logs` | ✅ **REPLACED** |
| `scripts/restore_to_msgraph_recovery.py` | `admin-assistant restore from-backup-calendars` | ✅ **REPLACED** |
| `scripts/export_appointments_for_msgraph.py` | `admin-assistant restore backup-calendar` | ✅ **REPLACED** |
| `scripts/verify_restored_appointments.py` | `admin-assistant restore list-configs` + `--dry-run` | ✅ **REPLACED** |
| `scripts/run_appointment_restoration.sh` | Direct CLI commands | ✅ **REPLACED** |
| `scripts/run_export_for_msgraph.sh` | Direct CLI commands | ✅ **REPLACED** |
| `scripts/run_msgraph_restoration.sh` | Direct CLI commands | ✅ **REPLACED** |

## Detailed Migration Examples

### 1. Basic Audit Log Restoration

**Old Way (REMOVED):**
```bash
# These scripts no longer exist
python scripts/restore_lost_appointments.py --start-date 2025-05-29 --end-date 2025-06-06
./scripts/run_appointment_restoration.sh --dry-run
```

**New Way:**
```bash
# Integrated into main CLI
admin-assistant restore from-audit-logs --user 1 --start-date "2025-05-29" --end-date "2025-06-06"
admin-assistant restore from-audit-logs --user 1 --dry-run
```

### 2. MSGraph Recovery

**Old Way (REMOVED):**
```bash
# These scripts no longer exist
python scripts/restore_to_msgraph_recovery.py --dry-run
./scripts/run_msgraph_restoration.sh
```

**New Way:**
```bash
# More flexible with multiple source calendars
admin-assistant restore from-backup-calendars --user 1 \
  --source "Recovered" "Recovered Missing" \
  --destination "MSGraph Recovery" \
  --dry-run

# Actual restoration
admin-assistant restore from-backup-calendars --user 1 \
  --source "Recovered" "Recovered Missing" \
  --destination "MSGraph Recovery"
```

### 3. Export for MSGraph

**Old Way (REMOVED):**
```bash
# These scripts no longer exist
python scripts/export_appointments_for_msgraph.py --format csv
./scripts/run_export_for_msgraph.sh
```

**New Way:**
```bash
# More format options and better control
admin-assistant restore backup-calendar --user 1 \
  --source "Main Calendar" \
  --destination "exports/calendar_backup.csv" \
  --format csv

# JSON export with date filtering
admin-assistant restore backup-calendar --user 1 \
  --source "Work Calendar" \
  --destination "exports/work_june.json" \
  --format json \
  --start-date "2025-06-01" \
  --end-date "2025-06-30"
```

### 4. Verification and Configuration

**Old Way (REMOVED):**
```bash
# These scripts no longer exist
python scripts/verify_restored_appointments.py
```

**New Way:**
```bash
# List restoration configurations
admin-assistant restore list-configs --user 1

# Use dry-run for verification
admin-assistant restore from-audit-logs --user 1 --dry-run
admin-assistant restore from-backup-calendars --user 1 --source "Test" --destination "Verify" --dry-run
```

## New Features Available

The new CLI commands provide additional features not available in the old scripts:

### 1. Rich Console Output
- **Progress Indicators**: Visual feedback during operations
- **Formatted Tables**: Clear display of results and configurations
- **Color-coded Status**: Easy to identify success, warnings, and errors

### 2. Enhanced Dry-Run Capabilities
```bash
# Preview what would be restored without making changes
admin-assistant restore from-audit-logs --user 1 --dry-run
admin-assistant restore from-backup-calendars --user 1 --source "Test" --destination "Preview" --dry-run
```

### 3. Flexible Source Selection
```bash
# Restore from multiple backup calendars at once
admin-assistant restore from-backup-calendars --user 1 \
  --source "Recovered" "Recovered Missing" "Manual Backup" \
  --destination "Consolidated"
```

### 4. Multiple Backup Formats
```bash
# CSV format
admin-assistant restore backup-calendar --user 1 --source "Calendar" --destination "backup.csv" --format csv

# JSON format with metadata
admin-assistant restore backup-calendar --user 1 --source "Calendar" --destination "backup.json" --format json

# ICS format for calendar imports
admin-assistant restore backup-calendar --user 1 --source "Calendar" --destination "backup.ics" --format ics

# Backup to another local calendar
admin-assistant restore backup-calendar --user 1 --source "Main" --destination "Backup Calendar" --format local_calendar
```

### 5. Date Range Filtering
```bash
# Filter by date range during restoration
admin-assistant restore from-backup-calendars --user 1 \
  --source "Large Calendar" \
  --destination "June Appointments" \
  --start-date "2025-06-01" \
  --end-date "2025-06-30"
```

### 6. Configuration Management
```bash
# List all restoration configurations
admin-assistant restore list-configs --user 1

# Configurations can be created programmatically for repeated operations
```

## Setup Requirements

### 1. Database Migration
Before using the new restoration commands, run the Alembic migration:

```bash
# Apply all pending migrations
./dev db upgrade

# Or using alembic directly
alembic upgrade head
```

This creates the `restoration_configurations` table with proper indexes, foreign key constraints, and sample configurations.

### 2. Verify Installation
Test that the new commands are available:

```bash
# Check if restoration commands are available
admin-assistant restore --help

# List available subcommands
admin-assistant restore list-configs --user 1
```

## Common Migration Patterns

### Pattern 1: Daily Audit Log Recovery
**Old Script Workflow:**
```bash
# Daily cron job (REMOVED)
0 9 * * * /path/to/scripts/run_appointment_restoration.sh
```

**New CLI Workflow:**
```bash
# Daily cron job
0 9 * * * admin-assistant restore from-audit-logs --user 1 --start-date "$(date -d 'yesterday' '+%Y-%m-%d')" --end-date "$(date '+%Y-%m-%d')"
```

### Pattern 2: Weekly Consolidation
**Old Script Workflow:**
```bash
# Weekly consolidation (REMOVED)
python scripts/restore_to_msgraph_recovery.py
python scripts/export_appointments_for_msgraph.py --format json
```

**New CLI Workflow:**
```bash
# Weekly consolidation
admin-assistant restore from-backup-calendars --user 1 \
  --source "Recovered" "Recovered Missing" \
  --destination "Weekly Consolidated"

admin-assistant restore backup-calendar --user 1 \
  --source "Weekly Consolidated" \
  --destination "exports/weekly_backup.json" \
  --format json
```

### Pattern 3: Monthly Archive
**Old Script Workflow:**
```bash
# Monthly export (REMOVED)
python scripts/export_appointments_for_msgraph.py --format csv --start-date "$(date -d 'last month' '+%Y-%m-01')"
```

**New CLI Workflow:**
```bash
# Monthly export with date filtering
admin-assistant restore backup-calendar --user 1 \
  --source "Main Calendar" \
  --destination "exports/$(date -d 'last month' '+%Y-%m')_backup.csv" \
  --format csv \
  --start-date "$(date -d 'last month' '+%Y-%m-01')" \
  --end-date "$(date -d 'last month' '+%Y-%m-31')"
```

## Troubleshooting Migration Issues

### Issue 1: "Command not found"
**Problem**: `admin-assistant restore` command not available

**Solution**: 
1. Ensure you're using the latest version with restoration integration
2. Check that the CLI is properly installed: `admin-assistant --help`
3. Verify the restoration module is loaded: `admin-assistant restore --help`

### Issue 2: "No restoration configurations found"
**Problem**: `admin-assistant restore list-configs` shows no configurations

**Solution**:
1. Run the database migration: `python scripts/create_restoration_tables.py`
2. The new system works without pre-configured settings, but configurations provide advanced features

### Issue 3: "Different output format"
**Problem**: Output looks different from old scripts

**Solution**: 
- The new CLI provides richer, more readable output
- Use `--dry-run` to preview operations
- All the same data is available, just formatted better

### Issue 4: "Missing script functionality"
**Problem**: Can't find equivalent for specific old script behavior

**Solution**:
- Check this migration guide for the equivalent command
- Use `admin-assistant restore <command> --help` for detailed options
- The new system is more flexible - you may need to adjust your approach

## Getting Help

### CLI Help System
```bash
# General restoration help
admin-assistant restore --help

# Specific command help
admin-assistant restore from-audit-logs --help
admin-assistant restore from-backup-calendars --help
admin-assistant restore backup-calendar --help
admin-assistant restore list-configs --help
```

### Documentation
- [Appointment Restoration Guide](./appointment-restoration-guide.md) - Complete usage guide
- [CLI Command Structure](../../2-architecture/HLD-CLI-001-Command-Structure.md) - Full CLI documentation

### Testing
Always test with `--dry-run` first:
```bash
# Safe testing
admin-assistant restore from-audit-logs --user 1 --dry-run
admin-assistant restore from-backup-calendars --user 1 --source "Test" --destination "Preview" --dry-run
```

## Benefits of Migration

1. **Unified Interface**: All admin-assistant functionality in one place
2. **Better Error Handling**: Clearer error messages and recovery suggestions
3. **Rich Output**: Tables, colors, and progress indicators
4. **More Flexible**: Better filtering, multiple sources, various formats
5. **Future-Proof**: Easier to extend with new features
6. **Consistent**: Same patterns as other admin-assistant commands
7. **Better Testing**: Comprehensive dry-run capabilities

The migration provides immediate benefits while maintaining all existing functionality with enhanced capabilities.