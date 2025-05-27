from sqlalchemy import Column, Integer, String, ForeignKey
from core.db import Base

class Location(Base):
    __tablename__ = 'locations'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    address = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False) 