from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from core.db import Base
from core.models.appointment import UTCDateTime


class ChatSession(Base):
    """
    Persistent chat history and AI suggestions, mapped to actions/tasks or other entities via entity_association.
    """

    __tablename__ = "chat_sessions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    messages = Column(
        JSON, nullable=True
    )  # List of messages with sender, timestamp, content, etc.
    status = Column(String(32), nullable=False, default="open")  # open, closed
    created_at = Column(UTCDateTime(), default=func.now(), nullable=False)
    updated_at = Column(
        UTCDateTime(), default=func.now(), onupdate=func.now(), nullable=False
    )
