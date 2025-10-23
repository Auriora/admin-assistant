"""Service layer components for Microsoft To Do deduplication."""

from .clustering_service import TaskClusteringService  # noqa: F401
from .duplicate_scoring import DuplicatePriorityScorer  # noqa: F401
from .exact_duplicate_service import ExactDuplicateService  # noqa: F401

__all__ = [
    "TaskClusteringService",
    "DuplicatePriorityScorer",
    "ExactDuplicateService",
]

