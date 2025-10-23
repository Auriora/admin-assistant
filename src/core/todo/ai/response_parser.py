"""Parse AI responses into structured deduplication decisions."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Iterable, List, Tuple

from core.todo.models import DedupDecision


logger = logging.getLogger(__name__)


class DedupResponseParser:
    """Convert raw model JSON into `DedupDecision` objects."""

    BASE_ACTIONS = {"keep", "delete", "merge"}

    def parse(
        self,
        ai_payload: str,
        task_entries: Iterable[Dict[str, Any]],
    ) -> Tuple[Dict[str, DedupDecision], List[str]]:
        entries = list(task_entries)
        decisions: Dict[str, DedupDecision] = {}
        errors: List[str] = []

        if not ai_payload:
            return decisions, ["Empty response from model"]

        try:
            data = json.loads(self._strip_code_fence(ai_payload))
        except json.JSONDecodeError as exc:
            return decisions, [f"Invalid JSON: {exc}"]

        decision_list = data.get("decisions")
        if not isinstance(decision_list, list):
            return decisions, ["Missing 'decisions' array"]

        seen_indices: set[int] = set()
        for decision_data in decision_list:
            if not isinstance(decision_data, dict):
                errors.append("Decision entry is not an object")
                continue

            index = decision_data.get("index")
            if not isinstance(index, int) or index < 0 or index >= len(entries):
                errors.append(f"Invalid index: {index}")
                continue
            if index in seen_indices:
                errors.append(f"Duplicate index {index}")
                continue
            seen_indices.add(index)

            raw_action = str(decision_data.get("action", "")).strip()
            if not raw_action:
                errors.append(f"Index {index} missing action")
                continue

            normalized_action = raw_action.lower()
            target_list = decision_data.get("target_list")
            merged_title = decision_data.get("merged_title")
            rationale = str(decision_data.get("rationale") or "").strip()
            comment = str(decision_data.get("comment") or "").strip()

            if normalized_action.startswith("move:"):
                _, _, list_name = raw_action.partition(":")
                if list_name.strip():
                    target_list = list_name.strip()
                normalized_action = "move"

            if normalized_action not in self.BASE_ACTIONS and normalized_action != "move":
                errors.append(f"Unsupported action '{raw_action}' at index {index}")
                continue

            if normalized_action == "merge" and not merged_title:
                errors.append(f"Merge action missing merged_title at index {index}")
                continue

            if normalized_action == "move":
                if not isinstance(target_list, str) or not target_list.strip():
                    errors.append(f"Move action missing target_list at index {index}")
                    continue
                target_list = target_list.strip()

            if rationale and len(rationale) > 120:
                rationale = rationale[:117].rstrip() + "…"
            if not rationale:
                rationale = f"AI chose {normalized_action}"

            if comment and len(comment) > 80:
                comment = comment[:77].rstrip() + "…"
            if not comment:
                comment = f"AI {normalized_action}"

            entry = entries[index]
            task = entry["task"]
            task_key = entry["task_key"]
            orig_index = entry["cluster_index"]

            decisions[task_key] = DedupDecision(
                task_key=task_key,
                cluster_index=orig_index,
                raw_action=raw_action,
                source="ai",
                rationale=rationale,
                comment=comment,
                merged_title=merged_title if normalized_action == "merge" else None,
                target_list=target_list if normalized_action == "move" else None,
            )

        if errors:
            logger.debug("AI response parse errors: %s", errors)

        return decisions, errors

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("```"):
            content = stripped.split("\n", 1)[1] if "\n" in stripped else ""
            if content.endswith("```"):
                content = content[: -3]
            return content.strip()
        return stripped

