"""Connection 仓库。"""
from __future__ import annotations

from sqlalchemy import or_

from app.models.connection import Connection
from app.repositories.base import BaseRepository


class ConnectionRepository(BaseRepository[Connection]):
    model = Connection

    def list(
        self,
        type: str | None = None,
        category: str | None = None,
        status: str | None = None,
        q: str | None = None,
    ) -> list[Connection]:
        query = self.db.query(Connection)
        if type:
            query = query.filter(Connection.type == type)
        if category:
            query = query.filter(Connection.category == category)
        if status:
            query = query.filter(Connection.status == status)
        if q:
            like = f"%{q}%"
            query = query.filter(or_(
                Connection.name.ilike(like),
                Connection.host.ilike(like),
                Connection.description.ilike(like),
            ))
        return query.order_by(Connection.created_at.desc()).all()

    def find_by_name(self, name: str) -> Connection | None:
        return self.db.query(Connection).filter(Connection.name == name).first()
