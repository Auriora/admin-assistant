"""
SQLAlchemy models for Admin Assistant.
"""
from app import db
from sqlalchemy.orm import relationship
from datetime import datetime, date

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=False)
    name = db.Column(db.String)
    role = db.Column(db.String)
    is_active = db.Column(db.Boolean, default=True)

    appointments = db.relationship('Appointment', back_populates='user')
    locations = db.relationship('Location', back_populates='user')
    categories = db.relationship('Category', back_populates='user')
    timesheets = db.relationship('Timesheet', back_populates='user')
    audit_logs = db.relationship('AuditLog', back_populates='user')
    rules = db.relationship('Rule', back_populates='user')
    notifications = db.relationship('Notification', back_populates='user')

class Location(db.Model):
    __tablename__ = 'locations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    address = db.Column(db.String)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    user = db.relationship('User', back_populates='locations')
    appointments = db.relationship('Appointment', back_populates='location')

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    user = db.relationship('User', back_populates='categories')
    appointments = db.relationship('Appointment', back_populates='category')

class Appointment(db.Model):
    __tablename__ = 'appointments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    subject = db.Column(db.String)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    is_private = db.Column(db.Boolean, default=False)
    is_archived = db.Column(db.Boolean, default=False)
    is_out_of_office = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', back_populates='appointments')
    location = db.relationship('Location', back_populates='appointments')
    category = db.relationship('Category', back_populates='appointments')
    timesheet_id = db.Column(db.Integer, db.ForeignKey('timesheets.id'))
    timesheet = db.relationship('Timesheet', back_populates='appointments')

class Timesheet(db.Model):
    __tablename__ = 'timesheets'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    pdf_path = db.Column(db.String)
    csv_path = db.Column(db.String)
    excel_path = db.Column(db.String)
    uploaded_to_onedrive = db.Column(db.Boolean, default=False)
    uploaded_to_xero = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='timesheets')
    appointments = db.relationship('Appointment', back_populates='timesheet')

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String, nullable=False)
    entity_type = db.Column(db.String)
    entity_id = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    details = db.Column(db.Text)

    user = db.relationship('User', back_populates='audit_logs')

class Rule(db.Model):
    __tablename__ = 'rules'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String)
    rule_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='rules')

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.String, nullable=False)
    type = db.Column(db.String)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='notifications') 