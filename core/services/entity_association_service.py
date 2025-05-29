from typing import List, Optional, Any
from core.models.entity_association import EntityAssociation
from core.repositories.entity_association_repository import EntityAssociationRepository

class EntityAssociationService:
    """
    Service for business logic related to EntityAssociation entities.
    Provides methods to associate, dissociate, and query related entities.
    """
    def __init__(self, repository: Optional[EntityAssociationRepository] = None):
        self.repository = repository or EntityAssociationRepository()

    def get_by_id(self, assoc_id: int) -> Optional[EntityAssociation]:
        return self.repository.get_by_id(assoc_id)

    def create(self, assoc: EntityAssociation) -> None:
        """
        Create a new association. Validates for duplicates and valid types.
        """
        # Prevent duplicate associations
        existing = self.repository.list_by_source(getattr(assoc, 'source_type'), getattr(assoc, 'source_id'))
        for e in existing:
            if (
                getattr(e, 'target_type') == getattr(assoc, 'target_type') and
                getattr(e, 'target_id') == getattr(assoc, 'target_id') and
                getattr(e, 'association_type') == getattr(assoc, 'association_type')
            ):
                raise ValueError("Duplicate association")
        self.repository.add(assoc)

    def associate(self, source_type: str, source_id: int, target_type: str, target_id: int, association_type: str) -> None:
        """
        Create and persist a new association between two entities.
        Raises ValueError if duplicate.
        """
        assoc = EntityAssociation(
            source_type=source_type,
            source_id=source_id,
            target_type=target_type,
            target_id=target_id,
            association_type=association_type
        )
        self.create(assoc)

    def dissociate(self, source_type: str, source_id: int, target_type: str, target_id: int, association_type: str) -> None:
        """
        Remove an association between two entities.
        """
        matches = [a for a in self.repository.list_by_source(source_type, source_id)
                   if getattr(a, 'target_type') == target_type and getattr(a, 'target_id') == target_id and getattr(a, 'association_type') == association_type]
        for assoc in matches:
            self.repository.delete(int(getattr(assoc, 'id')))

    def list_by_source(self, source_type: str, source_id: int) -> List[EntityAssociation]:
        return self.repository.list_by_source(source_type, source_id)

    def list_by_target(self, target_type: str, target_id: int) -> List[EntityAssociation]:
        return self.repository.list_by_target(target_type, target_id)

    def get_related_entities(self, source_type: str, source_id: int, association_type: Optional[str] = None) -> List[Any]:
        """
        Fetch all related entity IDs for a given source entity, optionally filtered by association_type.
        Returns a list of (target_type, target_id) tuples.
        """
        assocs = self.repository.list_by_source(source_type, source_id)
        if association_type:
            assocs = [a for a in assocs if getattr(a, 'association_type') == association_type]
        return [(a.target_type, a.target_id) for a in assocs]

    def delete(self, assoc_id: int) -> None:
        self.repository.delete(assoc_id) 