# Test Organization Guidelines

## Overview

The admin-assistant project uses a marker-based test organization system to separate core application tests from utility/development infrastructure tests.

## Test Categories

### Core Application Tests (Default)
- **Location**: `tests/unit/`, `tests/integration/`
- **Purpose**: Test business logic, services, repositories, CLI commands
- **Execution**: Included in default test runs
- **Examples**: Service tests, repository tests, CLI command tests

### Utility Tests
- **Location**: `tests/dev/`, or any test file marked with `@pytest.mark.utility`
- **Purpose**: Test development tools, testing infrastructure, build scripts
- **Execution**: Excluded from default runs, run explicitly with `utilities` command
- **Examples**: Testing helper validation, mock framework tests, development script tests

## Pytest Markers

### Available Markers
- `unit`: Unit tests
- `integration`: Integration tests  
- `slow`: Slow running tests
- `msgraph`: Tests requiring MS Graph API
- `db`: Tests requiring database
- `utility`: Tests for development and testing utilities
- `dev`: Tests for development tools and scripts

### Marking Tests

#### File-level marking (recommended)
```python
import pytest

# Mark all tests in this file as utility tests
pytestmark = pytest.mark.utility

class TestMyUtility:
    def test_something(self):
        pass
```

#### Individual test marking
```python
@pytest.mark.utility
def test_development_helper():
    pass
```

## Test Execution Commands

### Core Application Tests
```bash
# Default - runs core application tests only
python scripts/dev_cli.py test all

# Explicit core tests (same as above)
python scripts/dev_cli.py test core

# Unit tests only
python scripts/dev_cli.py test unit

# Integration tests only  
python scripts/dev_cli.py test integration
```

### Utility Tests
```bash
# Run utility tests only
python scripts/dev_cli.py test utilities

# Run all tests including utilities
python scripts/dev_cli.py test all-inclusive
```

### Coverage and Reporting
```bash
# Core tests with coverage
python scripts/dev_cli.py test all --coverage

# All tests with coverage
python scripts/dev_cli.py test all-inclusive --coverage
```

## Guidelines for Test Placement

### Core Application Tests
Place in standard test directories:
- Business logic → `tests/unit/services/`
- Data access → `tests/unit/repositories/`
- CLI commands → `tests/unit/cli/`
- End-to-end workflows → `tests/integration/`

### Utility Tests
Place in `tests/dev/` or mark with `@pytest.mark.utility`:
- Testing helper validation
- Mock framework tests
- Development script tests
- Build tool tests
- Test infrastructure validation

## Benefits

1. **Faster Development**: Default test runs exclude utility tests for faster feedback
2. **Clear Separation**: Obvious distinction between application and infrastructure tests
3. **Flexible Execution**: Can run any combination of test types as needed
4. **Accurate Coverage**: Core application coverage not skewed by utility tests
5. **Backward Compatibility**: All existing test execution methods continue to work

## Migration Guide

### For New Tests
1. Determine if the test is for core application functionality or development utilities
2. Place in appropriate directory or add appropriate marker
3. Use `pytestmark = pytest.mark.utility` for utility test files

### For Existing Tests
- Core application tests: No changes needed
- Development utility tests: Add `pytestmark = pytest.mark.utility` to file

## Examples

See `tests/dev/test_example_utility.py` for a complete example of utility test organization.
