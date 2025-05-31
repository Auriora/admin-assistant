from typing import List, Optional
from core.models.category import Category
from core.repositories.category_repository_base import BaseCategoryRepository


class CategoryService:
    """
    Service for business logic related to Category entities.
    """
    def __init__(self, repository: BaseCategoryRepository):
        self.repository = repository

    def get_by_id(self, category_id: str) -> Optional[Category]:
        """Retrieve a category by its ID."""
        return self.repository.get_by_id(category_id)

    def create(self, category: Category) -> None:
        """Create a new category after validation."""
        self.validate(category)
        self.repository.add(category)

    def list(self) -> List[Category]:
        """List all categories for the repository's user."""
        return self.repository.list()

    def update(self, category: Category) -> None:
        """Update an existing category after validation."""
        self.validate(category)
        self.repository.update(category)

    def delete(self, category_id: str) -> None:
        """Delete a category by its ID."""
        self.repository.delete(category_id)

    def get_by_name(self, name: str) -> Optional[Category]:
        """Get a category by name for the repository's user."""
        return self.repository.get_by_name(name)

    def validate(self, category: Category) -> None:
        """Validate a category before saving."""
        if not category.name or not category.name.strip():
            raise ValueError("Category name is required")
        
        if not category.user_id:
            raise ValueError("User ID is required")
        
        # Check for duplicate names for the same user
        existing = self.get_by_name(category.name.strip())
        if existing and getattr(existing, 'id', None) != getattr(category, 'id', None):
            raise ValueError(f"Category with name '{category.name}' already exists for this user")
