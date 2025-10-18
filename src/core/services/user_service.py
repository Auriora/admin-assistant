from typing import List, Optional

from core.models.user import User
from core.repositories.user_repository import UserRepository


class UserService:
    """
    Service for business logic related to User entities.
    """

    def __init__(self, repository: Optional[UserRepository] = None):
        # Store the provided repository (may be None); create lazily when accessed
        self._repository = repository
        # Track whether we *should* own the repository if we create one lazily
        self._owns_repository = repository is None

    @property
    def repository(self) -> UserRepository:
        """Lazily return or create the underlying repository."""
        if self._repository is None:
            # Local import to avoid importing DB-backed repo at module import time
            from core.repositories.user_repository import UserRepository as _UR

            self._repository = _UR()
            # We created the repository, so we own it
            self._owns_repository = True
        return self._repository

    @repository.setter
    def repository(self, value: UserRepository) -> None:
        self._repository = value
        # If caller injects a repository, we don't own it
        self._owns_repository = False

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Retrieve a User by its ID."""
        return self.repository.get_by_id(user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        """Retrieve a User by email address."""
        return self.repository.get_by_email(email)

    def get_by_username(self, username: str) -> Optional[User]:
        """Retrieve a User by username."""
        return self.repository.get_by_username(username)

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

        # Validate username uniqueness if provided
        username = getattr(user, "username", None)
        if username:
            username = str(username).strip()
            if not username:
                raise ValueError("Username cannot be empty or whitespace.")

            # Check for existing user with same username (excluding current user)
            existing_user = self.repository.get_by_username(username)
            if existing_user and existing_user.id != getattr(user, "id", None):
                raise ValueError(f"Username '{username}' is already taken.")

        # Add further validation as needed

    def close(self) -> None:
        """Close the repository if we own it and it has been created."""
        if self._owns_repository and self._repository is not None:
            try:
                self._repository.close()
            except Exception:
                # Don't raise during normal close
                pass

    def __del__(self):
        """Ensure repository is closed when service is garbage collected."""
        try:
            self.close()
        except Exception:
            # Ignore errors during garbage collection
            pass
