from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.models.chat_session import ChatSession
    from core.repositories.chat_session_repository import ChatSessionRepository
    from core.services.entity_association_service import EntityAssociationService


class ChatSessionService:
    """
    Service for business logic related to ChatSession entities.
    """

    def __init__(
        self,
        repository: ChatSessionRepository | None = None,
        association_service: EntityAssociationService | None = None,
    ):
        self._repository = repository
        self._association_service = association_service

    @property
    def repository(self) -> ChatSessionRepository:
        if self._repository is None:
            from core.repositories.chat_session_repository import ChatSessionRepository as _Repo

            self._repository = _Repo()
        return self._repository

    @property
    def association_service(self) -> EntityAssociationService:
        if self._association_service is None:
            from core.services.entity_association_service import EntityAssociationService as _Svc

            self._association_service = _Svc()
        return self._association_service

    def get_by_id(self, session_id: int) -> ChatSession | None:
        return self.repository.get_by_id(session_id)

    def create(self, session: ChatSession) -> None:
        self.repository.add(session)

    def list_by_user(self, user_id: int) -> list[ChatSession]:
        return self.repository.list_by_user(user_id)

    def delete(self, session_id: int) -> None:
        self.repository.delete(session_id)

    def append_message(self, session_id: int, message: dict) -> None:
        """
        Append a message to the chat session.
        """
        session = self.get_by_id(session_id)
        if not session:
            raise ValueError("ChatSession not found")
        messages = getattr(session, "messages", None) or []
        messages.append(message)
        setattr(session, "messages", messages)  # type: ignore
        self.repository.add(session)

    def get_chat_history(self, session_id: int) -> list[dict]:
        """
        Retrieve the full chat history for a session.
        """
        session = self.get_by_id(session_id)
        if not session:
            raise ValueError("ChatSession not found")
        return getattr(session, "messages", []) or []

    def close_session(self, session_id: int) -> None:
        """
        Mark a chat session as closed.
        """
        session = self.get_by_id(session_id)
        if not session:
            raise ValueError("ChatSession not found")
        setattr(session, "status", "closed")  # type: ignore
        self.repository.add(session)

    def reopen_session(self, session_id: int) -> None:
        """
        Reopen a closed chat session.
        """
        session = self.get_by_id(session_id)
        if not session:
            raise ValueError("ChatSession not found")
        setattr(session, "status", "open")  # type: ignore
        self.repository.add(session)

    def list_by_action(self, action_id: int) -> list[ChatSession]:
        """
        Fetch all chat sessions related to a specific action/task (using EntityAssociation).
        """
        related = self.association_service.list_by_target("action_log", action_id)
        sessions: list[ChatSession] = []
        for association in related:
            if getattr(association, "source_type") != "chat_session":
                continue
            session_id = getattr(association, "source_id", None)
            if session_id is None:
                continue
            session = self.get_by_id(int(session_id))
            if session:
                sessions.append(session)
        return sessions
