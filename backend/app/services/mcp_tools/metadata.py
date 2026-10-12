"""元数据工具 — ontology_get_attr_mapping + ontology_list_capabilities"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.action import EntityAction
from app.models.entity import EntityAttribute, OntologyEntity
from app.models.function import OntologyFunction
from app.models.object_binding import ObjectBinding
from app.models.shared_ref import OntologySharedRef
from app.services.mcp_tools.registry import MCPTool, register
from app.services.mcp_tools.resolve import resolve_ontology_id


@register
class GetAttrMappingTool(MCPTool):
    name = "ontology_get_attr_mapping"
    description = "返回属性到物理字段映射、主键和冻结transform定义。原生WHERE/SQL使用物理字段且返回源原值；ontology_object_find应用transform后返回本体属性值。"

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ontology_name": {"type": "string", "description": "本体英文标识"},
                "version_id": {"type": "string"},
                "object_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要查询的对象类名列表",
                },
                "user_id": {"type": "string", "description": "当前用户 ID"},
            },
            "required": ["ontology_name", "object_names", "user_id"],
            "additionalProperties": False,
        }

    async def execute(self, arguments: dict, **ctx: Any) -> Any:
        db: Session = ctx["db"]
        ontology_name = arguments["ontology_name"]
        object_names = arguments["object_names"]

        ontology_id = resolve_ontology_id(db, ontology_name)
        if not ontology_id:
            return {"error": f"本体 '{ontology_name}' 不存在"}

        # 查找属于此本体的实体（自有 + 共享）
        owned_ids = {r[0] for r in db.query(OntologyEntity.id).filter(
            OntologyEntity.ontology_id == ontology_id
        ).all()}
        shared_ids = {r[0] for r in db.query(OntologySharedRef.entity_id).filter(
            OntologySharedRef.target_ontology_id == ontology_id
        ).all()}
        all_entity_ids = owned_ids | shared_ids

        from app.services.mcp_tools.data_query import _get_entity_in_ontology, _entity_service
        results = []
        for obj_name in object_names:
            entity = _get_entity_in_ontology(db, ontology_id, obj_name, arguments.get("version_id"))
            if not entity:
                return {"error": f"对象 {obj_name} 不存在或名称有歧义"}

            # 获取属性映射：属性名 → 物理字段名（source_field）
            svc = _entity_service(db, entity)
            attr_to_col = svc.get_attr_field_map(entity.id)

            # 主键：从 ObjectBinding.id_column 获取
            resolved = svc.resolve_entity_asset(entity.id)
            if not resolved:
                return {"error": f"对象 {obj_name} 未绑定有效资产"}
            pk_col = resolved[1].id_column
            attribute_names = svc.get_query_attribute_names(entity.id)
            bindings = [resolved[1]] + [binding for _, binding in svc.resolve_entity_enrichments(entity.id)]
            transforms = {attribute_names[mapping["attribute_id"]]: mapping["transform"]
                for binding in bindings for mapping in binding.field_mappings or []
                if mapping.get("attribute_id") in attribute_names and mapping.get("transform")}

            results.append({
                "object_name": obj_name,
                "primary_key_column": pk_col,
                "attr_to_col": attr_to_col,
                "attribute_transforms": transforms,
                "sql_value_semantics": "physical_source",
                "object_value_semantics": "mapped_transformed",
            })

        if not results:
            return {"error": f"未找到对象: {object_names}", "mapping": []}

        return results


@register
class ListCapabilitiesTool(MCPTool):
    name = "ontology_list_capabilities"
    description = "列出本体内已注册的 logic 与/或 action 名称。"

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ontology_name": {"type": "string", "description": "本体英文标识"},
                "version_id": {"type": "string"},
                "user_id": {"type": "string", "description": "当前用户 ID"},
                "list_type": {
                    "type": "string",
                    "enum": ["logics", "actions", "all"],
                    "description": "筛选类型，默认 all",
                },
            },
            "required": ["ontology_name", "user_id"],
            "additionalProperties": False,
        }

    async def execute(self, arguments: dict, **ctx: Any) -> Any:
        db: Session = ctx["db"]
        ontology_name = arguments["ontology_name"]
        list_type = arguments.get("list_type", "all")

        ontology_id = resolve_ontology_id(db, ontology_name)
        if not ontology_id:
            return {"error": f"本体 '{ontology_name}' 不存在"}
        from app.models.version import OntologyVersion
        query = db.query(OntologyVersion).filter_by(ontology_id=ontology_id, status="published")
        version = query.filter_by(id=arguments["version_id"]).first() if arguments.get("version_id") else query.filter_by(is_active=True).first()
        if arguments.get("version_id") and not version:
            return {"error": "指定发布版本不存在"}
        if version:
            logics = [{"name": f.callable_name or f.name, "description": f.description or ""} for f in version.functions] if list_type in ("logics", "all") else []
            actions = [{"name": a.name, "description": a.description or ""} for a in version.actions] if list_type in ("actions", "all") else []
            return {"logics": logics, "actions": actions, "total_logics": len(logics), "total_actions": len(actions), "version_id": version.id}

        # 该本体范围内的实体 ID
        owned_ids = {r[0] for r in db.query(OntologyEntity.id).filter(
            OntologyEntity.ontology_id == ontology_id
        ).all()}
        shared_ids = {r[0] for r in db.query(OntologySharedRef.entity_id).filter(
            OntologySharedRef.target_ontology_id == ontology_id
        ).all()}
        all_entity_ids = owned_ids | shared_ids

        logics = []
        actions = []

        if list_type in ("logics", "all"):
            funcs = (
                db.query(OntologyFunction)
                .filter(
                    (OntologyFunction.ontology_id == ontology_id) |
                    (OntologyFunction.entity_id.in_(all_entity_ids))
                )
                .filter(OntologyFunction.status == "active")
                .all()
            )
            logics = [{"name": f.callable_name or f.name, "description": f.description or ""} for f in funcs]

        if list_type in ("actions", "all"):
            acts = (
                db.query(EntityAction)
                .filter(
                    (EntityAction.ontology_id == ontology_id) |
                    (EntityAction.entity_id.in_(all_entity_ids))
                )
                .filter(EntityAction.status == "active")
                .all()
            )
            actions = [{"name": a.name, "description": a.description or ""} for a in acts]

        return {
            "logics": logics,
            "actions": actions,
            "total_logics": len(logics),
            "total_actions": len(actions),
        }
