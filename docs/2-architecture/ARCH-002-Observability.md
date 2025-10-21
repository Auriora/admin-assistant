---
title: "Architecture: Observability Design"
id: "ARCH-002"
type: [ architecture, design ]
status: [ accepted ]
owner: "Auriora Team"
last_reviewed: "DD-MM-YYYY"
tags: [architecture, observability, logging, tracing]
links:
  tooling: []
---

# Observability Design

- **Owner**: Auriora Team
- **Status**: Accepted
- **Created Date**: DD-MM-YYYY
- **Last Updated**: DD-MM-YYYY
- **Audience**: [Developers, SRE]

## 1. Purpose

This document describes the observability design for the Admin Assistant application, covering logging, tracing, and metrics. It details the configuration, usage, and extension points for the current implementation.

## 2. Context

Logging is implemented using Python's built-in `logging` module and is configured in the Flask app factory (`app/__init__.py`). The application is also instrumented with OpenTelemetry for distributed tracing. This provides a comprehensive view of the application's behavior for debugging and performance monitoring.

## 3. Details

### 3.1. Logging Configuration

- **Log Level**:
  - Development: DEBUG
  - Testing: INFO
  - Production: WARNING
  - Can be overridden by the `LOG_LEVEL` environment variable.
- **Handlers**:
  - Console (stdout)
  - Rotating file handler at `logs/app.log` (max 10KB per file, 5 backups)
- **Format**:
  - Console: `[timestamp] LEVEL in module: message`
  - File: `[timestamp] LEVEL in module: message [pathname:lineno]`
- **Request Logging**: Each request logs the method, path, and remote IP.
- **Log File Location**: All logs are stored in the `logs/` directory at the project root.

### 3.2. Logging Usage

- **In Code**: Use `from flask import current_app` and `current_app.logger` for logging in routes and services.
  ```python
  current_app.logger.info('User logged in successfully')
  current_app.logger.error('Failed to fetch data from API')
  ```
- **Extending**: For non-Flask modules, use the standard `logging.getLogger(__name__)` pattern.

### 3.3. OpenTelemetry Integration

- **Tracing**: The application is instrumented with OpenTelemetry for distributed tracing. Flask routes and key functions are automatically traced and exported via the OTLP exporter (configurable via environment variables).
- **Metrics**: OpenTelemetry metrics can be enabled for future needs.
- **Custom Spans**: Custom spans can be added for critical business logic:
  ```python
  from opentelemetry import trace
  tracer = trace.get_tracer(__name__)
  with tracer.start_as_current_span("my_custom_operation"):
      # business logic here
  ```

### 3.4. Maintenance

- Log files are rotated automatically. The rotation policy (`maxBytes`/`backupCount`) is configured in `app/__init__.py`.

# References

- Link to related diagrams, tickets, or external resources.
