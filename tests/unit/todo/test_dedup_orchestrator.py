from types import SimpleNamespace

from core.todo.ai import AIDeduplicationService
from core.todo.config import TodoDedupConfig
from core.todo.models import TaskCluster


class _FakeChatCompletions:
    def __init__(self, response: str) -> None:
        self._response = response
        self.last_request = None

    def create(self, **kwargs):
        self.last_request = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self._response))]
        )


class _FakeOpenAIClient:
    def __init__(self, response: str) -> None:
        self.chat = SimpleNamespace(completions=_FakeChatCompletions(response))


def test_ai_dedup_service_processes_clusters() -> None:
    response = (
        '{"decisions": ['
        '{"index": 0, "action": "keep", "target_list": null, "merged_title": null, "rationale": "leave"},'
        '{"index": 1, "action": "move", "target_list": "Clients", "merged_title": null, "rationale": "list"}'
        ']}'
    )
    client = _FakeOpenAIClient(response)
    config = TodoDedupConfig(dedup_model="gpt-4o-mini")
    service = AIDeduplicationService(config=config, openai_client=client)

    tasks = [
        {"id": "t-1", "title": "Follow up", "task_list": "Inbox"},
        {"id": "t-2", "title": "Prepare report", "task_list": "Inbox"},
    ]
    clusters = [TaskCluster(cluster_id=1, indices=[0, 1])]

    decisions = service.process_clusters(tasks=tasks, clusters=clusters, available_lists=["Inbox", "Clients"])

    assert set(decisions.keys()) == {"t-1", "t-2"}
    assert decisions["t-2"].target_list == "Clients"
    assert client.chat.completions.last_request is not None


def test_ai_dedup_service_auto_duplicates_skip_model() -> None:
    client = _FakeOpenAIClient('{"decisions": []}')
    config = TodoDedupConfig(dedup_model="gpt-4o-mini")
    service = AIDeduplicationService(config=config, openai_client=client)

    tasks = [
        {"id": "t-1", "title": "Follow up", "body": "Email"},
        {"id": "t-2", "title": "Follow up", "body": "Email"},
    ]
    clusters = [TaskCluster(cluster_id=2, indices=[0, 1])]

    decisions = service.process_clusters(tasks=tasks, clusters=clusters, available_lists=["Inbox"])

    assert "t-2" in decisions and decisions["t-2"].raw_action == "delete"
    # When duplicates resolved automatically, model should not be invoked
    assert client.chat.completions.last_request is None
