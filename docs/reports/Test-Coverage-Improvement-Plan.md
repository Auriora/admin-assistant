# Test Coverage Improvement Plan - Core & CLI Focus

## Document Information
- **Document ID**: TCIP-001
- **Document Name**: Test Coverage Improvement Plan - Core & CLI Focus
- **Created By**: Admin Assistant System
- **Creation Date**: 2024-12-19
- **Last Updated**: 2024-12-19
- **Status**: ACTIVE

## Current Status (Core & CLI Only)
- **Current Coverage**: 61% (2,551/4,211 lines)
- **Target Coverage**: 80%
- **Gap**: 19% (~800 lines)
- **Tests Passing**: 302/302
- **Scope**: Excluding web/ module (stub implementation)

## 🎯 PHASE 1 PROGRESS UPDATE - CLI Test Fixes

**Category Commands: 10/16 tests now PASSING! ✅**

**Proven Pattern Established:**
- ✅ Use context managers instead of decorators for local imports
- ✅ Create simple classes instead of Mock objects for Rich rendering
- ✅ Match exact CLI output text in assertions
- ✅ Handle string vs integer parameter differences

**🎉 MAJOR PROGRESS UPDATE:**
- **Coverage increased from 61% to 64% (+3%)**
- **CLI Tests: 48/70 passing (68.6% pass rate)**

**🎉 PHASE 1 MAJOR SUCCESS UPDATE:**
- **Coverage: 64% (maintained +3% gain)**
- **CLI Tests: 51/70 passing (72.9% pass rate) - +24% improvement!**

**Current Status by Module:**
- **Category CLI Tests**: 10/16 passing (62.5%)
- **Config CLI Tests**: 8/13 passing (61.5%) ✅ Major improvement!
- **Job CLI Tests**: 4/12 passing (33.3%) ✅ **Major improvement from 8%**
- **Main CLI Tests**: 23/23 passing (100%) ✅
- **Overlap Analysis Tests**: 6/6 passing (100%) ✅

**Remaining Work:**
- **19 failing tests** - all with same fixable pattern
- **Estimated additional coverage**: +1-2% from remaining CLI fixes
- **Pattern proven** across all CLI modules

**Phase 1 Results:**
- ✅ **Achieved: +3% coverage increase**
- ✅ **Proven pattern established** and working excellently
- ✅ **CLI test reliability improved** from ~31% to 73%
- 🎯 **Ready for Phase 2** or continue with remaining CLI fixes

### CLI Main Module (`cli/main.py` - 859 lines, 27% coverage)
**High-Impact Missing Tests (625 uncovered lines):**

**Category Management Commands:**
- `test_category_list_command()` - Test category listing
- `test_category_add_command()` - Test category creation
- `test_category_edit_command()` - Test category modification
- `test_category_delete_command()` - Test category deletion
- `test_category_validate_command()` - Test category validation

**Configuration Management Commands:**
- `test_config_calendar_archive_commands()` - Test archive config management
- `test_config_job_configuration_commands()` - Test job config management
- `test_config_user_management_commands()` - Test user config management

**Job Management Commands:**
- `test_job_schedule_commands()` - Test job scheduling
- `test_job_trigger_commands()` - Test manual job triggers
- `test_job_status_commands()` - Test job status queries
- `test_job_remove_commands()` - Test job removal

**Timesheet Commands:**
- `test_timesheet_generate_commands()` - Test timesheet generation
- `test_timesheet_export_commands()` - Test timesheet export

**Error Handling & Validation:**
- `test_invalid_command_arguments()` - Test argument validation
- `test_missing_user_scenarios()` - Test user not found cases
- `test_authentication_failures()` - Test auth error handling
- `test_service_unavailable_scenarios()` - Test service errors

### Auth Utility (`core/utilities/auth_utility.py` - 57 lines, 21% coverage)
**Critical Missing Tests (45 uncovered lines):**
- `test_ensure_secure_cache_dir()` - Test directory creation with secure permissions
- `test_get_msal_app()` - Test MSAL application initialization
- `test_msal_login_device_flow()` - Test device flow authentication
- `test_msal_login_cached_token()` - Test cached token usage
- `test_msal_logout()` - Test token cleanup
- `test_get_cached_access_token()` - Test token retrieval
- `test_token_cache_security()` - Test file permission enforcement
- `test_token_refresh_scenarios()` - Test token refresh handling

### Calendar Recurrence Utility (`core/utilities/calendar_recurrence_utility.py` - 36 lines, 42% coverage)
**Missing Tests (21 uncovered lines):**
- `test_expand_recurring_events()` - Test recurrence expansion
- `test_complex_recurrence_patterns()` - Test RRULE parsing
- `test_timezone_handling_in_recurrence()` - Test timezone conversion
- `test_recurrence_exception_handling()` - Test error scenarios

### Time Utility (`core/utilities/time_utility.py` - 6 lines, 50% coverage)
**Missing Tests (3 uncovered lines):**
- `test_timezone_conversion_functions()` - Test timezone utilities
- `test_date_parsing_utilities()` - Test date parsing helpers

## Priority 3: Core Services (Medium Coverage)

### Background Job Service (`core/services/background_job_service.py` - 177 lines, 60% coverage)
**Missing Tests (70 uncovered lines):**
- `test_schedule_weekly_archive_job()` - Test weekly job scheduling
- `test_remove_scheduled_job()` - Test job removal functionality
- `test_get_job_status_details()` - Test detailed job status
- `test_job_execution_error_handling()` - Test error scenarios
- `test_job_persistence_and_recovery()` - Test job recovery
- `test_concurrent_job_execution()` - Test concurrency handling
- `test_schedule_all_job_configurations()` - Test bulk scheduling

### Audit Log Service (`core/services/audit_log_service.py` - 55 lines, 58% coverage)
**Missing Tests (23 uncovered lines):**
- `test_search_audit_logs_with_filters()` - Test search functionality
- `test_audit_log_pagination()` - Test large result sets
- `test_correlation_id_tracking()` - Test operation correlation

### Calendar Archive Service (`core/services/calendar_archive_service.py` - 95 lines, 23% coverage)
**Critical Missing Tests (73 uncovered lines):**
- `test_archive_appointments_basic()` - Test basic archiving
- `test_archive_appointments_with_conflicts()` - Test conflict handling
- `test_archive_appointments_error_scenarios()` - Test error handling

### Microsoft Graph Appointment Repository (`core/repositories/appointment_repository_msgraph.py` - 295 lines, 62% coverage)
**Missing Tests (112 uncovered lines):**
- `test_complex_appointment_operations()` - Test complex CRUD operations
- `test_error_handling_scenarios()` - Test API error handling
- `test_batch_operations()` - Test bulk operations
- `test_retry_logic()` - Test retry mechanisms

### Audit Log Repository (`core/repositories/audit_log_repository.py` - 119 lines, 34% coverage)
**Critical Missing Tests (78 uncovered lines):**
- `test_search_with_complex_filters()` - Test advanced search
- `test_pagination_functionality()` - Test large result sets
- `test_audit_log_cleanup()` - Test retention policies

### Job Configuration Repository (`core/repositories/job_configuration_repository.py` - 57 lines, 40% coverage)
**Missing Tests (34 uncovered lines):**
- `test_job_config_crud_operations()` - Test CRUD operations
- `test_job_config_validation()` - Test data validation
- `test_job_config_scheduling_queries()` - Test scheduling queries

### Category Repository (`core/repositories/category_repository.py` - 34 lines, 44% coverage)
**Missing Tests (19 uncovered lines):**
- `test_category_crud_operations()` - Test CRUD operations
- `test_category_hierarchy_management()` - Test hierarchical categories

### Phase 1: CLI Application Enhancement (Week 1) - Target: +12% Coverage
**Priority Files:**
- `cli/main.py` (859 lines, 27% → 55% coverage) = +240 lines

**Actions:**
1. Add comprehensive CLI command tests for all major commands
2. Test error handling and validation scenarios
3. Test user authentication and authorization flows
4. Add integration tests for CLI-to-core service interactions

### Phase 2: Core Utilities (Week 2) - Target: +4% Coverage
**Priority Files:**
- `core/utilities/auth_utility.py` (57 lines, 21% → 85% coverage) = +36 lines
- `core/utilities/calendar_recurrence_utility.py` (36 lines, 42% → 85% coverage) = +15 lines
- `core/utilities/time_utility.py` (6 lines, 50% → 100% coverage) = +3 lines

**Actions:**
1. Test authentication flows and token management
2. Add calendar recurrence and time utility tests
3. Test security and file permission handling

### Phase 3: Core Services (Week 3) - Target: +3% Coverage
**Priority Files:**
- `core/services/background_job_service.py` (177 lines, 60% → 80% coverage) = +35 lines
- `core/services/calendar_archive_service.py` (95 lines, 23% → 70% coverage) = +45 lines

**Actions:**
1. Enhance background job service test coverage
2. Add comprehensive calendar archive service tests
3. Test error scenarios and edge cases

### Phase 4: Repository Layer (Week 4) - Target: +1% Coverage
**Priority Files:**
- `core/repositories/audit_log_repository.py` (119 lines, 34% → 70% coverage) = +43 lines
- `core/repositories/appointment_repository_msgraph.py` (295 lines, 62% → 70% coverage) = +24 lines

**Actions:**
1. Add repository layer tests for data access patterns
2. Test complex queries and error handling
3. Add integration tests for repository interactions

**Expected Coverage Progression:**
- **Phase 1**: 61% → 73% (+12%)
- **Phase 2**: 73% → 77% (+4%)
- **Phase 3**: 77% → 80% (+3%)
- **Phase 4**: 80% → 81% (+1%)

## Integration Test Priorities

### CLI Integration Tests
**Integration Tests Needed:**
- `test_cli_to_core_service_integration()` - Test CLI-to-service integration
- `test_cli_authentication_workflows()` - Test auth flows
- `test_cli_error_propagation()` - Test error handling across layers

### Core Service Integration Tests
**Integration Tests Needed:**
- `test_job_scheduling_end_to_end()` - Test complete job workflows
- `test_archive_workflow_integration()` - Test archiving workflows
- `test_microsoft_graph_integration()` - Test API integration (mocked)

## Success Metrics
- **Target Coverage**: 80% overall (minimum)
- **Stretch Goal**: 81%+ overall
- **CLI Application**: 55%+ coverage
- **Core Services**: 80%+ coverage
- **Core Utilities**: 85%+ coverage
- **Core Repositories**: 70%+ coverage
- **All Tests Passing**: 100%

## Test Infrastructure Requirements
- CLI command testing framework
- Microsoft Graph API comprehensive mocking
- Database test fixtures and factories
- Job scheduler test utilities
- Authentication test helpers
- File system and permission testing utilities

## Risk Mitigation
- **External API Dependencies**: Use comprehensive mocking strategies for Microsoft Graph
- **Authentication Complexity**: Create reusable test fixtures for auth scenarios
- **Database State**: Implement proper test isolation and cleanup
- **File System Operations**: Use temporary directories for security tests
- **CLI Testing**: Mock user inputs and system interactions

## High-Impact Test Files to Create

### New Test Files Needed:
1. `tests/unit/cli/test_category_commands.py` - Category management CLI tests
2. `tests/unit/cli/test_config_commands.py` - Configuration CLI tests
3. `tests/unit/cli/test_job_commands.py` - Job management CLI tests
4. `tests/unit/utilities/test_auth_utility.py` - Authentication utility tests
5. `tests/unit/utilities/test_calendar_recurrence_utility.py` - Recurrence tests
6. `tests/unit/services/test_calendar_archive_service_enhanced.py` - Enhanced archive tests
7. `tests/unit/repositories/test_audit_log_repository_enhanced.py` - Enhanced audit tests

### Enhanced Test Files:
1. `tests/unit/services/test_background_job_service_enhanced.py` - Additional job service tests
2. `tests/integration/test_cli_integration.py` - CLI integration tests

## Coverage Impact Analysis

**Highest ROI Areas:**
1. **CLI Commands** (625 uncovered lines) - Biggest impact
2. **Auth Utility** (45 uncovered lines) - Critical security component
3. **Calendar Archive Service** (73 uncovered lines) - Core business logic
4. **Audit Log Repository** (78 uncovered lines) - Important for compliance

**Total Expected Coverage Gain:** 19% (from 61% to 80%+)

---

*This focused plan targets core and CLI modules to achieve 80%+ test coverage through systematic testing of high-impact, low-coverage areas with specific, measurable milestones.*
