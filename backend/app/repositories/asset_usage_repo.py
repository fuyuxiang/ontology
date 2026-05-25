"""AssetUsage 仓库 — Asset 反向引用台账。"""
from __future__ import annotations

from app.models.asset_usage import AssetUsage
from app.repositories.base import BaseRepository


class AssetUsageRepository(BaseRepository[AssetUsage]):
    model = AssetUsage

    def list_for_asset(self, asset_id: str) -> list[AssetUsage]:
        return (
            self.db.query(AssetUsage)
            .filter(AssetUsage.asset_id == asset_id)
            .order_by(AssetUsage.created_at.desc())
            .all()
        )

    def count_for_asset(self, asset_id: str) -> int:
        return self.db.query(AssetUsage).filter(AssetUsage.asset_id == asset_id).count()

    def upsert(self, asset_id: str, used_by_kind: str, used_by_id: str, note: str | None = None) -> AssetUsage:
        existing = (
            self.db.query(AssetUsage)
            .filter(
                AssetUsage.asset_id == asset_id,
                AssetUsage.used_by_kind == used_by_kind,
                AssetUsage.used_by_id == used_by_id,
            )
            .first()
        )
        if existing:
            if note is not None:
                existing.note = note
            return existing
        row = AssetUsage(
            asset_id=asset_id,
            used_by_kind=used_by_kind,
            used_by_id=used_by_id,
            note=note,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def remove(self, asset_id: str, used_by_kind: str, used_by_id: str) -> None:
        (
            self.db.query(AssetUsage)
            .filter(
                AssetUsage.asset_id == asset_id,
                AssetUsage.used_by_kind == used_by_kind,
                AssetUsage.used_by_id == used_by_id,
            )
            .delete()
        )
