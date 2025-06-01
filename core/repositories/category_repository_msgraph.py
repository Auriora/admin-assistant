import asyncio
from typing import List, Optional

from core.models.category import Category
from core.models.user import User

from .category_repository_base import BaseCategoryRepository


class MSGraphCategoryRepository(BaseCategoryRepository):
    """
    Repository for managing Category entities via Microsoft Graph API.
    Uses Outlook categories which are available through the Graph API.
    """

    def __init__(self, msgraph_client, user: User):
        super().__init__(user)
        self.client = msgraph_client

    def get_by_id(self, category_id: str) -> Optional[Category]:
        """Retrieve a category by its ID (sync wrapper)."""
        return asyncio.run(self._get_by_id_async(category_id))

    async def _get_by_id_async(self, category_id: str) -> Optional[Category]:
        """Async: Retrieve a category by its ID."""
        try:
            categories = await self.client.users.by_user_id(
                self.user.email
            ).outlook.master_categories.get()
            for ms_cat in getattr(categories, "value", []):
                if getattr(ms_cat, "id", None) == category_id:
                    return Category(
                        user_id=self.user.id,
                        name=getattr(ms_cat, "display_name", ""),
                        description=f"Color: {getattr(ms_cat, 'color', 'none')}",
                    )
            return None
        except Exception as e:
            raise RuntimeError(
                f"Failed to get category {category_id} for user {self.user.id} via MS Graph: {e}"
            ) from e

    def add(self, category: Category) -> None:
        """Add a new category (sync wrapper)."""
        return asyncio.run(self._add_async(category))

    async def _add_async(self, category: Category) -> None:
        """Async: Add a new category via MS Graph."""
        try:
            from msgraph.generated.models.outlook_category import \
                OutlookCategory

            ms_cat = OutlookCategory()
            ms_cat.display_name = (
                str(category.name) if hasattr(category, "name") else None
            )
            ms_cat.color = "preset0"  # Default color
            await self.client.users.by_user_id(
                self.user.email
            ).outlook.master_categories.post(body=ms_cat)
        except Exception as e:
            raise RuntimeError(
                f"Failed to add category for user {self.user.id} via MS Graph: {e}"
            ) from e

    def list(self) -> List[Category]:
        """List all categories for the repository's user (sync wrapper)."""
        return asyncio.run(self._list_async())

    async def _list_async(self) -> List[Category]:
        """Async: List all categories for the repository's user via MS Graph."""
        categories = []
        try:
            ms_categories = await self.client.users.by_user_id(
                self.user.email
            ).outlook.master_categories.get()
            for ms_cat in getattr(ms_categories, "value", []):
                categories.append(
                    Category(
                        user_id=self.user.id,
                        name=getattr(ms_cat, "display_name", ""),
                        description=f"Color: {getattr(ms_cat, 'color', 'none')}",
                    )
                )
            return categories
        except Exception as e:
            raise RuntimeError(
                f"Failed to list categories for user {self.user.id} via MS Graph: {e}"
            ) from e

    def update(self, category: Category) -> None:
        """Update an existing category (sync wrapper)."""
        return asyncio.run(self._update_async(category))

    async def _update_async(self, category: Category) -> None:
        """Async: Update an existing category via MS Graph."""
        try:
            # For MS Graph, we need to find the category by name and update it
            # This is a limitation of the Outlook categories API
            categories = await self.client.users.by_user_id(
                self.user.email
            ).outlook.master_categories.get()
            category_id = None
            for ms_cat in getattr(categories, "value", []):
                if getattr(ms_cat, "display_name", "") == category.name:
                    category_id = getattr(ms_cat, "id", None)
                    break

            if category_id:
                from msgraph.generated.models.outlook_category import \
                    OutlookCategory

                ms_cat = OutlookCategory()
                ms_cat.display_name = (
                    str(category.name) if hasattr(category, "name") else None
                )
                ms_cat.color = "preset0"  # Keep default color
                await self.client.users.by_user_id(
                    self.user.email
                ).outlook.master_categories.by_outlook_category_id(category_id).patch(
                    body=ms_cat
                )
            else:
                raise ValueError(f"Category '{category.name}' not found")
        except Exception as e:
            raise RuntimeError(
                f"Failed to update category for user {self.user.id} via MS Graph: {e}"
            ) from e

    def delete(self, category_id: str) -> None:
        """Delete a category by its ID (sync wrapper)."""
        return asyncio.run(self._delete_async(category_id))

    async def _delete_async(self, category_id: str) -> None:
        """Async: Delete a category by its ID via MS Graph."""
        try:
            await self.client.users.by_user_id(
                self.user.email
            ).outlook.master_categories.by_outlook_category_id(category_id).delete()
        except Exception as e:
            raise RuntimeError(
                f"Failed to delete category {category_id} for user {self.user.id} via MS Graph: {e}"
            ) from e

    def get_by_name(self, name: str) -> Optional[Category]:
        """Get a category by name for the repository's user (sync wrapper)."""
        return asyncio.run(self._get_by_name_async(name))

    async def _get_by_name_async(self, name: str) -> Optional[Category]:
        """Async: Get a category by name for the repository's user."""
        try:
            categories = await self.client.users.by_user_id(
                self.user.email
            ).outlook.master_categories.get()
            for ms_cat in getattr(categories, "value", []):
                if getattr(ms_cat, "display_name", "") == name:
                    return Category(
                        user_id=self.user.id,
                        name=getattr(ms_cat, "display_name", ""),
                        description=f"Color: {getattr(ms_cat, 'color', 'none')}",
                    )
            return None
        except Exception as e:
            raise RuntimeError(
                f"Failed to get category '{name}' for user {self.user.id} via MS Graph: {e}"
            ) from e
