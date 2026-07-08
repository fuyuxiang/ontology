"""元数据工具 — ontology_get_attr_mapping + ontology_list_capabilities"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.entity import EntityAttribute, OntologyEntity
from app.models.object_binding import ObjectBinding
from app.models.function import OntologyFunction
from app.models.action import EntityAction
from app.models.shared_ref import OntologySharedRef
from app.services.mcp_tools.registry import MCPTool, register
from app.services.mcp_tools.resolve import resolve_ontology_id


@register
class GetAttrMappingTool(MCPTool):
    name = "ontology_get_attr_mapping"
    description = "返回各对象「属性名 -> 物理字段名」及主键信息。对查询的 WHERE/SQL 应使用物理字段名。"

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ontology_name": {"type": "string", "description": "本体英文标识"},
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

        results = []
        for obj_name in object_names:
            entity = (
                db.query(OntologyEntity)
                .filter(
                    OntologyEntity.name == obj_name,
                    OntologyEntity.id.in_(all_entity_ids),
                )
                .first()
            )
            if not entity:
                continue

            # 获取属性映射：属性名 → 物理字段名（source_field）
            attrs = (
                db.query(EntityAttribute)
                .filter(EntityAttribute.entity_id == entity.id)
                .all()
            )
            attr_to_col = {}
            for a in attrs:
                attr_to_col[a.name] = a.source_field or a.name

            # 主键：从 ObjectBinding.id_column 获取
            binding = (
                db.query(ObjectBinding)
                .filter(
                    ObjectBinding.object_type_id == entity.id,
                    ObjectBinding.role == "primary",
                    ObjectBinding.status == "active",
                )
                .first()
            )
            pk_col = binding.id_column if binding and binding.id_column else "ID"

            results.append({
                "object_name": obj_name,
                "primary_key_column": pk_col,
                "attr_to_col": attr_to_col,
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
