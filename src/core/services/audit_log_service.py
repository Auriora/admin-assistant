import uuid
from datetime import date
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.models.audit_log import AuditLog
    from core.repositories.audit_log_repository import AuditLogRepository as _AuditRepo


class AuditLogService:
    """
    Service for managing audit logging with high-level business logic.
    Provides convenient methods for logging different types of operations.
    """

    def __init__(self, repository: Optional["_AuditRepo"] = None):
        self._repository = repository

    @property
    def repository(self) -> "_AuditRepo":
        if self._repository is None:
            from core.repositories.audit_log_repository import AuditLogRepository as _Repo

            self._repository = _Repo()
        return self._repository

    def log_operation(
        self,
        user_id: int,
        action_type: str,
        operation: str,
        status: str,
        message: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_data: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
        correlation_id: Optional[str] = None,
        parent_audit_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> "AuditLog":
        """
        Log a general operation with full audit details.

        Args:
            user_id: ID of the user performing the operation
            action_type: High-level action category (e.g., 'archive', 'overlap_resolution')
            operation: Specific operation (e.g., 'calendar_archive', 'resolve_overlap')
            status: Operation status ('success', 'failure', 'partial')
            message: Human-readable description
            resource_type: Type of resource affected (e.g., 'appointment', 'calendar')
            resource_id: ID of the affected resource
            details: Operation-specific details
            request_data: Input parameters/data
            response_data: Output/results
            duration_ms: Operation duration in milliseconds
            correlation_id: For tracking related operations
            parent_audit_id: For nested operations
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            The created AuditLog entry
        """
        from core.models.audit_log import AuditLog as _AuditLog

        audit_log = _AuditLog(
            user_id=user_id,
            action_type=action_type,
            operation=operation,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            message=message,
            details=details,
            request_data=request_data,
            response_data=response_data,
            duration_ms=duration_ms,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id,
            parent_audit_id=parent_audit_id,
        )

        return self.repository.add(audit_log)

    def log_archive_operation(
        self,
        user_id: int,
        operation: str,
        status: str,
        source_calendar_uri: str,
        archive_calendar_id: str,
        start_date: date,
        end_date: date,
        archived_count: int = 0,
        overlap_count: int = 0,
        errors: Optional[List[str]] = None,
        duration_ms: Optional[float] = None,
        correlation_id: Optional[str] = None,
    ) -> "AuditLog":
        """
        Log calendar archiving operations with specific archiving context.
        """
        details = {
            "source_calendar_uri": source_calendar_uri,
            "archive_calendar_id": archive_calendar_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "archived_count": archived_count,
            "overlap_count": overlap_count,
            "errors": errors or [],
        }

        message = (
            f"Archived {archived_count} appointments from {start_date} to {end_date}"
        )
        if overlap_count > 0:
            message += f", {overlap_count} overlaps detected"
        if errors:
            message += f", {len(errors)} errors occurred"

        return self.log_operation(
            user_id=user_id,
            action_type="archive",
            operation=operation,
            status=status,
            message=message,
            resource_type="calendar",
            resource_id=source_calendar_uri,
            details=details,
            duration_ms=duration_ms,
            correlation_id=correlation_id,
        )

    def log_overlap_resolution(
        self,
        user_id: int,
        action_log_id: int,
        resolution_type: str,
        status: str,
        appointments_affected: List[str],
        resolution_data: Dict[str, Any],
        ai_recommendations: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
        correlation_id: Optional[str] = None,
    ) -> "AuditLog":
        """
        Log overlap resolution operations with specific resolution context.
        """
        details = {
            "action_log_id": action_log_id,
            "resolution_type": resolution_type,
            "appointments_affected": appointments_affected,
            "resolution_data": resolution_data,
            "ai_recommendations": ai_recommendations,
        }

        message = f"Resolved overlap for {len(appointments_affected)} appointments using {resolution_type}"

        return self.log_operation(
            user_id=user_id,
            action_type="overlap_resolution",
            operation="resolve_overlap",
            status=status,
            message=message,
            resource_type="action_log",
            resource_id=str(action_log_id),
            details=details,
            duration_ms=duration_ms,
            correlation_id=correlation_id,
        )

    def log_api_call(
        self,
        user_id: int,
        api_name: str,
        endpoint: str,
        method: str,
        status: str,
        status_code: Optional[int] = None,
        request_data: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
        correlation_id: Optional[str] = None,
    ) -> "AuditLog":
        """
        Log external API calls for traceability and debugging.
        """
        details = {
            "api_name": api_name,
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
        }

        message = f"{method} {endpoint} - {status_code or 'N/A'}"

        return self.log_operation(
            user_id=user_id,
            action_type="api_call",
            operation=f"{api_name}_api_call",
            status=status,
            message=message,
            resource_type="api_endpoint",
            resource_id=endpoint,
            details=details,
            request_data=request_data,
            response_data=response_data,
            duration_ms=duration_ms,
            correlation_id=correlation_id,
        )

    def log_re_archive_operation(
        self,
        user_id: int,
        status: str,
        source_calendar_uri: str,
        archive_calendar_id: str,
        start_date: date,
        end_date: date,
        replaced_count: int = 0,
        new_archived_count: int = 0,
        duration_ms: Optional[float] = None,
        correlation_id: Optional[str] = None,
    ) -> "AuditLog":
        """
        Log re-archiving (replacement) operations.
        """
        details = {
            "source_calendar_uri": source_calendar_uri,
            "archive_calendar_id": archive_calendar_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "replaced_count": replaced_count,
            "new_archived_count": new_archived_count,
            "operation_type": "replacement",
        }

        message = f"Re-archived period {start_date} to {end_date}: replaced {replaced_count}, archived {new_archived_count}"

        return self.log_operation(
            user_id=user_id,
            action_type="re_archive",
            operation="calendar_re_archive",
            status=status,
            message=message,
            resource_type="calendar",
            resource_id=source_calendar_uri,
            details=details,
            duration_ms=duration_ms,
            correlation_id=correlation_id,
        )

    def generate_correlation_id(self) -> str:
        """Generate a unique correlation ID for tracking related operations."""
        return str(uuid.uuid4())

    def get_audit_trail(self, correlation_id: str) -> List[AuditLog]:
        """Get all audit log entries for a specific correlation ID."""
        return self.repository.list_by_correlation_id(correlation_id)

    def search_audit_logs(
        self,
        filters: Dict[str, Any],
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[AuditLog]:
        """Search audit logs with advanced filtering."""
        return self.repository.search(filters, limit, offset)

    def get_audit_summary(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Get a summary of audit activity for a user over the specified number of days.
        """
        end_date = date.today()
        start_date = date.fromordinal(end_date.toordinal() - days)

        logs = self.repository.list_by_date_range(start_date, end_date, user_id)

        summary: Dict[str, Any] = {
            "total_operations": len(logs),
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "by_action_type": {},
            "by_status": {},
            "by_operation": {},
        }

        for log in logs:
            # Count by action type
            action_type = log.action_type
            summary["by_action_type"][action_type] = (
                summary["by_action_type"].get(action_type, 0) + 1
            )

            # Count by status
            status = log.status
            summary["by_status"][status] = summary["by_status"].get(status, 0) + 1

            # Count by operation
            operation = log.operation
            summary["by_operation"][operation] = (
                summary["by_operation"].get(operation, 0) + 1
            )

        return summary

    def cleanup_old_logs(
        self, older_than_days: int, user_id: Optional[int] = None
    ) -> int:
        """
        Clean up audit logs older than the specified number of days.
        Returns the number of deleted entries.
        """
        cutoff_date = date.fromordinal(date.today().toordinal() - older_than_days)
        return self.repository.delete_old_entries(cutoff_date, user_id)
