# Memory Management in Tests

## Overview

This document describes the memory management improvements implemented to address memory accumulation issues in the test suite. The changes focus on ensuring proper cleanup of resources between tests, preventing memory leaks, and providing tools for monitoring memory usage.

## Identified Issues

The following issues were identified in the test suite:

1. **Immediate Resource Cleanup**: Resources were not being cleaned up immediately after tests, leading to memory accumulation.
2. **Global State Management**: Global state was not being reset consistently between tests.
3. **Thread Lifecycle Control**: Background threads were persisting beyond test boundaries.
4. **Connection Pool Management**: Multiple database engines were creating competing connection pools.
5. **Garbage Collection Timing**: The test suite relied on automatic garbage collection instead of explicit memory management.
6. **Test Isolation**: Resources were being shared between tests instead of being completely isolated.

## Implemented Solutions

### 1. Enhanced Global Cleanup Infrastructure

#### Comprehensive Cleanup Fixture

The `comprehensive_test_cleanup` fixture in `tests/conftest.py` was enhanced to:

- Track memory usage before and after tests
- Explicitly clear SQLAlchemy session registry
- Clean up database resources
- Wait for background threads to terminate with periodic garbage collection
- Force garbage collection of specific generations
- Clear module-level caches
- Log active thread names for debugging
- Log memory differences after cleanup

#### Memory Monitoring Fixture

The `memory_monitor` fixture in `tests/conftest.py` was enhanced to:

- Track memory usage before and after tests
- Warn about significant memory increases
- Provide detailed memory usage information

### 2. Enhanced AsyncRunner Cleanup

#### Improved AsyncRunner Shutdown Mechanism

The `shutdown` method in `AsyncRunner` class was enhanced to:

- Add more robust error handling
- Clear thread attributes to help garbage collection
- Wait for task cancellation with a short timeout
- Explicitly close the event loop
- Aggressively clear references to help garbage collection

#### Immediate Cleanup of Global Runner

The `shutdown_global_runner` function was enhanced to:

- Add additional attempts to force thread termination
- Explicitly clear all references to the runner
- Enhance garbage collection with different strategies
- Check for uncollectable objects and clear the garbage list
- Cancel any remaining async tasks

### 3. Database Session Management Improvements

#### Enhanced Database Cleanup Utility

The database cleanup utilities in `tests/utils/database_cleanup.py` were leveraged to:

- Track all database engines created during tests
- Properly dispose engines and close connections
- Clear SQLAlchemy scoped session registry
- Force garbage collection to clean up connection objects

#### Improved Database Session Fixtures

The database session fixtures in `tests/conftest.py` were enhanced to:

- Use scoped sessions for better cleanup
- Add robust error handling
- Explicitly clear session registries
- Optimize SQLite connection settings for testing

### 4. Memory-Aware Test Runner

A new script `tests/run_memory_aware_tests.py` was created to:

- Run pytest with memory monitoring
- Track memory usage before, during, and after test execution
- Provide detailed reports on memory usage
- Calculate memory growth rate
- Warn about significant memory increases

### 5. Pytest Configuration

The `pytest.ini` file was updated to include memory management settings:

- Added options for cleaner output in memory monitoring
- Leveraged existing markers for memory-intensive tests and tests requiring cleanup

## Recommendations for Future Improvements

1. **Regular Memory Profiling**: Run the memory-aware test runner regularly to identify and address memory leaks.

2. **Resource Tracking**: Implement more comprehensive resource tracking to ensure all resources are properly cleaned up.

3. **Test Isolation**: Consider using more isolated test environments, such as separate processes for tests that create many resources.

4. **Database Connection Pooling**: Review the database connection pooling strategy to ensure it's optimized for testing.

5. **Thread Management**: Implement more robust thread management to ensure all threads are properly terminated.

6. **Automated Memory Leak Detection**: Integrate memory leak detection into the CI/CD pipeline.

7. **Documentation**: Keep this document updated with new memory management strategies and best practices.

## Usage

### Running Tests with Memory Monitoring

To run tests with memory monitoring:

```bash
./tests/run_memory_aware_tests.py [test_path] [options]
```

Options:
- `-m, --markers`: Only run tests matching given mark expression
- `-k, --keywords`: Only run tests which match the given substring expression
- `--gc-debug`: Enable Python memory debugging
- `--sample-interval`: Memory sampling interval in seconds (default: 0.5)

### Example

```bash
# Run all tests with memory monitoring
./tests/run_memory_aware_tests.py

# Run specific test file
./tests/run_memory_aware_tests.py tests/unit/utilities/test_async_runner.py

# Run tests marked as memory_intensive
./tests/run_memory_aware_tests.py -m memory_intensive

# Run with memory debugging enabled
./tests/run_memory_aware_tests.py --gc-debug
```

## Conclusion

The implemented changes address the identified memory management issues by ensuring proper cleanup of resources between tests, preventing memory leaks, and providing tools for monitoring memory usage. These improvements should result in more reliable and efficient test execution, with reduced memory accumulation over time.