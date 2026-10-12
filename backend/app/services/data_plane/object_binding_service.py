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

from app.models.asset import Asset
from app.models.entity import EntityAttribute, OntologyEntity
from app.models.quality_rule import QualityRule, HealthStatus
from app.models.object_binding import ObjectBinding
from app.repositories.asset_repo import AssetRepository
from app.repositories.asset_usage_repo import AssetUsageRepository
from app.repositories.object_binding_repo import ObjectBindingRepository
from app.repositories.lineage_edge_repo import LineageEdgeRepository
from app.services.data_plane.event_bus import emit_after_commit, get_event_bus

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
        primary_source_column: str | None = None,
        enrichment_source_column: str | None = None,
        user_id: str | None = None,
    ) -> ObjectBinding:
        existing = self.repo.find_existing(object_type_id, asset_id, role)
        if existing:
            raise ValueError("已存在同 (object_type_id, asset_id, role) 的 binding，请改用更新")
        asset = self.assets.get_by_id(asset_id)
        if not asset:
            raise LookupError(f"资产不存在: {asset_id}")
        if role not in ("primary", "enrichment", "document_evidence"):
            raise ValueError("不支持的 binding role")
        if role == "primary" and self.repo.get_primary(object_type_id):
            raise ValueError("对象已存在活动主绑定，请先更新或删除原绑定")
        mappings = field_mappings or []
        id_column = id_column or (asset.primary_key[0] if asset.primary_key else None)
        self._validate(object_type_id, asset, mappings, id_column, role)
        join_ready = self._validate_join(object_type_id, asset, role, primary_source_column, enrichment_source_column)
        binding = ObjectBinding(
            object_type_id=object_type_id, asset_id=asset_id, role=role,
            field_mappings=mappings,
            id_column=id_column,
            filter_expr=filter_expr,
            primary_source_column=primary_source_column,
            enrichment_source_column=enrichment_source_column,
            status="active" if join_ready else "needs_review", created_by=user_id,
            review_reason=None if join_ready else "补充绑定缺少明确关联列，请配置 primary_source_column 与 enrichment_source_column 后重新确认",

        )
        self.db.add(binding)
        self.db.flush()
        # 反向引用：asset_usage
        self.usage.upsert(asset_id, "object_binding", binding.id, note=f"role={role}")
        # 兼容反写：EntityAttribute.source_table/source_field
        if binding.status == "active":
            self._mirror_to_entity_attributes(binding, asset)
            _auto_mount_quality_rules(self.db, asset_id, object_type_id, binding=binding)
        LineageEdgeRepository(self.db).upsert(source_kind="asset", source_id=asset_id,
            target_kind="object_type", target_id=object_type_id, relation="binds_to", via_module="binding")
        if binding.status != "active":
            LineageEdgeRepository(self.db).deprecate_for_binding(object_type_id, asset_id)
        self.db.flush()
        self.db.refresh(binding)
        # 血缘 + 事件
        emit_after_commit(self.db, "binding.created", {
            "binding_id": binding.id, "asset_id": asset_id,
            "object_type_id": object_type_id, "role": role, "lineage_persisted": True,
        })
        return binding

    def update(self, binding_id: str, **changes) -> ObjectBinding:
        b = self._must(binding_id)
        asset = self.assets.get_by_id(b.asset_id)
        if changes.get("status") not in (None, "active", "needs_review", "deprecated"):
            raise ValueError("不支持的 binding status")
        mappings = changes.get("field_mappings") if changes.get("field_mappings") is not None else b.field_mappings
        id_column = changes.get("id_column", b.id_column)
        deactivating = changes.get("status") in {"needs_review", "deprecated"} and all(
            key not in changes or changes[key] == getattr(b, key)
            for key in ("field_mappings", "id_column", "primary_source_column", "enrichment_source_column"))
        # A broken source must still be removable from service without first
        # repairing its schema or recreating its primary binding.
        if not deactivating:
            self._validate(b.object_type_id, asset, mappings, id_column, b.role)
        join_ready = True if deactivating else self._validate_join(b.object_type_id, asset, b.role,
            changes.get("primary_source_column", b.primary_source_column),
            changes.get("enrichment_source_column", b.enrichment_source_column))
        if not join_ready:
            changes.update(status="needs_review", review_reason="补充绑定缺少明确关联列，请配置 primary_source_column 与 enrichment_source_column 后重新确认")
        elif b.role == "enrichment" and any(k in changes for k in ("primary_source_column", "enrichment_source_column")) and b.status == "needs_review":
            changes.setdefault("status", "active")
            changes.setdefault("review_reason", None)
        if changes.get("status") == "active" and b.role == "primary":
            active = self.repo.get_primary(b.object_type_id)
            if active and active.id != b.id:
                raise ValueError("对象已存在活动主绑定")
        old_mappings = list(b.field_mappings or [])
        for k, v in changes.items():
            if k in ("field_mappings", "id_column", "filter_expr", "status", "review_reason", "primary_source_column", "enrichment_source_column"):
                if k in ("field_mappings", "status") and v is None:
                    continue
                setattr(b, k, v)
        if changes.get("field_mappings") is not None or "status" in changes:
            self._clear_mirrored_attributes(b, old_mappings)
            if b.status == "active":
                self._mirror_to_entity_attributes(b, self.assets.get_by_id(b.asset_id))
        if any(k in changes for k in ("field_mappings", "id_column", "status", "primary_source_column", "enrichment_source_column")):
            self._remove_auto_rules(b)
            self._remount_asset_rules(b.asset_id)
        lineage = LineageEdgeRepository(self.db)
        if b.status == "active":
            lineage.upsert(source_kind="asset", source_id=b.asset_id, target_kind="object_type",
                           target_id=b.object_type_id, relation="binds_to", via_module="binding")
        elif not self.repo.list(object_type_id=b.object_type_id, asset_id=b.asset_id, status="active"):
            lineage.deprecate_for_binding(b.object_type_id, b.asset_id)
        self.db.flush()
        self.db.refresh(b)
        emit_after_commit(self.db, "binding.updated", {
            "binding_id": b.id, "asset_id": b.asset_id, "object_type_id": b.object_type_id, "lineage_persisted": True,
        })
        return b

    def delete(self, binding_id: str) -> None:
        b = self._must(binding_id)
        # 反向引用清除
        self.usage.remove(b.asset_id, "object_binding", b.id)
        # 兼容反写：清除 EntityAttribute.source_*（仅当前 binding 涉及的 attribute_id）
        self._clear_mirrored_attributes(b, b.field_mappings or [])
        self._remove_auto_rules(b)
        asset_id, object_type_id = b.asset_id, b.object_type_id
        if b.role == "primary":
            for enrichment in self.repo.list(object_type_id=object_type_id, role="enrichment", status="active"):
                enrichment.status = "needs_review"
                enrichment.review_reason = "primary 绑定已删除，请重新确认 enrichment 关联规则"
                self._clear_mirrored_attributes(enrichment, enrichment.field_mappings or [])
                self._remove_auto_rules(enrichment)
                if not self.repo.list(object_type_id=object_type_id, asset_id=enrichment.asset_id, status="active"):
                    LineageEdgeRepository(self.db).deprecate_for_binding(object_type_id, enrichment.asset_id)
        self.db.delete(b)
        self.db.flush()
        for remaining in self.repo.list(asset_id=asset_id, status="active"):
            _auto_mount_quality_rules(self.db, remaining.asset_id, remaining.object_type_id, binding=remaining)
        if not self.repo.list(object_type_id=object_type_id, asset_id=asset_id, status="active"):
            LineageEdgeRepository(self.db).deprecate_for_binding(object_type_id, asset_id)
        emit_after_commit(self.db, "binding.deleted", {
            "asset_id": asset_id, "object_type_id": object_type_id, "lineage_persisted": True,
        })

    def _validate(self, object_type_id, asset, mappings, id_column, role):
        entity = self.db.get(OntologyEntity, object_type_id)
        if not entity:
            raise LookupError(f"对象不存在: {object_type_id}")
        if not asset or asset.status != "active":
            raise ValueError("绑定需要活动资产")
        if role in ("primary", "enrichment") and asset.kind not in ("table", "sql_view"):
            raise ValueError("数据绑定需要 table 或 sql_view 资产")
        if role == "document_evidence" and asset.kind != "document":
            raise ValueError("文档证据绑定需要 document 资产")
        attrs = {a.id for a in self.db.query(EntityAttribute).filter_by(entity_id=object_type_id).all()}
        columns = {c.get("name") for c in asset.schema_snapshot or []}
        seen = set()
        other_mapped = {fm.get("attribute_id")
            for other in self.repo.list(object_type_id=object_type_id, status="active")
            if not (other.asset_id == asset.id and other.role == role)
            for fm in (other.field_mappings or [])}
        for mapping in mappings or []:
            aid, col = mapping.get("attribute_id"), mapping.get("source_column")
            if aid not in attrs:
                raise ValueError(f"属性 {aid} 不属于绑定对象")
            if aid in seen:
                raise ValueError(f"属性 {aid} 重复映射")
            if aid in other_mapped:
                raise ValueError(f"属性 {aid} 已由其它数据绑定映射，请确认唯一属性来源")
            seen.add(aid)
            if not col or (columns and col not in columns):
                raise ValueError(f"源字段不存在: {col}")
            if mapping.get("transform"):
                from app.services.data_plane.mapping_transform import validate_transform
                validate_transform(mapping["transform"])
                primary_columns = {c.get("name") for c in asset.schema_snapshot or [] if c.get("is_pk")}
                if col == id_column or col in primary_columns:
                    raise ValueError("主键字段禁止 transform，实例身份必须保持原值")
        if id_column and columns and id_column not in columns:
            raise ValueError(f"主键源字段不存在: {id_column}")

    def _validate_join(self, object_id, asset, role, primary_column, enrichment_column):
        if role != "enrichment":
            if primary_column or enrichment_column:
                raise ValueError("只有 enrichment 绑定可以配置关联列")
            return True
        if not primary_column or not enrichment_column:
            return False
        primary = self.repo.get_primary(object_id)
        if not primary:
            raise ValueError("请先建立活动 primary 绑定，再配置 enrichment 关联")
        primary_asset = self.assets.get_by_id(primary.asset_id)
        if not primary_asset or primary_asset.status != "active":
            raise ValueError("enrichment 关联需要活动 primary 资产")
        if primary_column not in {c.get("name") for c in primary_asset.schema_snapshot or []}:
            raise ValueError(f"primary_source_column 不存在: {primary_column}")
        if enrichment_column not in {c.get("name") for c in asset.schema_snapshot or []}:
            raise ValueError(f"enrichment_source_column 不存在: {enrichment_column}")
        return True

    def _clear_mirrored_attributes(self, binding, mappings):
        for fm in mappings:
            attr = self.db.get(EntityAttribute, fm.get("attribute_id"))
            if not attr or attr.entity_id != binding.object_type_id:
                continue
            alternatives = [other for other in self.repo.list(object_type_id=binding.object_type_id, status="active")
                            if other.id != binding.id and any(m.get("attribute_id") == attr.id for m in other.field_mappings or [])]
            if alternatives:
                self._mirror_to_entity_attributes(alternatives[0], self.assets.get_by_id(alternatives[0].asset_id))
            else:
                attr.source_table = None
                attr.source_field = None
                attr.data_status = "未确认来源"

    def _remove_auto_rules(self, binding):
        rules = self.db.query(QualityRule).filter_by(description=f"auto:binding:{binding.id}").all()
        for rule in rules:
            self.db.query(HealthStatus).filter_by(rule_id=rule.id).delete()
            self.db.delete(rule)
        self.db.flush()

    def _remount_asset_rules(self, asset_id):
        """Reconcile shared requirements after removing their previous owner."""
        self.db.flush()
        for remaining in self.repo.list(asset_id=asset_id, status="active"):
            _auto_mount_quality_rules(self.db, asset_id, remaining.object_type_id, binding=remaining)

    def prepare_data_replacement(self, object_type_id, retained_pairs):
        """Release old assignments before validating the final set in one transaction.

        Preserve IDs for unchanged (asset, role) pairs; changing a source's role
        removes the old pair. Callers must commit only after every replacement
        has passed validation, so observers never see these intermediate states.
        """
        old = [binding for binding in self.repo.list(object_type_id=object_type_id)
               if binding.role in {"primary", "enrichment"}]
        for binding in old:
            binding.status = "needs_review"
        self.db.flush()
        for binding in old:
            self._clear_mirrored_attributes(binding, binding.field_mappings or [])
            self._remove_auto_rules(binding)
        for binding in old:
            if (binding.asset_id, binding.role) not in retained_pairs:
                self.delete(binding.id)
        for asset_id in {binding.asset_id for binding in old}:
            self._remount_asset_rules(asset_id)

    # ── 兼容反写 ───────────────────────────────────────
    def _mirror_to_entity_attributes(self, binding: ObjectBinding, asset: Any) -> None:
        if not asset or asset.kind not in {"table", "sql_view"}:
            return
        table_name = (asset.locator or {}).get("table") or (asset.alias or asset.name if asset.kind == "sql_view" else "")
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


def _auto_mount_quality_rules(db: Session, asset_id: str, object_type_id: str, *, binding=None) -> None:
    """Auto-mount quality rules based on entity attributes when a binding is created."""
    from app.models.entity import OntologyEntity
    from app.services.data_plane.quality_rule_service import QualityRuleService

    entity = db.get(OntologyEntity, object_type_id)
    if not entity:
        return

    svc = QualityRuleService(db)
    existing = svc.list_rules(asset_id)
    existing_keys, transformed_keys = set(), set()
    for rule in existing:
        params = rule.params if isinstance(rule.params, dict) else {}
        attribute_id, owner_id = params.get("binding_attribute_id"), params.get("binding_object_type_id")
        # Only null-ratio rules with both binding references evaluate converted
        # values. Unrelated/partial metadata must not hide a physical rule.
        if rule.kind == "null_ratio_max" and attribute_id and owner_id:
            transformed_keys.add((rule.kind, rule.column_name, owner_id, attribute_id))
        else:
            existing_keys.add((rule.kind, rule.column_name))

    field_map = {m.get("attribute_id"): m.get("source_column") for m in binding.field_mappings or []} if binding else {}
    pk = binding.id_column if binding else (entity.config_json or {}).get("primary_key", "")

    rules_to_create = []

    # Universal: row_count_min
    if ("row_count_min", None) not in existing_keys:
        rules_to_create.append({"name": "行数非空", "kind": "row_count_min", "column_name": None, "severity": "failure"})

    # Freshness is meaningful only for timestamp columns, never for an integer/string PK.
    asset = db.get(Asset, asset_id) if binding else None
    for col in (asset.schema_snapshot or []) if asset else []:
        if any(t in (col.get("type") or "").lower() for t in ("date", "time")):
            cname = col["name"]
            if ("freshness", cname) not in existing_keys:
                rules_to_create.append({"name": f"{cname} 新鲜度", "kind": "freshness", "column_name": cname, "severity": "warning"})
            break

    # PK uniqueness
    if pk and ("pk_uniqueness", pk) not in existing_keys:
        rules_to_create.append({"name": f"{pk} 唯一性", "kind": "pk_uniqueness", "column_name": pk, "severity": "failure"})

    # Required attributes → null_ratio_max
    attributes = db.query(EntityAttribute).filter_by(entity_id=object_type_id).all() if binding else entity.attributes
    for attr in attributes:
        column = field_map.get(attr.id) if binding else attr.name
        transformed = bool(binding and any(m.get("attribute_id") == attr.id and m.get("transform") for m in binding.field_mappings or []))
        missing = (("null_ratio_max", column, object_type_id, attr.id) not in transformed_keys if transformed
                   else ("null_ratio_max", column) not in existing_keys)
        if attr.required and column and missing:
            rules_to_create.append({
                "name": f"{attr.name} 非空",
                "kind": "null_ratio_max",
                "column_name": column,
                "severity": "warning",
                "params": {"binding_attribute_id": attr.id, "binding_object_type_id": object_type_id}
                          if transformed else {},
            })

    for r in rules_to_create:
        svc.create_rule(asset_id=asset_id, **r, commit=False,
                        description=f"auto:binding:{binding.id}" if binding else None)
