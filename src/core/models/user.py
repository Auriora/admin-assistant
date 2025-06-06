from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from core.db import Base
from core.models.appointment import UTCDateTime


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    username = Column(String, unique=True, nullable=True)
    name = Column(String)
    role = Column(String)
    is_active = Column(Boolean, default=True)
    ms_access_token = Column(String, nullable=True)
    ms_refresh_token = Column(String, nullable=True)
    ms_token_expires_at = Column(UTCDateTime(), nullable=True)
    profile_photo_url = Column(String, nullable=True)
    ms_token_cache = Column(
        String,
        nullable=True,
        doc="Encrypted MS Graph token cache (Fernet base64-encoded string)",
    )
    # Relationship to ArchiveConfiguration
    archive_configurations = relationship("ArchiveConfiguration", back_populates="user")
    # Relationship to Calendar
    calendars = relationship("Calendar", back_populates="user")
    # Relationship to JobConfiguration
    job_configurations = relationship("JobConfiguration", back_populates="user")
    # Relationship to RestorationConfiguration
    restoration_configurations = relationship("RestorationConfiguration", back_populates="user")
