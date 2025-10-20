# Augment AI Prompts for Full Async Migration

## Overview

This document provides detailed Augment AI prompts for each task in the full async architecture migration. Each prompt is designed to be specific, actionable, and include context about the current codebase.

## Phase 1: Database & Repository Layer

### Task 1.1: Add Async Database Dependencies

**Prompt:**
```
Update the pyproject.toml file in the admin-assistant project to add async database dependencies. 
Add asyncpg~=0.29.0, sqlalchemy[asyncio]~=2.0.0, and alembic[async]~=1.12.0 to the dependencies. 
Remove any sync-only database dependencies that are no longer needed. 
Ensure compatibility with existing dependencies and Python 3.12+ requirement.
```

### Task 1.2: Configure Async SQLAlchemy Engine

**Prompt:**
```
Create a new async database configuration in src/core/database.py for the admin-assistant project. 
Replace the current sync SQLAlchemy setup with create_async_engine and AsyncSession. 
Include proper connection pooling configuration, error handling, and async session lifecycle management. 
Maintain compatibility with the existing database URL configuration and environment variables.
```

### Task 1.3: Update Database Connection Management

**Prompt:**
```
Update the database connection management in the admin-assistant project to support async operations. 
Modify src/core/database.py to include async context managers for database sessions. 
Create async dependency injection functions for FastAPI and ensure proper session cleanup. 
Include error handling for connection failures and transaction rollbacks.
```

### Task 1.4: Create Async Session Management

**Prompt:**
```
Implement async session management utilities for the admin-assistant project. 
Create async context managers and dependency injection functions in src/core/database.py. 
Ensure proper session lifecycle management, transaction handling, and connection pooling. 
Include utilities for testing with async database sessions.
```

### Task 1.5: Convert Base Repository Classes

**Prompt:**
```
Convert the BaseAppointmentRepository class in src/core/repositories/appointment_repository_base.py 
to be fully async. Update all CRUD method signatures to async, remove sync wrapper methods, 
and implement proper async SQLAlchemy patterns. Maintain all existing functionality and 
add proper type hints for async operations.
```

### Task 1.6: Update All Model Repositories

**Prompt:**
```
Convert all repository classes in src/core/repositories/ to use async SQLAlchemy patterns. 
Update UserRepository, CalendarRepository, and other model repositories to be fully async. 
Replace all sync database queries with async equivalents using select(), where(), and 
scalar_one_or_none(). Ensure proper async session handling and error management.
```

### Task 1.7: Remove Sync Wrappers from MSGraph

**Prompt:**
```
Clean up the MSGraphAppointmentRepository in src/core/repositories/appointment_repository_msgraph.py 
by removing all sync wrapper methods (get_by_id, add, list_for_user, etc.). 
Keep only the async methods (aget_by_id, aadd, alist_for_user, etc.) and update 
any remaining references to use the async versions directly.
```

### Task 1.8: Update Repository Tests

**Prompt:**
```
Update all repository tests in tests/unit/repositories/ to use async patterns with pytest-asyncio. 
Convert test methods to async, update database session fixtures for async, and ensure 
all repository method calls use await. Maintain comprehensive test coverage and 
add new tests for async-specific functionality.
```

## Phase 2: Service Layer

### Task 2.1: Convert UserService to Async

**Prompt:**
```
Convert the UserService class in src/core/services/user_service.py to be fully async. 
Update all method signatures to async, add await keywords for repository calls, 
and ensure proper async error handling. Update dependency injection and 
maintain all existing functionality including authentication and user management.
```

### Task 2.2: Convert CalendarArchiveService to Async

**Prompt:**
```
Convert the CalendarArchiveService in src/core/services/calendar_archive_service.py to async. 
Update all business logic methods to be async, ensure proper await usage for repository 
and external API calls, and maintain all existing archiving functionality. 
Include proper async error handling and logging.
```

### Task 2.3: Convert CategoryProcessingService to Async

**Prompt:**
```
Convert the CategoryProcessingService in src/core/services/category_processing_service.py 
to be fully async. Update all category validation and processing methods to async, 
ensure proper await usage for database operations, and maintain all existing 
category management functionality.
```

### Task 2.4: Update Service Dependency Injection

**Prompt:**
```
Update the service dependency injection system in the admin-assistant project to support 
async services. Modify service initialization, lifecycle management, and dependency 
resolution for async patterns. Ensure proper async context propagation throughout 
the service layer and update any service factory functions.
```

### Task 2.5: Convert CalendarArchiveOrchestrator

**Prompt:**
```
Convert the CalendarArchiveOrchestrator in src/core/orchestrators/calendar_archive_orchestrator.py 
to async. Update the archive_user_appointments method and all workflow methods to be async. 
Ensure proper async handling of repository calls, service interactions, and error management. 
Maintain all existing orchestration logic and audit functionality.
```

### Task 2.6: Convert OverlapResolutionOrchestrator

**Prompt:**
```
Convert the OverlapResolutionOrchestrator in src/core/orchestrators/ to async. 
Update all overlap detection and resolution methods to be async, ensure proper 
await usage for service calls, and maintain all existing overlap resolution logic. 
Include proper async error handling and chat integration.
```

### Task 2.7: Update Audit and Logging Services

**Prompt:**
```
Convert audit and logging services in src/core/services/ to be async-compatible. 
Update AuditLogService and ReversibleAuditService to handle async operations, 
ensure proper async context management for audit trails, and maintain all 
existing audit functionality with async database operations.
```

### Task 2.8: Convert Background Job Services

**Prompt:**
```
Convert the BackgroundJobService in src/core/services/background_job_service.py to async. 
Update job scheduling, execution, and monitoring methods to be async. 
Prepare for migration from Flask-APScheduler to AsyncIOScheduler while 
maintaining all existing job management functionality.
```

## Phase 3: Application Layer

### Task 3.1: Set Up FastAPI Application Structure

**Prompt:**
```
Create a new FastAPI application structure to replace the current Flask app in the 
admin-assistant project. Set up the main FastAPI app in src/web/main.py with proper 
CORS, middleware, and error handling. Create the basic routing structure and 
dependency injection system for async services.
```

### Task 3.2: Migrate Authentication System

**Prompt:**
```
Migrate the Flask-Login authentication system to FastAPI's security system. 
Convert the current user authentication in src/web/app/auth/ to use FastAPI's 
OAuth2 and JWT token system. Ensure MS Graph authentication integration works 
correctly and maintain all existing authentication functionality.
```

### Task 3.3: Convert API Endpoints to FastAPI

**Prompt:**
```
Convert all Flask routes in src/web/app/routes/ to FastAPI endpoints. 
Update calendar management, user management, and configuration endpoints to use 
FastAPI's async route handlers. Set up Pydantic models for request/response 
validation and maintain all existing API functionality.
```

### Task 3.4: Update Request/Response Models

**Prompt:**
```
Create Pydantic models for all API request and response schemas in the admin-assistant 
FastAPI application. Replace Flask's request handling with Pydantic validation models. 
Ensure proper data validation, serialization, and error handling for all API endpoints.
```

### Task 3.5: Set Up AsyncClick CLI Structure

**Prompt:**
```
Create a new AsyncClick CLI structure to replace the current Typer CLI in the 
admin-assistant project. Set up the main CLI application in cli/main.py with 
async command support and proper error handling. Maintain the existing command 
structure and argument parsing.
```

### Task 3.6: Convert Calendar Management Commands

**Prompt:**
```
Convert all calendar management CLI commands in cli/ to use AsyncClick. 
Update archive, list, analyze-overlaps, and other calendar commands to be async. 
Ensure proper async service integration and maintain all existing CLI functionality 
including progress indicators and error handling.
```

### Task 3.7: Convert Configuration Commands

**Prompt:**
```
Convert all configuration management CLI commands to AsyncClick. 
Update user management, archive configuration, and system configuration commands 
to be async. Ensure proper async database operations and maintain all existing 
configuration management functionality.
```

### Task 3.8: Convert Job Management Commands

**Prompt:**
```
Convert all job management CLI commands to AsyncClick. 
Update job scheduling, monitoring, and management commands to be async. 
Ensure compatibility with the new AsyncIOScheduler and maintain all existing 
job management functionality.
```

## Phase 4: Background Jobs & Integration

### Task 4.1: Set Up AsyncIOScheduler

**Prompt:**
```
Replace the Flask-APScheduler system with AsyncIOScheduler in the admin-assistant project. 
Set up the new scheduler in src/core/services/background_job_service.py with proper 
async job execution, persistence, and monitoring. Ensure compatibility with existing 
job configurations and scheduling patterns.
```

### Task 4.2: Convert Scheduled Archive Jobs

**Prompt:**
```
Convert all scheduled archive job functions to async in the admin-assistant project. 
Update daily and weekly archive jobs to use async service calls and proper error handling. 
Ensure job persistence, monitoring, and retry logic work correctly with AsyncIOScheduler.
```

### Task 4.3: Convert Backup Jobs

**Prompt:**
```
Convert all backup job functions to async in the admin-assistant project. 
Update calendar backup jobs to use async operations and ensure proper integration 
with the async service layer. Maintain all existing backup functionality and 
error handling.
```

### Task 4.4: Update Job Monitoring and Management

**Prompt:**
```
Update job monitoring and management functionality for AsyncIOScheduler in the 
admin-assistant project. Ensure job status tracking, health monitoring, and 
management interfaces work correctly with async jobs. Maintain all existing 
monitoring and alerting functionality.
```

### Task 4.5: Integration Testing Across All Layers

**Prompt:**
```
Create comprehensive integration tests for the async architecture in the admin-assistant 
project. Set up test scenarios that verify async operations work correctly across 
all layers (repository, service, orchestrator, API, CLI). Ensure proper async 
context management and error handling in integration scenarios.
```

### Task 4.6: Performance Optimization

**Prompt:**
```
Optimize the async architecture performance in the admin-assistant project. 
Implement connection pooling, optimize async database queries, and tune async 
HTTP client configurations. Add performance monitoring and ensure optimal 
resource utilization for async operations.
```

### Task 4.7: Error Handling and Logging Updates

**Prompt:**
```
Update error handling and logging throughout the async architecture in the 
admin-assistant project. Ensure proper async exception handling, context 
propagation for logging, and error recovery mechanisms. Maintain comprehensive 
audit trails and error reporting functionality.
```

### Task 4.8: Documentation Updates

**Prompt:**
```
Update all documentation in the admin-assistant project for the new async architecture. 
Update API documentation, CLI help text, developer guides, and deployment instructions. 
Ensure all examples and code snippets reflect the new async patterns and usage.
```

## Phase 5: Testing & Deployment

### Task 5.1: Comprehensive Async Test Suite

**Prompt:**
```
Create a comprehensive async test suite for the admin-assistant project. 
Set up pytest-asyncio configuration, create async test fixtures, and ensure 
95%+ test coverage for all async components. Include unit tests, integration tests, 
and end-to-end tests for the complete async architecture.
```

### Task 5.2: Performance Benchmarking

**Prompt:**
```
Create performance benchmarks to compare the new async architecture with the 
current sync version in the admin-assistant project. Set up load testing scenarios 
for API endpoints, database operations, and background jobs. Measure and document 
throughput, latency, and resource utilization improvements.
```

### Task 5.3: Load Testing and Stress Testing

**Prompt:**
```
Implement comprehensive load testing and stress testing for the async admin-assistant 
application. Test concurrent user scenarios, high-volume API requests, and 
background job processing under load. Ensure the async architecture meets 
performance targets and handles edge cases correctly.
```

### Task 5.4: Security Testing

**Prompt:**
```
Conduct security testing for the new async architecture in the admin-assistant project. 
Verify authentication and authorization work correctly in async contexts, test for 
async-specific security vulnerabilities, and ensure all security controls are 
maintained in the new architecture.
```

### Task 5.5: Staging Deployment and Validation

**Prompt:**
```
Deploy the async admin-assistant application to staging environment and conduct 
comprehensive validation. Set up ASGI server configuration, environment variables, 
and monitoring. Validate all functionality works correctly in the staging environment 
and perform user acceptance testing.
```

### Task 5.6: Production Deployment Preparation

**Prompt:**
```
Prepare the async admin-assistant application for production deployment. 
Create deployment scripts, update infrastructure configuration for ASGI, 
set up monitoring and alerting, and prepare rollback procedures. 
Ensure all production requirements are met for the async architecture.
```

### Task 5.7: Monitoring and Alerting Setup

**Prompt:**
```
Set up comprehensive monitoring and alerting for the async admin-assistant application. 
Configure performance monitoring, error tracking, health checks, and alerting for 
async operations. Ensure proper observability for the new architecture and 
integration with existing monitoring systems.
```

### Task 5.8: Go-Live and Post-Deployment Monitoring

**Prompt:**
```
Execute the production deployment of the async admin-assistant application and 
implement post-deployment monitoring. Monitor system performance, error rates, 
and user experience during the initial rollout. Ensure proper incident response 
procedures and performance optimization based on production metrics.
```

## Usage Instructions

1. **Copy the relevant prompt** for the task you're working on
2. **Provide additional context** about your specific environment or requirements
3. **Review the generated code** carefully before implementation
4. **Test thoroughly** before moving to the next task
5. **Update this document** with any lessons learned or prompt improvements

## Prompt Customization Tips

- Add specific file paths and class names for more targeted results
- Include error messages or specific issues you're encountering
- Mention any constraints or requirements specific to your environment
- Reference existing patterns or conventions in your codebase
- Ask for specific testing scenarios or edge cases to consider
