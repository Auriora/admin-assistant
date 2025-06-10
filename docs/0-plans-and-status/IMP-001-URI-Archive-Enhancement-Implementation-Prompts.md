# Implementation Prompts for URI and Archive Enhancement

## Document Information
- **Document ID**: IMP-001
- **Document Name**: Step-by-Step Implementation Prompts
- **Created By**: Admin Assistant System
- **Creation Date**: 2025-01-27
- **Purpose**: Augment AI implementation prompts for URI format changes and archive/timesheet commands

---

## Implementation Overview

This document provides step-by-step prompts for implementing:
1. **URI Format Enhancement**: Add account context to calendar URIs
2. **Archive Command Simplification**: Allow overlaps for complete data preservation
3. **Timesheet Command**: New category-filtered archiving for billing
4. **Database Migration**: Safe migration of existing URIs

**Total Estimated Time**: 7-10 hours across 8 implementation steps

---

## Step 1: Update URI Utility with Account Context (1 hour)

### **Prompt 1A: Enhance ParsedURI Dataclass**

```
Update the ParsedURI dataclass in src/core/utilities/uri_utility.py to include account context support.

Current format: <scheme>://<namespace>/<identifier>
New format: <scheme>://<account>/<namespace>/<identifier>

Requirements:
1. Add 'account' field to ParsedURI dataclass
2. Update the dataclass to handle the new URI structure
3. Maintain backward compatibility with existing URIs
4. Add proper type hints and documentation

The ParsedURI should support both formats:
- Legacy: msgraph://calendars/primary
- New: msgraph://user@example.com/calendars/primary

Ensure the account field is properly extracted and validated.
```

### **Prompt 1B: Update URI Parsing Functions**

```
Update the URI parsing and construction functions in src/core/utilities/uri_utility.py to handle account context.

Requirements:
1. Modify parse_resource_uri() to extract account from URI path
2. Update construct_resource_uri() to include account parameter
3. Add account validation logic
4. Handle both legacy and new URI formats seamlessly
5. Update all related helper functions

Examples of expected behavior:
- parse_resource_uri("msgraph://user@example.com/calendars/primary") should extract account="user@example.com"
- construct_resource_uri("msgraph", "user@example.com", "calendars", "primary") should return "msgraph://user@example.com/calendars/primary"

Maintain all existing functionality while adding the new account context support.
```

---

## Step 2: Enhance Calendar Resolver (1 hour)

### **Prompt 2: Update Calendar Resolver for Account Validation**

```
Update the CalendarResolver class in src/core/utilities/calendar_resolver.py to validate account context against the user.

Requirements:
1. Add account validation method _validate_account_context()
2. Validate that URI account context matches the user (email, username, or ID)
3. Update resolve_calendar_uri() to perform account validation
4. Add appropriate error handling for account mismatches
5. Maintain backward compatibility with URIs that don't have account context

The resolver should:
- Accept URIs with or without account context
- Validate account context when present
- Raise CalendarResolutionError for account mismatches
- Log validation results for debugging

Example validation logic:
- URI: msgraph://bruce@company.com/calendars/primary
- User email: bruce@company.com → Valid
- User email: jane@company.com → Invalid (raise error)
```

---

## Step 3: Create Database Migration Script (1.5 hours)

### **Prompt 3A: Create Migration File Structure**

```
Create a new Alembic migration file at src/core/migrations/versions/YYYYMMDD_add_account_context_to_uris.py.

Requirements:
1. Create migration that adds account context to existing calendar URIs
2. Add new columns: allow_overlaps (Boolean, default True), archive_purpose (String, default 'general')
3. Include comprehensive error handling and logging
4. Support both upgrade and downgrade operations
5. Add migration statistics and validation

The migration should:
- Update all existing URIs in archive_configurations table
- Use user email as primary account context, fallback to username, then user_id
- Handle edge cases (missing users, null emails/usernames)
- Provide detailed logging of all changes
- Be fully reversible
```

### **Prompt 3B: Implement URI Transformation Functions**

```
Implement the URI transformation functions for the database migration in src/core/migrations/versions/YYYYMMDD_add_account_context_to_uris.py.

Requirements:
1. add_account_context_to_uri(uri, account_context) - Add account to URI
2. remove_account_context_from_uri(uri) - Remove account from URI (for rollback)
3. get_account_context_for_user(connection, user_id) - Get user's account context
4. Handle all URI formats: msgraph://, local://, legacy formats
5. Include comprehensive test cases

Examples:
- add_account_context_to_uri("msgraph://calendars/primary", "user@example.com") → "msgraph://user@example.com/calendars/primary"
- remove_account_context_from_uri("msgraph://user@example.com/calendars/primary") → "msgraph://calendars/primary"

Include edge case handling for malformed URIs, empty values, and unknown formats.
```

---

## Step 4: Create Migration Test Script (1 hour)

### **Prompt 4: Create Migration Test and Validation Script**

```
Create a comprehensive test script at scripts/test_uri_migration.py to validate the migration logic before deployment.

Requirements:
1. Test all URI transformation functions with comprehensive test cases
2. Simulate database migration with sample data
3. Validate both forward and reverse migrations
4. Test edge cases: empty URIs, malformed URIs, missing user data
5. Provide clear pass/fail reporting

The script should include:
- test_comprehensive_uri_scenarios() - Test all URI transformation cases
- simulate_database_migration() - Mock database migration with sample configs
- Validation of migration statistics and error handling
- Clear output showing what would happen during actual migration

Test cases should cover:
- Primary calendars, named calendars, legacy formats
- Different account types: emails, usernames, user IDs
- Already migrated URIs, unknown formats
- Special characters in emails/usernames
```

---

## Step 5: Update Archive Configuration Model (30 minutes)

### **Prompt 5: Enhance Archive Configuration Model**

```
Update the ArchiveConfiguration model in src/core/models/archive_configuration.py to support the new URI format and archive options.

Requirements:
1. Update column documentation to reflect new URI format with account context
2. Add allow_overlaps column (Boolean, default True)
3. Add archive_purpose column (String, default 'general')
4. Add helper methods: is_timesheet_archive property, get_account_context method
5. Update __repr__ method to include new fields

The enhanced model should:
- Support both 'general' and 'timesheet' archive purposes
- Allow configuration of overlap handling behavior
- Provide easy access to account context from URIs
- Maintain backward compatibility with existing configurations
- Include comprehensive documentation for all fields
```

---

## Step 6: Simplify Archive Command (1 hour)

### **Prompt 6: Modify Archive Service to Allow Overlaps**

```
Update the calendar archive service in src/core/services/calendar_archive_service.py to support simplified archiving that allows overlaps.

Requirements:
1. Add allow_overlaps parameter to prepare_appointments_for_archive()
2. When allow_overlaps=True, archive all appointments including overlaps
3. Still detect and report overlaps, but don't exclude them from archiving
4. Maintain backward compatibility with existing behavior
5. Update return status to include "ok_with_overlaps" when overlaps are present but allowed

The simplified logic should:
- Remove the overlap exclusion logic when allow_overlaps=True
- Continue to remove exact duplicates for data quality
- Report overlaps in the conflicts field for transparency
- Preserve all appointment data for complete audit trails
- Add comprehensive logging of the archiving decisions
```

---

## Step 7: Create Timesheet Archive Service (2 hours)

### **Prompt 7A: Create Timesheet Archive Service**

```
Create a new TimesheetArchiveService class at src/core/services/timesheet_archive_service.py for category-filtered archiving.

Requirements:
1. Filter appointments to include only business categories (billable, non-billable, travel)
2. Apply automatic overlap resolution using EnhancedOverlapResolutionService
3. Exclude personal appointments and 'Free' status appointments
4. Integrate with existing CategoryProcessingService
5. Provide clean, billing-ready data output

The service should:
- Define TIMESHEET_CATEGORIES constant for business categories
- Implement _filter_business_appointments() method
- Implement _resolve_overlaps_automatically() method
- Detect travel appointments by subject keywords
- Use existing overlap resolution rules (Free → Tentative → Priority)
- Return statistics on filtered and resolved appointments
```

### **Prompt 7B: Integrate Timesheet Service with Archive Orchestrator**

```
Update the CalendarArchiveOrchestrator in src/core/orchestrators/calendar_archive_orchestrator.py to support timesheet-specific archiving.

Requirements:
1. Add support for archive_purpose configuration option
2. Route to TimesheetArchiveService when archive_purpose='timesheet'
3. Use simplified archive logic when allow_overlaps=True
4. Maintain all existing functionality for general archiving
5. Add comprehensive audit logging for both archive types

The orchestrator should:
- Check ArchiveConfiguration.archive_purpose to determine processing type
- Use TimesheetArchiveService for timesheet archives
- Use simplified overlap handling for general archives when allow_overlaps=True
- Log the archive type and processing decisions
- Maintain backward compatibility with existing configurations
```

---

## Step 8: Update CLI Commands (1.5 hours)

### **Prompt 8A: Add Timesheet CLI Commands**

```
Add new timesheet commands to the CLI in src/cli/main.py.

Requirements:
1. Add timesheet_app = typer.Typer(help="Timesheet archiving operations")
2. Create 'admin-assistant calendar timesheet' command
3. Create 'admin-assistant config calendar timesheet create' command
4. Support all existing archive command options
5. Add timesheet-specific help text and examples

Commands to implement:
- admin-assistant calendar timesheet <config_name> --user <USER> --date <DATE>
- admin-assistant config calendar timesheet create --user <USER> [options]
- admin-assistant config calendar timesheet list --user <USER>

The commands should:
- Use the same date parsing and user resolution as archive commands
- Create ArchiveConfiguration with archive_purpose='timesheet'
- Provide clear help text explaining timesheet vs archive differences
- Include examples in help text
```

### **Prompt 8B: Update Archive CLI for New URI Format**

```
Update the existing archive CLI commands in src/cli/main.py to support the new URI format with account context.

Requirements:
1. Update archive configuration creation to use new URI format
2. Add auto-completion for account context based on user
3. Support both old and new URI formats for backward compatibility
4. Update help text and examples to show new URI format
5. Add validation for URI format and account context

The updates should:
- Auto-detect user account context (email > username > user_id)
- Allow manual specification of account context in URIs
- Validate that account context matches the specified user
- Provide helpful error messages for URI format issues
- Update all CLI help text and examples to use new format
```

---

## Step 9: Comprehensive Testing (1 hour)

### **Prompt 9: Create Comprehensive Test Suite**

```
Create comprehensive tests for all the new functionality across multiple test files.

Requirements:
1. Update tests/unit/utilities/test_uri_utility.py for new URI parsing
2. Create tests/unit/services/test_timesheet_archive_service.py
3. Update tests/unit/orchestrators/test_calendar_archive_orchestrator.py
4. Create integration tests for the complete workflow
5. Test migration script functionality

Test coverage should include:
- URI parsing and construction with account context
- Account validation in CalendarResolver
- Timesheet filtering and overlap resolution
- Archive simplification (allowing overlaps)
- CLI command functionality
- Migration script edge cases
- Error handling and validation

Each test file should:
- Cover all new methods and functionality
- Test edge cases and error conditions
- Validate backward compatibility
- Include performance considerations
- Provide clear test documentation
```

---

## Implementation Checklist

### **Pre-Implementation**
- [ ] Review current codebase structure
- [ ] Backup database before migration
- [ ] Run existing tests to ensure baseline functionality

### **Phase 1: URI Enhancement**
- [ ] **Step 1**: Update URI utility with account context
- [ ] **Step 2**: Enhance calendar resolver for account validation
- [ ] **Step 3**: Create database migration script
- [ ] **Step 4**: Create migration test script
- [ ] **Step 5**: Update archive configuration model

### **Phase 2: Archive Simplification**
- [ ] **Step 6**: Modify archive service to allow overlaps

### **Phase 3: Timesheet Implementation**
- [ ] **Step 7**: Create timesheet archive service
- [ ] **Step 8**: Update CLI commands

### **Phase 4: Testing and Validation**
- [ ] **Step 9**: Create comprehensive test suite
- [ ] Run migration test script
- [ ] Execute database migration
- [ ] Validate post-migration functionality
- [ ] Run full test suite

### **Post-Implementation**
- [ ] Update documentation
- [ ] Create user migration guide
- [ ] Monitor system performance
- [ ] Gather user feedback

---

## Success Criteria

### **Technical Validation**
- [ ] All tests pass with 95%+ coverage
- [ ] Migration completes without data loss
- [ ] URI format works with account context
- [ ] Archive allows overlaps when configured
- [ ] Timesheet filtering works correctly
- [ ] CLI commands function as expected

### **Functional Validation**
- [ ] Existing archive configurations continue working
- [ ] New timesheet archives filter correctly
- [ ] Overlap handling works as designed
- [ ] Account context validation prevents unauthorized access
- [ ] Migration is fully reversible

### **User Experience**
- [ ] CLI commands are intuitive and well-documented
- [ ] Error messages are clear and helpful
- [ ] Migration process is transparent
- [ ] New features integrate seamlessly

---

## Risk Mitigation

### **Database Migration Risks**
- **Mitigation**: Comprehensive testing with migration test script
- **Backup**: Full database backup before migration
- **Rollback**: Tested downgrade migration available

### **URI Format Changes**
- **Mitigation**: Backward compatibility maintained
- **Validation**: Account context validation prevents errors
- **Testing**: Comprehensive URI parsing tests

### **Archive Behavior Changes**
- **Mitigation**: Configurable overlap handling
- **Default**: Safe defaults maintain existing behavior
- **Documentation**: Clear explanation of changes

---

## Quick Reference Commands

### **Migration Commands**
```bash
# Test migration logic
python scripts/test_uri_migration.py

# Backup database
cp admin_assistant.db admin_assistant.db.backup.$(date +%Y%m%d_%H%M%S)

# Run migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

### **New CLI Commands**
```bash
# Create timesheet archive configuration
admin-assistant config calendar timesheet create --user 1 \
  --name "Weekly Billing" \
  --source-uri "msgraph://bruce@company.com/calendars/primary" \
  --dest-uri "msgraph://bruce@company.com/calendars/timesheet-archive"

# Run timesheet archiving
admin-assistant calendar timesheet "Weekly Billing" --user 1 --date "last week"

# Run general archiving (with overlaps allowed)
admin-assistant calendar archive "Complete Archive" --user 1 --date "last week"
```

### **URI Format Examples**
```bash
# New format with account context
msgraph://bruce@company.com/calendars/primary
msgraph://bruce@company.com/calendars/"Timesheet Archive"
local://bcherrington/calendars/personal

# Legacy format (still supported)
msgraph://calendars/primary
local://calendars/personal
```

This implementation plan provides a systematic approach to implementing all requested changes while maintaining system stability and data integrity.
