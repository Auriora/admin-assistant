"""
SQLAlchemy models for Admin Assistant.
"""
from web.app import db
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
    ms_token_expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
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
