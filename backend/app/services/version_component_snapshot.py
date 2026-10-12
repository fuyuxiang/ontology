"""Immutable executable component snapshots owned by the version transaction."""
from __future__ import annotations

import copy
import hashlib
import ast
from pathlib import Path

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.action import EntityAction
from app.models.function import OntologyFunction
from app.models.version_components import OntologyVersionAction, OntologyVersionFunction


def _remap_attr_ids(items, attr_map):
    if items is None:
        return None
    result = copy.deepcopy(items)
    for item in result:
        key = "attribute_id" if "attribute_id" in item else "entity_attribute_id" if "entity_attribute_id" in item else None
        if key:
            item["version_attribute_id"] = attr_map.get(item.pop(key))
    return result


def _validate_source_entry(code, function_name, label):
    from app.services.function_runtime.sandbox import UnifiedSandbox
    validation = UnifiedSandbox().validate(code)
    if not validation.valid:
        raise ValueError(f"{label} 代码校验失败: {'; '.join(validation.errors)}")
    tree = ast.parse(code)
    if not any(isinstance(node, ast.FunctionDef) and node.name == function_name for node in tree.body):
        raise ValueError(f"{label} 缺少已登记的入口 {function_name}，请等待登记或修复后再发布")


def snapshot_components_for_version(db: Session, version, *, replace=False) -> dict:
    """Freeze code/config on submission; approval reuses the reviewed snapshot."""
    existing_f = db.query(OntologyVersionFunction).filter_by(version_id=version.id)
    existing_a = db.query(OntologyVersionAction).filter_by(version_id=version.id)
    if not replace and (getattr(version, "components_frozen", False) or existing_f.count() or existing_a.count()):
        return {"functions_count": existing_f.count(), "actions_count": existing_a.count()}
    if replace:
        existing_f.delete(synchronize_session=False)
        existing_a.delete(synchronize_session=False)
    entities = {e.source_entity_id: e for e in version.entities}
    if not entities:
        version.components_frozen = True
        return {"functions_count": 0, "actions_count": 0}
    attr_map = {a.source_attribute_id: a.id for e in entities.values() for a in e.attributes}
    scoped = [OntologyFunction.entity_id.in_(entities)]
    if version.ontology_id:
        scoped.append(OntologyFunction.ontology_id == version.ontology_id)
    functions = db.query(OntologyFunction).filter(or_(*scoped), OntologyFunction.status == "active").all()
    for fn in functions:
        from app.services.action_contracts import validate_parameter_references
        validate_parameter_references(db, fn.input_schema, version.ontology_id)
        owners = {fn.ontology_id} if fn.ontology_id else set()
        for entity_id in set(fn.entity_ids or []) | ({fn.entity_id} if fn.entity_id else set()):
            from app.models.entity import OntologyEntity
            linked = db.get(OntologyEntity, entity_id)
            if not linked:
                raise ValueError(f"函数 {fn.name} 引用的对象不存在")
            owners.add(linked.ontology_id)
        if owners and owners != {version.ontology_id}:
            raise ValueError(f"函数 {fn.name} 的关联对象不属于当前本体")
        source_code = None
        checksum = fn.checksum
        if fn.source_path:
            try:
                source_code = Path(fn.source_path).read_text(encoding="utf-8")
            except OSError as exc:
                raise ValueError(f"函数 {fn.name} 的工作区源码不可读取，无法发布") from exc
            _validate_source_entry(source_code, fn.func_name or fn.callable_name, f"函数 {fn.name}")
            checksum = hashlib.sha256(source_code.encode()).hexdigest()
        else:
            if not (fn.logic_body or "").strip():
                raise ValueError(f"函数 {fn.name} 的执行内容不能为空，请完善代码或设为草稿")
            if fn.logic_type == "sql":
                from app.services.data_plane.sql_introspect import introspect
                analysis = introspect(fn.logic_body)
                if not analysis.ok or not analysis.is_select or not fn.entity_id:
                    raise ValueError(f"SQL 函数 {fn.name} 必须绑定对象并提供有效的只读 SELECT")
            elif fn.logic_type in {"expression", "python"}:
                from app.services.function_runtime.sandbox import UnifiedSandbox
                from textwrap import indent
                code = fn.logic_body if fn.logic_type == "expression" else "def execute(params):\n" + indent(fn.logic_body, "    ")
                validation = UnifiedSandbox().validate(code)
                if not validation.valid:
                    raise ValueError(f"函数 {fn.name} 代码校验失败: {'; '.join(validation.errors)}")
                if fn.logic_type == "expression":
                    try:
                        ast.parse(fn.logic_body, mode="eval")
                    except SyntaxError as exc:
                        raise ValueError(f"函数 {fn.name} 必须为单个表达式") from exc
            else:
                raise ValueError(f"函数 {fn.name} 使用未支持的执行类型 {fn.logic_type}")
        # Legacy schema requires a version_entity_id. Ontology-scoped functions
        # attach to a representative entity while retaining explicit entity_ids.
        ve = entities.get(fn.entity_id) or next(iter(entities.values()))
        db.add(OntologyVersionFunction(
            version_id=version.id, source_function_id=fn.id, version_entity_id=ve.id,
            name=fn.name, description=fn.description, return_type=fn.return_type,
            input_schema=_remap_attr_ids(fn.input_schema, attr_map),
            logic_type=fn.logic_type, logic_body=fn.logic_body,
            callable_name=fn.callable_name, tags=copy.deepcopy(fn.tags),
            source_code=source_code, func_name=fn.func_name, checksum=checksum,
            ontology_id=fn.ontology_id or version.ontology_id,
            entity_ids=copy.deepcopy(fn.entity_ids or ([fn.entity_id] if fn.entity_id else [])),
        ))
    actions = db.query(EntityAction).filter(
        EntityAction.status == "active",
        or_(EntityAction.entity_id.in_(entities),
            EntityAction.ontology_id == version.ontology_id if version.ontology_id else
            (EntityAction.entity_id.is_(None) & EntityAction.ontology_id.is_(None))),
    ).all()
    for action in actions:
        from app.services.action_contracts import validate_action_config, validate_parameter_references
        validate_parameter_references(db, action.parameters_json, version.ontology_id)
        if action.ontology_id and action.ontology_id != version.ontology_id:
            raise ValueError(f"行动 {action.name} 不属于当前本体")
        validate_action_config(db, action.action_type, action.type_config, version.ontology_id, action.entity_id)
        ve = entities.get(action.entity_id)
        type_config = copy.deepcopy(action.type_config or {})
        if action.action_type == "custom_script" and type_config.get("source_path"):
            try:
                type_config["source_code"] = Path(type_config["source_path"]).read_text(encoding="utf-8")
            except OSError as exc:
                raise ValueError(f"行动 {action.name} 的工作区源码不可读取，无法发布") from exc
            _validate_source_entry(type_config["source_code"], type_config.get("func_name"), f"行动 {action.name}")
            type_config["checksum"] = hashlib.sha256(type_config["source_code"].encode()).hexdigest()
        type_config["ontology_id"] = action.ontology_id or version.ontology_id
        type_config["version_id"] = version.id
        db.add(OntologyVersionAction(
            version_id=version.id, source_action_id=action.id,
            version_entity_id=ve.id if ve else None,
            name=action.name, category=action.category, action_type=action.action_type,
            type_config=type_config, description=action.description,
            parameters_json=_remap_attr_ids(action.parameters_json, attr_map),
            output_schema=copy.deepcopy(action.output_schema),
        ))
    version.components_frozen = True
    db.flush()
    return {"functions_count": len(functions), "actions_count": len(actions)}


def clone_components_for_version(db, source, target, entity_map, attr_map):
    """Rollback copies history, including code, rather than resnapshotting drafts."""
    for model in (OntologyVersionFunction, OntologyVersionAction):
        for original in db.query(model).filter_by(version_id=source.id).all():
            fields = {c.name: copy.deepcopy(getattr(original, c.name))
                      for c in model.__table__.columns if c.name not in {"id", "created_at"}}
            fields["version_id"] = target.id
            fields["version_entity_id"] = entity_map.get(original.version_entity_id)
            if model is OntologyVersionAction and fields.get("type_config"):
                fields["type_config"]["version_id"] = target.id
            schema_key = "input_schema" if model is OntologyVersionFunction else "parameters_json"
            for param in fields[schema_key] or []:
                if "version_attribute_id" in param:
                    param["version_attribute_id"] = attr_map.get(param["version_attribute_id"])
            db.add(model(**fields))
    target.components_frozen = True
    db.flush()


def capture_binding(db, entity_id):
    from app.models.object_binding import ObjectBinding
    from app.models.asset import Asset
    binding = db.query(ObjectBinding).filter_by(object_type_id=entity_id, role="primary", status="active").first()
    if not binding:
        return None
    asset = db.get(Asset, binding.asset_id)
    def primary_keys(source):
        return sorted(set(source.primary_key or []) | {
            column.get("name") for column in source.schema_snapshot or [] if column.get("is_pk") and column.get("name")
        }) if source else []
    enrichments = []
    for enrichment in db.query(ObjectBinding).filter_by(object_type_id=entity_id, role="enrichment").filter(ObjectBinding.status != "deprecated").all():
        enrichment_asset = db.get(Asset, enrichment.asset_id)
        enrichments.append({"binding_id": enrichment.id, "asset_id": enrichment.asset_id,
            "primary_source_column": getattr(enrichment, "primary_source_column", None),
            "enrichment_source_column": getattr(enrichment, "enrichment_source_column", None),
            "field_mappings": copy.deepcopy(enrichment.field_mappings), "filter_expr": enrichment.filter_expr,
            "asset_locator": copy.deepcopy(enrichment_asset.locator if enrichment_asset else None),
            "asset_primary_keys": primary_keys(enrichment_asset),
            "connection_id": enrichment_asset.connection_id if enrichment_asset else None,
            "status": enrichment.status})
    return {"asset_id": binding.asset_id, "id_column": binding.id_column,
            "field_mappings": copy.deepcopy(binding.field_mappings), "filter_expr": binding.filter_expr,
            "asset_locator": copy.deepcopy(asset.locator if asset else None),
            "asset_primary_keys": primary_keys(asset),
            "connection_id": asset.connection_id if asset else None, "enrichments": enrichments}
