from sqlalchemy.orm import Session
from typing import Type, Any, List, Optional, Dict, Tuple
from .base_store import BaseStore

class SQLAlchemyStore(BaseStore):
    """
    Generic SQLAlchemy store for CRUD operations.
    """
    def __init__(self, session: Session, model: Type[Any]):
        self.session = session
        self.model = model

    def add(self, obj: Any) -> None:
        self.session.add(obj)
        self.session.commit()

    def get(self, id: Any) -> Optional[Any]:
        return self.session.query(self.model).get(id)

    def list(self, filters: Optional[Dict] = None, page: int = 1, page_size: int = 100) -> Tuple[List[Any], int]:
        query = self.session.query(self.model)
        if filters:
            query = query.filter_by(**filters)
        total = query.count()
        results = query.offset((page - 1) * page_size).limit(page_size).all()
        return results, total

    def update(self, obj: Any) -> None:
        self.session.merge(obj)
        self.session.commit()

    def delete(self, id: Any) -> None:
        obj = self.get(id)
        if obj:
            self.session.delete(obj)
            self.session.commit() 