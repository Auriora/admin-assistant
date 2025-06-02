from typing import List, Optional

from core.db import SessionLocal
from core.models.user import User


class UserRepository:
    """
    Repository for managing User entities.
    """

    def __init__(self, session=None):
        self.session = session or SessionLocal()

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Retrieve a User by its ID."""
        return self.session.get(User, user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        """Retrieve a User by email address."""
        return self.session.query(User).filter_by(email=email).first()

    def add(self, user: User) -> None:
        """Add a new User."""
        self.session.add(user)
        self.session.commit()

    def list(self, is_active: Optional[bool] = None) -> List[User]:
        """List all users, optionally filtered by is_active."""
        query = self.session.query(User)
        if is_active is not None:
            query = query.filter_by(is_active=is_active)
        return query.all()

    def update(self, user: User) -> None:
        """Update an existing User."""
        self.session.merge(user)
        self.session.commit()

    def delete(self, user_id: int) -> None:
        """Delete a User by its ID."""
        user = self.get_by_id(user_id)
        if user:
            self.session.delete(user)
            self.session.commit()
