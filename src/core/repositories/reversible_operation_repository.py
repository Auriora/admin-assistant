from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy import and_, desc, asc, or_
from sqlalchemy.orm import Session

from core.db import SessionLocal
from core.models.reversible_operation import ReversibleOperation, ReversibleOperationItem


class ReversibleOperationRepository:
    """
    Repository for managing ReversibleOperation and ReversibleOperationItem entities.
    """

    def __init__(self, session: Optional[Session] = None):
        self.session = session or SessionLocal()

    def add_operation(self, operation: ReversibleOperation) -> ReversibleOperation:
        """Add a new ReversibleOperation and return it with ID populated."""
        self.session.add(operation)
        self.session.commit()
        self.session.refresh(operation)
        return operation

    def add_item(self, item: ReversibleOperationItem) -> ReversibleOperationItem:
        """Add a new ReversibleOperationItem and return it with ID populated."""
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def get_operation_by_id(self, operation_id: int) -> Optional[ReversibleOperation]:
        """Retrieve a ReversibleOperation by its ID."""
        return self.session.get(ReversibleOperation, operation_id)

    def get_item_by_id(self, item_id: int) -> Optional[ReversibleOperationItem]:
        """Retrieve a ReversibleOperationItem by its ID."""
        return self.session.get(ReversibleOperationItem, item_id)

    def list_operations_by_user(
        self, 
        user_id: int, 
        limit: Optional[int] = None,
        operation_type: Optional[str] = None,
        is_reversed: Optional[bool] = None,
    ) -> List[ReversibleOperation]:
        """List ReversibleOperations for a specific user."""
        query = self.session.query(ReversibleOperation).filter_by(user_id=user_id)
        
        if operation_type:
            query = query.filter_by(operation_type=operation_type)
        
        if is_reversed is not None:
            query = query.filter_by(is_reversed=is_reversed)
        
        query = query.order_by(desc(ReversibleOperation.created_at))
        
        if limit:
            query = query.limit(limit)
        
        return query.all()

    def list_operations_by_correlation_id(self, correlation_id: str) -> List[ReversibleOperation]:
        """List all ReversibleOperations with the same correlation ID."""
        return (
            self.session.query(ReversibleOperation)
            .filter_by(correlation_id=correlation_id)
            .order_by(asc(ReversibleOperation.created_at))
            .all()
        )

    def list_operations_by_date_range(
        self,
        start_date: date,
        end_date: date,
        user_id: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[ReversibleOperation]:
        """List ReversibleOperations within a date range."""
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        query = self.session.query(ReversibleOperation).filter(
            and_(
                ReversibleOperation.created_at >= start_datetime,
                ReversibleOperation.created_at <= end_datetime,
            )
        )

        if user_id:
            query = query.filter_by(user_id=user_id)

        query = query.order_by(desc(ReversibleOperation.created_at))

        if limit:
            query = query.limit(limit)

        return query.all()

    def list_reversible_operations(
        self,
        user_id: Optional[int] = None,
        operation_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[ReversibleOperation]:
        """List operations that can be reversed (not yet reversed and marked as reversible)."""
        query = self.session.query(ReversibleOperation).filter(
            and_(
                ReversibleOperation.is_reversible == True,
                ReversibleOperation.is_reversed == False,
            )
        )

        if user_id:
            query = query.filter_by(user_id=user_id)

        if operation_type:
            query = query.filter_by(operation_type=operation_type)

        query = query.order_by(desc(ReversibleOperation.created_at))

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_operation_items(self, operation_id: int) -> List[ReversibleOperationItem]:
        """Get all items for a specific operation."""
        return (
            self.session.query(ReversibleOperationItem)
            .filter_by(operation_id=operation_id)
            .order_by(asc(ReversibleOperationItem.created_at))
            .all()
        )

    def get_items_by_external_id(
        self, 
        external_id: str, 
        item_type: Optional[str] = None
    ) -> List[ReversibleOperationItem]:
        """Get operation items by external ID (e.g., MS Graph event ID)."""
        query = self.session.query(ReversibleOperationItem).filter_by(external_id=external_id)
        
        if item_type:
            query = query.filter_by(item_type=item_type)
        
        return query.all()

    def update_operation(self, operation: ReversibleOperation) -> None:
        """Update a ReversibleOperation."""
        self.session.merge(operation)
        self.session.commit()

    def update_item(self, item: ReversibleOperationItem) -> None:
        """Update a ReversibleOperationItem."""
        self.session.merge(item)
        self.session.commit()

    def search_operations(
        self,
        filters: Dict[str, Any],
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[ReversibleOperation]:
        """
        Advanced search for operations with multiple filters.

        Args:
            filters: Dict with possible keys:
                - user_id: int
                - operation_type: str
                - operation_name: str
                - is_reversible: bool
                - is_reversed: bool
                - correlation_id: str
                - start_date: date
                - end_date: date
        """
        query = self.session.query(ReversibleOperation)

        # Apply filters
        if "user_id" in filters:
            query = query.filter_by(user_id=filters["user_id"])

        if "operation_type" in filters:
            query = query.filter_by(operation_type=filters["operation_type"])

        if "operation_name" in filters:
            query = query.filter_by(operation_name=filters["operation_name"])

        if "is_reversible" in filters:
            query = query.filter_by(is_reversible=filters["is_reversible"])

        if "is_reversed" in filters:
            query = query.filter_by(is_reversed=filters["is_reversed"])

        if "correlation_id" in filters:
            query = query.filter_by(correlation_id=filters["correlation_id"])

        if "start_date" in filters and "end_date" in filters:
            start_datetime = datetime.combine(filters["start_date"], datetime.min.time())
            end_datetime = datetime.combine(filters["end_date"], datetime.max.time())
            query = query.filter(
                and_(
                    ReversibleOperation.created_at >= start_datetime,
                    ReversibleOperation.created_at <= end_datetime,
                )
            )

        # Order by creation date (newest first)
        query = query.order_by(desc(ReversibleOperation.created_at))

        # Apply pagination
        if offset:
            query = query.offset(offset)

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_operation_dependencies(self, operation_id: int) -> Dict[str, List[ReversibleOperation]]:
        """
        Get operations that this operation depends on and operations that depend on this one.
        
        Returns:
            Dict with 'dependencies' and 'dependents' keys
        """
        operation = self.get_operation_by_id(operation_id)
        if not operation:
            return {"dependencies": [], "dependents": []}

        dependencies = []
        if operation.depends_on_operations:
            dependencies = (
                self.session.query(ReversibleOperation)
                .filter(ReversibleOperation.id.in_(operation.depends_on_operations))
                .all()
            )

        dependents = []
        if operation.blocks_operations:
            dependents = (
                self.session.query(ReversibleOperation)
                .filter(ReversibleOperation.id.in_(operation.blocks_operations))
                .all()
            )

        return {
            "dependencies": dependencies,
            "dependents": dependents,
        }

    def mark_operation_as_blocking(self, operation_id: int, blocked_operation_id: int) -> None:
        """Mark one operation as blocking another (creates dependency relationship)."""
        operation = self.get_operation_by_id(operation_id)
        blocked_operation = self.get_operation_by_id(blocked_operation_id)
        
        if not operation or not blocked_operation:
            raise ValueError("One or both operations not found")

        # Add to blocks_operations list
        if not operation.blocks_operations:
            operation.blocks_operations = []
        if blocked_operation_id not in operation.blocks_operations:
            operation.blocks_operations.append(blocked_operation_id)

        # Add to depends_on_operations list
        if not blocked_operation.depends_on_operations:
            blocked_operation.depends_on_operations = []
        if operation_id not in blocked_operation.depends_on_operations:
            blocked_operation.depends_on_operations.append(operation_id)

        self.session.commit()

    def delete_old_operations(self, older_than_days: int, user_id: Optional[int] = None) -> int:
        """
        Delete old reversible operations (and their items) that are older than specified days.
        Only deletes operations that have been reversed or are marked as non-reversible.
        
        Args:
            older_than_days: Delete operations older than this many days
            user_id: Optional user ID to limit deletion to specific user
            
        Returns:
            Number of operations deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        
        query = self.session.query(ReversibleOperation).filter(
            and_(
                ReversibleOperation.created_at < cutoff_date,
                or_(
                    ReversibleOperation.is_reversed == True,
                    ReversibleOperation.is_reversible == False,
                )
            )
        )
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        operations_to_delete = query.all()
        count = len(operations_to_delete)
        
        # Delete items first (due to foreign key constraints)
        for operation in operations_to_delete:
            self.session.query(ReversibleOperationItem).filter_by(
                operation_id=operation.id
            ).delete()
        
        # Delete operations
        for operation in operations_to_delete:
            self.session.delete(operation)
        
        self.session.commit()
        return count
