from core.todo.models import DedupDecision, TaskCluster
from core.todo.services import ExactDuplicateService


def test_exact_duplicate_service_marks_duplicates() -> None:
    service = ExactDuplicateService()
    cluster = TaskCluster(cluster_id=1, indices=[0, 1, 2])

    tasks = [
        {
            "id": "task-1",
            "title": "Follow up with Contoso",
            "body": "Send recap email",
            "task_list": "Clients",
            "row_index": 1,
        },
        {
            "id": "task-2",
            "title": "Follow up with Contoso",
            "body": "Send recap email",
            "task_list": "Clients",
            "row_index": 2,
        },
        {
            "id": "task-3",
            "title": "Book travel",
            "body": "Reserve flight",
            "task_list": "Personal",
        },
    ]

    decisions = service.detect_exact_duplicates(tasks, cluster=cluster)

    assert "task-2" in decisions
    duplicate = decisions["task-2"]
    assert isinstance(duplicate, DedupDecision)
    assert duplicate.cluster_id == 1
    assert duplicate.cluster_size == 3
    assert duplicate.raw_action == "delete"
    assert duplicate.canonical_cluster_index == 0

    assert "task-1" not in decisions
    assert "task-3" not in decisions

