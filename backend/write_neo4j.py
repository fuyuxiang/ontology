"""
将场景5v2.json中的本体实体、属性、关系三元组写入Neo4j
Neo4j: bolt://123.56.188.16:7687, user=bonc, password=bonc12345
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "场景5v2.json")
NEO4J_URI = "bolt://123.56.188.16:7687"
NEO4J_USER = "bonc"
NEO4J_PASSWORD = "bonc12345"


def write_to_neo4j(schema_path: str):
    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)

    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("ERROR: neo4j包未安装，请执行 pip install neo4j")
        return False

    print(f"连接Neo4j: {NEO4J_URI}")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        print("Neo4j连接成功")
    except Exception as e:
        print(f"ERROR: Neo4j连接失败: {e}")
        return False

    with driver.session() as session:
        # ── 清除旧数据(同namespace) ──
        ns = schema.get("scenario", {}).get("namespace", "s5")
        session.run("MATCH (n {namespace: $ns}) DETACH DELETE n", ns=ns)
        print(f"已清除namespace={ns}的旧数据")

        # ── 1. 写入实体节点 ──
        print(f"\n--- 写入实体节点 ---")
        for obj in schema.get("object_types", []):
            entity_id = f"{ns}_{obj['name']}"
            props = {
                "entity_id": entity_id,
                "name": obj["name"],
                "display_name": obj.get("display_name", ""),
                "tier": obj.get("tier", 3),
                "namespace": ns,
                "description": obj.get("description", ""),
                "primary_key": obj.get("primary_key", ""),
                "datasource_ref": obj.get("datasource_ref", ""),
            }
            session.run(
                """
                MERGE (e:OntologyEntity {entity_id: $entity_id})
                SET e += $props
                """,
                entity_id=entity_id, props=props
            )
            print(f"  [+] 实体: {obj['name']} (tier{obj.get('tier',3)})")

            # ── 2. 写入属性节点并关联 ──
            for prop in obj.get("properties", []):
                attr_id = f"{entity_id}.{prop['name']}"
                attr_props = {
                    "attr_id": attr_id,
                    "name": prop["name"],
                    "display_name": prop.get("display_name", ""),
                    "type": prop.get("type", "string"),
                    "required": prop.get("required", False),
                    "description": prop.get("description", ""),
                    "namespace": ns,
                }
                session.run(
                    """
                    MERGE (a:EntityAttribute {attr_id: $attr_id})
                    SET a += $props
                    WITH a
                    MATCH (e:OntologyEntity {entity_id: $entity_id})
                    MERGE (e)-[:HAS_ATTRIBUTE]->(a)
                    """,
                    attr_id=attr_id, props=attr_props, entity_id=entity_id
                )

            # 计算属性
            for cp in obj.get("computed_properties", []):
                attr_id = f"{entity_id}.{cp['name']}"
                attr_props = {
                    "attr_id": attr_id,
                    "name": cp["name"],
                    "display_name": cp.get("display_name", ""),
                    "type": "computed",
                    "expression": cp.get("expression", ""),
                    "description": cp.get("description", ""),
                    "namespace": ns,
                }
                session.run(
                    """
                    MERGE (a:EntityAttribute {attr_id: $attr_id})
                    SET a += $props
                    WITH a
                    MATCH (e:OntologyEntity {entity_id: $entity_id})
                    MERGE (e)-[:HAS_COMPUTED_ATTRIBUTE]->(a)
                    """,
                    attr_id=attr_id, props=attr_props, entity_id=entity_id
                )

            prop_count = len(obj.get("properties", [])) + len(obj.get("computed_properties", []))
            print(f"       {prop_count} 个属性已写入")

        # ── 3. 写入关系三元组 ──
        print(f"\n--- 写入关系三元组 ---")
        for link in schema.get("link_types", []):
            src_ns = link.get("source_namespace", ns)
            tgt_ns = link.get("target_namespace", ns)
            from_id = f"{src_ns}_{link['source_type']}"
            to_id = f"{tgt_ns}_{link['target_type']}"

            session.run(
                """
                MATCH (s:OntologyEntity {entity_id: $from_id})
                MATCH (t:OntologyEntity {entity_id: $to_id})
                MERGE (s)-[r:ONTOLOGY_RELATION {name: $name}]->(t)
                SET r.display_name = $display_name,
                    r.cardinality = $cardinality,
                    r.description = $description,
                    r.namespace = $namespace
                """,
                from_id=from_id, to_id=to_id,
                name=link["name"],
                display_name=link.get("display_name", ""),
                cardinality=link.get("cardinality", "one_to_many"),
                description=link.get("description", ""),
                namespace=ns,
            )
            print(f"  [+] {link['source_type']} --[{link['name']}]--> {link['target_type']}")

        # ── 统计 ──
        result = session.run("MATCH (e:OntologyEntity {namespace: $ns}) RETURN count(e) AS cnt", ns=ns)
        entity_count = result.single()["cnt"]
        result = session.run("MATCH (a:EntityAttribute {namespace: $ns}) RETURN count(a) AS cnt", ns=ns)
        attr_count = result.single()["cnt"]
        result = session.run("MATCH ()-[r:ONTOLOGY_RELATION {namespace: $ns}]->() RETURN count(r) AS cnt", ns=ns)
        rel_count = result.single()["cnt"]

        print(f"\n{'='*60}")
        print(f"Neo4j写入完成!")
        print(f"  实体节点: {entity_count}, 属性节点: {attr_count}, 关系: {rel_count}")
        print(f"{'='*60}")

    driver.close()
    return True


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else SCHEMA_PATH
    print(f"Schema文件: {os.path.abspath(path)}")
    success = write_to_neo4j(path)
    sys.exit(0 if success else 1)
