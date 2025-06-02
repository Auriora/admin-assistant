from typing import Any, Optional

from sqlalchemy.orm import Session

from core.models.user import User
from core.repositories.appointment_repository_base import BaseAppointmentRepository
from core.repositories.appointment_repository_msgraph import (
    MSGraphAppointmentRepository,
)
from core.repositories.appointment_repository_sqlalchemy import (
    SQLAlchemyAppointmentRepository,
)

# Import mock client only if needed to avoid test dependency in production


class AppointmentRepositoryFactory:
    """
    Factory for creating AppointmentRepository instances based on backend type.
    """

    @staticmethod
    def create(backend: str, **kwargs) -> BaseAppointmentRepository:
        calendar_id = kwargs.get("calendar_id")
        if not calendar_id:
            raise ValueError(
                "calendar_id must be provided for all appointment repositories."
            )
        if backend == "sqlalchemy":
            session: Session = kwargs["session"]
            user = kwargs["user"]
            return SQLAlchemyAppointmentRepository(user, calendar_id, session)
        elif backend == "msgraph":
            msgraph_client = kwargs["msgraph_client"]
            user = kwargs["user"]
            return MSGraphAppointmentRepository(msgraph_client, user, calendar_id)
        else:
            raise ValueError(f"Unknown backend: {backend}")


def get_appointment_repository(
    user: User,
    calendar_id: str,
    use_mock: bool = False,
    mock_data: Optional[Any] = None,
    session: Optional[Any] = None,
) -> Any:
    """
    Factory function to instantiate the appropriate AppointmentRepository.

    Args:
        user (User): The user for whom the repository is created.
        calendar_id (str): The calendar ID to use.
        use_mock (bool): Whether to use a mock MS Graph client (for testing).
        mock_data (Optional[Any]): Data to use for the mock client.
        session (Optional[Any]): SQLAlchemy session for SQL repository.

    Returns:
        Any: An instance of the appropriate AppointmentRepository.
    """
    if use_mock:
        try:
            from tests.mocks.msgraph_mocks import MockMSGraphClient
        except ImportError as e:
            raise ImportError(
                "MockMSGraphClient could not be imported. Ensure test dependencies are available."
            ) from e
        if mock_data is None:
            raise ValueError("mock_data must be provided when use_mock is True.")
        mock_client = MockMSGraphClient(mock_data)
        return MSGraphAppointmentRepository(mock_client, user, calendar_id)  # type: ignore
    elif session is not None:
        return SQLAlchemyAppointmentRepository(user, calendar_id, session)
    else:
        # For live MS Graph, expect a graph_client to be provided via mock_data
        if mock_data is None:
            raise ValueError(
                "graph_client must be provided as mock_data for live MS Graph repository."
            )
        return MSGraphAppointmentRepository(mock_data, user, calendar_id)
