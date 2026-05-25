"""ObjectBindingService — ObjectType ↔ Asset 强类型映射。

建模模块拥有 ObjectBinding 资源，但服务放在共享层，便于：
- 数据集成侧：删 Asset 前查引用、画 Asset→ObjectType 血缘
- AI 自动构建：发布时自动落 Binding（来自草稿的 backing_asset_ids）

兼容期：写 Binding 时同步反写 EntityAttribute.source_table/source_field（让老 MappingView 仍能正确显示）。
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.entity import EntityAttribute
from app.models.object_binding import ObjectBinding
from app.repositories.asset_repo import AssetRepository
from app.repositories.asset_usage_repo import AssetUsageRepository
from app.repositories.object_binding_repo import ObjectBindingRepository
from app.services.data_plane.event_bus import get_event_bus

logger = logging.getLogger(__name__)


class ObjectBindingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ObjectBindingRepository(db)
        self.assets = AssetRepository(db)
        self.usage = AssetUsageRepository(db)
        self.bus = get_event_bus()

    def list(self, *, object_type_id: str | None = None, asset_id: str | None = None,
             role: str | None = None, status: str | None = "active") -> list[ObjectBinding]:
        return self.repo.list(object_type_id=object_type_id, asset_id=asset_id,
                              role=role, status=status)

    def get(self, binding_id: str) -> ObjectBinding | None:
        return self.repo.get_by_id(binding_id)

    def create(
        self,
        *,
        object_type_id: str,
        asset_id: str,
        role: str = "primary",
        field_mappings: list[dict] | None = None,
        id_column: str | None = None,
        filter_expr: str | None = None,
        user_id: str | None = None,
    ) -> ObjectBinding:
        existing = self.repo.find_existing(object_type_id, asset_id, role)
        if existing:
            raise ValueError("已存在同 (object_type_id, asset_id, role) 的 binding，请改用更新")
        asset = self.assets.get_by_id(asset_id)
        if not asset:
            raise LookupError(f"资产不存在: {asset_id}")
        binding = ObjectBinding(
            object_type_id=object_type_id, asset_id=asset_id, role=role,
            field_mappings=field_mappings or [],
            id_column=id_column or (asset.primary_key[0] if asset.primary_key else None),
            filter_expr=filter_expr,
            status="active", created_by=user_id,
        )
        self.db.add(binding)
        self.db.flush()
        # 反向引用：asset_usage
        self.usage.upsert(asset_id, "object_binding", binding.id, note=f"role={role}")
        # 兼容反写：EntityAttribute.source_table/source_field
        self._mirror_to_entity_attributes(binding, asset)
        self.db.commit()
        self.db.refresh(binding)
        # 血缘 + 事件
        self.bus.emit("binding.created", {
            "binding_id": binding.id, "asset_id": asset_id,
            "object_type_id": object_type_id, "role": role,
        })
        return binding

    def update(self, binding_id: str, **changes) -> ObjectBinding:
        b = self._must(binding_id)
        for k, v in changes.items():
            if k in ("field_mappings", "id_column", "filter_expr", "status", "review_reason") and v is not None:
                setattr(b, k, v)
        if changes.get("field_mappings") is not None:
            self._mirror_to_entity_attributes(b, self.assets.get_by_id(b.asset_id))
        self.db.commit()
        self.db.refresh(b)
        self.bus.emit("binding.updated", {
            "binding_id": b.id, "asset_id": b.asset_id, "object_type_id": b.object_type_id,
        })
        return b

    def delete(self, binding_id: str) -> None:
        b = self._must(binding_id)
        # 反向引用清除
        self.usage.remove(b.asset_id, "object_binding", b.id)
        # 兼容反写：清除 EntityAttribute.source_*（仅当前 binding 涉及的 attribute_id）
        for fm in (b.field_mappings or []):
            attr_id = fm.get("attribute_id")
            if attr_id:
                attr = self.db.get(EntityAttribute, attr_id)
                if attr:
                    attr.source_table = None
                    attr.source_field = None
                    attr.data_status = "未确认来源"
        asset_id, object_type_id = b.asset_id, b.object_type_id
        self.db.delete(b)
        self.db.commit()
        self.bus.emit("binding.deleted", {
            "asset_id": asset_id, "object_type_id": object_type_id,
        })

    # ── 兼容反写 ───────────────────────────────────────
    def _mirror_to_entity_attributes(self, binding: ObjectBinding, asset: Any) -> None:
        if not asset or asset.kind != "table":
            return
        table_name = (asset.locator or {}).get("table") or ""
        for fm in binding.field_mappings or []:
            attr_id = fm.get("attribute_id")
            col = fm.get("source_column")
            if not (attr_id and col):
                continue
            attr = self.db.get(EntityAttribute, attr_id)
            if not attr:
                continue
            attr.source_table = table_name
            attr.source_field = col
            attr.data_status = "已确认来源"

    def _must(self, binding_id: str) -> ObjectBinding:
        b = self.repo.get_by_id(binding_id)
        if not b:
            raise LookupError(f"binding 不存在: {binding_id}")
        return b
