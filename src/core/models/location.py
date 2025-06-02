from sqlalchemy import Column, ForeignKey, Integer, String

from core.db import Base


class Location(Base):
    __tablename__ = "locations"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    address = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
