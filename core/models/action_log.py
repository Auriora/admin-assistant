from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from datetime import datetime
from core.db import Base

class ActionLog(Base):
    __tablename__ = 'action_log'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    event_id = Column(String, nullable=True)
    event_subject = Column(String, nullable=True)
    action_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    message = Column(String, nullable=True)
    timestamp = Column(DateTime, default=func.now(), nullable=False) 