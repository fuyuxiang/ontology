from __future__ import annotations

from app.models.datasource import DataSource
from app.repositories.base import BaseRepository


class DataSourceRepository(BaseRepository[DataSource]):
    model = DataSource

    def list_with_filters(
        self,
        type: str | None = None,
        status: str | None = None,
        q: str | None = None,
    ) -> list[DataSource]:
        query = self.db.query(DataSource)
        if type:
            query = query.filter(DataSource.type == type)
        if status:
            query = query.filter(DataSource.status == status)
        if q:
            query = query.filter(DataSource.name.ilike(f"%{q}%"))
        return query.order_by(DataSource.created_at.desc()).all()

    def find_by_name(self, name: str) -> DataSource | None:
        return self.db.query(DataSource).filter(DataSource.name == name).first()

    def find_by_type(self, ds_type: str) -> DataSource | None:
        return self.db.query(DataSource).filter(DataSource.type == ds_type).first()
