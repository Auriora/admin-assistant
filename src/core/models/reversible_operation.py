from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship

from core.db import Base
from core.models.appointment import UTCDateTime


class ReversibleOperation(Base):
    """
    Model for tracking operations that can be reversed/undone.
    
    This extends the audit logging system to capture enough information
    to completely reverse any operation, enabling safe rollbacks.
    """

    __tablename__ = "reversible_operations"

    id = Column(Integer, primary_key=True)
    audit_log_id = Column(Integer, ForeignKey("audit_log.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Operation identification
    operation_type = Column(String(64), nullable=False)  # 'archive', 'delete', 'update', 'create'
    operation_name = Column(String(128), nullable=False)  # 'calendar_archive_replace', 'appointment_delete'
    
    # Reversibility status
    is_reversible = Column(Boolean, default=True, nullable=False)
    is_reversed = Column(Boolean, default=False, nullable=False)
    reverse_reason = Column(Text, nullable=True)  # Why it was reversed
    
    # State capture for reversal
    before_state = Column(JSON, nullable=True)  # Complete state before operation
    after_state = Column(JSON, nullable=True)   # Complete state after operation
    reverse_instructions = Column(JSON, nullable=False)  # How to reverse this operation
    
    # Dependencies and relationships
    depends_on_operations = Column(JSON, nullable=True)  # List of operation IDs this depends on
    blocks_operations = Column(JSON, nullable=True)     # List of operation IDs that depend on this
    
    # Metadata
    correlation_id = Column(String(128), nullable=True)  # Link related operations
    created_at = Column(UTCDateTime, default=datetime.utcnow, nullable=False)
    reversed_at = Column(UTCDateTime, nullable=True)
    reversed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    audit_log = relationship("AuditLog", backref="reversible_operation")
    user = relationship("User", foreign_keys=[user_id])
    reversed_by_user = relationship("User", foreign_keys=[reversed_by_user_id])

    def __repr__(self):
        return f"<ReversibleOperation(id={self.id}, operation_type='{self.operation_type}', is_reversed={self.is_reversed})>"


class ReversibleOperationItem(Base):
    """
    Individual items/entities affected by a reversible operation.
    
    For operations that affect multiple items (like bulk archive),
    this tracks each individual item for granular reversal.
    """

    __tablename__ = "reversible_operation_items"

    id = Column(Integer, primary_key=True)
    operation_id = Column(Integer, ForeignKey("reversible_operations.id"), nullable=False)
    
    # Item identification
    item_type = Column(String(64), nullable=False)  # 'appointment', 'calendar', 'user'
    item_id = Column(String(128), nullable=False)   # ID of the affected item
    external_id = Column(String(128), nullable=True)  # External system ID (e.g., MS Graph ID)
    
    # Item-specific state
    before_state = Column(JSON, nullable=True)  # Item state before operation
    after_state = Column(JSON, nullable=True)   # Item state after operation
    reverse_action = Column(String(64), nullable=False)  # 'restore', 'delete', 'update'
    reverse_data = Column(JSON, nullable=True)  # Data needed to reverse this item
    
    # Status
    is_reversed = Column(Boolean, default=False, nullable=False)
    reverse_error = Column(Text, nullable=True)  # Error if reversal failed
    
    # Timestamps
    created_at = Column(UTCDateTime, default=datetime.utcnow, nullable=False)
    reversed_at = Column(UTCDateTime, nullable=True)
    
    # Relationships
    operation = relationship("ReversibleOperation", backref="items")

    def __repr__(self):
        return f"<ReversibleOperationItem(id={self.id}, item_type='{self.item_type}', item_id='{self.item_id}', is_reversed={self.is_reversed})>"
