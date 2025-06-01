from typing import List, Optional

from core.db import SessionLocal
from core.models.chat_session import ChatSession


class ChatSessionRepository:
    """
    Repository for managing ChatSession entities.
    """

    def __init__(self, session=None):
        self.session = session or SessionLocal()

    def get_by_id(self, session_id: int) -> Optional[ChatSession]:
        return self.session.get(ChatSession, session_id)

    def add(self, session: ChatSession) -> None:
        self.session.add(session)
        self.session.commit()

    def list_by_user(self, user_id: int) -> List[ChatSession]:
        return self.session.query(ChatSession).filter_by(user_id=user_id).all()

    def delete(self, session_id: int) -> None:
        session = self.get_by_id(session_id)
        if session:
            self.session.delete(session)
            self.session.commit()
