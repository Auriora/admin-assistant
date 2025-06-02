"""
Custom exception classes for the Admin Assistant project.
Follows the exception handling guidelines in docs/guidelines/exception_handling.md.
"""


class AdminAssistantException(Exception):
    """
    Base exception for the Admin Assistant project.
    All custom exceptions should inherit from this class.
    """

    pass


class AppointmentRepositoryException(AdminAssistantException):
    """
    Exception raised for errors in appointment repository operations.
    """

    pass


class CalendarServiceException(AdminAssistantException):
    """
    Exception raised for errors in calendar service operations.
    """

    pass


class OrchestrationException(AdminAssistantException):
    """
    Exception raised for errors in orchestration layer operations.
    """

    pass


class DuplicateAppointmentException(AppointmentRepositoryException):
    """
    Exception raised when attempting to add a duplicate appointment (same user, start_time, end_time, subject).
    """

    pass


class ImmutableAppointmentException(AppointmentRepositoryException):
    """
    Exception raised when attempting to modify an archived appointment that is immutable.
    Archived appointments are immutable except for the user who owns them.
    """

    pass
