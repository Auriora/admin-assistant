from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Text
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String)
    role = Column(String)
    is_active = Column(Boolean, default=True)

    appointments = relationship('Appointment', back_populates='user')
    locations = relationship('Location', back_populates='user')
    categories = relationship('Category', back_populates='user')
    timesheets = relationship('Timesheet', back_populates='user')
    audit_logs = relationship('AuditLog', back_populates='user')
    rules = relationship('Rule', back_populates='user')
    notifications = relationship('Notification', back_populates='user')

class Location(Base):
    __tablename__ = 'locations'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    address = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    user = relationship('User', back_populates='locations')
    appointments = relationship('Appointment', back_populates='location')

class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    user = relationship('User', back_populates='categories')
    appointments = relationship('Appointment', back_populates='category')

class Appointment(Base):
    __tablename__ = 'appointments'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    subject = Column(String)
    location_id = Column(Integer, ForeignKey('locations.id'))
    category_id = Column(Integer, ForeignKey('categories.id'))
    is_private = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    is_out_of_office = Column(Boolean, default=False)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    user = relationship('User', back_populates='appointments')
    location = relationship('Location', back_populates='appointments')
    category = relationship('Category', back_populates='appointments')
    timesheet_id = Column(Integer, ForeignKey('timesheets.id'))
    timesheet = relationship('Timesheet', back_populates='appointments')

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
    created_at = Column(DateTime)

    user = relationship('User', back_populates='timesheets')
    appointments = relationship('Appointment', back_populates='timesheet')

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    action = Column(String, nullable=False)
    entity_type = Column(String)
    entity_id = Column(Integer)
    timestamp = Column(DateTime)
    details = Column(Text)

    user = relationship('User', back_populates='audit_logs')

class Rule(Base):
    __tablename__ = 'rules'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    rule_json = Column(Text)
    created_at = Column(DateTime)

    user = relationship('User', back_populates='rules')

class Notification(Base):
    __tablename__ = 'notifications'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    message = Column(String, nullable=False)
    type = Column(String)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime)

    user = relationship('User', back_populates='notifications') 