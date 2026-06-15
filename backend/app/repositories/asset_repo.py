"""Asset 仓库。"""
from __future__ import annotations

from sqlalchemy import or_

from app.models.asset import Asset
from app.repositories.base import BaseRepository


class AssetRepository(BaseRepository[Asset]):
    model = Asset

    def list(
        self,
        *,
        kind: str | None = None,
        kinds: list[str] | None = None,
        connection_id: str | None = None,
        domain: str | None = None,
        status: str | None = "active",
        q: str | None = None,
        document_source_type: str | None = None,
    ) -> list[Asset]:
        query = self.db.query(Asset)
        if status:
            query = query.filter(Asset.status == status)
        if kind:
            query = query.filter(Asset.kind == kind)
        elif kinds:
            query = query.filter(Asset.kind.in_(kinds))
        if connection_id:
            query = query.filter(Asset.connection_id == connection_id)
        if domain:
            query = query.filter(Asset.domain == domain)
        if document_source_type:
            query = query.filter(Asset.document_source_type == document_source_type)
        if q:
            like = f"%{q}%"
            query = query.filter(or_(
                Asset.name.ilike(like),
                Asset.alias.ilike(like),
                Asset.description.ilike(like),
            ))
        return query.order_by(Asset.created_at.desc()).all()

    def find_by_alias(self, alias: str) -> Asset | None:
        return self.db.query(Asset).filter(Asset.alias == alias).first()

    def find_by_legacy_datasource(self, ds_id: str) -> Asset | None:
        return self.db.query(Asset).filter(Asset.legacy_datasource_id == ds_id).first()

    def find_by_legacy_business_document(self, doc_id: str) -> Asset | None:
        return self.db.query(Asset).filter(Asset.legacy_business_document_id == doc_id).first()

    def find_table_by_connection_table(self, connection_id: str, table_name: str) -> Asset | None:
        """按 connection + 表名查 table 资产。用于业务模块用 (conn,table) 查 asset。"""
        return (
            self.db.query(Asset)
            .filter(
                Asset.connection_id == connection_id,
                Asset.kind == "table",
                Asset.locator["table"].as_string() == table_name,
            )
            .first()
        )

    def find_table_by_name(self, table_name: str) -> Asset | None:
        """按表名查 table 资产（不限 connection）。"""
        return (
            self.db.query(Asset)
            .filter(
                Asset.kind == "table",
                Asset.locator["table"].as_string() == table_name,
            )
            .first()
        )

    def list_active_structured(self) -> list[Asset]:
        """返回所有 active 且有 schema_snapshot 的结构化资产。"""
        return (
            self.db.query(Asset)
            .filter(Asset.kind.in_(["table", "sql_view"]))
            .filter(Asset.status == "active")
            .filter(Asset.schema_snapshot.isnot(None))
            .all()
        )

    def count_by_connection(self, connection_id: str) -> int:
        return self.db.query(Asset).filter(Asset.connection_id == connection_id).count()
