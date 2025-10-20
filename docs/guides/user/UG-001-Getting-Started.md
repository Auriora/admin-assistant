# Getting Started with Admin Assistant

## Document Information
- **Document ID**: UG-001
- **Document Name**: Getting Started Guide
- **Created By**: Admin Assistant System
- **Creation Date**: 2024-12-19
- **Status**: ACTIVE
- **Target Audience**: End Users

## Overview

Admin Assistant is a Microsoft 365 Calendar management system that automates calendar archiving, appointment categorization, overlap resolution, and timesheet generation. This guide will help you get started with the core features.

## Prerequisites

### System Requirements
- Python 3.8 or higher
- Microsoft 365 account with calendar access
- Admin Assistant installed and configured

### Initial Setup
1. **Install Admin Assistant** (if not already installed)
2. **Configure Microsoft 365 Authentication**
3. **Set up your first archive configuration**

## Quick Start

### 1. Authentication

First, authenticate with Microsoft 365:

```bash
admin-assistant login msgraph --user <YOUR_USER_ID>
```

This will open a browser window for Microsoft 365 authentication. Follow the prompts to grant calendar access permissions.

### 2. Create Your First Archive Configuration

Set up a configuration to archive your calendar events:

```bash
admin-assistant config calendar archive create --user <YOUR_USER_ID>
```

You'll be prompted to provide:
- **Configuration Name**: A descriptive name (e.g., "Daily Work Archive")
- **Source Calendar**: Your main calendar URI
- **Destination Calendar**: Your archive calendar URI
- **Timezone**: Your local timezone (e.g., "America/New_York")

### 3. Run Your First Archive

Archive yesterday's appointments:

```bash
admin-assistant calendar archive "Daily Work Archive" --user <YOUR_USER_ID> --date "yesterday"
```

## Core Features

### Calendar Archiving

**Purpose**: Move completed appointments from your main calendar to an archive calendar for record-keeping.

**Key Benefits**:
- Keeps your main calendar clean and focused
- Maintains permanent record of all appointments
- Supports compliance and billing requirements
- Automatic overlap detection and resolution

**Basic Usage**:
```bash
# Archive specific date
admin-assistant calendar archive "Work Archive" --user <USER_ID> --date "2024-12-18"

# Archive last 7 days (rolling period ending yesterday)
admin-assistant calendar archive "Work Archive" --user <USER_ID> --date "last 7 days"

# Archive last week (previous calendar week)
admin-assistant calendar archive "Work Archive" --user <USER_ID> --date "last week"

# Archive last month (previous calendar month)
admin-assistant calendar archive "Work Archive" --user <USER_ID> --date "last month"
```

**Date Period Types**:
- **Rolling periods** ('last X days'): Fixed number of days ending yesterday
- **Calendar periods** ('last week', 'last month'): Complete calendar periods (previous week/month)
- **Week start day**: Determined by locale (Monday for most locales, Sunday for US)

### Category Management

**Purpose**: Organize appointments by customer and billing type for timesheet generation.

**Category Format**: `<Customer Name> - <Billing Type>`
- Examples: "Acme Corp - Consulting", "Internal - Admin", "Personal - Break"

**Basic Usage**:
```bash
# List all categories
admin-assistant category list --user <USER_ID>

# Add new category
admin-assistant category add --user <USER_ID> --name "New Client - Development"

# Validate appointment categories
admin-assistant category validate --user <USER_ID> --start-date "2024-12-01" --end-date "2024-12-31"
```

### Overlap Analysis

**Purpose**: Identify and resolve conflicting appointments in your calendar.

**Automatic Resolution Rules**:
- Free appointments are ignored
- Confirmed appointments take priority over tentative
- Private appointments are handled separately

**Basic Usage**:
```bash
# Analyze overlaps for date range
admin-assistant calendar analyze-overlaps --user <USER_ID> --start-date "2024-12-01" --end-date "2024-12-31"

# Auto-resolve overlaps
admin-assistant calendar analyze-overlaps --user <USER_ID> --auto-resolve --start-date "2024-12-01"
```

### Background Jobs

**Purpose**: Schedule automatic archiving to run daily or weekly.

**Basic Usage**:
```bash
# Schedule daily archiving at 11:59 PM
admin-assistant jobs schedule --user <USER_ID> --archive-config <CONFIG_ID> --schedule-type daily --hour 23 --minute 59

# Check job status
admin-assistant jobs status --user <USER_ID>

# Trigger manual job
admin-assistant jobs trigger --user <USER_ID> --archive-config <CONFIG_ID>
```

## Common Workflows

### Daily Workflow
1. **Morning**: Review any overlap notifications from previous day
2. **During Day**: Use consistent category format for new appointments
3. **Evening**: Archive is automatically triggered (if scheduled)

### Weekly Workflow
1. **Monday**: Review category validation for previous week
2. **Friday**: Generate timesheet for the week (when implemented)
3. **Weekend**: System performs any scheduled maintenance

### Monthly Workflow
1. **Month End**: Generate monthly timesheet reports
2. **Review**: Check audit logs for any issues
3. **Cleanup**: Archive old audit logs if needed

## Best Practices

### Appointment Categorization
- **Use Consistent Format**: Always use "Customer - Billing Type" format
- **Special Categories**: 
  - "Online" for remote meetings (no travel time needed)
  - "Admin" for administrative tasks
  - "Break" for personal time
- **Private Appointments**: Mark personal appointments as private

### Calendar Management
- **Regular Archiving**: Set up daily automatic archiving
- **Clean Categories**: Regularly validate and clean up categories
- **Overlap Resolution**: Address overlaps promptly to maintain data integrity

### Security
- **Token Management**: Tokens are automatically managed and refreshed
- **Private Data**: Private appointments are excluded from client timesheets
- **Audit Trail**: All operations are logged for compliance

## Troubleshooting

### Common Issues

**Authentication Expired**
```bash
# Re-authenticate
admin-assistant login msgraph --user <USER_ID>
```

**Archive Configuration Not Found**
```bash
# List available configurations
admin-assistant config calendar archive list --user <USER_ID>
```

**Category Validation Errors**
```bash
# Check category format issues
admin-assistant category validate --user <USER_ID> --issues
```

**Job Not Running**
```bash
# Check job health
admin-assistant jobs health

# Check job status
admin-assistant jobs status --user <USER_ID>
```

### Getting Help

**View Command Help**:
```bash
# General help
admin-assistant --help

# Specific command help
admin-assistant calendar archive --help
admin-assistant category --help
```

**Check System Status**:
```bash
# Job scheduler health
admin-assistant jobs health

# List all configurations
admin-assistant config calendar archive list --user <USER_ID>
```

## Next Steps

### Advanced Features (Coming Soon)
- **PDF Timesheet Generation**: Generate professional timesheets from archived appointments
- **Travel Detection**: Automatic travel time calculation and appointment creation
- **Xero Integration**: Direct invoice generation with timesheet attachments
- **Email Automation**: Automatic client communication and timesheet delivery

### Learning More
- **CLI Reference**: See [CLI Command Structure](../../2-architecture/CLI-001-Command-Structure.md)
- **Workflows**: See [Outlook Calendar Management Workflow](../../1-requirements/workflows/outlook-calendar-management-workflow.md)
- **Architecture**: See [System Architecture](../../2-architecture/ARCH-001-System-Architecture.md)

## Support

For technical issues or questions:
1. Check the troubleshooting section above
2. Review the audit logs for error details
3. Consult the technical documentation
4. Contact your system administrator

---

*This guide covers the core functionality available in Admin Assistant. Additional features are being actively developed.*
