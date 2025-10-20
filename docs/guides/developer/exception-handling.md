# Exception Handling Guidelines for Admin Assistant

## Purpose
Robust exception handling ensures reliability, maintainability, and debuggability of the application. Proper error handling prevents silent failures, provides meaningful feedback, and supports observability and compliance.

## Best Practices
- **Be specific:** Catch only exceptions you can handle meaningfully. Avoid bare `except:` clauses.
- **Do not suppress errors:** Never mask or silently swallow exceptions. Always log and propagate or transform them appropriately.
- **Use custom exceptions:** Define and use domain-specific exceptions for clarity and maintainability.
- **Preserve context:** Use exception chaining (`raise ... from e`) to retain the original traceback and context.
- **Add context:** Use `Exception.add_note()` (Python 3.11+) to enrich exceptions as they propagate.
- **Log exceptions:** Always log exceptions with stack traces using `logger.exception()`.
- **Handle at the right layer:** Handle exceptions at the layer where you have enough context to act or transform them meaningfully.
- **Test error cases:** Write tests for error scenarios to ensure correct handling and reporting.
- **Use ExceptionGroup:** For concurrent code (Python 3.11+), use `ExceptionGroup` to handle multiple errors together.

## Layer-Specific Guidance
- **Repository Layer:**
  - Catch and wrap only data-access-specific exceptions (e.g., database, API errors).
  - Raise custom repository exceptions with context, using `from e` to chain.
  - Never return `None` or empty lists on error—raise or propagate exceptions.
- **Service Layer:**
  - Catch repository and domain exceptions, add business context, and re-raise or transform as needed.
  - Use custom service exceptions for business logic errors.
- **Orchestration Layer:**
  - Aggregate and report errors from services and repositories.
  - Log all exceptions and return structured error information for the UI or API.

## Custom Exceptions
- Define a base exception (e.g., `AdminAssistantException`) for the project.
- Subclass for domain, service, and repository errors (e.g., `AppointmentRepositoryException`, `CalendarServiceException`).
- Include meaningful messages and relevant context in exception attributes.

## Logging
- Use `logger.exception()` to log exceptions with stack traces.
- Include user, operation, and relevant IDs in log messages.
- Never log sensitive data (see [Observability Guidelines](observability.md)).

## Examples
```python
class AdminAssistantException(Exception):
    """Base exception for the Admin Assistant project."""
    pass

class AppointmentRepositoryException(AdminAssistantException):
    pass

# Repository layer
try:
    ... # database or API call
except SomeAPIError as e:
    logger.exception(f"Failed to fetch appointments for user {user_id}")
    raise AppointmentRepositoryException("Failed to fetch appointments") from e

# Service layer
try:
    appointments = repo.list_for_user(user_id)
except AppointmentRepositoryException as e:
    logger.error(f"Service error: {e}")
    raise CalendarServiceException("Could not retrieve appointments") from e

# Adding context with add_note (Python 3.11+)
try:
    ...
except Exception as e:
    e.add_note(f"Error occurred while processing user {user_id}")
    raise

# Handling ExceptionGroup (Python 3.11+)
try:
    ... # concurrent tasks
except* ExceptionGroup as eg:
    for exc in eg.exceptions:
        logger.error(f"Concurrent error: {exc}")
```

## Common Pitfalls to Avoid
- Do not use `except Exception:` without re-raising or logging.
- Do not return default values on error—raise or propagate exceptions.
- Do not leak sensitive information in error messages or logs.

## Further Reading
- [Python Exception Handling Patterns](https://jerrynsh.com/python-exception-handling-patterns-and-best-practices/)
- [PEP 654 – Exception Groups and except*](https://peps.python.org/pep-0654/)
- [Python logging documentation](https://docs.python.org/3/library/logging.html)

## Summary for guidelines.mdc
- All exceptions must be handled explicitly and logged with context.
- Use custom exceptions and exception chaining (`from e`).
- Never mask, suppress, or silently swallow errors.
- Add context to exceptions as they propagate.
- Handle exceptions at the appropriate layer and always test error scenarios. 