from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from core.db import Base

class Prompt(Base):
    """
    Stores system, user, and action-specific prompts for AI functionality.
    """
    __tablename__ = 'prompts'
    id = Column(Integer, primary_key=True)
    prompt_type = Column(String(32), nullable=False)  # system, user, action-specific
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    action_type = Column(String(64), nullable=True)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False) 