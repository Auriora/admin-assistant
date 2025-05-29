from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.types import Enum
from sqlalchemy.sql import func
from core.db import Base

class EntityAssociation(Base):
    """
    Generic mapping table to associate any entity (calendar, appointment, chat session, action log, etc.)
    with any other entity, supporting extensibility and reducing schema complexity.
    """
    __tablename__ = 'entity_association'
    id = Column(Integer, primary_key=True)
    source_type = Column(String(64), nullable=False)
    source_id = Column(Integer, nullable=False)
    target_type = Column(String(64), nullable=False)
    target_id = Column(Integer, nullable=False)
    association_type = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False) 