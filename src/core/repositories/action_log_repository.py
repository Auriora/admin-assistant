from typing import List, Optional

from core.db import SessionLocal
from core.models.action_log import ActionLog


class ActionLogRepository:
    """
    Repository for managing ActionLog entities.
    """

    def __init__(self, session=None):
        self.session = session or SessionLocal()

    def get_by_id(self, log_id: int) -> Optional[ActionLog]:
        """Retrieve an ActionLog by its ID."""
        return self.session.get(ActionLog, log_id)

    def add(self, log: ActionLog) -> ActionLog:
        """Add a new ActionLog entry and return it with ID populated."""
        self.session.add(log)
        self.session.commit()
        self.session.refresh(log)
        return log

    def list_for_user(self, user_id: int) -> List[ActionLog]:
        """List all ActionLog entries for a given user."""
        return self.session.query(ActionLog).filter_by(user_id=user_id).all()

    def list_by_event(self, event_id: str) -> List[ActionLog]:
        """List all ActionLog entries for a given event."""
        return self.session.query(ActionLog).filter_by(event_id=event_id).all()

    def update(self, log: ActionLog) -> None:
        """Update an existing ActionLog entry."""
        self.session.merge(log)
        self.session.commit()

    def delete(self, log_id: int) -> None:
        """Delete an ActionLog entry by its ID."""
        log = self.get_by_id(log_id)
        if log:
            self.session.delete(log)
            self.session.commit()

    def list_by_state(self, state: str) -> List[ActionLog]:
        """
        List all ActionLog entries by state (e.g., open, resolved).
        """
        return self.session.query(ActionLog).filter_by(state=state).all()

    def update_recommendations(self, log_id: int, recommendations: dict) -> None:
        """
        Update the recommendations field for a given ActionLog.
        :param recommendations: Should be a JSON-serializable dict.
        """
        log = self.get_by_id(log_id)
        if log:
            # Ensure recommendations is JSON-serializable
            log.recommendations = recommendations  # type: ignore
            self.session.commit()

    def list_by_event_type(self, event_type: str) -> List[ActionLog]:
        """List all ActionLog entries by event type."""
        return self.session.query(ActionLog).filter_by(event_type=event_type).all()

    def list_pending_overlaps(self) -> List[ActionLog]:
        """List all pending overlap resolution tasks."""
        return (
            self.session.query(ActionLog)
            .filter_by(event_type="overlap_resolution", state="pending")
            .all()
        )
