# Test Failure Analysis & Systematic Resolution Plan

**Document**: TEST-FAILURE-ANALYSIS-001  
**Date**: 2025-01-27  
**Status**: Ready for Implementation  
**Current State**: 68 test failures (91.1% pass rate)  
**Target**: <38 test failures (>95% pass rate)

## Executive Summary

Comprehensive analysis of 68 test failures in the admin-assistant project, categorized by root cause with systematic implementation plan to achieve >95% test pass rate.

## Failure Categories & Analysis

### High Priority Issues (39 tests)

| Category | Count | Root Cause | Impact |
|----------|-------|------------|---------|
| **CLI Category Commands** | 14 | Database schema missing (`no such table: users`) | CRITICAL |
| **CLI Import Paths** | 25 | Missing functions (`resolve_cli_user`, `parse_flexible_date`) | HIGH |

### Medium Priority Issues (18 tests)

| Category | Count | Root Cause | Impact |
|----------|-------|------------|---------|
| **Migration Tests** | 11 | Missing `get_migration_module` helper function | MEDIUM |
| **Service Integration** | 7 | API signature mismatches, missing implementations | MEDIUM |

### Low Priority Issues (11 tests)

| Category | Count | Root Cause | Impact |
|----------|-------|------------|---------|
| **URI Utilities** | 8 | Account context parsing incomplete | LOW |
| **Test Expectations** | 3 | Test assertions need updates | LOW |

## Implementation Plan

### Phase 1: Database Schema Fixes (14 tests) 🔴 HIGH PRIORITY

**Issue**: `sqlite3.OperationalError: no such table: users`

**Root Cause**: Test database initialization not creating required tables

**Files to Fix**:
- `tests/conftest.py` - Ensure proper database setup
- `tests/unit/cli/test_category_commands.py` - Update test fixtures

**Implementation Steps**:
1. Verify `Base.metadata.create_all(engine)` includes all models
2. Check test database session configuration
3. Ensure proper transaction handling in CLI tests
4. Validate user fixture creation

**Validation Command**:
```bash
.venv/bin/python -m pytest tests/unit/cli/test_category_commands.py -v
```

**Expected Result**: All 14 category command tests should pass

---

### Phase 2: CLI Import Path Fixes (25 tests) 🔴 HIGH PRIORITY

**Issue**: `AttributeError: module 'cli.main' has no attribute 'resolve_cli_user'`

**Root Cause**: Functions moved to different modules but tests not updated

**Files to Fix**:
- `tests/unit/cli/test_overlap_analysis_cli.py`
- `tests/unit/cli/test_timesheet_commands.py`
- `tests/unit/cli/test_job_commands.py`

**Import Updates Needed**:
```python
# OLD (failing)
from cli.main import resolve_cli_user, parse_flexible_date

# NEW (correct)
from core.utilities.user_resolution import resolve_user as resolve_cli_user
from cli.common.utils import parse_flexible_date
```

**Implementation Steps**:
1. Update all CLI test imports to use correct module paths
2. Fix missing `calendar_commands` and `config_commands` references
3. Update CLI command structure expectations
4. Verify function signatures match

**Validation Command**:
```bash
.venv/bin/python -m pytest tests/unit/cli/test_overlap_analysis_cli.py tests/unit/cli/test_timesheet_commands.py -v
```

**Expected Result**: 25 CLI-related tests should pass

---

### Phase 3: Migration Test Utilities (11 tests) 🟡 MEDIUM PRIORITY

**Issue**: `NameError: name 'get_migration_module' is not defined`

**Root Cause**: Missing test helper function for migration module loading

**Files to Fix**:
- `tests/unit/migrations/test_account_context_migration.py`

**Implementation Steps**:
1. Add `get_migration_module()` helper function:
```python
def get_migration_module():
    """Load migration module for testing."""
    import importlib.util
    import sys
    
    migration_path = os.path.join(
        os.path.dirname(__file__), 
        '../../../src/core/migrations/versions/20250610_add_account_context_to_uris.py'
    )
    spec = importlib.util.spec_from_file_location("migration_module", migration_path)
    migration_module = importlib.util.module_from_spec(spec)
    sys.modules["migration_module"] = migration_module
    spec.loader.exec_module(migration_module)
    return migration_module
```

2. Fix module path format issues
3. Update migration test expectations

**Validation Command**:
```bash
.venv/bin/python -m pytest tests/unit/migrations/test_account_context_migration.py -v
```

**Expected Result**: All 11 migration tests should pass

---

### Phase 4: Service API Alignment (10 tests) 🟡 MEDIUM PRIORITY

**Issue**: Method signature mismatches and missing implementations

**Root Cause**: Service APIs changed but tests not updated

**Files to Fix**:
- `tests/unit/orchestrators/test_calendar_archive_orchestrator.py`
- `tests/unit/services/test_timesheet_archive_service.py`

**Implementation Steps**:
1. Remove `allow_overlaps` parameter from `CalendarArchiveOrchestrator.archive_user_appointments()`
2. Fix missing `process_appointments_for_timesheet` method calls
3. Update result format expectations (remove `business_appointments` key)
4. Fix statistics key mismatches (`resolved_count` vs `resolved`)

**Validation Command**:
```bash
.venv/bin/python -m pytest tests/unit/orchestrators/ tests/unit/services/ -v
```

**Expected Result**: 10 service integration tests should pass

---

### Phase 5: URI Utility Completion (8 tests) 🟢 LOW PRIORITY

**Issue**: Account context parsing not fully implemented

**Root Cause**: URI parsing logic incomplete for account context

**Files to Fix**:
- `src/core/utilities/uri_utility.py`
- `tests/unit/utilities/test_uri_utility.py`

**Implementation Steps**:
1. Complete account context extraction in `ParsedURI`
2. Fix URI validation logic for account context
3. Update user-friendly identifier formatting
4. Handle malformed URI edge cases

**Validation Command**:
```bash
.venv/bin/python -m pytest tests/unit/utilities/test_uri_utility.py -v
```

**Expected Result**: 8 URI utility tests should pass

## Progress Tracking

### Success Metrics

| Phase | Target Reduction | Cumulative Failures | Pass Rate |
|-------|------------------|---------------------|-----------|
| **Start** | - | 68 | 91.1% |
| **Phase 1** | -14 | 54 | 93.0% |
| **Phase 2** | -25 | 29 | 96.2% |
| **Phase 3** | -11 | 18 | 97.7% |
| **Phase 4** | -7 | 11 | 98.6% |
| **Phase 5** | -8 | 3 | 99.6% |

### Validation Commands

**Run All Tests**:
```bash
.venv/bin/python -m pytest tests/unit/ --tb=short -v
```

**Check Progress by Category**:
```bash
.venv/bin/python -m pytest tests/unit/ --tb=no -v | grep "FAILED" | cut -d':' -f1 | sort | uniq -c | sort -nr
```

**Quick Status Check**:
```bash
.venv/bin/python -m pytest tests/unit/ --tb=no | tail -1
```

## Risk Assessment

### High Risk Items
- **Database Schema Changes**: Could affect production migrations
- **CLI Import Changes**: May break existing CLI usage

### Mitigation Strategies
- Test database changes in isolation
- Verify CLI backward compatibility
- Run full test suite after each phase
- Validate migration functionality separately

## Next Steps

1. **Start with Phase 1** - Database schema fixes (highest impact)
2. **Proceed incrementally** - Complete each phase before moving to next
3. **Validate continuously** - Run tests after each fix
4. **Monitor for regressions** - Ensure no new failures introduced

## Success Criteria

✅ **Target Achievement**: >95% test pass rate (<38 failures)  
✅ **No Regressions**: No new test failures introduced  
✅ **Systematic Progress**: Each phase reduces failures as planned  
✅ **Production Safety**: All fixes maintain backward compatibility

---

**Ready for Implementation**: This plan provides a systematic approach to resolve all 68 test failures with clear priorities, implementation steps, and validation criteria.
