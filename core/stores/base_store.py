from typing import Any, List, Optional, Dict, Tuple
from abc import ABC, abstractmethod

class BaseStore(ABC):
    """
    Abstract base class for all data stores.
    """
    @abstractmethod
    def add(self, obj: Any) -> None:
        """Add a new object to the store."""
        pass

    @abstractmethod
    def get(self, id: Any) -> Optional[Any]:
        """Retrieve an object by its ID."""
        pass

    @abstractmethod
    def list(self, filters: Optional[Dict] = None, page: int = 1, page_size: int = 100) -> Tuple[List[Any], int]:
        """List objects with optional filtering and paging. Returns (results, total_count)."""
        pass

    @abstractmethod
    def update(self, obj: Any) -> None:
        """Update an existing object in the store."""
        pass

    @abstractmethod
    def delete(self, id: Any) -> None:
        """Delete an object by its ID."""
        pass 