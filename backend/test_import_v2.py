"""
模拟本体浏览器 -> 对象管理 -> 新建对象 -> 从文件导入JSON
将场景5v2.json通过系统API导入，而非硬编码在项目代码中
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, Base
from app.models.entity import OntologyEntity, EntityAttribute
from app.models.relation import EntityRelation
from app.models.rule import BusinessRule, EntityAction

# 确保表存在
Base.metadata.create_all(bind=engine)

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "场景5v2.json")


def simulate_file_import(json_path: str):
    """模拟前端上传JSON文件后，后端import_schema的完整流程"""
    if not os.path.exists(json_path):
        print(f"ERROR: 文件不存在: {json_path}")
        return False

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    scenario = data.get("scenario", {})
    namespace = scenario.get("namespace", "")
    print(f"\n{'='*60}")
    print(f"模拟导入: {scenario.get('scenario_name', '未知场景')}")
    print(f"命名空间: {namespace}")
    print(f"{'='*60}")

    db = SessionLocal()
    try:
        # ── 1. 导入 object_types (实体+属性) ──
        entity_map = {}
        for obj in data.get("object_types", []):
            eid = f"{namespace}_{obj['name']}" if namespace else obj["name"]

            # 清除已存在的同名实体(重新导入)
            existing = db.query(OntologyEntity).filter(OntologyEntity.id == eid).first()
            if existing:
                db.delete(existing)
                db.flush()

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
                    "datasource_name": obj.get("datasource_ref", ""),
                },
            )
            db.add(entity)
            entity_map[obj["name"]] = eid

            # 导入属性
            for prop in obj.get("properties", []):
                constraints = {}
                if prop.get("enum_values"):
                    constraints["enumValues"] = prop["enum_values"]
                    constraints["enumLabels"] = prop.get("enum_labels", [])
                if prop.get("min") is not None:
                    constraints["min"] = prop["min"]
                if prop.get("max") is not None:
                    constraints["max"] = prop["max"]
                if prop.get("indexed"):
                    constraints["indexed"] = True

                attr = EntityAttribute(
                    entity_id=eid,
                    name=prop["name"],
                    type=prop.get("type", "string"),
                    description=prop.get("description", prop.get("display_name", "")),
                    required=prop.get("required", False),
                    example=str(prop.get("default", "")) if prop.get("default") else None,
                    constraints_json=constraints if constraints else None,
                )
                db.add(attr)

            # 导入计算属性
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
            print(f"  [+] 实体: {obj['name']} ({obj.get('display_name','')}) - {prop_count} 属性")

        db.flush()

        # ── 2. 导入 link_types (关系) ──
        for link in data.get("link_types", []):
            source = link.get("source_type", "")
            target = link.get("target_type", "")
            source_ns = link.get("source_namespace", namespace)
            target_ns = link.get("target_namespace", namespace)
            from_id = f"{source_ns}_{source}" if source_ns else source
            to_id = f"{target_ns}_{target}" if target_ns else target

            if not db.get(OntologyEntity, from_id) or not db.get(OntologyEntity, to_id):
                print(f"  [skip] 关系: {source} -> {target} (实体不存在)")
                continue

            # 清除已存在的同名关系
            existing = db.query(EntityRelation).filter(
                EntityRelation.from_entity_id == from_id,
                EntityRelation.to_entity_id == to_id,
                EntityRelation.name == link["name"],
            ).first()
            if existing:
                db.delete(existing)
                db.flush()

            cardinality_map = {
                "one_to_many": "1:N", "many_to_one": "N:1",
                "one_to_one": "1:1", "many_to_many": "N:N",
            }
            card = cardinality_map.get(link.get("cardinality", ""), link.get("cardinality", "1:N"))

            rel = EntityRelation(
                from_entity_id=from_id,
                to_entity_id=to_id,
                name=link["name"],
                rel_type=link.get("directionality", "directed"),
                cardinality=card,
                description=link.get("description", ""),
            )
            db.add(rel)
            print(f"  [+] 关系: {source} --[{link['name']}]--> {target}")

        db.flush()

        # ── 3. 导入 action_types (动作) ──
        for act in data.get("action_types", []):
            entity_id = None
            for obj_name, eid in entity_map.items():
                if obj_name.lower() in act.get("description", "").lower() or obj_name.lower() in act["name"].lower():
                    entity_id = eid
                    break
            if not entity_id:
                # 默认关联到ChurnRiskWarning
                entity_id = entity_map.get("ChurnRiskWarning", list(entity_map.values())[0] if entity_map else None)

            if entity_id:
                action = EntityAction(
                    entity_id=entity_id,
                    name=act.get("display_name", act["name"]),
                    type=act.get("trigger", "automatic"),
                    status="active",
                )
                db.add(action)
                print(f"  [+] 动作: {act['name']} ({act.get('display_name', '')})")

        db.commit()

        # ── 统计 ──
        total_entities = db.query(OntologyEntity).count()
        total_attrs = db.query(EntityAttribute).count()
        total_rels = db.query(EntityRelation).count()
        total_actions = db.query(EntityAction).count()
        print(f"\n{'='*60}")
        print(f"导入完成!")
        print(f"  实体: {total_entities}, 属性: {total_attrs}, 关系: {total_rels}, 动作: {total_actions}")
        print(f"{'='*60}")
        return True

    except Exception as e:
        db.rollback()
        print(f"ERROR: 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else SCHEMA_PATH
    print(f"导入文件: {os.path.abspath(path)}")
    success = simulate_file_import(path)
    sys.exit(0 if success else 1)
