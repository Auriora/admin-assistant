# URI Migration Test Suite

## Overview

The `test_uri_migration.py` script provides comprehensive testing of the URI migration logic before deployment. It validates all URI transformation functions and simulates the database migration process with sample data.

## What It Tests

### 1. URI Transformation Functions
- **Basic transformations**: Primary calendars, local calendars, exchange calendars
- **Complex identifiers**: Calendars with spaces, quotes, special characters
- **Legacy formats**: Empty URIs, "calendar", "primary" that need fixing
- **Malformed URIs**: Missing schemes, bare identifiers
- **Account context detection**: Already migrated URIs (should not change)
- **Different account types**: Emails, usernames, numeric IDs
- **International characters**: Unicode calendar names and emails
- **Edge cases**: Empty/null accounts, very long identifiers

### 2. URI Removal Functions
- **Account context removal**: Email accounts, numeric accounts, usernames
- **Complex identifiers**: Spaces, quotes, special characters
- **Already legacy format**: URIs that don't need changes
- **Edge cases**: Empty URIs, malformed URIs, missing paths

### 3. Roundtrip Transformations
- **Bidirectional testing**: Add context then remove it
- **Data integrity**: Ensures original URI is preserved
- **Various scenarios**: Different calendar types and account formats

### 4. Account Context Resolution
- **Priority order**: Email preferred, username fallback, user ID last resort
- **Data combinations**: Complete user data, partial data, empty data
- **Edge cases**: Invalid emails, empty strings, whitespace-only data
- **International support**: Unicode emails and usernames

### 5. Database Migration Simulation
- **Sample data**: 8 users with various data combinations
- **15 archive configurations**: Different URI formats and edge cases
- **Forward migration**: Adding account context to existing URIs
- **Migration statistics**: Success/failure counts, error tracking
- **User context mapping**: Account resolution for each user

### 6. Edge Cases and Error Handling
- **Null/None inputs**: Graceful handling of missing data
- **Very long inputs**: URIs and accounts with extreme lengths
- **Special characters**: Newlines, tabs, invalid characters
- **Malformed data**: Invalid URIs, malformed accounts
- **Error recovery**: Continues processing despite individual failures

## Test Results

The script provides detailed output showing:
- ✅/❌ Pass/fail status for each test
- Expected vs actual results for failures
- Migration statistics and transformations
- Comprehensive final summary with success rates

## Key Findings

### Account Detection Logic
The current migration logic detects accounts by:
- Email addresses (contains '@')
- Numeric IDs (all digits)
- **Note**: Plain usernames are NOT detected as existing accounts

This means:
- `msgraph://user@example.com/calendars/primary` → Already has account (no change)
- `msgraph://123/calendars/primary` → Already has account (no change)  
- `msgraph://johndoe/calendars/primary` → Gets account added: `msgraph://user@example.com/johndoe/calendars/primary`

### Migration Safety
- **Forward migration**: Safely adds account context to legacy URIs
- **Reverse migration**: Cleanly removes account context
- **Error handling**: Robust error recovery and logging
- **Data preservation**: No data loss during transformations

## Usage

```bash
# Run the comprehensive test suite
cd /path/to/admin-assistant
source .venv/bin/activate
python scripts/test_uri_migration.py
```

## Exit Codes
- `0`: All tests passed - migration is safe to deploy
- `1`: Some tests failed - review implementation before deployment

## Sample Output

The script shows exactly what would happen during migration:

```
✅ Config 1 (Primary Archive):
   User: john.doe@company.com
   Source: msgraph://calendars/primary → msgraph://john.doe@company.com/calendars/primary
   Dest:   msgraph://calendars/Archive → msgraph://john.doe@company.com/calendars/Archive
```

This comprehensive testing ensures the URI migration will work correctly in production with real data.
