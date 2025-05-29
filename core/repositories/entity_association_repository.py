from typing import List, Optional
from core.models.entity_association import EntityAssociation
from core.db import SessionLocal

class EntityAssociationRepository:
    """
    Repository for managing EntityAssociation entities.
    """
    def __init__(self, session=None):
        self.session = session or SessionLocal()

    def get_by_id(self, assoc_id: int) -> Optional[EntityAssociation]:
        return self.session.get(EntityAssociation, assoc_id)

    def add(self, assoc: EntityAssociation) -> None:
        self.session.add(assoc)
        self.session.commit()

    def list_by_source(self, source_type: str, source_id: int) -> List[EntityAssociation]:
        return self.session.query(EntityAssociation).filter_by(source_type=source_type, source_id=source_id).all()

    def list_by_target(self, target_type: str, target_id: int) -> List[EntityAssociation]:
        return self.session.query(EntityAssociation).filter_by(target_type=target_type, target_id=target_id).all()

    def delete(self, assoc_id: int) -> None:
        assoc = self.get_by_id(assoc_id)
        if assoc:
            self.session.delete(assoc)
            self.session.commit() 