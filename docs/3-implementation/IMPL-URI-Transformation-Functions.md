---
title: "Implementation: URI Transformation Functions"
id: "IMPL-URI-Transformation-Functions"
type: [ implementation, utility ]
status: [ accepted ]
owner: "Auriora Team"
last_reviewed: "DD-MM-YYYY"
tags: [implementation, uri, transformation, migration, utility]
links:
  tooling: []
---

# Implementation Guide: URI Transformation Functions

- **Owner**: Auriora Team
- **Status**: Accepted
- **Created Date**: DD-MM-YYYY
- **Last Updated**: DD-MM-YYYY
- **Audience**: [Developers, Database Administrators]
- **Scope**: Root

## 1. Purpose

This document describes the implementation of URI transformation functions, specifically designed for the database migration that adds account context to URIs within the Admin Assistant project. These functions ensure that calendar URIs are consistently formatted, support user-specific contexts, and maintain backward compatibility.

## 2. Key Concepts

### 2.1. Implemented Functions

#### `add_account_context_to_uri(uri: str, account_context: str) -> str`

Adds account context to a URI if it doesn't already have it.

-   **Transformations**: Converts `msgraph://calendars/primary` to `msgraph://user@example.com/calendars/primary`.
-   **Features**: Handles empty/legacy URIs, detects existing context, fixes malformed URIs, supports all schemes, and preserves query parameters/fragments.

#### `remove_account_context_from_uri(uri: str) -> str`

Removes account context from a URI to revert to a legacy format.

-   **Transformations**: Converts `msgraph://user@example.com/calendars/primary` to `msgraph://calendars/primary`.
-   **Features**: Detects account context by `@` symbol or numeric patterns, preserves URIs without context, and handles malformed URIs gracefully.

#### `get_account_context_for_user(connection, user_id: int) -> str`

Retrieves the best available account context for a user from the database.

-   **Priority Order**: User email (preferred) > Username (fallback) > User ID (last resort).
-   **Features**: Validates email format, trims whitespace, handles missing users, and includes comprehensive error handling.

### 2.2. Test Coverage

An extensive test suite of **81 comprehensive test cases** covers:

-   Basic functionality, including legacy URI transformations and account context detection.
-   Removal function tests for various account formats and malformed URIs.
-   Roundtrip tests to ensure reversibility.
-   Database function tests for email, username, and user ID fallbacks, including error handling.
-   Edge cases, malformed URI handling, special account formats, and unicode support.
-   Performance and limits testing with extremely long accounts and URIs.

## 3. Usage

### 3.1. Basic Usage

```python
# Add account context
result = add_account_context_to_uri("msgraph://calendars/primary", "user@example.com")
# Result: "msgraph://user@example.com/calendars/primary"

# Remove account context
result = remove_account_context_from_uri("msgraph://user@example.com/calendars/primary")
# Result: "msgraph://calendars/primary"

# Get user account context
account = get_account_context_for_user(connection, user_id=1)
# Result: "user@example.com" (or username/user_id as fallback)
```

### 3.2. Edge Cases Handled

```python
# Legacy formats
add_account_context_to_uri("", "user@example.com")
# Result: "msgraph://user@example.com/calendars/primary"

# Already has context
add_account_context_to_uri("msgraph://user@example.com/calendars/primary", "different@example.com")
# Result: "msgraph://user@example.com/calendars/primary" (unchanged)

# Malformed URIs
add_account_context_to_uri("calendars/primary", "user@example.com")
# Result: "msgraph://user@example.com/calendars/calendars/primary"

# Unicode support
add_account_context_to_uri("msgraph://calendars/日本語", "用户@example.com")
# Result: "msgraph://用户@example.com/calendars/日本語"
```

### 3.3. Running Tests

```bash
# Run comprehensive test suite
source .venv/bin/activate
python -m pytest tests/unit/migrations/test_uri_transformation_migration.py -v

# Run demonstration script
python scripts/test_uri_migration_functions.py
```

## 4. Internal Behaviour

### 4.1. Migration Integration

These functions are integrated into the database migration `20250610_add_account_context_to_uris.py`. During the upgrade process, they transform source and destination URIs for all archive configurations, providing detailed logging and statistics. The downgrade process uses `remove_account_context_from_uri` to revert to the legacy format.

### 4.2. Error Handling

Comprehensive error handling includes graceful fallback for database errors, automatic correction of malformed URIs where possible, sensible defaults for missing data, and full Unicode support.

### 4.3. Backward Compatibility

Legacy URIs are automatically detected and transformed. Existing account context is preserved, and roundtrip transformations maintain data integrity. The system gracefully degrades for edge cases.

### 4.4. Security Considerations

SQL injection protection is ensured through proper parameter escaping. Input validation is performed on account formats, and database errors are isolated to prevent propagation. Transformations are reversible to maintain data integrity.

## 5. Extension Points

### 5.1. Future Enhancements

-   Support for additional URI schemes.
-   Enhanced account validation logic.
-   Further performance optimizations.
-   Additional transformation patterns as new requirements emerge.

# References

-   [Account Context URI Migration Summary](IMPL-Migration-Summary.md)
-   [Current Database Schema](DATA-002-Current-Schema.md)
-   [System Architecture](ARCH-001-System-Architecture.md)
