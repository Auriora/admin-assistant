---
title: "Test Strategy: Memory Management in Tests"
id: "STRAT-Memory-Management"
type: [ testing, test-strategy ]
status: [ approved ]
owner: "Auriora Team"
last_reviewed: "DD-MM-YYYY"
tags: [testing, memory, strategy, performance]
links:
  tooling: []
---

# Test Strategy: Memory Management in Tests

- **Owner**: Auriora Team
- **Status**: Approved
- **Created Date**: 2024-12-19
- **Last Updated**: 2024-12-19
- **Audience**: [QA Team, Developers, SRE]
- **Scope**: Admin Assistant Test Suite

## 1. Purpose

This document outlines the strategy for managing memory within the Admin Assistant test suite. The primary objective is to address and prevent memory accumulation issues, ensure proper cleanup of resources between tests, and provide tools for monitoring memory usage. This strategy aims to improve test reliability, efficiency, and maintainability.

## 2. Test Matrix

| Level       | Purpose                                     | Tooling                               | Owner              |
|-------------|---------------------------------------------|---------------------------------------|--------------------|
| Unit        | Isolated component memory usage             | `pytest`, `memory_monitor` fixture    | Development Team   |
| Integration | Inter-component memory leaks                | `pytest`, `memory_monitor` fixture    | QA Team            |
| End-to-End  | Full workflow memory footprint              | `run_memory_aware_tests.py`           | QA Team            |

## 3. Environments

-   **Test Execution Environment**: Python 3.12.x within a virtual environment.
-   **Database**: In-memory SQLite for test isolation, ensuring no persistent state affects memory across runs.
-   **Fixtures**: Global test fixtures (`tests/conftest.py`) provide consistent setup and teardown, including database sessions, user models, and mock external clients.

## 4. Automation

### 4.1. Identified Issues

1.  **Immediate Resource Cleanup**: Resources were not being cleaned up immediately after tests, leading to memory accumulation.
2.  **Global State Management**: Global state was not being reset consistently between tests.
3.  **Thread Lifecycle Control**: Background threads were persisting beyond test boundaries.
4.  **Connection Pool Management**: Multiple database engines were creating competing connection pools.
5.  **Garbage Collection Timing**: The test suite relied on automatic garbage collection instead of explicit memory management.
6.  **Test Isolation**: Resources were being shared between tests instead of being completely isolated.

### 4.2. Implemented Solutions

#### 4.2.1. Enhanced Global Cleanup Infrastructure

-   **Comprehensive Cleanup Fixture**: The `comprehensive_test_cleanup` fixture in `tests/conftest.py` was enhanced to:
    -   Track memory usage before and after tests.
    -   Explicitly clear SQLAlchemy session registry.
    -   Clean up database resources.
    -   Wait for background threads to terminate with periodic garbage collection.
    -   Force garbage collection of specific generations.
    -   Clear module-level caches.
    -   Log active thread names for debugging.
    -   Log memory differences after cleanup.
-   **Memory Monitoring Fixture**: The `memory_monitor` fixture in `tests/conftest.py` was enhanced to:
    -   Track memory usage before and after tests.
    -   Warn about significant memory increases.
    -   Provide detailed memory usage information.

#### 4.2.2. Enhanced AsyncRunner Cleanup

-   **Improved AsyncRunner Shutdown Mechanism**: The `shutdown` method in `AsyncRunner` class was enhanced to:
    -   Add more robust error handling.
    -   Clear thread attributes to help garbage collection.
    -   Wait for task cancellation with a short timeout.
    -   Explicitly close the event loop.
    -   Aggressively clear references to help garbage collection.
-   **Immediate Cleanup of Global Runner**: The `shutdown_global_runner` function was enhanced to:
    -   Add additional attempts to force thread termination.
    -   Explicitly clear all references to the runner.
    -   Enhance garbage collection with different strategies.
    -   Check for uncollectable objects and clear the garbage list.
    -   Cancel any remaining async tasks.

#### 4.2.3. Database Session Management Improvements

-   **Enhanced Database Cleanup Utility**: Utilities in `tests/utils/database_cleanup.py` were leveraged to track and properly dispose of database engines, close connections, and clear SQLAlchemy scoped session registries.
-   **Improved Database Session Fixtures**: Fixtures in `tests/conftest.py` were enhanced to use scoped sessions, add robust error handling, and optimize SQLite connection settings.

#### 4.2.4. Memory-Aware Test Runner

-   A new script `tests/run_memory_aware_tests.py` was created to run `pytest` with memory monitoring, providing detailed reports on memory usage and growth rate.

#### 4.2.5. Pytest Configuration

-   The `pytest.ini` file was updated to include memory management settings and leverage existing markers for memory-intensive tests.

### 4.3. Usage

#### Running Tests with Memory Monitoring

```bash
./tests/run_memory_aware_tests.py [test_path] [options]
```

**Options**:
-   `-m, --markers`: Only run tests matching given mark expression.
-   `-k, --keywords`: Only run tests which match the given substring expression.
-   `--gc-debug`: Enable Python memory debugging.
-   `--sample-interval`: Memory sampling interval in seconds (default: 0.5).

#### Example

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

## 5. Manual Validation

-   Regular execution of `run_memory_aware_tests.py` to manually inspect memory reports and identify unexpected growth.
-   Ad-hoc profiling of specific test modules identified as memory-intensive.

## 6. Risks & Mitigations

-   **Risk**: Memory leaks from external libraries or complex integrations.
    -   **Mitigation**: Comprehensive mocking of external APIs (e.g., MS Graph) to isolate application code. Regular updates to dependencies.
-   **Risk**: Uncaught global state or lingering threads causing memory accumulation.
    -   **Mitigation**: Aggressive cleanup fixtures and explicit shutdown mechanisms for asynchronous components.
-   **Risk**: Performance degradation due to excessive memory usage in CI/CD.
    -   **Mitigation**: Automated memory monitoring in CI/CD pipelines with alerts for significant increases.

## 7. Recommendations for Future Improvements

1.  **Regular Memory Profiling**: Run the memory-aware test runner regularly to identify and address memory leaks.
2.  **Resource Tracking**: Implement more comprehensive resource tracking to ensure all resources are properly cleaned up.
3.  **Test Isolation**: Consider using more isolated test environments, such as separate processes for tests that create many resources.
4.  **Database Connection Pooling**: Review the database connection pooling strategy to ensure it's optimized for testing.
5.  **Thread Management**: Implement more robust thread management to ensure all threads are properly terminated.
6.  **Automated Memory Leak Detection**: Integrate memory leak detection into the CI/CD pipeline.
7.  **Documentation**: Keep this document updated with new memory management strategies and best practices.

## 8. Conclusion

The implemented changes address the identified memory management issues by ensuring proper cleanup of resources between tests, preventing memory leaks, and providing tools for monitoring memory usage. These improvements should result in more reliable and efficient test execution, with reduced memory accumulation over time.

# References

-   [Implementation: Testing and Observability](../3-implementation/IMPL-Testing-And-Observability.md)
-   `tests/conftest.py` (relative path to project root)
-   `tests/run_memory_aware_tests.py` (relative path to project root)
