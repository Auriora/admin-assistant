from sqlalchemy import Column, Integer, String, Boolean, DateTime
from core.db import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String)
    role = Column(String)
    is_active = Column(Boolean, default=True)
    ms_access_token = Column(String, nullable=True)
    ms_refresh_token = Column(String, nullable=True)
    ms_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    profile_photo_url = Column(String, nullable=True) 