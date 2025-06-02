from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String

from core.db import Base
from core.models.appointment import UTCDateTime


class Timesheet(Base):
    __tablename__ = "timesheets"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    pdf_path = Column(String)
    csv_path = Column(String)
    excel_path = Column(String)
    uploaded_to_onedrive = Column(Boolean, default=False)
    uploaded_to_xero = Column(Boolean, default=False)
    created_at = Column(UTCDateTime())
