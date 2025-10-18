from typing import Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from core.models.action_log import ActionLog
    from core.repositories.action_log_repository import ActionLogRepository as _ActionRepo
    from core.services.entity_association_service import EntityAssociationService as _AssocSvc


class ActionLogService:
    """
    Service for business logic related to ActionLog entities, including state management, recommendations, and associations.
    """

    def __init__(
        self,
        repository: Optional["_ActionRepo"] = None,
        association_service: Optional["_AssocSvc"] = None,
    ):
        self._repository = repository
        self._association_service = association_service

    @property
    def repository(self) -> "_ActionRepo":
        if self._repository is None:
            from core.repositories.action_log_repository import ActionLogRepository as _Repo

            self._repository = _Repo()
        return self._repository

    @property
    def association_service(self) -> "_AssocSvc":
        if self._association_service is None:
            from core.services.entity_association_service import EntityAssociationService as _Svc

            self._association_service = _Svc()
        return self._association_service

    def get_by_id(self, log_id: int) -> Optional["ActionLog"]:
        return self.repository.get_by_id(log_id)

    def create(self, log: "ActionLog") -> None:
        self.repository.add(log)

    def list_for_user(self, user_id: int) -> List["ActionLog"]:
        return self.repository.list_for_user(user_id)

    def list_by_state(self, state: str) -> List["ActionLog"]:
        return self.repository.list_by_state(state)

    def transition_state(self, log_id: int, new_state: str) -> None:
        """
        Transition the state of an ActionLog (e.g., open → resolved → archived).
        Raises ValueError if log not found.
        """
        log = self.get_by_id(log_id)
        if not log:
            raise ValueError("ActionLog not found")
        setattr(log, "state", new_state)  # type: ignore
        self.repository.update(log)

    def attach_recommendations(self, log_id: int, recommendations: dict) -> None:
        """
        Attach or update AI recommendations for an ActionLog.
        """
        self.repository.update_recommendations(log_id, recommendations)

    def summarize_actions(self, user_id: int) -> List[Any]:
        """
        Summarize or group actions for the UI. Returns a list of dicts grouped by state.
        """
        actions = self.list_for_user(user_id)
        summary = {}
        for action in actions:
            state = getattr(action, "state", "unknown")
            summary.setdefault(state, []).append(action)
        return [{"state": k, "actions": v} for k, v in summary.items()]

    def get_related_entities(self, db: "Session", log_id: int) -> List[Any]:
        """
        Fetch all entities related to this ActionLog via EntityAssociation.
        Returns a list of (target_type, target_id) tuples.
        """
        return self.association_service.get_related_entities(db, "action_log", log_id)
