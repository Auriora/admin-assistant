"""
SQLAlchemy models for Admin Assistant.
"""

import os
import secrets
from datetime import UTC, date, datetime

from flask_login import UserMixin
from sqlalchemy.orm import relationship
from sqlalchemy_utils import EncryptedType, StringEncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine

from web.app import db


def get_encryption_key():
    """
    Get encryption key from environment with security validation.
    Generates a secure key for development if not provided.
    """
    key = os.environ.get("ENCRYPTION_KEY")

    if not key:
        # In development, generate a secure random key
        if os.environ.get("APP_ENV") == "development":
            key = secrets.token_urlsafe(32)[:32]  # 32 bytes for AES-256
            print(
                "WARNING: Using generated encryption key for development. Set ENCRYPTION_KEY environment variable for production."
            )
        else:
            raise ValueError(
                "ENCRYPTION_KEY environment variable is required for production"
            )

    # Validate key length (minimum 32 characters for AES-256)
    if len(key) < 32:
        raise ValueError("ENCRYPTION_KEY must be at least 32 characters long")

    return key


# Secure encryption key with validation
ENCRYPTION_KEY = get_encryption_key()


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=False)
    name = db.Column(db.String)
    role = db.Column(db.String)
    is_active = db.Column(db.Boolean, default=True)
    ms_access_token = db.Column(
        StringEncryptedType(db.String, ENCRYPTION_KEY, AesEngine, "pkcs5"),
        nullable=True,
    )
    ms_refresh_token = db.Column(
        StringEncryptedType(db.String, ENCRYPTION_KEY, AesEngine, "pkcs5"),
        nullable=True,
    )
    ms_token_expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
    profile_photo_url = db.Column(db.String, nullable=True)

    appointments = db.relationship("Appointment", back_populates="user")
    locations = db.relationship("Location", back_populates="user")
    categories = db.relationship("Category", back_populates="user")
    timesheets = db.relationship("Timesheet", back_populates="user")
    audit_logs = db.relationship("AuditLog", back_populates="user")
    rules = db.relationship("Rule", back_populates="user")
    archive_preference = db.relationship(
        "ArchivePreference", back_populates="user", uselist=False
    )
