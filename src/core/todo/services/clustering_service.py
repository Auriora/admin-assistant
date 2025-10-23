"""Services for grouping similar Microsoft To Do tasks."""

from __future__ import annotations

from typing import Any, Iterable, List, Sequence

from core.todo.config import TodoDedupConfig
from core.todo.models import Task, TaskCluster

try:  # pragma: no cover - import failure handled in runtime path
    from rapidfuzz import fuzz
except ImportError as exc:  # pragma: no cover - should be caught via tests
    raise RuntimeError("rapidfuzz is required for TaskClusteringService") from exc


def _get_text(task: Any, keys: Iterable[str]) -> str:
    """Return the first non-empty text found for the provided keys."""

    for key in keys:
        value = None
        if isinstance(task, Task) and hasattr(task, key):
            value = getattr(task, key)
        elif isinstance(task, dict):
            value = task.get(key)
        elif hasattr(task, key):
            value = getattr(task, key)
        else:
            raw = getattr(task, "raw", {})
            if isinstance(raw, dict):
                value = raw.get(key)
        if value:
            text = str(value).strip()
            if text:
                return text
    return ""


class TaskClusteringService:
    """Cluster tasks using fuzzy matching heuristics."""

    def __init__(self, config: TodoDedupConfig | None = None):
        self._config = config or TodoDedupConfig.from_env()

    @property
    def config(self) -> TodoDedupConfig:
        """Return the active configuration."""

        return self._config

    def cluster_tasks(
        self,
        tasks: Sequence[Any],
        *,
        threshold: int | None = None,
        include_singletons: bool = True,
        use_body: bool = True,
    ) -> List[TaskCluster]:
        """Group tasks into clusters of similar titles/bodies."""

        if not tasks:
            return []

        effective_threshold = threshold or self.config.fuzzy_score_threshold

        titles = []
        bodies = []
        for task in tasks:
            title = _get_text(task, ("original_title", "title", "body_preview"))
            body = _get_text(task, ("body", "body_content", "summary")) if use_body else ""
            titles.append(title)
            bodies.append(body[:200] if body else "")

        visited: set[int] = set()
        clusters: List[TaskCluster] = []

        for index, title in enumerate(titles):
            if index in visited:
                continue

            member_indices = [index]
            for candidate_index in range(index + 1, len(titles)):
                if candidate_index in visited:
                    continue

                title_score = fuzz.partial_ratio(title, titles[candidate_index])
                if not use_body:
                    combined_score = title_score
                else:
                    body_score = 0
                    if bodies[index] and bodies[candidate_index]:
                        body_score = fuzz.partial_ratio(bodies[index], bodies[candidate_index])
                    combined_score = int(0.7 * title_score + 0.3 * body_score)
                    combined_score = max(combined_score, title_score)

                if combined_score >= effective_threshold:
                    member_indices.append(candidate_index)

            if len(member_indices) > 1:
                visited.update(member_indices)
                clusters.append(TaskCluster(cluster_id=len(clusters) + 1, indices=member_indices))
            elif include_singletons:
                visited.add(index)
                clusters.append(TaskCluster(cluster_id=len(clusters) + 1, indices=member_indices))

        return clusters

