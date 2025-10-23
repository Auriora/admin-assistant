"""Prompt construction utilities for To Do deduplication."""

from __future__ import annotations

import json
import textwrap
from typing import Any, Dict, Iterable, Sequence

from core.todo.config import TodoDedupConfig


def _truncate(value: str, limit: int) -> str:
    clean = " ".join(value.split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"


class PromptBuilder:
    """Build prompts for To Do deduplication clusters."""

    BODY_SNIPPET_LENGTH = 160
    LINK_PREVIEW_LENGTH = 120

    _DEFAULT_SYSTEM_PROMPT = (
        "You are an expert Microsoft To Do cleanup assistant. "
        "Return ONLY the JSON decisions requested."
    )

    _DEFAULT_TEMPLATE = textwrap.dedent(
        """
        You are assisting with deduplicating Microsoft To Do tasks. You are given a list of candidate tasks with concise metadata and a JSON array to compare. Review the provided tasks and return a single JSON object describing a decision for each input item. Follow these rules exactly.

        1. Output format
           - Return only JSON, nothing else.
           - Top-level object: `decisions`: array of objects.
           - Each decision object must contain:
             - `index` (integer): matches the input index.
             - `action` (string): one of `keep`, `merge`, `delete`, `move`.
             - `target_list` (string or null): null or an exact string from `available_lists`.
             - `merged_title` (string or null): populated only for `merge` and ≤250 chars.
             - `rationale` (string): ≤120 chars, plain English, no confidential text.

        2. Determinism and safety
           - Use provided `available_lists` exactly; do not invent new list names.
           - Prefer the least-destructive action when uncertain.
           - `move` and `merge` are mutually exclusive.
           - Do not expose raw confidential text beyond short rationales.

        3. Auto-validation
           - Before returning, ensure indices cover every input task exactly once.
           - If validation fails, return `{{"decisions": [], "error": "<reason>"}}`.

        available_lists: {available_lists}
        user_emails: {user_emails}

        Tasks (JSON array):
        {tasks_json}
        """
    ).strip()

    def __init__(self, config: TodoDedupConfig) -> None:
        self._config = config

    @property
    def system_prompt(self) -> str:
        return self._DEFAULT_SYSTEM_PROMPT

    def build_prompt(
        self,
        tasks: Sequence[Dict[str, Any]],
        available_lists: Iterable[str],
    ) -> str:
        payload = [self._task_payload(task, index) for index, task in enumerate(tasks)]

        available_lists_str = ", ".join(f'"{name}"' for name in sorted(set(available_lists)))
        user_emails_str = ", ".join(sorted(self._config.user_emails)) or "(none)"

        return self._DEFAULT_TEMPLATE.format(
            tasks_json=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            available_lists=available_lists_str,
            user_emails=user_emails_str,
        )

    def _task_payload(self, task: Dict[str, Any], index: int) -> Dict[str, Any]:
        return {
            "index": index,
            "title": _truncate(str(task.get("title") or task.get("original_title") or "Untitled"), self.BODY_SNIPPET_LENGTH),
            "list": task.get("task_list") or task.get("list_name"),
            "owner": task.get("owner_hint") or "",
            "body": _truncate(str(task.get("body") or task.get("body_content") or ""), self.BODY_SNIPPET_LENGTH),
            "due": task.get("due") or task.get("due_date_time"),
            "is_reminder_on": task.get("is_reminder_on"),
            "linked_message_preview": _truncate(str(task.get("linked_message_preview") or ""), self.LINK_PREVIEW_LENGTH),
        }
