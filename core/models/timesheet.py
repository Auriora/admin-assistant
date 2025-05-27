from sqlalchemy import Column, Integer, String, Date, Boolean, DateTime, ForeignKey
from core.db import Base

class Timesheet(Base):
    __tablename__ = 'timesheets'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    pdf_path = Column(String)
    csv_path = Column(String)
    excel_path = Column(String)
    uploaded_to_onedrive = Column(Boolean, default=False)
    uploaded_to_xero = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True)) 