from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.models.prompt import Prompt
    from core.repositories.prompt_repository import PromptRepository as _PromptRepo


class PromptService:
    """
    Service for business logic related to Prompt entities.
    """

    def __init__(self, repository: Optional["_PromptRepo"] = None):
        self._repository = repository
        self._owns_repository = repository is None  # Track if we created the repository
        self._closed = False

    @property
    def repository(self) -> "_PromptRepo":
        if self._repository is None:
            from core.repositories.prompt_repository import PromptRepository as _Repo

            self._repository = _Repo()
            self._owns_repository = True
        return self._repository

    def get_by_id(self, prompt_id: int) -> Optional["Prompt"]:
        return self.repository.get_by_id(prompt_id)

    def create(self, prompt: "Prompt") -> None:
        self.repository.add(prompt)

    def list_by_user(self, user_id: int) -> List["Prompt"]:
        return self.repository.list_by_user(user_id)

    def list_by_type(self, prompt_type: str) -> List["Prompt"]:
        return self.repository.list_by_type(prompt_type)

    def delete(self, prompt_id: int) -> None:
        self.repository.delete(prompt_id)

    def get_most_relevant_prompt(
        self, user_id: Optional[int], action_type: Optional[str]
    ) -> Optional["Prompt"]:
        """
        Fetch the most relevant prompt for a user and action_type, falling back to system prompt if needed.
        Priority: user+action > user > action > system.
        """
        # Try user+action
        if user_id and action_type:
            prompts = [
                p
                for p in self.repository.list_by_user(user_id)
                if getattr(p, "action_type") == action_type
            ]
            if prompts:
                return prompts[0]
        # Try user
        if user_id:
            prompts = self.repository.list_by_user(user_id)
            if prompts:
                return prompts[0]
        # Try action
        if action_type:
            prompts = self.repository.list_by_type("action-specific")
            prompts = [p for p in prompts if getattr(p, "action_type") == action_type]
            if prompts:
                return prompts[0]
        # Try system
        prompts = self.repository.list_by_type("system")
        if prompts:
            return prompts[0]
        return None

    def update_prompt(self, prompt_id: int, content: str) -> None:
        """
        Update the content of an existing prompt.
        """
        prompt = self.repository.get_by_id(prompt_id)
        if not prompt:
            raise ValueError("Prompt not found")
        setattr(prompt, "content", content)  # type: ignore
        self.repository.add(prompt)  # add() will merge if already present

    def validate_prompt(self, prompt: "Prompt") -> None:
        """
        Validate prompt uniqueness and content.
        Raises ValueError if invalid.
        """
        if (
            not getattr(prompt, "content", None)
            or not str(getattr(prompt, "content", "")).strip()
        ):
            raise ValueError("Prompt content is required.")
        # Uniqueness: user_id + action_type + prompt_type
        user_id = getattr(prompt, "user_id", None)
        action_type = getattr(prompt, "action_type", None)
        prompt_type = getattr(prompt, "prompt_type", None)
        all_prompts = (
            self.repository.list_by_user(user_id)
            if user_id
            else self.repository.list_by_type(str(prompt_type) if prompt_type else "")
        )
        for p in all_prompts:
            if (
                getattr(p, "action_type", None) == action_type
                and getattr(p, "prompt_type", None) == prompt_type
                and getattr(p, "id", None) != getattr(prompt, "id", None)
            ):
                raise ValueError("Duplicate prompt for this user/action/type.")

    def close(self):
        """
        Close the service and clean up resources.

        This method ensures that any resources used by the service are properly
        cleaned up when the service is no longer needed.
        """
        if self._closed:
            return

        # Close the repository if we own it
        if self._owns_repository and self._repository:
            try:
                self._repository.close()
            except Exception:
                pass

        self._closed = True

    def __del__(self):
        """Ensure resources are cleaned up when the service is garbage collected."""
        try:
            self.close()
        except:
            # Ignore errors during garbage collection
            pass
