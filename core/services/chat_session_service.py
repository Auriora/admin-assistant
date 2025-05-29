from typing import List, Optional
from core.models.chat_session import ChatSession
from core.repositories.chat_session_repository import ChatSessionRepository
from core.services.entity_association_service import EntityAssociationService

class ChatSessionService:
    """
    Service for business logic related to ChatSession entities.
    """
    def __init__(self, repository: Optional[ChatSessionRepository] = None, association_service: Optional[EntityAssociationService] = None):
        self.repository = repository or ChatSessionRepository()
        self.association_service = association_service or EntityAssociationService()

    def get_by_id(self, session_id: int) -> Optional[ChatSession]:
        return self.repository.get_by_id(session_id)

    def create(self, session: ChatSession) -> None:
        self.repository.add(session)

    def list_by_user(self, user_id: int) -> List[ChatSession]:
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
        messages = getattr(session, 'messages', None) or []
        messages.append(message)
        setattr(session, 'messages', messages)  # type: ignore
        self.repository.add(session)

    def get_chat_history(self, session_id: int) -> list:
        """
        Retrieve the full chat history for a session.
        """
        session = self.get_by_id(session_id)
        if not session:
            raise ValueError("ChatSession not found")
        return getattr(session, 'messages', []) or []

    def close_session(self, session_id: int) -> None:
        """
        Mark a chat session as closed.
        """
        session = self.get_by_id(session_id)
        if not session:
            raise ValueError("ChatSession not found")
        setattr(session, 'status', 'closed')  # type: ignore
        self.repository.add(session)

    def reopen_session(self, session_id: int) -> None:
        """
        Reopen a closed chat session.
        """
        session = self.get_by_id(session_id)
        if not session:
            raise ValueError("ChatSession not found")
        setattr(session, 'status', 'open')  # type: ignore
        self.repository.add(session)

    def list_by_action(self, action_id: int) -> list:
        """
        Fetch all chat sessions related to a specific action/task (using EntityAssociation).
        """
        related = self.association_service.list_by_target('action_log', action_id)
        chat_session_ids = [getattr(a, 'source_id') for a in related if getattr(a, 'source_type') == 'chat_session']
        return [self.get_by_id(int(cid)) for cid in chat_session_ids if self.get_by_id(int(cid))] 