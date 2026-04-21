from __future__ import annotations

from typing import TypeVar, Generic, Type

from sqlalchemy.orm import Session

from app.database import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    model: Type[T]

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, id: str) -> T | None:
        return self.db.get(self.model, id)

    def create(self, obj: T) -> T:
        self.db.add(obj)
        self.db.flush()
        return obj

    def delete(self, obj: T) -> None:
        self.db.delete(obj)

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, obj: T) -> T:
        self.db.refresh(obj)
        return obj
