"""Repository for interacting with Microsoft To Do via Microsoft Graph."""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional

import requests

from core.models.user import User
from core.todo.models import LinkedResource, Task, TaskDateTime
from core.utilities.graph_utility import get_graph_client

try:
    from opentelemetry import trace

    tracer = trace.get_tracer(__name__)
except ImportError:  # pragma: no cover - tracing is optional in tests
    tracer = None


logger = logging.getLogger(__name__)


class MSGraphTaskRepositoryError(RuntimeError):
    """Raised when Microsoft Graph returns an error for To Do operations."""


class MSGraphTaskRepository:
    """Provides high-fidelity access to Microsoft To Do tasks via Graph."""

    TASK_SELECT_FIELDS = [
        "id",
        "title",
        "status",
        "importance",
        "hasAttachments",
        "isReminderOn",
        "categories",
        "createdDateTime",
        "lastModifiedDateTime",
        "completedDateTime",
        "dueDateTime",
        "startDateTime",
        "reminderDateTime",
        "body",
        "bodyPreview",
    ]
    LIST_SELECT_FIELDS = ["id", "displayName", "wellknownListName"]
    DEFAULT_TOP = 100
    GRAPH_TIMEOUT_SECONDS = 30

    def __init__(self, *, http_client: Optional[requests.Session] = None) -> None:
        """Initialise the repository with an optional custom HTTP client."""

        self._http_client = http_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def list_all_tasks(self, user: User, access_token: str) -> List[Task]:
        """Return all incomplete tasks (including flagged emails) for the user."""

        if not access_token:
            raise ValueError("access_token is required to call Microsoft Graph")

        if tracer:
            with tracer.start_as_current_span("todo.list_all_tasks"):
                return self._list_all_tasks_impl(user, access_token)
        return self._list_all_tasks_impl(user, access_token)

    def update_task(
        self,
        user: User,
        access_token: str,
        task: Task,
        changes: Dict[str, Any],
    ) -> Task:
        """Apply updates to an existing task and return the refreshed representation."""

        if not access_token:
            raise ValueError("access_token is required to call Microsoft Graph")
        if not task.task_id:
            raise ValueError("Task must include a task_id before it can be updated")

        if tracer:
            with tracer.start_as_current_span("todo.update_task"):
                return self._update_task_impl(user, access_token, task, changes)
        return self._update_task_impl(user, access_token, task, changes)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _list_all_tasks_impl(self, user: User, access_token: str) -> List[Task]:
        client = get_graph_client(user, access_token)
        base_url = self._resolve_base_url(client)
        headers = self._build_headers(access_token)

        list_items = self._get_collection(
            f"{base_url}/me/todo/lists",
            headers,
            params={"$select": ",".join(self.LIST_SELECT_FIELDS)},
        )

        tasks: List[Task] = []
        for list_payload in list_items:
            list_id = list_payload.get("id")
            if not list_id:
                continue

            list_metadata = {
                "list_id": list_id,
                "list_name": list_payload.get("displayName"),
                "wellknown_list_name": list_payload.get("wellknownListName"),
            }

            task_url = f"{base_url}/me/todo/lists/{list_id}/tasks"
            params = {
                "$select": ",".join(self.TASK_SELECT_FIELDS),
                "$orderby": "lastModifiedDateTime desc",
                "$expand": "linkedResources",
                "$filter": "status ne 'completed'",
                "$top": str(self.DEFAULT_TOP),
            }

            task_payloads = self._get_collection(task_url, headers, params=params)
            for task_payload in task_payloads:
                linked_resources = self._parse_linked_resources(
                    task_payload.get("linkedResources", []) or [],
                    list_metadata,
                    base_url,
                    headers,
                )
                tasks.append(Task.from_graph(task_payload, list_metadata, linked_resources))

        return tasks

    def _update_task_impl(
        self,
        user: User,
        access_token: str,
        task: Task,
        changes: Dict[str, Any],
    ) -> Task:
        if not isinstance(changes, dict) or not changes:
            raise ValueError("changes must be a non-empty dictionary")

        client = get_graph_client(user, access_token)
        base_url = self._resolve_base_url(client)
        headers = self._build_headers(access_token)

        target_list_id = (
            changes.get("list_id")
            or changes.get("parent_list_id")
            or changes.get("parentListId")
            or task.list_id
        )
        if not target_list_id:
            raise ValueError("Unable to determine destination list for the task update")

        payload = self._build_patch_payload(changes)
        if not payload:
            # Nothing to update; return the existing task unchanged
            return task

        patch_headers = deepcopy(headers)
        patch_headers["Content-Type"] = "application/json"
        etag = changes.get("etag") or task.etag
        if etag:
            patch_headers["If-Match"] = etag

        task_url = f"{base_url}/me/todo/lists/{target_list_id}/tasks/{task.task_id}"
        self._http_patch(task_url, patch_headers, payload)

        # Refresh the task using the destination list metadata
        list_metadata = (
            {"list_id": task.list_id, "list_name": task.list_name, "wellknown_list_name": task.wellknown_list_name}
            if target_list_id == task.list_id
            else self._lookup_list_metadata(base_url, headers, target_list_id)
        )

        refreshed_payload = self._http_get(
            task_url,
            headers,
            params={
                "$select": ",".join(self.TASK_SELECT_FIELDS),
                "$expand": "linkedResources",
            },
        )

        linked_resources = self._parse_linked_resources(
            refreshed_payload.get("linkedResources", []) or [],
            list_metadata,
            base_url,
            headers,
        )

        updated_task = Task.from_graph(refreshed_payload, list_metadata, linked_resources)
        return updated_task

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------
    def _http_get(
        self,
        url: str,
        headers: Dict[str, str],
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        response = self._send_request("GET", url, headers=headers, params=params)
        return response.json() if self._has_body(response) else {}

    def _http_patch(
        self,
        url: str,
        headers: Dict[str, str],
        payload: Dict[str, Any],
    ) -> None:
        response = self._send_request("PATCH", url, headers=headers, json=payload)
        if response.status_code >= 400:
            raise MSGraphTaskRepositoryError(
                f"Graph PATCH failed ({response.status_code}) for {self._redact_url(url)}: {response.text}"
            )

    def _send_request(self, method: str, url: str, **kwargs: Any):
        client = self._http_client or requests
        try:
            response = client.request(
                method,
                url,
                timeout=self.GRAPH_TIMEOUT_SECONDS,
                **kwargs,
            )
        except requests.RequestException as exc:  # pragma: no cover - network failure path
            raise MSGraphTaskRepositoryError(
                f"Graph {method} failed for {self._redact_url(url)}: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise MSGraphTaskRepositoryError(
                f"Graph {method} failed ({response.status_code}) for {self._redact_url(url)}: {response.text}"
            )
        return response

    @staticmethod
    def _has_body(response: requests.Response) -> bool:
        return bool(response.content and response.content.strip())

    # ------------------------------------------------------------------
    # Data shaping helpers
    # ------------------------------------------------------------------
    def _get_collection(
        self,
        url: str,
        headers: Dict[str, str],
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        next_url: Optional[str] = url
        next_params = params
        visited: set[str] = set()

        while next_url:
            response = self._http_get(next_url, headers, params=next_params)
            values = response.get("value", []) or []
            if not isinstance(values, list):
                logger.warning("Unexpected Graph response format for %s", self._redact_url(next_url))
                break
            items.extend(values)

            next_link = self._extract_next_link(response)
            if not next_link or next_link in visited:
                break
            visited.add(next_link)
            next_url = next_link
            next_params = None

        return items

    @staticmethod
    def _extract_next_link(response: Dict[str, Any]) -> Optional[str]:
        return (
            response.get("@odata.nextLink")
            or response.get("odata.nextLink")
            or response.get("@odata.nextlink")
        )

    def _parse_linked_resources(
        self,
        raw_resources: Iterable[Dict[str, Any]],
        list_metadata: Dict[str, Optional[str]],
        base_url: str,
        headers: Dict[str, str],
    ) -> List[LinkedResource]:
        resources: List[LinkedResource] = []
        is_flagged_list = (list_metadata.get("wellknown_list_name") or "").lower() == "flaggedemails"

        for raw in raw_resources:
            resource = LinkedResource(
                resource_id=raw.get("id"),
                application_name=raw.get("applicationName"),
                display_name=raw.get("displayName"),
                external_id=raw.get("externalId"),
                web_url=raw.get("webUrl"),
                resource_type=raw.get("@odata.type") or raw.get("type"),
                preview=raw.get("preview"),
                body=raw.get("body"),
                body_content_type=raw.get("bodyContentType"),
                raw=raw,
            )

            if is_flagged_list:
                self._enrich_flagged_email_resource(resource, base_url, headers)

            resources.append(resource)

        return resources

    def _enrich_flagged_email_resource(
        self,
        resource: LinkedResource,
        base_url: str,
        headers: Dict[str, str],
    ) -> None:
        if resource.preview and resource.body:
            return

        if not resource.external_id:
            return

        # Fetch the source email for additional context
        message_url = f"{base_url}/me/messages/{resource.external_id}"
        params = {"$select": "bodyPreview,body,webLink"}
        try:
            message_payload = self._http_get(message_url, headers, params=params)
        except MSGraphTaskRepositoryError as exc:
            logger.debug("Unable to enrich flagged email resource %s: %s", resource.external_id, exc)
            return

        resource.preview = resource.preview or message_payload.get("bodyPreview")
        body = message_payload.get("body") or {}
        resource.body = resource.body or body.get("content")
        resource.body_content_type = resource.body_content_type or body.get("contentType")
        resource.web_url = resource.web_url or message_payload.get("webLink")

    def _build_patch_payload(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}

        for key, value in changes.items():
            normalized_key = self._normalize_change_key(key)
            if normalized_key is None:
                continue

            if normalized_key in {"dueDateTime", "startDateTime", "reminderDateTime"}:
                payload[normalized_key] = self._serialize_task_datetime(value)
            elif normalized_key == "body":
                payload[normalized_key] = self._serialize_body(value)
            elif normalized_key == "linkedResources":
                payload[normalized_key] = value
            elif normalized_key in {"categories"} and value is None:
                payload[normalized_key] = []
            else:
                payload[normalized_key] = value

        # list changes handled separately via target list id
        for discard_key in ("list_id", "parent_list_id", "parentListId", "etag"):
            payload.pop(discard_key, None)

        return payload

    @staticmethod
    def _normalize_change_key(key: str) -> Optional[str]:
        mapping = {
            "title": "title",
            "status": "status",
            "importance": "importance",
            "categories": "categories",
            "dueDateTime": "dueDateTime",
            "due_date_time": "dueDateTime",
            "startDateTime": "startDateTime",
            "start_date_time": "startDateTime",
            "reminderDateTime": "reminderDateTime",
            "reminder_date_time": "reminderDateTime",
            "body": "body",
            "body_content": "body",
            "body_content_type": "body",
            "isReminderOn": "isReminderOn",
            "is_reminder_on": "isReminderOn",
            "hasAttachments": "hasAttachments",
            "has_attachments": "hasAttachments",
            "linked_resources": "linkedResources",
            "linkedResources": "linkedResources",
        }
        return mapping.get(key)

    @staticmethod
    def _serialize_task_datetime(value: Any) -> Optional[Dict[str, Optional[str]]]:
        if value is None:
            return None
        if isinstance(value, TaskDateTime):
            return value.to_graph()
        if isinstance(value, dict):
            return {
                "dateTime": value.get("dateTime") or value.get("date_time"),
                "timeZone": value.get("timeZone") or value.get("time_zone"),
            }
        raise ValueError("Unsupported datetime payload for task update")

    @staticmethod
    def _serialize_body(value: Any) -> Optional[Dict[str, Optional[str]]]:
        if value is None:
            return None
        if isinstance(value, dict):
            if "content" in value:
                return {
                    "content": value.get("content"),
                    "contentType": value.get("contentType") or value.get("content_type"),
                }
        raise ValueError("Body updates must supply a mapping with content and content type")

    def _lookup_list_metadata(
        self,
        base_url: str,
        headers: Dict[str, str],
        list_id: str,
    ) -> Dict[str, Optional[str]]:
        response = self._http_get(
            f"{base_url}/me/todo/lists/{list_id}",
            headers,
            params={"$select": ",".join(self.LIST_SELECT_FIELDS)},
        )
        return {
            "list_id": response.get("id"),
            "list_name": response.get("displayName"),
            "wellknown_list_name": response.get("wellknownListName"),
        }

    @staticmethod
    def _build_headers(access_token: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

    @staticmethod
    def _resolve_base_url(client) -> str:
        base_url = getattr(getattr(client, "request_adapter", None), "base_url", None)
        base_url = base_url or "https://graph.microsoft.com/v1.0"
        return base_url.rstrip("/")

    @staticmethod
    def _redact_url(url: str) -> str:
        if not url:
            return url
        if "?" in url:
            base, _ = url.split("?", 1)
            return base
        return url
