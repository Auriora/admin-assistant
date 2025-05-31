from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.types import JSON
from datetime import datetime
from core.db import Base
from core.models.appointment import UTCDateTime


class AuditLog(Base):
    """
    Dedicated audit log for compliance and traceability.
    Records all critical system actions including archiving, overlap resolutions, 
    re-archiving operations, API calls, and system events.
    
    Separate from ActionLog which is used for task management.
    """
    __tablename__ = 'audit_log'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Core audit fields
    action_type = Column(String(64), nullable=False)  # e.g., 'archive', 'overlap_resolution', 're_archive', 'api_call'
    operation = Column(String(128), nullable=False)   # e.g., 'calendar_archive', 'resolve_overlap', 'msgraph_api_call'
    resource_type = Column(String(64), nullable=True) # e.g., 'appointment', 'calendar', 'user'
    resource_id = Column(String(128), nullable=True)  # ID of the affected resource
    
    # Status and outcome
    status = Column(String(32), nullable=False)       # 'success', 'failure', 'partial'
    message = Column(Text, nullable=True)             # Human-readable description
    
    # Detailed context and metadata
    details = Column(JSON, nullable=True)             # Operation-specific details
    request_data = Column(JSON, nullable=True)        # Input parameters/data
    response_data = Column(JSON, nullable=True)       # Output/results
    
    # Performance and technical details
    duration_ms = Column(Float, nullable=True)        # Operation duration in milliseconds
    ip_address = Column(String(45), nullable=True)    # IPv4/IPv6 address
    user_agent = Column(String(512), nullable=True)   # Browser/client info
    
    # Traceability
    correlation_id = Column(String(128), nullable=True) # For tracking related operations
    parent_audit_id = Column(Integer, ForeignKey('audit_log.id'), nullable=True) # For nested operations
    
    # Timestamps
    created_at = Column(UTCDateTime(), default=datetime.now, nullable=False)
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action_type='{self.action_type}', operation='{self.operation}', status='{self.status}')>"
