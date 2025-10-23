"""Domain models representing Microsoft To Do tasks and linked resources."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Set, Literal


@dataclass(slots=True)
class TaskDateTime:
    """Represents a Microsoft Graph DateTimeTimeZone payload."""

    date_time: Optional[str]
    time_zone: Optional[str]

    @classmethod
    def from_graph(cls, value: Optional[Dict[str, Any]]) -> Optional["TaskDateTime"]:
        """Create an instance from the Graph DateTimeTimeZone representation."""

        if value is None:
            return None
        return cls(date_time=value.get("dateTime"), time_zone=value.get("timeZone"))

    def to_graph(self) -> Dict[str, Optional[str]]:
        """Serialize the object back into the Graph API representation."""

        return {"dateTime": self.date_time, "timeZone": self.time_zone}


@dataclass(slots=True)
class LinkedResource:
    """Represents a linked resource associated with a To Do task (e.g., flagged email)."""

    resource_id: Optional[str]
    application_name: Optional[str]
    display_name: Optional[str]
    external_id: Optional[str]
    web_url: Optional[str]
    resource_type: Optional[str]
    preview: Optional[str] = None
    body: Optional[str] = None
    body_content_type: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Task:
    """Represents a Microsoft To Do task enriched with linked resources."""

    task_id: str
    list_id: str
    title: Optional[str]
    status: Optional[str]
    importance: Optional[str]
    has_attachments: Optional[bool]
    is_reminder_on: Optional[bool]
    categories: List[str]
    created_datetime: Optional[datetime]
    last_modified_datetime: Optional[datetime]
    completed_datetime: Optional[datetime]
    due_date_time: Optional[TaskDateTime]
    start_date_time: Optional[TaskDateTime]
    reminder_date_time: Optional[TaskDateTime]
    body_content: Optional[str]
    body_content_type: Optional[str]
    body_preview: Optional[str]
    etag: Optional[str]
    list_name: Optional[str] = None
    wellknown_list_name: Optional[str] = None
    linked_resources: List[LinkedResource] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
        """Parse an ISO formatted datetime string into an aware datetime."""

        if not value:
            return None
        try:
            if value.endswith("Z"):
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            parsed = datetime.fromisoformat(value)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            return None

    @classmethod
    def from_graph(
        cls,
        payload: Dict[str, Any],
        list_metadata: Dict[str, Optional[str]],
        linked_resources: List[LinkedResource],
    ) -> "Task":
        """Create a Task domain model from raw Graph payload data."""

        return cls(
            task_id=payload.get("id"),
            list_id=list_metadata.get("list_id") or "",
            title=payload.get("title"),
            status=payload.get("status"),
            importance=payload.get("importance"),
            has_attachments=payload.get("hasAttachments"),
            is_reminder_on=payload.get("isReminderOn"),
            categories=payload.get("categories", []) or [],
            created_datetime=cls._parse_datetime(payload.get("createdDateTime")),
            last_modified_datetime=cls._parse_datetime(payload.get("lastModifiedDateTime")),
            completed_datetime=cls._parse_datetime(payload.get("completedDateTime")),
            due_date_time=TaskDateTime.from_graph(payload.get("dueDateTime")),
            start_date_time=TaskDateTime.from_graph(payload.get("startDateTime")),
            reminder_date_time=TaskDateTime.from_graph(payload.get("reminderDateTime")),
            body_content=(payload.get("body") or {}).get("content"),
            body_content_type=(payload.get("body") or {}).get("contentType"),
            body_preview=payload.get("bodyPreview"),
            etag=(payload.get("@odata.etag") or payload.get("etag")),
            list_name=list_metadata.get("list_name"),
            wellknown_list_name=list_metadata.get("wellknown_list_name"),
            linked_resources=linked_resources,
            raw=payload,
        )


@dataclass(slots=True)
class TaskCluster:
    """Cluster of related task indices identified during deduplication."""

    cluster_id: int
    indices: List[int]

    @property
    def size(self) -> int:
        """Return the number of tasks represented by the cluster."""

        return len(self.indices)


DecisionAction = Literal["keep", "delete", "merge", "move"]
DecisionSource = Literal["auto", "ai", "rule"]


@dataclass(slots=True)
class DedupDecision:
    """Structured decision emitted by deduplication pipelines."""

    task_key: str
    cluster_index: int
    raw_action: str
    source: DecisionSource
    rationale: str
    comment: str
    merged_title: Optional[str] = None
    target_list: Optional[str] = None
    cluster_id: Optional[int] = None
    cluster_size: Optional[int] = None
    canonical_cluster_index: Optional[int] = None
    canonical_row_index: Optional[int] = None
    canonical_list: Optional[str] = None

    def action(self) -> DecisionAction:
        """Return the normalized action for the decision."""

        action_lower = self.raw_action.lower()
        if action_lower.startswith("move"):
            return "move"
        if action_lower in {"keep", "delete", "merge"}:
            return action_lower  # type: ignore[return-value]
        return "keep"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the decision into a dictionary suitable for persistence."""

        return {
            "task_key": self.task_key,
            "cluster_index": self.cluster_index,
            "raw_action": self.raw_action,
            "source": self.source,
            "rationale": self.rationale,
            "comment": self.comment,
            "merged_title": self.merged_title,
            "target_list": self.target_list,
            "cluster_id": self.cluster_id,
            "cluster_size": self.cluster_size,
            "canonical_cluster_index": self.canonical_cluster_index,
            "canonical_row_index": self.canonical_row_index,
            "canonical_list": self.canonical_list,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "DedupDecision":
        """Hydrate a decision from a dictionary representation."""

        return cls(
            task_key=str(payload.get("task_key", "")),
            cluster_index=int(payload.get("cluster_index", 0)),
            raw_action=str(payload.get("raw_action", "keep")),
            source=str(payload.get("source", "ai")) or "ai",  # type: ignore[arg-type]
            rationale=str(payload.get("rationale", "")),
            comment=str(payload.get("comment", "")),
            merged_title=payload.get("merged_title"),
            target_list=payload.get("target_list"),
            cluster_id=payload.get("cluster_id"),
            cluster_size=payload.get("cluster_size"),
            canonical_cluster_index=payload.get("canonical_cluster_index"),
            canonical_row_index=payload.get("canonical_row_index"),
            canonical_list=payload.get("canonical_list"),
        )


__all__: Set[str] = {
    "TaskDateTime",
    "LinkedResource",
    "Task",
    "TaskCluster",
    "DedupDecision",
}
