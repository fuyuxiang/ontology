"""
本体 Schema JSON 导入器
支持导入标准格式的本体 JSON 文件（object_types + link_types + action_types）
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, Base
from app.models.entity import OntologyEntity, EntityAttribute, gen_uuid
from app.models.relation import EntityRelation
from app.models.rule import BusinessRule, EntityAction


def import_schema(json_path: str, db):
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    scenario = data.get("scenario", {})
    namespace = scenario.get("namespace", "")
    scenario_name = scenario.get("scenario_name", json_path)
    print(f"\n=== Importing: {scenario_name} (ns={namespace}) ===")

    # ── 导入 object_types ──
    entity_map = {}
    for obj in data.get("object_types", []):
        eid = f"{namespace}_{obj['name']}" if namespace else obj["name"]

        # 跳过已存在的
        existing = db.query(OntologyEntity).filter(OntologyEntity.id == eid).first()
        if existing:
            print(f"  [skip] {obj['name']} already exists")
            entity_map[obj["name"]] = eid
            continue

        entity = OntologyEntity(
            id=eid,
            name=obj["name"],
            name_cn=obj.get("display_name", obj["name"]),
            tier=obj.get("tier", 3),
            status="active",
            description=obj.get("description", ""),
            schema_json={
                "namespace": namespace,
                "primary_key": obj.get("primary_key"),
                "datasource_ref": obj.get("datasource_ref"),
            },
        )
        db.add(entity)
        entity_map[obj["name"]] = eid

        # 属性
        for prop in obj.get("properties", []):
            constraints = {}
            if prop.get("enum_values"):
                constraints["enumValues"] = prop["enum_values"]
                constraints["enumLabels"] = prop.get("enum_labels", [])
            if prop.get("min") is not None:
                constraints["min"] = prop["min"]
            if prop.get("max") is not None:
                constraints["max"] = prop["max"]
            if prop.get("pattern"):
                constraints["pattern"] = prop["pattern"]
            if prop.get("indexed"):
                constraints["indexed"] = True
            if prop.get("precision"):
                constraints["precision"] = prop["precision"]

            attr = EntityAttribute(
                entity_id=eid,
                name=prop["name"],
                type=prop.get("type", "string"),
                description=prop.get("description", prop.get("display_name", "")),
                required=prop.get("required", False),
                example=prop.get("default", None),
                constraints_json=constraints if constraints else None,
            )
            db.add(attr)

        # computed_properties
        for cp in obj.get("computed_properties", []):
            attr = EntityAttribute(
                entity_id=eid,
                name=cp["name"],
                type="computed",
                description=cp.get("description", cp.get("display_name", "")),
                required=False,
                constraints_json={"expression": cp.get("expression", "")},
            )
            db.add(attr)

        prop_count = len(obj.get("properties", [])) + len(obj.get("computed_properties", []))
        print(f"  [+] {obj['name']} ({obj.get('display_name', '')}) - {prop_count} props")

    db.flush()

    # ── 导入 link_types ──
    for link in data.get("link_types", []):
        source = link.get("source_type", "")
        target = link.get("target_type", "")

        # 解析 namespace
        source_ns = link.get("source_namespace", namespace)
        target_ns = link.get("target_namespace", namespace)
        from_id = f"{source_ns}_{source}" if source_ns else source
        to_id = f"{target_ns}_{target}" if target_ns else target

        # 如果目标是 core 命名空间的对象（如 Staff），跳过（不在当前数据库中）
        if not db.get(OntologyEntity, from_id) or not db.get(OntologyEntity, to_id):
            # 尝试不带 namespace
            if db.get(OntologyEntity, source):
                from_id = source
            if db.get(OntologyEntity, target):
                to_id = target
            # 尝试按 name 字段查找
            if not db.get(OntologyEntity, from_id):
                found = db.query(OntologyEntity).filter(OntologyEntity.name == source).first()
                if found:
                    from_id = found.id
            if not db.get(OntologyEntity, to_id):
                found = db.query(OntologyEntity).filter(OntologyEntity.name == target).first()
                if found:
                    to_id = found.id
            if not db.get(OntologyEntity, from_id) or not db.get(OntologyEntity, to_id):
                print(f"  [skip link] {source} -> {target} (entity not found)")
                continue

        # 检查是否已存在
        existing = db.query(EntityRelation).filter(
            EntityRelation.from_entity_id == from_id,
            EntityRelation.to_entity_id == to_id,
            EntityRelation.name == link["name"],
        ).first()
        if existing:
            continue

        cardinality_map = {
            "one_to_many": "1:N", "many_to_one": "N:1",
            "one_to_one": "1:1", "many_to_many": "N:N",
        }
        card = cardinality_map.get(link.get("cardinality", ""), link.get("cardinality", "1:N"))

        rel = EntityRelation(
            from_entity_id=from_id,
            to_entity_id=to_id,
            name=link["name"],
            rel_type=link.get("cardinality", "has_many"),
            cardinality=card,
            description=link.get("description", link.get("display_name", "")),
        )
        db.add(rel)
        print(f"  [+] {source} --[{link['name']}]--> {target} ({card})")

    # ── 导入 action_types ──
    for act in data.get("action_types", []):
        # 找关联实体（从 parameters 或 preconditions 推断）
        entity_id = None
        for obj_name, eid in entity_map.items():
            if obj_name.lower() in act.get("description", "").lower() or obj_name.lower() in act["name"].lower():
                entity_id = eid
                break
        if not entity_id:
            entity_id = list(entity_map.values())[0] if entity_map else None

        if entity_id:
            action = EntityAction(
                entity_id=entity_id,
                name=act.get("display_name", act["name"]),
                type=act.get("trigger", "automatic"),
                status="active",
            )
            db.add(action)
            print(f"  [+] Action: {act['name']} ({act.get('display_name', '')})")

    db.commit()
    print(f"  Done: {len(data.get('object_types', []))} objects, {len(data.get('link_types', []))} links, {len(data.get('action_types', []))} actions")


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    json_files = [
        r"E:\工作\国信\AI数据集项目\本体\材料\场景1-宽带装机退单稽核 本体Schema v2(1).json",
        r"E:\工作\国信\AI数据集项目\本体\材料\scenario4_ge_kpi_ontology_v5(1).json",
        r"E:\工作\国信\AI数据集项目\本体\材料\fttr_renewal_ontology.json",
    ]

    for jf in json_files:
        if os.path.exists(jf):
            import_schema(jf, db)
        else:
            print(f"File not found: {jf}")

    # 统计
    total_entities = db.query(OntologyEntity).count()
    total_attrs = db.query(EntityAttribute).count()
    total_rels = db.query(EntityRelation).count()
    total_actions = db.query(EntityAction).count()
    print(f"\n=== Total: {total_entities} entities, {total_attrs} attrs, {total_rels} relations, {total_actions} actions ===")

    db.close()
