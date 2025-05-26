# Logging Design for Admin Assistant

## Overview
Logging is implemented using Python's built-in `logging` module and is configured in the Flask app factory (`app/__init__.py`). Logs are written to both the console and a rotating file handler. The log level is determined by the environment (development, testing, production) or can be set via environment variables.

## Configuration
- **Log Level:**
  - Development: DEBUG (or as set in `.env.development`)
  - Testing: INFO (or as set in `.env.testing`)
  - Production: WARNING (or as set in `.env.production`)
  - Can be overridden by `LOG_LEVEL` environment variable.
- **Handlers:**
  - Console (stdout)
  - Rotating file handler at `logs/app.log` (max 10KB per file, 5 backups)
- **Format:**
  - Console: `[timestamp] LEVEL in module: message`
  - File: `[timestamp] LEVEL in module: message [pathname:lineno]`
- **Request Logging:**
  - Each request logs method, path, and remote IP before handling.

## Usage in Code
- Use `from flask import current_app` and `current_app.logger` for logging in routes and services.
- Example:
  ```python
  current_app.logger.info('User logged in successfully')
  current_app.logger.error('Failed to fetch data from API')
  ```

## Log File Location
- All logs are stored in the `logs/` directory at the project root.
- The main log file is `logs/app.log`.

## Extending Logging
- To add logging to new modules, import `current_app` and use its logger.
- For non-Flask modules, use the standard `logging.getLogger(__name__)` pattern and configure handlers as needed.

## Maintenance
- Log files are rotated automatically. Old logs are kept as backups (up to 5 files).
- Monitor log file size and adjust `maxBytes`/`backupCount` in `app/__init__.py` if needed.

## OpenTelemetry Integration
- **Tracing:**
  - The application is instrumented with OpenTelemetry for distributed tracing.
  - Flask routes and key service functions are automatically traced.
  - Traces are exported using the OTLP exporter (default: localhost:4317, configurable via environment variables).
- **Metrics:**
  - OpenTelemetry metrics can be enabled for future observability needs.
- **Configuration:**
  - OpenTelemetry is initialized in `app/__init__.py`.
  - Exporter and sampling configuration can be set via environment variables or in the app config.
- **Usage:**
  - Traces are automatically generated for HTTP requests and selected service logic.
  - Custom spans can be added using the OpenTelemetry API for critical business logic.

## Example: Custom Span
```python
from opentelemetry import trace
tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("my_custom_operation"):
    # business logic here
``` 