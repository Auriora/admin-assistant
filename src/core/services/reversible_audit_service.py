import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from core.models.audit_log import AuditLog
from core.models.reversible_operation import ReversibleOperation, ReversibleOperationItem
from core.repositories.audit_log_repository import AuditLogRepository
from core.services.audit_log_service import AuditLogService


class ReversibleAuditService:
    """
    Service for managing reversible operations with comprehensive audit logging.
    
    This service extends the standard audit logging to capture enough information
    to completely reverse any operation, enabling safe rollbacks and undo functionality.
    """

    def __init__(self, session: Session):
        self.session = session
        self.audit_service = AuditLogService()
        self.audit_repository = AuditLogRepository(session)

    @staticmethod
    def _to_json_safe(val):
        """
        Convert values to JSON-safe format, handling datetime objects and other non-serializable types.
        """
        from sqlalchemy.orm.attributes import InstrumentedAttribute

        if val is None:
            return None
        if isinstance(val, InstrumentedAttribute) or hasattr(val, "expression"):
            return None
        if isinstance(val, (str, int, float, bool)):
            return val
        if isinstance(val, datetime):
            return val.isoformat()
        if isinstance(val, list):
            return [ReversibleAuditService._to_json_safe(v) for v in val]
        if isinstance(val, dict):
            return {
                str(k): ReversibleAuditService._to_json_safe(v)
                for k, v in val.items()
            }
        # For any other type, convert to string
        return str(val)

    def start_reversible_operation(
        self,
        user_id: int,
        operation_type: str,
        operation_name: str,
        correlation_id: Optional[str] = None,
        depends_on: Optional[List[int]] = None,
    ) -> Tuple[ReversibleOperation, str]:
        """
        Start a new reversible operation.
        
        Args:
            user_id: ID of user performing the operation
            operation_type: Type of operation ('archive', 'delete', 'update', 'create')
            operation_name: Specific operation name ('calendar_archive_replace')
            correlation_id: Optional correlation ID for related operations
            depends_on: List of operation IDs this operation depends on
            
        Returns:
            Tuple of (ReversibleOperation, correlation_id)
        """
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Create initial audit log entry
        audit_log = self.audit_service.log_operation(
            user_id=user_id,
            action_type=operation_type,
            operation=operation_name,
            status="started",
            message=f"Started reversible operation: {operation_name}",
            correlation_id=correlation_id,
        )

        # Create reversible operation record
        reversible_op = ReversibleOperation(
            audit_log_id=audit_log.id,
            user_id=user_id,
            operation_type=operation_type,
            operation_name=operation_name,
            correlation_id=correlation_id,
            depends_on_operations=depends_on or [],
            reverse_instructions={
                "operation_type": operation_type,
                "operation_name": operation_name,
                "items": [],
                "metadata": {},
            },
        )

        self.session.add(reversible_op)
        self.session.commit()
        self.session.refresh(reversible_op)

        return reversible_op, correlation_id

    def capture_item_state(
        self,
        operation: ReversibleOperation,
        item_type: str,
        item_id: str,
        before_state: Dict[str, Any],
        reverse_action: str,
        reverse_data: Optional[Dict[str, Any]] = None,
        external_id: Optional[str] = None,
    ) -> ReversibleOperationItem:
        """
        Capture the state of an individual item before an operation.
        
        Args:
            operation: The reversible operation this item belongs to
            item_type: Type of item ('appointment', 'calendar')
            item_id: Unique identifier for the item
            before_state: Complete state of the item before operation
            reverse_action: Action needed to reverse ('restore', 'delete', 'update')
            reverse_data: Additional data needed for reversal
            external_id: External system ID (e.g., MS Graph event ID)
            
        Returns:
            ReversibleOperationItem instance
        """
        # Ensure all state data is JSON-safe
        safe_before_state = self._to_json_safe(before_state)
        safe_reverse_data = self._to_json_safe(reverse_data or {})

        item = ReversibleOperationItem(
            operation_id=operation.id,
            item_type=item_type,
            item_id=item_id,
            external_id=external_id,
            before_state=safe_before_state,
            reverse_action=reverse_action,
            reverse_data=safe_reverse_data,
        )

        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)

        return item

    def update_item_after_state(
        self,
        item: ReversibleOperationItem,
        after_state: Dict[str, Any],
    ) -> None:
        """
        Update an item with its state after the operation completed.
        
        Args:
            item: The operation item to update
            after_state: Complete state of the item after operation
        """
        # Ensure after_state is JSON-safe
        safe_after_state = self._to_json_safe(after_state)
        item.after_state = safe_after_state
        self.session.commit()

    def complete_operation(
        self,
        operation: ReversibleOperation,
        status: str,
        message: str,
        response_data: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
    ) -> None:
        """
        Mark a reversible operation as completed.
        
        Args:
            operation: The operation to complete
            status: Final status ('success', 'failure', 'partial')
            message: Completion message
            response_data: Operation results
            duration_ms: Operation duration
        """
        # Update the audit log
        audit_log = self.session.get(AuditLog, operation.audit_log_id)
        if audit_log:
            audit_log.status = status
            audit_log.message = message
            audit_log.response_data = response_data
            audit_log.duration_ms = duration_ms

        # Update reversible operation
        operation.after_state = response_data or {}
        
        # If operation failed, mark as non-reversible
        if status == "failure":
            operation.is_reversible = False
            operation.reverse_reason = "Operation failed - cannot reverse"

        self.session.commit()

    def get_operation_by_id(self, operation_id: int) -> Optional[ReversibleOperation]:
        """Get a reversible operation by ID."""
        return self.session.get(ReversibleOperation, operation_id)

    def get_operations_by_correlation_id(self, correlation_id: str) -> List[ReversibleOperation]:
        """Get all reversible operations with the same correlation ID."""
        return (
            self.session.query(ReversibleOperation)
            .filter_by(correlation_id=correlation_id)
            .order_by(ReversibleOperation.created_at)
            .all()
        )

    def get_reversible_operations(
        self,
        user_id: Optional[int] = None,
        operation_type: Optional[str] = None,
        is_reversed: Optional[bool] = None,
        limit: Optional[int] = None,
    ) -> List[ReversibleOperation]:
        """
        Get reversible operations with optional filtering.
        
        Args:
            user_id: Filter by user ID
            operation_type: Filter by operation type
            is_reversed: Filter by reversal status
            limit: Maximum number of results
            
        Returns:
            List of ReversibleOperation instances
        """
        query = self.session.query(ReversibleOperation)

        if user_id:
            query = query.filter_by(user_id=user_id)
        if operation_type:
            query = query.filter_by(operation_type=operation_type)
        if is_reversed is not None:
            query = query.filter_by(is_reversed=is_reversed)

        query = query.order_by(ReversibleOperation.created_at.desc())

        if limit:
            query = query.limit(limit)

        return query.all()

    def check_operation_dependencies(self, operation: ReversibleOperation) -> Tuple[bool, List[str]]:
        """
        Check if an operation can be safely reversed based on dependencies.
        
        Args:
            operation: Operation to check
            
        Returns:
            Tuple of (can_reverse, blocking_reasons)
        """
        blocking_reasons = []

        # Check if operation is already reversed
        if operation.is_reversed:
            blocking_reasons.append("Operation has already been reversed")

        # Check if operation is marked as non-reversible
        if not operation.is_reversible:
            blocking_reasons.append(f"Operation is not reversible: {operation.reverse_reason}")

        # Check for dependent operations that haven't been reversed
        if operation.blocks_operations:
            dependent_ops = (
                self.session.query(ReversibleOperation)
                .filter(ReversibleOperation.id.in_(operation.blocks_operations))
                .filter_by(is_reversed=False)
                .all()
            )
            
            if dependent_ops:
                op_names = [op.operation_name for op in dependent_ops]
                blocking_reasons.append(f"Dependent operations must be reversed first: {', '.join(op_names)}")

        return len(blocking_reasons) == 0, blocking_reasons

    def reverse_operation(
        self,
        operation_id: int,
        reversed_by_user_id: int,
        reason: str,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Reverse a completed operation.

        Args:
            operation_id: ID of operation to reverse
            reversed_by_user_id: ID of user performing the reversal
            reason: Reason for reversal
            dry_run: If True, only simulate the reversal without executing

        Returns:
            Dict with reversal results and any errors
        """
        operation = self.get_operation_by_id(operation_id)
        if not operation:
            return {"success": False, "error": "Operation not found"}

        # Check if operation can be reversed
        can_reverse, blocking_reasons = self.check_operation_dependencies(operation)
        if not can_reverse:
            return {
                "success": False,
                "error": "Cannot reverse operation",
                "reasons": blocking_reasons,
            }

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "message": "Operation can be safely reversed",
                "items_to_reverse": len(operation.items),
                "reverse_actions": [item.reverse_action for item in operation.items],
            }

        # Execute the reversal
        reversal_results = {
            "success": True,
            "reversed_items": 0,
            "failed_items": 0,
            "errors": [],
        }

        try:
            # Start reversal audit log
            reversal_audit = self.audit_service.log_operation(
                user_id=reversed_by_user_id,
                action_type="reverse",
                operation=f"reverse_{operation.operation_name}",
                status="started",
                message=f"Started reversal of operation {operation_id}: {reason}",
                correlation_id=operation.correlation_id,
                parent_audit_id=operation.audit_log_id,
            )

            # Reverse each item
            for item in operation.items:
                try:
                    self._reverse_operation_item(item)
                    item.is_reversed = True
                    item.reversed_at = datetime.utcnow()
                    reversal_results["reversed_items"] += 1
                except Exception as e:
                    item.reverse_error = str(e)
                    reversal_results["failed_items"] += 1
                    reversal_results["errors"].append(f"Failed to reverse {item.item_type} {item.item_id}: {str(e)}")

            # Mark operation as reversed if all items succeeded
            if reversal_results["failed_items"] == 0:
                operation.is_reversed = True
                operation.reversed_at = datetime.utcnow()
                operation.reversed_by_user_id = reversed_by_user_id
                operation.reverse_reason = reason
                status = "success"
                message = f"Successfully reversed operation {operation_id}"
            else:
                status = "partial"
                message = f"Partially reversed operation {operation_id}: {reversal_results['failed_items']} items failed"

            # Update reversal audit log
            reversal_audit.status = status
            reversal_audit.message = message
            reversal_audit.response_data = reversal_results

            self.session.commit()

        except Exception as e:
            self.session.rollback()
            reversal_results["success"] = False
            reversal_results["error"] = str(e)

        return reversal_results

    def _reverse_operation_item(self, item: ReversibleOperationItem) -> None:
        """
        Reverse a single operation item.

        This method delegates to specific reversal handlers based on item type.
        """
        if item.reverse_action == "restore":
            self._restore_item(item)
        elif item.reverse_action == "delete":
            self._delete_item(item)
        elif item.reverse_action == "update":
            self._update_item(item)
        else:
            raise ValueError(f"Unknown reverse action: {item.reverse_action}")

    def _restore_item(self, item: ReversibleOperationItem) -> None:
        """Restore an item that was deleted."""
        if item.item_type == "appointment":
            self._restore_appointment(item)
        else:
            raise ValueError(f"Cannot restore item type: {item.item_type}")

    def _delete_item(self, item: ReversibleOperationItem) -> None:
        """Delete an item that was created."""
        if item.item_type == "appointment":
            self._delete_appointment(item)
        else:
            raise ValueError(f"Cannot delete item type: {item.item_type}")

    def _update_item(self, item: ReversibleOperationItem) -> None:
        """Update an item to its previous state."""
        if item.item_type == "appointment":
            self._update_appointment(item)
        else:
            raise ValueError(f"Cannot update item type: {item.item_type}")

    def _restore_appointment(self, item: ReversibleOperationItem) -> None:
        """Restore a deleted appointment."""
        # This would integrate with the appointment repository
        # to recreate the appointment from the stored before_state
        from core.repositories.appointment_repository_msgraph import MSGraphAppointmentRepository
        from core.models.appointment import Appointment

        # Reconstruct appointment from before_state
        before_state = item.before_state
        if not before_state:
            raise ValueError("No before_state available for restoration")

        # Create appointment object from stored state
        appointment = Appointment(**before_state)

        # Use the appropriate repository to restore
        # This is a simplified example - real implementation would need
        # to determine the correct repository and handle MS Graph specifics
        raise NotImplementedError("Appointment restoration not yet implemented")

    def _delete_appointment(self, item: ReversibleOperationItem) -> None:
        """Delete an appointment that was created."""
        # This would integrate with the appointment repository to delete
        raise NotImplementedError("Appointment deletion not yet implemented")

    def _update_appointment(self, item: ReversibleOperationItem) -> None:
        """Update an appointment to its previous state."""
        # This would integrate with the appointment repository to update
        raise NotImplementedError("Appointment update not yet implemented")
