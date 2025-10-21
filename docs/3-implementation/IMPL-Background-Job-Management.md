---
title: "Implementation: Background Job Management"
id: "IMPL-Background-Job-Management"
type: [ implementation, jobs ]
status: [ accepted ]
owner: "Auriora Team"
last_reviewed: "DD-MM-YYYY"
tags: [implementation, jobs, scheduler, flask-apscheduler]
links:
  tooling: []
---

# Implementation Guide: Background Job Management

- **Owner**: Auriora Team
- **Status**: Accepted
- **Created Date**: 2024-12-19
- **Last Updated**: 2024-12-19
- **Audience**: [Developers, Maintainers]
- **Scope**: Root

## 1. Purpose

This document describes the implementation of background job management for scheduled and manual archive triggers within the Admin Assistant system. It covers comprehensive job scheduling, monitoring, and management capabilities using Flask-APScheduler, providing a robust and scalable solution.

## 2. Key Concepts

### 2.1. Completed Components

#### Core Services

-   **`BackgroundJobService`** (`core/services/background_job_service.py`): Handles job scheduling (daily/weekly), manual triggering, status monitoring, and removal.
-   **`ScheduledArchiveService`** (`core/services/scheduled_archive_service.py`): Manages high-level schedules, auto-scheduling for active users, and health monitoring based on configurations.

#### Flask Integration

-   **Flask App Configuration** (`web/app/__init__.py`): Initializes Flask-APScheduler, integrates services, manages app context, and optionally auto-schedules jobs on startup.

#### Web API Routes

-   **Job Management Routes** (`web/app/routes/main.py`): Provides RESTful endpoints for scheduling, triggering, status checks, and removal of jobs.

#### CLI Commands

-   **Job Management CLI** (`cli/main.py`): Offers command-line access for all job management functionalities.

### 2.2. Technical Architecture

#### Service Layer Architecture

```
┌─────────────────────────────────────┐
│        Flask Application           │
├─────────────────────────────────────┤
│     ScheduledArchiveService        │
├─────────────────────────────────────┤
│     BackgroundJobService           │
├─────────────────────────────────────┤
│       Flask-APScheduler            │
├─────────────────────────────────────┤
│      ArchiveJobRunner              │
└─────────────────────────────────────┘
```

#### Job Flow

1.  **Scheduled Jobs**: Flask-APScheduler triggers `_run_scheduled_archive`.
2.  **Manual Jobs**: API/CLI triggers `trigger_manual_archive`.
3.  **Job Execution**: Both call `ArchiveJobRunner.run_archive_job`.
4.  **Archive Processing**: Uses the existing `CalendarArchiveOrchestrator`.

## 3. Usage

### 3.1. Web API Usage

#### Schedule Daily Job

```bash
curl -X POST http://localhost:5000/jobs/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "schedule_type": "daily",
    "hour": 23,
    "minute": 59
  }'
```

#### Trigger Manual Job

```bash
curl -X POST http://localhost:5000/jobs/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-12-18",
    "end_date": "2024-12-18"
  }'
```

#### Get Job Status

```bash
curl http://localhost:5000/jobs/status
```

### 3.2. CLI Usage

#### Schedule Daily Job

```bash
admin-assistant jobs schedule --user 1 --type daily --hour 23 --minute 59
```

#### Trigger Manual Job

```bash
admin-assistant jobs trigger --user 1 --start 2024-12-18 --end 2024-12-18
```

#### Check Job Status

```bash
admin-assistant jobs status --user 1
```

#### Remove All Jobs

```bash
admin-assistant jobs remove --user 1 --confirm
```

## 4. Internal Behaviour

### 4.1. Key Features

-   **Flexible Scheduling**: Supports daily and weekly jobs with specified times, and manual job triggering with custom date ranges.
-   **Comprehensive Management**: Includes job status monitoring, health checks, robust error handling, and clean job removal.
-   **Multi-Interface Access**: Accessible via Web API, CLI, and direct Flask app integration.
-   **Configuration Integration**: Integrates with existing archive configurations and user management, automatically detecting active configurations.

### 4.2. Configuration

-   **Flask App Configuration**: The scheduler is automatically initialized in the Flask app. Optional auto-scheduling for active users on startup can be enabled.
-   **Job Persistence**: Jobs are persisted by Flask-APScheduler and will survive application restarts. The default is an in-memory store, but it can be configured for persistent storage.

### 4.3. Error Handling

-   **Robust Error Management**: Comprehensive exception handling at service, API, CLI, and job levels, with proper HTTP status codes and user-friendly messages.
-   **Logging**: Detailed logging of job execution, results, and errors with full stack traces.

### 4.4. Security Considerations

-   **Authentication**: Web API requires Flask-Login, CLI uses the existing user authentication system, and job execution runs with appropriate user context.
-   **Authorization**: Ensures users can only manage their own jobs and validates user ownership of archive configurations.

### 4.5. Performance Considerations

-   **Scalability**: Features like job coalescing and max instances limit concurrent job execution. Uses cron-based scheduling for efficiency.
-   **Resource Management**: Minimal memory footprint, proper database connection management, and automatic recovery from transient failures.

### 4.6. Testing

-   **Test Coverage**: Comprehensive unit tests for all services, integration tests for end-to-end job execution, and testing of error scenarios.
-   **Running Tests**:
    ```bash
    pytest tests/unit/services/test_background_job_service.py -v
    pytest tests/ -k "job" -v
    ```

## 5. Extension Points

### 5.1. Future Enhancements

1.  **Persistent Job Store**: Implement database-backed job persistence.
2.  **Job History**: Track historical job execution.
3.  **Advanced Scheduling**: Support more complex scheduling patterns.
4.  **Notification System**: Integrate job completion notifications.
5.  **Metrics and Monitoring**: Implement detailed job execution metrics.

# References

-   [Implementation Plan](../plans/PM-ASYNC-001-Full-Migration-Plan.md) (Note: This path might need adjustment if the file is renamed or moved.)
-   [System Architecture](../2-architecture/ARCH-001-System-Architecture.md)
