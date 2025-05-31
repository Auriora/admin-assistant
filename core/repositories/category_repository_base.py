from abc import ABC, abstractmethod
from typing import List, Optional
from core.models.category import Category
from core.models.user import User


class BaseCategoryRepository(ABC):
    def __init__(self, user: User):
        self.user = user

    @abstractmethod
    def get_by_id(self, category_id: str) -> Optional[Category]:
        """Retrieve a category by its ID."""
        pass

    @abstractmethod
    def add(self, category: Category) -> None:
        """Add a new category."""
        pass

    @abstractmethod
    def list(self) -> List[Category]:
        """List all categories for the repository's user."""
        pass

    @abstractmethod
    def update(self, category: Category) -> None:
        """Update an existing category."""
        pass

    @abstractmethod
    def delete(self, category_id: str) -> None:
        """Delete a category by its ID."""
        pass

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Category]:
        """Get a category by name for the repository's user."""
        pass
