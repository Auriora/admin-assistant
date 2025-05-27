"""
SQLAlchemy models for Admin Assistant.
"""
from app import db
from sqlalchemy.orm import relationship
from datetime import datetime, date, UTC
from sqlalchemy_utils import EncryptedType, StringEncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine
import os
from flask_login import UserMixin

# Key for encryption (should be stored securely in production)
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', 'devkeydevkeydevkeydevkey')

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=False)
    name = db.Column(db.String)
    role = db.Column(db.String)
    is_active = db.Column(db.Boolean, default=True)
    ms_access_token = db.Column(StringEncryptedType(db.String, ENCRYPTION_KEY, AesEngine, 'pkcs5'), nullable=True)
    ms_refresh_token = db.Column(StringEncryptedType(db.String, ENCRYPTION_KEY, AesEngine, 'pkcs5'), nullable=True)
    ms_token_expires_at = db.Column(db.DateTime, nullable=True)
    profile_photo_url = db.Column(db.String, nullable=True)

    appointments = db.relationship('Appointment', back_populates='user')
    locations = db.relationship('Location', back_populates='user')
    categories = db.relationship('Category', back_populates='user')
    timesheets = db.relationship('Timesheet', back_populates='user')
    audit_logs = db.relationship('AuditLog', back_populates='user')
    rules = db.relationship('Rule', back_populates='user')
    notifications = db.relationship('Notification', back_populates='user')
    notification_preferences = db.relationship('NotificationPreference', back_populates='user')
    archive_preference = db.relationship('ArchivePreference', back_populates='user', uselist=False)

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
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

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
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    user = db.relationship('User', back_populates='timesheets')
    appointments = db.relationship('Appointment', back_populates='timesheet')

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String, nullable=False)
    entity_type = db.Column(db.String)
    entity_id = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    details = db.Column(db.Text)

    user = db.relationship('User', back_populates='audit_logs')

class Rule(db.Model):
    __tablename__ = 'rules'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String)
    rule_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    user = db.relationship('User', back_populates='rules')

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.String, nullable=False)
    type = db.Column(db.String)
    channel = db.Column(db.String, default='toast')  # 'toast', 'email', or 'both'
    transaction_id = db.Column(db.String, nullable=True)  # Unique event/transaction identifier
    pct_complete = db.Column(db.Integer, nullable=True, default=None)  # Percentage complete
    progress = db.Column(db.String, nullable=True, default=None)  # Progress description
    state = db.Column(db.String, nullable=True, default=None)  # e.g. not started, in-progress, success, failed
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    user = db.relationship('User', back_populates='notifications')

    def __init__(self, **kwargs):
        for field in ['user_id', 'message', 'type', 'channel', 'transaction_id', 'pct_complete', 'progress', 'state', 'is_read', 'created_at']:
            if field in kwargs:
                setattr(self, field, kwargs[field])
        if not hasattr(self, 'created_at') or self.created_at is None:
            self.created_at = datetime.now(UTC)

class NotificationClass(db.Model):
    __tablename__ = 'notification_classes'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String, unique=True, nullable=False)
    label = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=True)
    preferences = db.relationship('NotificationPreference', back_populates='notification_class_obj')

    def __init__(self, **kwargs):
        for field in ['key', 'label', 'description']:
            if field in kwargs:
                setattr(self, field, kwargs[field])

class NotificationPreference(db.Model):
    __tablename__ = 'notification_preferences'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    notification_class = db.Column(db.String, db.ForeignKey('notification_classes.key'), nullable=False)
    channel = db.Column(db.String, nullable=False)  # 'toast', 'email', 'both', 'none'

    user = db.relationship('User', back_populates='notification_preferences')
    notification_class_obj = db.relationship('NotificationClass', back_populates='preferences')

    def __init__(self, **kwargs):
        for field in ['user_id', 'notification_class', 'channel']:
            if field in kwargs:
                setattr(self, field, kwargs[field])

class ArchivePreference(db.Model):
    __tablename__ = 'archive_preferences'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    ms_calendar_id = db.Column(db.String, nullable=True)  # Microsoft calendar ID for archiving
    # Add more fields for future preferences here
    user = db.relationship('User', back_populates='archive_preference') 