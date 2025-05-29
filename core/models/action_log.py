from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.types import JSON
from datetime import datetime
from core.db import Base
from core.models.appointment import UTCDateTime

class ActionLog(Base):
    """
    Central task/action log for user attention and audit.
    - state: open, resolved, archived, etc.
    - description: summary of the required action/task.
    - details: JSON for additional context.
    - recommendations: JSON for serialized AI recommendations.
    """
    __tablename__ = 'action_log'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    event_type = Column(String, nullable=False)
    state = Column(String, nullable=False, default='open')
    description = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)
    created_at = Column(UTCDateTime(), default=datetime.now, nullable=False)
    updated_at = Column(UTCDateTime(), default=datetime.now, onupdate=datetime.now, nullable=False) 