"""Resolve instance queries from a published mapping instead of mutable drafts."""
from types import SimpleNamespace
from app.models.asset import Asset
from app.services.data_plane.entity_data_service import EntityDataService


class VersionEntityDataService(EntityDataService):
    def __init__(self, db, version_entity):
        super().__init__(db)
        self.version_entity = version_entity

    def get_query_attribute_names(self, entity_id):
        return {attribute.source_attribute_id: attribute.name for attribute in self.version_entity.attributes}

    def get_query_attribute_specs(self, entity_id):
        return {attribute.name: {"type": attribute.type, "required": attribute.required,
                                 "enum": (getattr(attribute, "constraints_json", None) or {}).get("enum")}
                for attribute in self.version_entity.attributes}

    def resolve_entity_asset(self, entity_id):
        snapshot = self.version_entity.binding_snapshot
        if not snapshot:
            # Legacy snapshots did not contain bindings; do not claim version
            # stability by silently substituting a current mapping.
            raise ValueError("该历史版本没有数据绑定快照，请重新发布后使用实例查询")
        asset = self.db.get(Asset, snapshot["asset_id"])
        if not asset or asset.status != "active":
            raise ValueError("发布版本依赖的数据资产已删除或失效")
        if asset.locator != snapshot.get("asset_locator") or asset.connection_id != snapshot.get("connection_id"):
            raise ValueError("发布版本依赖的资产定位已变更，请审核并重新发布")
        return asset, SimpleNamespace(**snapshot, status="active")

    def get_attr_field_map(self, entity_id):
        mappings = (self.version_entity.binding_snapshot or {}).get("field_mappings") or []
        by_id = {item.get("attribute_id"): item.get("source_column") for item in mappings}
        return {a.name: by_id[a.source_attribute_id] for a in self.version_entity.attributes
                if by_id.get(a.source_attribute_id)}

    def resolve_entity_enrichments(self, entity_id):
        results = []
        for snapshot in (self.version_entity.binding_snapshot or {}).get("enrichments") or []:
            if snapshot.get("status") != "active":
                raise ValueError("发布版本含未完成审核的 enrichment 绑定，请修复后重新发布")
            if not snapshot.get("primary_source_column") or not snapshot.get("enrichment_source_column"):
                raise ValueError("历史 enrichment 绑定缺少明确关联字段，请修复后重新发布")
            asset = self.db.get(Asset, snapshot["asset_id"])
            if not asset or asset.status != "active":
                raise ValueError("发布版本依赖的 enrichment 数据资产已删除或失效")
            if asset.locator != snapshot.get("asset_locator") or asset.connection_id != snapshot.get("connection_id"):
                raise ValueError("发布版本依赖的 enrichment 资产定位已变更，请审核并重新发布")
            results.append((asset, SimpleNamespace(**snapshot)))
        return results
