from typing import List, Optional

from core.db import SessionLocal
from core.models.prompt import Prompt


class PromptRepository:
    """
    Repository for managing Prompt entities.
    """

    def __init__(self, session=None):
        self.session = session or SessionLocal()
        self._owns_session = session is None  # Track if we created the session

    def get_by_id(self, prompt_id: int) -> Optional[Prompt]:
        return self.session.get(Prompt, prompt_id)

    def add(self, prompt: Prompt) -> None:
        self.session.add(prompt)
        self.session.commit()

    def list_by_user(self, user_id: int) -> List[Prompt]:
        return self.session.query(Prompt).filter_by(user_id=user_id).all()

    def list_by_type(self, prompt_type: str) -> List[Prompt]:
        return self.session.query(Prompt).filter_by(prompt_type=prompt_type).all()

    def delete(self, prompt_id: int) -> None:
        prompt = self.get_by_id(prompt_id)
        if prompt:
            self.session.delete(prompt)
            self.session.commit()

    def close(self) -> None:
        """Close the session if we own it."""
        if self._owns_session and self.session:
            self.session.close()

    def __del__(self):
        """Ensure session is closed when repository is garbage collected."""
        try:
            self.close()
        except:
            # Ignore errors during garbage collection
            pass
