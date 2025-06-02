from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, asc, desc, or_
from sqlalchemy.orm import Session

from core.db import SessionLocal
from core.models.audit_log import AuditLog


class AuditLogRepository:
    """
    Repository for managing AuditLog entities with comprehensive querying capabilities.
    """

    def __init__(self, session: Optional[Session] = None):
        self.session = session or SessionLocal()

    def add(self, audit_log: AuditLog) -> AuditLog:
        """Add a new AuditLog entry and return it with ID populated."""
        self.session.add(audit_log)
        self.session.commit()
        self.session.refresh(audit_log)
        return audit_log

    def get_by_id(self, audit_id: int) -> Optional[AuditLog]:
        """Retrieve an AuditLog by its ID."""
        return self.session.get(AuditLog, audit_id)

    def list_for_user(
        self, user_id: int, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[AuditLog]:
        """List all AuditLog entries for a given user with optional pagination."""
        query = (
            self.session.query(AuditLog)
            .filter_by(user_id=user_id)
            .order_by(desc(AuditLog.created_at))
        )

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        return query.all()

    def list_by_action_type(
        self,
        action_type: str,
        user_id: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[AuditLog]:
        """List AuditLog entries by action type, optionally filtered by user."""
        query = self.session.query(AuditLog).filter_by(action_type=action_type)

        if user_id:
            query = query.filter_by(user_id=user_id)

        query = query.order_by(desc(AuditLog.created_at))

        if limit:
            query = query.limit(limit)

        return query.all()

    def list_by_operation(
        self, operation: str, user_id: Optional[int] = None, limit: Optional[int] = None
    ) -> List[AuditLog]:
        """List AuditLog entries by operation, optionally filtered by user."""
        query = self.session.query(AuditLog).filter_by(operation=operation)

        if user_id:
            query = query.filter_by(user_id=user_id)

        query = query.order_by(desc(AuditLog.created_at))

        if limit:
            query = query.limit(limit)

        return query.all()

    def list_by_status(
        self, status: str, user_id: Optional[int] = None, limit: Optional[int] = None
    ) -> List[AuditLog]:
        """List AuditLog entries by status, optionally filtered by user."""
        query = self.session.query(AuditLog).filter_by(status=status)

        if user_id:
            query = query.filter_by(user_id=user_id)

        query = query.order_by(desc(AuditLog.created_at))

        if limit:
            query = query.limit(limit)

        return query.all()

    def list_by_correlation_id(self, correlation_id: str) -> List[AuditLog]:
        """List all AuditLog entries with the same correlation ID for tracing related operations."""
        return (
            self.session.query(AuditLog)
            .filter_by(correlation_id=correlation_id)
            .order_by(asc(AuditLog.created_at))
            .all()
        )

    def list_by_date_range(
        self,
        start_date: date,
        end_date: date,
        user_id: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[AuditLog]:
        """List AuditLog entries within a date range."""
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        query = self.session.query(AuditLog).filter(
            and_(
                AuditLog.created_at >= start_datetime,
                AuditLog.created_at <= end_datetime,
            )
        )

        if user_id:
            query = query.filter_by(user_id=user_id)

        query = query.order_by(desc(AuditLog.created_at))

        if limit:
            query = query.limit(limit)

        return query.all()

    def search(
        self,
        filters: Dict[str, Any],
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[AuditLog]:
        """
        Advanced search with multiple filters.

        Args:
            filters: Dict with possible keys:
                - user_id: int
                - action_type: str
                - operation: str
                - status: str
                - resource_type: str
                - resource_id: str
                - correlation_id: str
                - start_date: date
                - end_date: date
                - message_contains: str (for text search in message)
        """
        query = self.session.query(AuditLog)

        # Apply filters
        if "user_id" in filters:
            query = query.filter_by(user_id=filters["user_id"])

        if "action_type" in filters:
            query = query.filter_by(action_type=filters["action_type"])

        if "operation" in filters:
            query = query.filter_by(operation=filters["operation"])

        if "status" in filters:
            query = query.filter_by(status=filters["status"])

        if "resource_type" in filters:
            query = query.filter_by(resource_type=filters["resource_type"])

        if "resource_id" in filters:
            query = query.filter_by(resource_id=filters["resource_id"])

        if "correlation_id" in filters:
            query = query.filter_by(correlation_id=filters["correlation_id"])

        if "start_date" in filters and "end_date" in filters:
            start_datetime = datetime.combine(
                filters["start_date"], datetime.min.time()
            )
            end_datetime = datetime.combine(filters["end_date"], datetime.max.time())
            query = query.filter(
                and_(
                    AuditLog.created_at >= start_datetime,
                    AuditLog.created_at <= end_datetime,
                )
            )

        if "message_contains" in filters:
            query = query.filter(AuditLog.message.contains(filters["message_contains"]))

        # Order by creation date (newest first)
        query = query.order_by(desc(AuditLog.created_at))

        # Apply pagination
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        return query.all()

    def count_by_filters(self, filters: Dict[str, Any]) -> int:
        """Count audit log entries matching the given filters."""
        query = self.session.query(AuditLog)

        # Apply same filters as search method
        if "user_id" in filters:
            query = query.filter_by(user_id=filters["user_id"])

        if "action_type" in filters:
            query = query.filter_by(action_type=filters["action_type"])

        if "operation" in filters:
            query = query.filter_by(operation=filters["operation"])

        if "status" in filters:
            query = query.filter_by(status=filters["status"])

        if "resource_type" in filters:
            query = query.filter_by(resource_type=filters["resource_type"])

        if "resource_id" in filters:
            query = query.filter_by(resource_id=filters["resource_id"])

        if "correlation_id" in filters:
            query = query.filter_by(correlation_id=filters["correlation_id"])

        if "start_date" in filters and "end_date" in filters:
            start_datetime = datetime.combine(
                filters["start_date"], datetime.min.time()
            )
            end_datetime = datetime.combine(filters["end_date"], datetime.max.time())
            query = query.filter(
                and_(
                    AuditLog.created_at >= start_datetime,
                    AuditLog.created_at <= end_datetime,
                )
            )

        if "message_contains" in filters:
            query = query.filter(AuditLog.message.contains(filters["message_contains"]))

        return query.count()

    def delete_old_entries(
        self, older_than_date: date, user_id: Optional[int] = None
    ) -> int:
        """
        Delete audit log entries older than the specified date.
        Returns the number of deleted entries.
        """
        cutoff_datetime = datetime.combine(older_than_date, datetime.max.time())

        query = self.session.query(AuditLog).filter(
            AuditLog.created_at < cutoff_datetime
        )

        if user_id:
            query = query.filter_by(user_id=user_id)

        count = query.count()
        query.delete()
        self.session.commit()

        return count
