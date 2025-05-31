from typing import List, Optional
from core.models.category import Category
from core.models.user import User
from core.db import SessionLocal
from .category_repository_base import BaseCategoryRepository


class SQLAlchemyCategoryRepository(BaseCategoryRepository):
    """
    Repository for managing Category entities.
    """
    def __init__(self, user: User, session=None):
        super().__init__(user)
        self.session = session or SessionLocal()

    def get_by_id(self, category_id: str) -> Optional[Category]:
        """Retrieve a category by its ID."""
        # For SQLAlchemy, convert string ID to int
        try:
            int_id = int(category_id)
            return self.session.get(Category, int_id)
        except (ValueError, TypeError):
            return None

    def add(self, category: Category) -> None:
        """Add a new category."""
        self.session.add(category)
        self.session.commit()

    def list(self) -> List[Category]:
        """List all categories for the repository's user."""
        return self.session.query(Category).filter_by(user_id=self.user.id).all()

    def update(self, category: Category) -> None:
        """Update an existing category."""
        self.session.merge(category)
        self.session.commit()

    def delete(self, category_id: str) -> None:
        """Delete a category by its ID."""
        category = self.get_by_id(category_id)
        if category:
            self.session.delete(category)
            self.session.commit()

    def get_by_name(self, name: str) -> Optional[Category]:
        """Get a category by name for the repository's user."""
        return self.session.query(Category).filter_by(name=name, user_id=self.user.id).first()

    # Legacy method for backward compatibility
    def list_by_user(self, user_id: int) -> List[Category]:
        """List all categories for a given user (legacy method)."""
        return self.session.query(Category).filter_by(user_id=user_id).all()

    def get_by_name_and_user(self, name: str, user_id: int) -> Optional[Category]:
        """Get a category by name and user ID (legacy method)."""
        return self.session.query(Category).filter_by(name=name, user_id=user_id).first()
