"""ObjectBinding 仓库。"""
from __future__ import annotations

from app.models.object_binding import ObjectBinding
from app.repositories.base import BaseRepository


class ObjectBindingRepository(BaseRepository[ObjectBinding]):
    model = ObjectBinding

    def list(
        self,
        *,
        object_type_id: str | None = None,
        asset_id: str | None = None,
        role: str | None = None,
        status: str | None = None,
    ) -> list[ObjectBinding]:
        q = self.db.query(ObjectBinding)
        if object_type_id:
            q = q.filter(ObjectBinding.object_type_id == object_type_id)
        if asset_id:
            q = q.filter(ObjectBinding.asset_id == asset_id)
        if role:
            q = q.filter(ObjectBinding.role == role)
        if status:
            q = q.filter(ObjectBinding.status == status)
        return q.order_by(ObjectBinding.created_at.desc()).all()

    def get_primary(self, object_type_id: str) -> ObjectBinding | None:
        return (
            self.db.query(ObjectBinding)
            .filter(
                ObjectBinding.object_type_id == object_type_id,
                ObjectBinding.role == "primary",
                ObjectBinding.status == "active",
            )
            .first()
        )

    def find_existing(self, object_type_id: str, asset_id: str, role: str) -> ObjectBinding | None:
        return (
            self.db.query(ObjectBinding)
            .filter(
                ObjectBinding.object_type_id == object_type_id,
                ObjectBinding.asset_id == asset_id,
                ObjectBinding.role == role,
            )
            .first()
        )

    def list_for_asset(self, asset_id: str) -> list[ObjectBinding]:
        return self.list(asset_id=asset_id, status="active")
