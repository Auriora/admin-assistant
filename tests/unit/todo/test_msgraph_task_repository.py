from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict

import pytest

from core.todo.models import Task
from core.todo.repositories.msgraph_task_repository import (
    MSGraphTaskRepository,
    MSGraphTaskRepositoryError,
)


@pytest.fixture
def user() -> SimpleNamespace:
    return SimpleNamespace(id=1, email="user@example.com")


@pytest.fixture
def repository() -> MSGraphTaskRepository:
    return MSGraphTaskRepository()


def test_list_all_tasks_handles_pagination(repository: MSGraphTaskRepository, user: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    lists_response = {"value": [{"id": "list1", "displayName": "Tasks", "wellknownListName": None}]}

    first_page = {
        "value": [
            {
                "id": "task1",
                "title": "First",
                "status": "notStarted",
                "importance": "normal",
                "hasAttachments": False,
                "isReminderOn": False,
                "categories": [],
                "createdDateTime": "2025-10-21T12:00:00Z",
                "lastModifiedDateTime": "2025-10-21T12:00:00Z",
                "linkedResources": [],
            }
        ],
        "@odata.nextLink": "https://graph.microsoft.com/v1.0/me/todo/lists/list1/tasks?$skip=1",
    }

    second_page = {
        "value": [
            {
                "id": "task2",
                "title": "Second",
                "status": "inProgress",
                "importance": "high",
                "hasAttachments": True,
                "isReminderOn": True,
                "categories": ["Work"],
                "createdDateTime": "2025-10-22T09:00:00Z",
                "lastModifiedDateTime": "2025-10-22T10:00:00Z",
                "linkedResources": [],
            }
        ]
    }

    def fake_http_get(url: str, headers: Dict[str, str], params: Dict[str, str] | None = None):
        if url.endswith("/me/todo/lists"):
            assert params["$select"] == "id,displayName,wellknownListName"
            return lists_response
        if url.endswith("/me/todo/lists/list1/tasks"):
            assert params["$top"] == str(repository.DEFAULT_TOP)
            return first_page
        if url.startswith("https://graph.microsoft.com/v1.0/me/todo/lists/list1/tasks?$skip=1"):
            return second_page
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(repository, "_http_get", fake_http_get)

    tasks = repository.list_all_tasks(user, "token")
    assert len(tasks) == 2
    assert [task.task_id for task in tasks] == ["task1", "task2"]
    assert all(task.list_id == "list1" for task in tasks)


def test_list_all_tasks_enriches_flagged_email(repository: MSGraphTaskRepository, user: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    lists_response = {
        "value": [
            {
                "id": "flag",
                "displayName": "Flagged Emails",
                "wellknownListName": "flaggedEmails",
            }
        ]
    }

    flagged_task = {
        "id": "task-flag",
        "title": "Follow up",
        "status": "notStarted",
        "createdDateTime": "2025-10-21T09:00:00Z",
        "lastModifiedDateTime": "2025-10-21T10:00:00Z",
        "linkedResources": [
            {
                "id": "res1",
                "applicationName": "Outlook",
                "displayName": "Email subject",
                "externalId": "MSG123",
                "webUrl": None,
            }
        ],
    }

    message_payload = {
        "bodyPreview": "Preview body",
        "body": {"content": "<p>Body</p>", "contentType": "html"},
        "webLink": "https://outlook.office.com/mail/MSG123",
    }

    def fake_http_get(url: str, headers: Dict[str, str], params: Dict[str, str] | None = None):
        if url.endswith("/me/todo/lists"):
            return lists_response
        if url.endswith("/me/todo/lists/flag/tasks"):
            return {"value": [flagged_task]}
        if url.endswith("/me/messages/MSG123"):
            assert params == {"$select": "bodyPreview,body,webLink"}
            return message_payload
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(repository, "_http_get", fake_http_get)

    tasks = repository.list_all_tasks(user, "token")
    assert len(tasks) == 1
    task = tasks[0]
    assert task.body_preview is None
    assert task.linked_resources
    resource = task.linked_resources[0]
    assert resource.preview == "Preview body"
    assert resource.body == "<p>Body</p>"
    assert resource.web_url == "https://outlook.office.com/mail/MSG123"


def make_task(task_id: str = "task1", list_id: str = "list1") -> Task:
    return Task(
        task_id=task_id,
        list_id=list_id,
        title="Original",
        status="notStarted",
        importance="normal",
        has_attachments=False,
        is_reminder_on=False,
        categories=[],
        created_datetime=datetime.now(),
        last_modified_datetime=datetime.now(),
        completed_datetime=None,
        due_date_time=None,
        start_date_time=None,
        reminder_date_time=None,
        body_content=None,
        body_content_type=None,
        body_preview=None,
        etag="etag123",
        list_name="Tasks",
        wellknown_list_name=None,
        linked_resources=[],
        raw={},
    )


def test_update_task_sends_patch_payload(repository: MSGraphTaskRepository, user: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: Dict[str, Dict[str, str] | Dict[str, str] | Dict[str, Any]] = {}

    def fake_http_patch(url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> None:
        captured["url"] = url
        captured["headers"] = headers
        captured["payload"] = payload

    refreshed_payload = {
        "id": "task1",
        "title": "Updated",
        "status": "inProgress",
        "importance": "high",
        "hasAttachments": False,
        "isReminderOn": False,
        "categories": [],
        "createdDateTime": "2025-10-21T12:00:00Z",
        "lastModifiedDateTime": "2025-10-21T12:30:00Z",
        "linkedResources": [],
    }

    monkeypatch.setattr(repository, "_http_patch", fake_http_patch)
    monkeypatch.setattr(repository, "_http_get", lambda url, headers, params=None: refreshed_payload)

    task = make_task()
    updated = repository.update_task(
        user,
        "token",
        task,
        changes={"title": "Updated", "status": "inProgress"},
    )

    assert "payload" in captured
    assert captured["payload"] == {"title": "Updated", "status": "inProgress"}
    assert captured["headers"]["If-Match"] == "etag123"
    assert updated.title == "Updated"
    assert updated.status == "inProgress"


def test_update_task_raises_on_graph_error(repository: MSGraphTaskRepository, user: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_http_patch(url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> None:
        raise MSGraphTaskRepositoryError("Failed")

    monkeypatch.setattr(repository, "_http_patch", fake_http_patch)

    task = make_task()

    with pytest.raises(MSGraphTaskRepositoryError):
        repository.update_task(
            user,
            "token",
            task,
            changes={"title": "Updated"},
        )
