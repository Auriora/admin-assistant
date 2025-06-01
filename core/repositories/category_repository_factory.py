from typing import Any, Optional

from sqlalchemy.orm import Session

from core.models.user import User
from core.repositories.category_repository import SQLAlchemyCategoryRepository
from core.repositories.category_repository_base import BaseCategoryRepository
from core.repositories.category_repository_msgraph import MSGraphCategoryRepository


class CategoryRepositoryFactory:
    """
    Factory for creating CategoryRepository instances based on backend type.
    """

    @staticmethod
    def create(backend: str, **kwargs) -> BaseCategoryRepository:
        user = kwargs.get("user")
        if not user:
            raise ValueError("user must be provided for all category repositories.")

        if backend == "local":
            session: Session = kwargs.get("session")
            return SQLAlchemyCategoryRepository(user, session)
        elif backend == "msgraph":
            msgraph_client = kwargs.get("msgraph_client")
            if not msgraph_client:
                raise ValueError("msgraph_client must be provided for msgraph backend.")
            return MSGraphCategoryRepository(msgraph_client, user)
        else:
            raise ValueError(f"Unknown backend: {backend}")


def get_category_repository(
    user: User,
    store: str = "local",
    msgraph_client: Optional[Any] = None,
    session: Optional[Any] = None,
) -> BaseCategoryRepository:
    """
    Factory function to instantiate the appropriate CategoryRepository.

    Args:
        user (User): The user for whom the repository is created.
        store (str): The store type: 'local' or 'msgraph'.
        msgraph_client (Optional[Any]): MS Graph client for msgraph store.
        session (Optional[Any]): SQLAlchemy session for local store.

    Returns:
        BaseCategoryRepository: An instance of the appropriate CategoryRepository.
    """
    if store == "local":
        return CategoryRepositoryFactory.create("local", user=user, session=session)
    elif store == "msgraph":
        if msgraph_client is None:
            raise ValueError("msgraph_client must be provided for msgraph store.")
        return CategoryRepositoryFactory.create(
            "msgraph", user=user, msgraph_client=msgraph_client
        )
    else:
        raise ValueError(f"Unknown store: {store}. Must be 'local' or 'msgraph'.")
