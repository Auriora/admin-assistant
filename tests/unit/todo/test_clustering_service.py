from core.todo.config import TodoDedupConfig
from core.todo.services import TaskClusteringService


def test_cluster_tasks_groups_similar_titles() -> None:
    config = TodoDedupConfig(fuzzy_score_threshold=82)
    service = TaskClusteringService(config)

    tasks = [
        {"title": "Follow up with Contoso", "body": "Email Alan about pricing"},
        {"title": "Follow-up with Contoso", "body": "email alan re pricing"},
        {"title": "Prepare quarterly report", "body": "Compile slide deck"},
    ]

    clusters = service.cluster_tasks(tasks)

    assert clusters, "Expected clusters to be generated"
    assert clusters[0].indices == [0, 1]
    assert clusters[0].size == 2
    assert clusters[1].indices == [2]


def test_cluster_tasks_respects_threshold() -> None:
    config = TodoDedupConfig(fuzzy_score_threshold=95)
    service = TaskClusteringService(config)

    tasks = [
        {"title": "Email Contoso", "body": ""},
        {"title": "Email Tailspin", "body": ""},
    ]

    clusters = service.cluster_tasks(tasks, include_singletons=False)

    assert clusters == []

