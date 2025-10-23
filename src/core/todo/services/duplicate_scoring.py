"""Priority scoring helpers for duplicate resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Tuple

from core.todo.models import Task


def _get(task: Any, key: str, default: Any = None) -> Any:
    """Generic attribute/dict accessor."""

    if isinstance(task, Task):
        if hasattr(task, key):
            return getattr(task, key)
        return task.raw.get(key, default)
    if isinstance(task, Mapping):
        return task.get(key, default)
    return getattr(task, key, default)


@dataclass(slots=True)
class DuplicatePriorityScorer:
    """Calculate ordering preference when selecting canonical tasks."""

    GENERIC_LISTS = {
        "Tasks",
        "Tasks From Meetings",
        "Flagged Emails",
    }

    def score(self, task: Any) -> Tuple[int, int, int]:
        """Return a tuple used to rank a task within a duplicate group."""

        score = 0
        list_score = 0

        task_list = str(_get(task, "task_list", "") or "")
        owner = str(_get(task, "owner_hint", "") or "")

        if task_list and task_list not in self.GENERIC_LISTS:
            list_score += 2

        if owner and "@" in owner:
            domain = owner.split("@", 1)[1].lower()
            company = domain.split(".")[0]
            if company and company in task_list.lower():
                list_score += 4

        if owner and task_list == "Tasks From Meetings":
            list_score -= 1

        if _get(task, "due") or _get(task, "due_date_time"):
            score += 3

        reminder = str(_get(task, "is_reminder_on", "") or "").lower()
        if reminder in {"true", "1", "yes"}:
            score += 2

        importance = str(_get(task, "importance", "") or "").lower()
        if importance == "high":
            score += 1

        row_index = _get(task, "row_index", 0) or 0

        return score, list_score, -int(row_index)

