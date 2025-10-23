"""Services for exact duplicate detection within task clusters."""

from __future__ import annotations

from typing import Any, Dict, Mapping, MutableMapping, Sequence

from core.todo.models import DedupDecision, Task, TaskCluster
from .duplicate_scoring import DuplicatePriorityScorer, _get


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(str(value).lower().split())


def _task_key(task: Any) -> str:
    if isinstance(task, Task):
        if task.task_id:
            return task.task_id
        raw = task.raw
        if isinstance(raw, Mapping):
            return str(raw.get("id") or raw.get("lookup_key") or raw.get("row_index"))
    if isinstance(task, Mapping):
        return str(task.get("id") or task.get("lookup_key") or task.get("row_index"))
    if hasattr(task, "id"):
        return str(getattr(task, "id"))
    if hasattr(task, "lookup_key"):
        return str(getattr(task, "lookup_key"))
    return str(id(task))


class ExactDuplicateService:
    """Identify exact duplicates and emit canonical delete decisions."""

    def __init__(self, scorer: DuplicatePriorityScorer | None = None):
        self._scorer = scorer or DuplicatePriorityScorer()

    def detect_exact_duplicates(
        self,
        tasks: Sequence[Any],
        *,
        cluster: TaskCluster | None = None,
        original_indices: Sequence[int] | None = None,
    ) -> Dict[str, DedupDecision]:
        """Return a mapping of task keys to duplicate decisions."""

        if not tasks:
            return {}

        indices = list(original_indices or range(len(tasks)))
        signature_map: Dict[tuple[str, str], list[int]] = {}

        for idx, task in enumerate(tasks):
            title = _normalize_text(_get(task, "original_title") or _get(task, "title"))
            body = _normalize_text(
                _get(task, "body")
                or _get(task, "body_content")
                or _get(task, "summary")
            )
            signature_map.setdefault((title, body), []).append(idx)

        decisions: Dict[str, DedupDecision] = {}

        for matching_indices in signature_map.values():
            if len(matching_indices) <= 1:
                continue

            canonical_index = max(matching_indices, key=lambda idx: self._scorer.score(tasks[idx]))
            canonical_task = tasks[canonical_index]
            canonical_row = _get(canonical_task, "row_index")
            canonical_list = _get(canonical_task, "task_list")

            for duplicate_index in matching_indices:
                if duplicate_index == canonical_index:
                    continue
                task = tasks[duplicate_index]
                key = _task_key(task)
                rationale = f"Auto delete exact duplicate of cluster index {canonical_index}"
                decisions[key] = DedupDecision(
                    task_key=key,
                    cluster_index=int(indices[duplicate_index]),
                    raw_action="delete",
                    source="auto",
                    rationale=rationale,
                    comment="Auto duplicate",
                    cluster_id=cluster.cluster_id if cluster else None,
                    cluster_size=cluster.size if cluster else None,
                    canonical_cluster_index=int(indices[canonical_index]),
                    canonical_row_index=canonical_row,
                    canonical_list=canonical_list,
                )

        return decisions

