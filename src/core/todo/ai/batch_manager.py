"""Batch API helpers for OpenAI-based deduplication workflows."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


logger = logging.getLogger(__name__)


def token_parameter_for_model(model: str) -> str:
    model_lower = model.lower()
    if model_lower.startswith("gpt-5"):
        return "max_output_tokens"
    if model_lower.startswith("o1"):
        return "max_completion_tokens"
    return "max_tokens"


def uses_responses_api(model: str) -> bool:
    return model.lower().startswith("gpt-5")


class BatchRequestBuilder:
    """Build JSONL batches for OpenAI."""

    def __init__(self) -> None:
        self._requests: List[Dict[str, Any]] = []
        self._endpoint: Optional[str] = None

    def add_request(
        self,
        *,
        custom_id: str,
        model: str,
        messages: Iterable[Dict[str, str]],
        max_tokens: int,
        temperature: Optional[float] = None,
    ) -> None:
        messages_list = list(messages)
        token_field = token_parameter_for_model(model)

        if uses_responses_api(model):
            body: Dict[str, Any] = {
                "model": model,
                "input": messages_list,
                token_field: max_tokens,
            }
            request = {"custom_id": custom_id, "method": "POST", "url": "/v1/responses", "body": body}
        else:
            body = {
                "model": model,
                "messages": messages_list,
                token_field: max_tokens,
            }
            if temperature is not None:
                body["temperature"] = temperature
            request = {"custom_id": custom_id, "method": "POST", "url": "/v1/chat/completions", "body": body}

        if self._endpoint and self._endpoint != request["url"]:
            raise ValueError("Mixed endpoints within the same batch are not supported")
        self._endpoint = request["url"]
        self._requests.append(request)

    def to_jsonl(self, output_file: Path) -> None:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open("w", encoding="utf-8") as handle:
            for request in self._requests:
                handle.write(json.dumps(request) + "\n")

    def clear(self) -> None:
        self._requests.clear()
        self._endpoint = None

    @property
    def endpoint(self) -> str:
        return self._endpoint or "/v1/chat/completions"

    def __len__(self) -> int:
        return len(self._requests)


class BatchJobManager:
    """Submit and poll OpenAI batch jobs."""

    def __init__(self, client: Any, state_dir: Path) -> None:
        self._client = client
        self._state_dir = state_dir
        self._state_dir.mkdir(parents=True, exist_ok=True)

    def submit(self, input_file: Path, *, endpoint: str, description: Optional[str] = None) -> str:
        with input_file.open("rb") as handle:
            file_resource = self._client.files.create(file=handle, purpose="batch")

        batch = self._client.batches.create(
            input_file_id=file_resource.id,
            endpoint=endpoint,
            completion_window="24h",
            metadata={"description": description or "todo-dedup"},
        )

        state_file = self._state_dir / f"batch_{batch.id}.json"
        state_payload = {
            "batch_id": batch.id,
            "input_file_id": file_resource.id,
            "input_file_path": str(input_file),
            "status": batch.status,
            "endpoint": endpoint,
            "description": description,
        }
        state_file.write_text(json.dumps(state_payload), encoding="utf-8")
        return batch.id

    def wait_for_completion(self, batch_id: str, *, poll_interval: int, timeout_seconds: int) -> Dict[str, Any]:
        start = time.time()
        while True:
            batch = self._client.batches.retrieve(batch_id)
            status = getattr(batch, "status", "unknown")
            if status in {"completed", "failed", "cancelled"}:
                return batch.to_dict() if hasattr(batch, "to_dict") else dict(batch)
            if time.time() - start > timeout_seconds:
                raise TimeoutError(f"Batch {batch_id} did not complete before timeout")
            time.sleep(poll_interval)
