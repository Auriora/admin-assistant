# Observability Guidelines for Admin Assistant

## Purpose
Logging and tracing help with debugging, monitoring, and auditing application behavior. Follow these guidelines to ensure logs and traces are useful and consistent.

## Log Levels
- `DEBUG`: Detailed information, typically of interest only when diagnosing problems.
- `INFO`: Confirmation that things are working as expected.
- `WARNING`: An indication that something unexpected happened, or indicative of some problem in the near future.
- `ERROR`: Due to a more serious problem, the software has not been able to perform some function.
- `CRITICAL`: A serious error, indicating that the program itself may be unable to continue running.

## Best Practices
- Use `current_app.logger` in Flask routes/services.
- Use the appropriate log level for the message.
- Include context (user, endpoint, IDs) where possible.
- Do not log sensitive information (passwords, secrets, tokens).
- Log exceptions with `logger.exception()` to include stack trace.
- Avoid excessive logging in performance-critical code.

## Examples
```python
current_app.logger.debug('Starting data sync job')
current_app.logger.info(f'User {user.email} logged in')
current_app.logger.warning('API rate limit approaching')
current_app.logger.error('Failed to fetch data from external API')
try:
    ...
except Exception as e:
    current_app.logger.exception(f'Unexpected error: {str(e)}')
```

## Troubleshooting
- Check both console and `logs/app.log` for errors.
- Use `DEBUG` level in development for detailed output.
- Rotate logs are kept in `logs/` directory.

## Further Reading
- [Python logging documentation](https://docs.python.org/3/library/logging.html)
- [Flask logging](https://flask.palletsprojects.com/en/latest/logging/)

## OpenTelemetry Guidelines
- Use OpenTelemetry for distributed tracing of HTTP requests and key business logic.
- Prefer automatic instrumentation for Flask and supported libraries.
- For custom operations, use `tracer.start_as_current_span()` to create spans.
- Always name spans meaningfully (e.g., 'msgraph.refresh_token', 'user.login').
- Do not include sensitive data in span attributes or events.
- Configure exporters and sampling via environment variables or app config.
- Review traces in your observability backend (e.g., Jaeger, OTLP collector).

## Example
```python
from opentelemetry import trace
tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("service.operation"):
    ...
``` 