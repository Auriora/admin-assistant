"""Configuration helpers for To Do deduplication services."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from typing import Set


def _get_bool_env(var_name: str, default: bool) -> bool:
    """Return boolean value for an environment variable."""

    value = os.environ.get(var_name)
    if value is None:
        return default
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return default


def _get_int_env(var_name: str, default: int) -> int:
    """Return integer value for an environment variable."""

    value = os.environ.get(var_name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_str_env(var_name: str, default: str) -> str:
    """Return string value for an environment variable."""

    return os.environ.get(var_name, default).strip() or default


def _get_set_env(var_name: str) -> Set[str]:
    """Return a set parsed from a comma separated environment variable."""

    value = os.environ.get(var_name)
    if not value:
        return set()
    return {token.strip() for token in value.split(",") if token.strip()}


@dataclass(slots=True)
class TodoDedupConfig:
    """Runtime configuration for To Do deduplication services."""

    fuzzy_score_threshold: int = 86
    dedup_model: str = "gpt-4o-mini"
    dedup_max_completion_tokens: int = 2000
    batch_enabled: bool = False
    batch_poll_interval_seconds: int = 60
    batch_completion_timeout_seconds: int = 3600
    user_emails: Set[str] = field(default_factory=set)

    @classmethod
    def from_env(cls) -> "TodoDedupConfig":
        """Create configuration hydrated from environment variables."""

        return cls(
            fuzzy_score_threshold=_get_int_env("TODO_DEDUP_THRESHOLD", cls.fuzzy_score_threshold),
            dedup_model=_get_str_env("TODO_DEDUP_MODEL", cls.dedup_model),
            dedup_max_completion_tokens=_get_int_env(
                "TODO_DEDUP_MAX_COMPLETION_TOKENS", cls.dedup_max_completion_tokens
            ),
            batch_enabled=_get_bool_env("TODO_DEDUP_BATCH_ENABLED", cls.batch_enabled),
            batch_poll_interval_seconds=_get_int_env(
                "TODO_DEDUP_BATCH_POLL_INTERVAL", cls.batch_poll_interval_seconds
            ),
            batch_completion_timeout_seconds=_get_int_env(
                "TODO_DEDUP_BATCH_TIMEOUT", cls.batch_completion_timeout_seconds
            ),
            user_emails=_get_set_env("TODO_DEDUP_USER_EMAILS"),
        )


__all__ = ["TodoDedupConfig"]
