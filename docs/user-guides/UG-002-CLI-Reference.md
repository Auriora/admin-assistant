# CLI Reference Guide

## Document Information
- **Document ID**: UG-002
- **Document Name**: CLI Reference Guide
- **Created By**: Admin Assistant System
- **Creation Date**: 2024-12-19
- **Status**: ACTIVE
- **Target Audience**: End Users and Administrators

## Overview

This guide provides comprehensive reference documentation for all Admin Assistant CLI commands. All commands are organized by functional area and include examples, options, and usage patterns.

## Global Options

All commands support these global options:

| Option | Description | Environment Variable |
|--------|-------------|---------------------|
| `--user <USER_ID_OR_USERNAME>` | User ID or username to operate on | `ADMIN_ASSISTANT_USER` |
| `--help` | Show command help | - |

## User Identification

The CLI supports multiple ways to identify users with the following precedence (highest to lowest):

1. **Command-line argument**: `--user <username_or_id>`
2. **ADMIN_ASSISTANT_USER environment variable**: `export ADMIN_ASSISTANT_USER=username`
3. **OS environment variables**: `USER`, `USERNAME`, or `LOGNAME`

### Examples

```bash
# Using explicit user ID (traditional)
admin-assistant calendar archive --user 123

# Using username (new)
admin-assistant calendar archive --user john.doe

# Using environment variable
export ADMIN_ASSISTANT_USER=john.doe
admin-assistant calendar archive

# Using OS username (automatic fallback)
# If your OS username matches a user in the system
admin-assistant calendar archive
```

## Command Categories

### Authentication Commands (`admin-assistant login`)

#### Login to Microsoft 365
```bash
admin-assistant login msgraph --user <USER_ID>
```
**Purpose**: Authenticate with Microsoft 365 using device code flow
**Output**: Opens browser for authentication, caches token locally
**Token Location**: `~/.cache/admin-assistant/ms_token.json`

#### Logout
```bash
admin-assistant login logout --user <USER_ID>
```
**Purpose**: Remove cached Microsoft 365 tokens
**Effect**: Requires re-authentication for next operation

### Calendar Commands (`admin-assistant calendar`)

#### Archive Calendar Events
```bash
admin-assistant calendar archive --user <USER_ID> --archive-config <CONFIG_ID> --date <DATE_SPEC>
```

**Required Options**:
- `--user <USER_ID>`: User to archive for
- `--archive-config <CONFIG_ID>`: Archive configuration to use
- `--date <DATE_SPEC>`: Date or date range to archive

**Date Specifications**:
- `"today"` - Archive today's appointments
- `"yesterday"` - Archive yesterday's appointments
- `"last 7 days"` - Archive last 7 days (rolling period ending yesterday)
- `"last week"` - Archive previous calendar week (Monday-Sunday or Sunday-Saturday based on locale)
- `"last 30 days"` - Archive last 30 days (rolling period ending yesterday)
- `"last month"` - Archive previous calendar month (e.g., all of May if run in June)
- `"2024-12-18"` - Specific date (YYYY-MM-DD)
- `"31-12-2024"` - Specific date (DD-MM-YYYY)
- `"31-Dec"` - Date without year (current year assumed)
- `"1-6 to 7-6"` - Date range (DD-MM to DD-MM)
- `"1-6-2024 - 7-6-2024"` - Date range with years

**Note**:
- Rolling periods ('last X days') end on yesterday to ensure only completed periods are archived
- Calendar periods ('last week', 'last month') refer to complete calendar periods (previous week/month)
- Week start day is determined by locale settings (Monday for most locales, Sunday for US)

**Examples**:
```bash
# Archive yesterday's appointments
admin-assistant calendar archive --user 1 --archive-config 1 --date "yesterday"

# Archive specific date
admin-assistant calendar archive --user 1 --archive-config 1 --date "2024-12-18"

# Archive date range
admin-assistant calendar archive --user 1 --archive-config 1 --date "1-12 to 7-12"
```

#### List Calendars
```bash
admin-assistant calendar list --user <USER_ID> [--datastore <STORE>]
```

**Options**:
- `--datastore <STORE>`: Data store to query (`local`, `msgraph`, `all`)

**Examples**:
```bash
# List all calendars
admin-assistant calendar list --user 1

# List only Microsoft Graph calendars
admin-assistant calendar list --user 1 --datastore msgraph
```

#### Create Calendar
```bash
admin-assistant calendar create --user <USER_ID> --store <STORE> --name <NAME> [--description <DESC>]
```

**Required Options**:
- `--store <STORE>`: Calendar store (`local` or `msgraph`)
- `--name <NAME>`: Calendar name

**Optional Options**:
- `--description <DESC>`: Calendar description

#### Analyze Overlaps
```bash
admin-assistant calendar analyze-overlaps --user <USER_ID> [OPTIONS]
```

**Options**:
- `--start-date <DATE>`: Start date for analysis
- `--end-date <DATE>`: End date for analysis
- `--auto-resolve`: Apply automatic resolution rules
- `--details/--no-details`: Show detailed overlap information

**Examples**:
```bash
# Analyze overlaps for date range
admin-assistant calendar analyze-overlaps --user 1 --start-date "2024-12-01" --end-date "2024-12-31"

# Auto-resolve overlaps
admin-assistant calendar analyze-overlaps --user 1 --auto-resolve --start-date "2024-12-01"
```

### Category Commands (`admin-assistant category`)

#### List Categories
```bash
admin-assistant category list --user <USER_ID> [--store <STORE>]
```

**Options**:
- `--store <STORE>`: Category store (`local` or `msgraph`)

#### Add Category
```bash
admin-assistant category add --user <USER_ID> [OPTIONS]
```

**Options**:
- `--store <STORE>`: Category store (`local` or `msgraph`)
- `--name <NAME>`: Category name
- `--description <DESC>`: Category description
- `--color <COLOR>`: Category color

**Interactive Mode**: If options not provided, prompts for input

#### Edit Category
```bash
admin-assistant category edit --user <USER_ID> --id <CATEGORY_ID> [OPTIONS]
```

**Required Options**:
- `--id <CATEGORY_ID>`: Category ID to edit

**Optional Options**:
- `--store <STORE>`: Category store
- `--name <NAME>`: New category name
- `--description <DESC>`: New category description
- `--color <COLOR>`: New category color

#### Delete Category
```bash
admin-assistant category delete --user <USER_ID> --id <CATEGORY_ID> [OPTIONS]
```

**Options**:
- `--store <STORE>`: Category store
- `--confirm`: Skip confirmation prompt

#### Validate Categories
```bash
admin-assistant category validate --user <USER_ID> [OPTIONS]
```

**Options**:
- `--start-date <DATE>`: Start date for validation
- `--end-date <DATE>`: End date for validation
- `--stats/--no-stats`: Show category statistics
- `--issues/--no-issues`: Show validation issues

**Examples**:
```bash
# Validate categories for date range
admin-assistant category validate --user 1 --start-date "2024-12-01" --end-date "2024-12-31"

# Show only validation issues
admin-assistant category validate --user 1 --no-stats --issues
```

### Configuration Commands (`admin-assistant config`)

#### Archive Configuration Management

**List Archive Configurations**:
```bash
admin-assistant config calendar archive list --user <USER_ID>
```

**Create Archive Configuration**:
```bash
admin-assistant config calendar archive create --user <USER_ID> [OPTIONS]
```

**Options**:
- `--name <NAME>`: Configuration name
- `--source-uri <URI>`: Source calendar URI
- `--dest-uri <URI>`: Destination calendar URI
- `--timezone <TZ>`: Timezone (IANA format)
- `--active`: Set as active configuration

**Interactive Mode**: If options not provided, prompts for input

**Edit Archive Configuration**:
```bash
admin-assistant config calendar archive edit --user <USER_ID> --config-id <CONFIG_ID> [OPTIONS]
```

**Delete Archive Configuration**:
```bash
admin-assistant config calendar archive delete --user <USER_ID> --config-id <CONFIG_ID> [--confirm]
```

**Activate/Deactivate Configuration**:
```bash
admin-assistant config calendar archive activate --user <USER_ID> --config-id <CONFIG_ID>
admin-assistant config calendar archive deactivate --user <USER_ID> --config-id <CONFIG_ID>
```

### Background Job Commands (`admin-assistant jobs`)

#### Schedule Jobs
```bash
admin-assistant jobs schedule --user <USER_ID> --archive-config <CONFIG_ID> [OPTIONS]
```

**Required Options**:
- `--archive-config <CONFIG_ID>`: Archive configuration to use

**Optional Options**:
- `--schedule-type <TYPE>`: Schedule type (`daily`, `weekly`, `manual`)
- `--hour <HOUR>`: Hour to run (0-23)
- `--minute <MINUTE>`: Minute to run (0-59)
- `--day-of-week <DAY>`: Day of week for weekly jobs (0=Monday, 6=Sunday)
- `--archive-window-days <DAYS>`: Days to look back for archiving

**Examples**:
```bash
# Schedule daily archiving at 11:59 PM
admin-assistant jobs schedule --user 1 --archive-config 1 --schedule-type daily --hour 23 --minute 59

# Schedule weekly archiving on Sundays
admin-assistant jobs schedule --user 1 --archive-config 1 --schedule-type weekly --day-of-week 6
```

#### Trigger Manual Jobs
```bash
admin-assistant jobs trigger --user <USER_ID> --archive-config <CONFIG_ID> [OPTIONS]
```

**Options**:
- `--archive-window-days <DAYS>`: Days to look back for archiving

#### Job Status and Management
```bash
# Check job status
admin-assistant jobs status --user <USER_ID>

# Remove scheduled jobs
admin-assistant jobs remove --user <USER_ID> [--confirm]

# Health check
admin-assistant jobs health
```

### Timesheet Commands (`admin-assistant timesheet`)

**Note**: Timesheet functionality is currently in development. Commands are implemented but functionality is limited.

#### Export Timesheet
```bash
admin-assistant timesheet export --user <USER_ID> [--output <FORMAT>]
```

**Options**:
- `--output <FORMAT>`: Output format (`PDF` or `CSV`)

#### Upload Timesheet
```bash
admin-assistant timesheet upload --user <USER_ID> --destination <DEST>
```

**Options**:
- `--destination <DEST>`: Upload destination (e.g., `Xero`)

## Command Examples by Use Case

### Daily Operations

**Morning Setup**:
```bash
# Check authentication status
admin-assistant login msgraph --user 1

# Check for any scheduled job issues
admin-assistant jobs health
```

**End of Day**:
```bash
# Archive yesterday's appointments
admin-assistant calendar archive --user 1 --archive-config 1 --date "yesterday"

# Check for overlaps
admin-assistant calendar analyze-overlaps --user 1 --date "yesterday" --auto-resolve
```

### Weekly Operations

**Monday Morning**:
```bash
# Validate categories for previous week
admin-assistant category validate --user 1 --start-date "last week" --stats

# Archive last week if not automated
admin-assistant calendar archive "Work Archive" --user 1 --date "last week"
```

**Friday Afternoon**:
```bash
# Generate timesheet for the week (when implemented)
admin-assistant timesheet export --user 1 --output PDF
```

### Setup and Configuration

**Initial Setup**:
```bash
# Authenticate
admin-assistant login msgraph --user 1

# Create archive configuration
admin-assistant config calendar archive create --user 1

# Schedule daily archiving
admin-assistant jobs schedule --user 1 --config 1 --schedule-type daily
```

**Category Management**:
```bash
# Add common categories
admin-assistant category add --user 1 --name "Client A - Consulting"
admin-assistant category add --user 1 --name "Client B - Development"
admin-assistant category add --user 1 --name "Internal - Admin"
```

## Error Handling

### Common Error Scenarios

**Authentication Required**:
```
Error: No valid MS Graph token found. Please login with 'admin-assistant login msgraph'.
```
**Solution**: Run `admin-assistant login msgraph --user <USER_ID>`

**Configuration Not Found**:
```
Error: Archive configuration not found: 999
```
**Solution**: List configurations with `admin-assistant config calendar archive list --user <USER_ID>`

**Invalid Date Format**:
```
Error: Unable to parse date: "invalid-date"
```
**Solution**: Use supported date formats (see Date Specifications above)

### Debugging Commands

**Check System Status**:
```bash
# Job scheduler health
admin-assistant jobs health

# List all configurations
admin-assistant config calendar archive list --user 1

# Check authentication
admin-assistant login msgraph --user 1
```

## Tips and Best Practices

### Command Efficiency
- Set `ADMIN_ASSISTANT_USER` environment variable to avoid repeating `--user` option
- Use command aliases for frequently used commands
- Combine operations where possible (e.g., `--auto-resolve` with overlap analysis)

### Data Management
- Regular category validation prevents timesheet issues
- Schedule automatic archiving to maintain clean calendars
- Use consistent category naming for better reporting

### Troubleshooting
- Always check `admin-assistant jobs health` if scheduled operations fail
- Use `--help` on any command for detailed option information
- Check audit logs for detailed error information

---

*This CLI reference covers all implemented commands in Admin Assistant. Additional commands will be added as new features are developed.*
