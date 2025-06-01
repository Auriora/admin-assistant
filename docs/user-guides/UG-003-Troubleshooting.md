# Troubleshooting Guide

## Document Information
- **Document ID**: UG-003
- **Document Name**: Troubleshooting Guide
- **Created By**: Admin Assistant System
- **Creation Date**: 2024-12-19
- **Status**: ACTIVE
- **Target Audience**: End Users and Administrators

## Overview

This guide provides solutions to common issues encountered when using Admin Assistant. Issues are organized by functional area with step-by-step resolution procedures.

## Quick Diagnostic Commands

Before diving into specific issues, run these commands to check system health:

```bash
# Check job scheduler health
admin-assistant jobs health

# Verify authentication
admin-assistant login msgraph --user <USER_ID>

# List configurations
admin-assistant config calendar archive list --user <USER_ID>

# Check job status
admin-assistant jobs status --user <USER_ID>
```

## Authentication Issues

### Issue: "No valid MS Graph token found"

**Symptoms**:
- Commands fail with authentication error
- Error message: "Please login with 'admin-assistant login msgraph'"

**Causes**:
- Token expired or not present
- Token cache corrupted
- First-time setup

**Resolution**:
```bash
# Re-authenticate with Microsoft 365
admin-assistant login msgraph --user <USER_ID>
```

**Follow-up**:
- Browser window should open for authentication
- Grant calendar permissions when prompted
- Verify token is cached: Check for `~/.cache/admin-assistant/ms_token.json`

### Issue: Authentication browser doesn't open

**Symptoms**:
- Device code displayed but browser doesn't open
- Manual navigation required

**Resolution**:
1. Copy the device code from terminal
2. Manually navigate to: https://microsoft.com/devicelogin
3. Enter the device code
4. Complete authentication process

### Issue: "Insufficient privileges" error

**Symptoms**:
- Authentication succeeds but operations fail
- Permission-related error messages

**Causes**:
- Insufficient Microsoft 365 permissions
- Admin consent required

**Resolution**:
1. Contact your Microsoft 365 administrator
2. Request calendar read/write permissions
3. Ensure admin consent is granted for the application

## Calendar Archiving Issues

### Issue: "Archive configuration not found"

**Symptoms**:
- Archive command fails with configuration error
- Error: "Archive configuration not found: <ID>"

**Diagnosis**:
```bash
# List available configurations
admin-assistant config calendar archive list --user <USER_ID>
```

**Resolution**:
1. Use correct configuration ID from the list
2. If no configurations exist, create one:
```bash
admin-assistant config calendar archive create --user <USER_ID>
```

### Issue: "Calendar not found" during archiving

**Symptoms**:
- Archive operation fails
- Source or destination calendar not accessible

**Diagnosis**:
```bash
# List available calendars
admin-assistant calendar list --user <USER_ID> --datastore msgraph
```

**Resolution**:
1. Verify calendar URIs in configuration
2. Check calendar permissions
3. Update configuration if needed:
```bash
admin-assistant config calendar archive edit --user <USER_ID> --config-id <CONFIG_ID>
```

### Issue: Archive operation takes too long

**Symptoms**:
- Archive command hangs or times out
- Large number of appointments to process

**Causes**:
- Large date range
- Network connectivity issues
- API rate limiting

**Resolution**:
1. Use smaller date ranges:
```bash
# Instead of "last month", use smaller chunks
admin-assistant calendar archive --user <USER_ID> --archive-config <CONFIG_ID> --date "2024-12-01"
admin-assistant calendar archive --user <USER_ID> --archive-config <CONFIG_ID> --date "2024-12-02"
```

2. Check network connectivity
3. Retry operation if it fails

### Issue: Duplicate appointments in archive

**Symptoms**:
- Same appointment appears multiple times in archive
- Archive operation reports duplicates

**Causes**:
- Multiple archive runs on same date
- Recurring event processing issues

**Resolution**:
1. Admin Assistant automatically handles duplicates
2. Check audit logs for details:
```bash
# Review recent operations (check audit_log table)
```

3. If persistent, contact administrator

## Category Management Issues

### Issue: Category validation shows many errors

**Symptoms**:
- High number of validation issues
- Appointments with incorrect category format

**Diagnosis**:
```bash
# Check validation details
admin-assistant category validate --user <USER_ID> --start-date "last week" --issues
```

**Common Issues and Fixes**:

**Missing Categories**:
- Add missing categories:
```bash
admin-assistant category add --user <USER_ID> --name "Client Name - Billing Type"
```

**Incorrect Format**:
- Update appointment categories to use "Customer - Billing Type" format
- Use consistent naming conventions

**Special Categories**:
- Ensure special categories exist:
```bash
admin-assistant category add --user <USER_ID> --name "Online"
admin-assistant category add --user <USER_ID> --name "Admin"
admin-assistant category add --user <USER_ID> --name "Break"
```

### Issue: Cannot add or edit categories

**Symptoms**:
- Category operations fail
- Permission or validation errors

**Resolution**:
1. Check authentication status
2. Verify category name format
3. For Microsoft Graph categories, ensure proper permissions

## Background Job Issues

### Issue: Scheduled jobs not running

**Symptoms**:
- Archiving doesn't happen automatically
- No recent job execution

**Diagnosis**:
```bash
# Check job health
admin-assistant jobs health

# Check job status
admin-assistant jobs status --user <USER_ID>
```

**Common Causes and Solutions**:

**Job Scheduler Not Running**:
- Restart the application
- Check system resources

**Inactive Configuration**:
```bash
# Activate configuration
admin-assistant config calendar archive activate --user <USER_ID> --config-id <CONFIG_ID>
```

**Inactive Job**:
```bash
# Reschedule job
admin-assistant jobs schedule --user <USER_ID> --archive-config <CONFIG_ID> --schedule-type daily
```

### Issue: Job fails with authentication error

**Symptoms**:
- Scheduled jobs fail
- Authentication errors in logs

**Resolution**:
1. Re-authenticate:
```bash
admin-assistant login msgraph --user <USER_ID>
```

2. Verify token persistence
3. Check token refresh settings

## Overlap Resolution Issues

### Issue: Overlaps not resolving automatically

**Symptoms**:
- Overlap analysis shows conflicts
- Auto-resolution doesn't work

**Diagnosis**:
```bash
# Check overlap details
admin-assistant calendar analyze-overlaps --user <USER_ID> --start-date "yesterday" --details
```

**Understanding Auto-Resolution Rules**:
- **Free appointments**: Automatically ignored
- **Tentative vs Confirmed**: Confirmed takes priority
- **Private appointments**: Handled separately
- **Complex overlaps**: May require manual resolution

**Manual Resolution**:
1. Review overlap details
2. Update appointment status (Free/Tentative/Confirmed)
3. Mark appropriate appointments as private
4. Re-run analysis

## Date Parsing Issues

### Issue: "Unable to parse date" error

**Symptoms**:
- Commands fail with date parsing error
- Invalid date format messages

**Supported Date Formats**:
- `"today"`, `"yesterday"`
- `"last 7 days"`, `"last week"`, `"last month"`
- `"2024-12-18"` (YYYY-MM-DD)
- `"31-12-2024"` (DD-MM-YYYY)
- `"31-Dec"` (DD-MMM, current year)
- `"1-6 to 7-6"` (DD-MM to DD-MM)

**Resolution**:
Use one of the supported formats above.

## Performance Issues

### Issue: Commands running slowly

**Symptoms**:
- Long response times
- Operations timing out

**Causes**:
- Large datasets
- Network connectivity
- API rate limiting

**Resolution**:
1. **Reduce scope**:
   - Use smaller date ranges
   - Process data in chunks

2. **Check connectivity**:
   - Verify internet connection
   - Test Microsoft Graph API access

3. **Monitor resources**:
   - Check system memory and CPU
   - Close unnecessary applications

## Data Integrity Issues

### Issue: Missing appointments after archiving

**Symptoms**:
- Appointments not found in archive
- Data appears lost

**Diagnosis**:
1. Check audit logs for operation details
2. Verify archive calendar access
3. Check for error messages during archiving

**Resolution**:
1. **Verify archive location**:
```bash
admin-assistant calendar list --user <USER_ID> --datastore msgraph
```

2. **Check configuration**:
```bash
admin-assistant config calendar archive list --user <USER_ID>
```

3. **Re-run archive if needed**:
```bash
admin-assistant calendar archive --user <USER_ID> --archive-config <CONFIG_ID> --date <DATE>
```

### Issue: Duplicate or corrupted data

**Symptoms**:
- Inconsistent appointment data
- Duplicate entries

**Resolution**:
1. Admin Assistant includes duplicate detection
2. Check audit logs for operation history
3. Contact administrator if data corruption suspected

## System-Level Issues

### Issue: Application won't start

**Symptoms**:
- CLI commands not found
- Import errors

**Resolution**:
1. **Check installation**:
```bash
which admin-assistant
python -c "import core; print('Core module OK')"
```

2. **Verify environment**:
```bash
# Activate virtual environment if used
source .venv/bin/activate

# Check Python version
python --version
```

3. **Reinstall if necessary**

### Issue: Database connection errors

**Symptoms**:
- Database-related error messages
- Operations fail to persist

**Resolution**:
1. Check database file permissions
2. Verify database schema is up to date:
```bash
alembic current
alembic upgrade head
```

3. Check disk space availability

## Getting Additional Help

### Log Analysis

**Audit Logs**: Check the audit_log table for detailed operation history
**Application Logs**: Review application logs for error details
**System Logs**: Check system logs for infrastructure issues

### Diagnostic Information

When reporting issues, include:
1. **Command executed**: Exact command that failed
2. **Error message**: Complete error output
3. **System information**: OS, Python version, Admin Assistant version
4. **Recent operations**: What was done before the issue occurred

### Contact Information

For persistent issues:
1. Check this troubleshooting guide
2. Review the user guides and documentation
3. Contact your system administrator
4. Provide diagnostic information when reporting issues

## Preventive Measures

### Regular Maintenance

**Daily**:
- Monitor scheduled job execution
- Address any overlap notifications

**Weekly**:
- Run category validation
- Review audit logs for issues

**Monthly**:
- Check system health
- Update configurations if needed
- Review and clean up old data

### Best Practices

1. **Consistent Categorization**: Use standard category format
2. **Regular Archiving**: Don't let main calendar get too cluttered
3. **Monitor Jobs**: Check job status regularly
4. **Keep Tokens Fresh**: Re-authenticate if experiencing issues
5. **Backup Configurations**: Document your archive configurations

---

*This troubleshooting guide covers common issues with Admin Assistant. For additional support, consult the technical documentation or contact your administrator.*
