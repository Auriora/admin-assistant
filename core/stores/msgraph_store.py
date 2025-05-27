from typing import Any, List, Optional, Dict, Tuple
from .base_store import BaseStore

class MSGraphStore(BaseStore):
    """
    Store implementation for Microsoft Graph API appointments.
    """
    def __init__(self, msgraph_client):
        self.client = msgraph_client  # Should be an authenticated client/session

    def add(self, obj: Any) -> None:
        """Add a new appointment via MS Graph API."""
        self.client.create_event(obj)

    def get(self, id: Any) -> Optional[Any]:
        """Retrieve an appointment by ID via MS Graph API."""
        return self.client.get_event(id)

    def list(self, filters: Optional[Dict] = None, page: int = 1, page_size: int = 100) -> Tuple[List[Any], int]:
        """List appointments with optional filtering and paging via MS Graph API."""
        events, total = self.client.list_events(filters=filters, page=page, page_size=page_size)
        return events, total

    def update(self, obj: Any) -> None:
        """Update an appointment via MS Graph API."""
        self.client.update_event(obj)

    def delete(self, id: Any) -> None:
        """Delete an appointment by ID via MS Graph API."""
        self.client.delete_event(id) 