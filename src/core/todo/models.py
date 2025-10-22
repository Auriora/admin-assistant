"""Domain models representing Microsoft To Do tasks and linked resources."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional


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

