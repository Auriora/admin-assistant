"""AI-assisted deduplication orchestration service."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Iterable, List, Mapping, MutableSequence, Optional

from core.todo.config import TodoDedupConfig
from core.todo.models import DedupDecision, TaskCluster
from core.todo.services import ExactDuplicateService
from .prompt_builder import PromptBuilder
from .response_parser import DedupResponseParser

try:  # pragma: no cover - optional dependency
    from opentelemetry import trace
except ImportError:  # pragma: no cover - OTEL optional
    trace = None  # type: ignore


logger = logging.getLogger(__name__)


def _task_key(task: Mapping[str, Any]) -> str:
    return str(
        task.get("id")
        or task.get("task_id")
        or task.get("lookup_key")
        or task.get("row_index")
    )


class AIDeduplicationService:
    """Coordinate auto-deduplication and AI-backed decisions."""

    def __init__(
        self,
        *,
        config: Optional[TodoDedupConfig] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        parser: Optional[DedupResponseParser] = None,
        exact_duplicate_service: Optional[ExactDuplicateService] = None,
        openai_client: Any = None,
    ) -> None:
        self._config = config or TodoDedupConfig.from_env()
        self._prompt_builder = prompt_builder or PromptBuilder(self._config)
        self._parser = parser or DedupResponseParser()
        self._exact_duplicates = exact_duplicate_service or ExactDuplicateService()
        self._client = openai_client or self._create_openai_client()
        self._tracer = trace.get_tracer(__name__) if trace else None

    def process_clusters(
        self,
        *,
        tasks: List[Mapping[str, Any]],
        clusters: Iterable[TaskCluster],
        available_lists: Iterable[str],
    ) -> Dict[str, DedupDecision]:
        decisions: Dict[str, DedupDecision] = {}
        available_lists_list = list(available_lists)

        for cluster in clusters:
            span_ctx = (
                self._tracer.start_as_current_span("todo.ai_dedup_cluster", attributes={"cluster.id": cluster.cluster_id})
                if self._tracer
                else None
            )
            with span_ctx if span_ctx else _NullContext():
                cluster_decisions = self._process_cluster(
                    tasks=tasks,
                    cluster=cluster,
                    available_lists=available_lists_list,
                )
                decisions.update(cluster_decisions)

        return decisions

    def _process_cluster(
        self,
        *,
        tasks: List[Mapping[str, Any]],
        cluster: TaskCluster,
        available_lists: List[str],
    ) -> Dict[str, DedupDecision]:
        cluster_tasks = [tasks[index] for index in cluster.indices]

        # Auto-detect exact duplicates first
        auto_decisions = self._exact_duplicates.detect_exact_duplicates(
            cluster_tasks,
            cluster=cluster,
            original_indices=cluster.indices,
        )

        handled_keys = set(auto_decisions.keys())

        remaining_entries: List[Dict[str, Any]] = []
        for local_index, global_index in enumerate(cluster.indices):
            task = tasks[global_index]
            key = _task_key(task)
            if key in handled_keys:
                continue
            remaining_entries.append(
                {
                    "task": task,
                    "task_key": key,
                    "cluster_index": global_index,
                }
            )

        if len(remaining_entries) <= 1:
            for entry in remaining_entries:
                key = entry["task_key"]
                auto_decisions[key] = DedupDecision(
                    task_key=key,
                    cluster_index=entry["cluster_index"],
                    raw_action="keep",
                    source="auto",
                    rationale="Auto keep task",
                    comment="Auto keep",
                    cluster_id=cluster.cluster_id,
                    cluster_size=cluster.size,
                )
            return auto_decisions

        # Prepare prompt for AI decisions
        prompt_tasks = [entry["task"] for entry in remaining_entries]
        prompt = self._prompt_builder.build_prompt(prompt_tasks, available_lists)

        messages = [
            {"role": "system", "content": self._prompt_builder.system_prompt},
            {"role": "user", "content": prompt},
        ]

        response_content = self._invoke_model(messages=messages)

        ai_decisions, errors = self._parser.parse(response_content, remaining_entries)

        if errors:
            logger.warning("AI dedup parser reported issues: %s", errors)

        for decision in ai_decisions.values():
            decision.cluster_id = cluster.cluster_id
            decision.cluster_size = cluster.size

        auto_decisions.update(ai_decisions)
        return auto_decisions

    def _invoke_model(self, *, messages: List[Dict[str, str]]) -> str:
        completion = self._client.chat.completions.create(
            model=self._config.dedup_model,
            messages=messages,
            max_tokens=self._config.dedup_max_completion_tokens,
        )
        choice = completion.choices[0]
        message = getattr(choice, "message", choice["message"] if isinstance(choice, Mapping) else None)
        content = getattr(message, "content", None)
        if content is None and isinstance(message, Mapping):
            content = message.get("content")
        if content is None:
            raise ValueError("Model response missing message content")
        return content

    def _create_openai_client(self) -> Any:
        try:
            import openai  # type: ignore
        except ImportError as exc:  # pragma: no cover - runtime guard
            raise RuntimeError("openai package is required for AIDeduplicationService") from exc

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable required for dedup service")

        return openai.OpenAI(api_key=api_key)


class _NullContext:
    def __enter__(self) -> None:  # pragma: no cover - minimal helper
        return None

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover
        return None

