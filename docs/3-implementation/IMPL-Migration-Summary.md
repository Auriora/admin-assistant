# Account Context URI Migration Summary

## Overview

This document summarizes the new Alembic migration file `20250610_add_account_context_to_uris.py` that adds account context to existing calendar URIs and introduces new archive configuration columns.

## Migration Details

### File Location
```
src/core/migrations/versions/20250610_add_account_context_to_uris.py
```

### Revision Information
- **Revision ID**: `20250610_add_account_context_to_uris`
- **Revises**: `add_restoration_configurations_table`
- **Create Date**: 2025-06-10 00:00:00.000000

## Changes Made

### 1. New Columns Added to `archive_configurations` Table

#### `allow_overlaps` Column
- **Type**: Boolean
- **Default**: True
- **Nullable**: False
- **Purpose**: Controls whether overlapping appointments are allowed in archive operations
- **Use Case**: Enables filtering by appointment categories (travel, billable, non-billable) for timesheet/billing purposes

#### `archive_purpose` Column
- **Type**: String(50)
- **Default**: 'general'
- **Nullable**: False
- **Purpose**: Categorizes the purpose of the archive configuration
- **Use Case**: Supports business billing with categories like 'Billable - [Customer Name]' and 'Non-billable - [Customer Name]'

### 2. URI Account Context Migration

#### Transformation Logic
The migration updates existing calendar URIs to include account context:

**Before (Legacy Format):**
```
msgraph://calendars/primary
msgraph://calendars/"Activity Archive"
local://calendars/personal
```

**After (New Format with Account Context):**
```
msgraph://user@example.com/calendars/primary
msgraph://user@example.com/calendars/"Activity Archive"
local://user@example.com/calendars/personal
```

#### Account Context Priority
The migration uses the following priority order for determining account context:

1. **User email** (preferred) - e.g., `user@example.com`
2. **Username** (fallback) - e.g., `jdoe`
3. **User ID** (last resort) - e.g., `123`

#### Edge Case Handling
- **Missing users**: Uses user_id as context
- **Null/empty emails**: Falls back to username
- **Null/empty usernames**: Falls back to user_id
- **Already migrated URIs**: Skips URIs that already have account context
- **Malformed URIs**: Attempts to fix by adding proper scheme and context

## Migration Features

### Comprehensive Error Handling
- Individual configuration errors don't stop the entire migration
- Detailed error logging for troubleshooting
- Graceful handling of missing or invalid user data

### Migration Statistics
The migration provides detailed statistics including:
- Total configurations processed
- Successfully updated configurations
- Skipped configurations (already have account context)
- Error configurations
- User contexts created
- Account context mappings used

### Validation
Post-migration validation ensures:
- All configurations have account context in their URIs
- Source and destination URIs are properly formatted
- Migration completeness verification

### Reversibility
The migration is fully reversible with a comprehensive `downgrade()` function that:
- Removes account context from all URIs
- Drops the new columns (`allow_overlaps`, `archive_purpose`)
- Provides rollback statistics

## Model Updates

### Updated `ArchiveConfiguration` Model
The SQLAlchemy model in `src/core/models/archive_configuration.py` has been updated to include:

```python
allow_overlaps = Column(
    Boolean,
    default=True,
    nullable=False,
    doc="Whether to allow overlapping appointments in archive operations",
)
archive_purpose = Column(
    String(50),
    default='general',
    nullable=False,
    doc="Purpose of the archive configuration (general, billing, travel, etc.)",
)
```

### Updated Documentation
- Model docstring updated to include new attributes
- `__repr__` method updated to show new fields

## Testing

### URI Transformation Logic Testing
The migration includes comprehensive testing of URI transformation functions:
- Adding account context to various URI formats
- Removing account context (for rollback)
- Roundtrip testing (add then remove should return original)
- Edge case handling (empty URIs, malformed URIs, etc.)

### Test Results
All URI transformation tests pass, ensuring:
- Correct handling of legacy formats
- Proper account context addition
- Reversible transformations
- Edge case robustness

## Usage Examples

### Business Billing Categories
With the new `archive_purpose` column, users can create configurations like:
```
archive_purpose = 'Billable - Modena'
archive_purpose = 'Non-billable - Modena'
archive_purpose = 'Travel'
```

### Overlap Control
The `allow_overlaps` column enables:
- Filtering appointments by categories for billing
- Preventing overlap conflicts in specific archive scenarios
- Maintaining appointment integrity during archival

## Migration Safety

### Backup Compatibility
- Migration preserves all existing data
- Fully reversible with comprehensive rollback
- Detailed logging for audit trails
- Error handling prevents data corruption

### Production Readiness
- Tested URI transformation logic
- Comprehensive error handling
- Detailed validation and statistics
- Safe fallback mechanisms for edge cases

## Next Steps

1. **Run the migration** in a development environment first
2. **Review migration output** and statistics
3. **Test the new columns** in application code
4. **Update any dependent services** that use archive configurations
5. **Deploy to production** after thorough testing

## Support

For questions or issues with this migration:
1. Review the detailed logging output during migration
2. Check the validation statistics for completeness
3. Use the rollback functionality if needed
4. Refer to the URI utility functions for format specifications
