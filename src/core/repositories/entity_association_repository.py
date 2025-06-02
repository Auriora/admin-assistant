from typing import List, Optional

from sqlalchemy.orm import Session

from core.models.entity_association import EntityAssociation


class EntityAssociationHelper:
    """
    Helper/service for managing EntityAssociation entities. Stateless; requires db session to be passed to each method.
    """

    def __init__(self):
        pass

    def get_by_id(self, db: Session, assoc_id: int) -> Optional[EntityAssociation]:
        return db.get(EntityAssociation, assoc_id)

    def add(self, db: Session, assoc: EntityAssociation) -> None:
        db.add(assoc)
        db.commit()

    def list_by_source(
        self, db: Session, source_type: str, source_id: int
    ) -> List[EntityAssociation]:
        return (
            db.query(EntityAssociation)
            .filter_by(source_type=source_type, source_id=source_id)
            .all()
        )

    def list_by_target(
        self, db: Session, target_type: str, target_id: int
    ) -> List[EntityAssociation]:
        return (
            db.query(EntityAssociation)
            .filter_by(target_type=target_type, target_id=target_id)
            .all()
        )

    def delete(self, db: Session, assoc_id: int) -> None:
        assoc = self.get_by_id(db, assoc_id)
        if assoc:
            db.delete(assoc)
            db.commit()
