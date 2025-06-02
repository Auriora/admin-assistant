from typing import List, Optional

from core.models.user import User
from core.repositories.user_repository import UserRepository


class UserService:
    """
    Service for business logic related to User entities.
    """

    def __init__(self, repository: Optional[UserRepository] = None):
        self.repository = repository or UserRepository()

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Retrieve a User by its ID."""
        return self.repository.get_by_id(user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        """Retrieve a User by email address."""
        return self.repository.get_by_email(email)

    def create(self, user: User) -> None:
        """Create a new User after validation."""
        self.validate(user)
        self.repository.add(user)

    def list(self, is_active: Optional[bool] = None) -> List[User]:
        """List all users, optionally filtered by is_active."""
        return self.repository.list(is_active=is_active)

    def update(self, user: User) -> None:
        """Update an existing User after validation."""
        self.validate(user)
        self.repository.update(user)

    def delete(self, user_id: int) -> None:
        """Delete a User by its ID."""
        self.repository.delete(user_id)

    def validate(self, user: User) -> None:
        """
        Validate User fields. Raises ValueError if invalid.
        """
        email = getattr(user, "email", None)
        if not email or not str(email).strip():
            raise ValueError("User email is required.")
        # Add further validation as needed
