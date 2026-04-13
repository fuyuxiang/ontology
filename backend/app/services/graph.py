"""
Neo4j 图服务层
- PostgreSQL 存结构化数据（实体属性、规则、用户、审计）
- Neo4j 存本体关系图谱（实体节点 + 关系边）
- 两者通过 entity_id 关联
- 所有 neo4j 导入延迟执行，避免 pandas/numpy 冲突
"""
from __future__ import annotations

from app.config import settings

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        from neo4j import GraphDatabase
        _driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
    return _driver


def close_driver():
    global _driver
    if _driver:
        _driver.close()
        _driver = None


def ensure_constraints(driver: Driver):
    """创建唯一性约束"""
    with driver.session() as session:
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE")


# ── 节点操作 ──

def upsert_entity_node(entity_id: str, name: str, name_cn: str, tier: int, status: str):
    driver = get_driver()
    with driver.session() as session:
        session.run(
            """
            MERGE (e:Entity {entity_id: $entity_id})
            SET e.name = $name, e.name_cn = $name_cn, e.tier = $tier, e.status = $status
            """,
            entity_id=entity_id, name=name, name_cn=name_cn, tier=tier, status=status,
        )


def delete_entity_node(entity_id: str):
    driver = get_driver()
    with driver.session() as session:
        session.run("MATCH (e:Entity {entity_id: $id}) DETACH DELETE e", id=entity_id)


# ── 关系操作 ──

def create_relation(from_id: str, to_id: str, rel_name: str, cardinality: str):
    driver = get_driver()
    with driver.session() as session:
        session.run(
            f"""
            MATCH (a:Entity {{entity_id: $from_id}})
            MATCH (b:Entity {{entity_id: $to_id}})
            MERGE (a)-[r:`{rel_name}`]->(b)
            SET r.cardinality = $cardinality
            """,
            from_id=from_id, to_id=to_id, cardinality=cardinality,
        )


def delete_relation(from_id: str, to_id: str, rel_name: str):
    driver = get_driver()
    with driver.session() as session:
        session.run(
            f"""
            MATCH (a:Entity {{entity_id: $from_id}})-[r:`{rel_name}`]->(b:Entity {{entity_id: $to_id}})
            DELETE r
            """,
            from_id=from_id, to_id=to_id,
        )


# ── 图遍历 ──

def get_neighbors(entity_id: str, depth: int = 2, direction: str = "both") -> dict:
    """获取指定实体的 N 度关联图"""
    driver = get_driver()
    dir_pattern = {
        "outgoing": "-[r*1..{depth}]->",
        "incoming": "<-[r*1..{depth}]-",
        "both": "-[r*1..{depth}]-",
    }[direction].replace("{depth}", str(depth))

    with driver.session() as session:
        result = session.run(
            f"""
            MATCH (start:Entity {{entity_id: $id}})
            OPTIONAL MATCH (start){dir_pattern}(neighbor:Entity)
            WITH start, collect(DISTINCT neighbor) AS neighbors
            UNWIND neighbors AS n
            OPTIONAL MATCH (n)-[rel]-(other:Entity) WHERE other IN neighbors OR other = start
            RETURN start, collect(DISTINCT n) AS nodes,
                   collect(DISTINCT {{from: startNode(rel).entity_id, to: endNode(rel).entity_id, type: type(rel), card: rel.cardinality}}) AS edges
            """,
            id=entity_id,
        )
        record = result.single()
        if not record:
            return {"nodes": [], "edges": []}

        start_node = record["start"]
        nodes = [
            {"id": start_node["entity_id"], "name": start_node["name"], "name_cn": start_node["name_cn"], "tier": start_node["tier"], "status": start_node["status"]}
        ]
        for n in record["nodes"]:
            if n and n["entity_id"] != entity_id:
                nodes.append({"id": n["entity_id"], "name": n["name"], "name_cn": n["name_cn"], "tier": n["tier"], "status": n["status"]})

        edges = []
        for e in record["edges"]:
            if e and e.get("from") and e.get("to"):
                edges.append({"from_id": e["from"], "to_id": e["to"], "label": e["type"], "cardinality": e.get("card", "")})

        return {"nodes": nodes, "edges": edges}


def get_full_graph() -> dict:
    """获取完整图谱"""
    driver = get_driver()
    with driver.session() as session:
        nodes_result = session.run("MATCH (e:Entity) RETURN e")
        nodes = []
        for record in nodes_result:
            n = record["e"]
            nodes.append({"id": n["entity_id"], "name": n["name"], "name_cn": n["name_cn"], "tier": n["tier"], "status": n["status"]})

        edges_result = session.run(
            "MATCH (a:Entity)-[r]->(b:Entity) RETURN a.entity_id AS from_id, a.name AS from_name, b.entity_id AS to_id, b.name AS to_name, type(r) AS label, r.cardinality AS cardinality"
        )
        edges = [dict(record) for record in edges_result]

        return {"nodes": nodes, "edges": edges}


# ── 无环检测（借鉴 clawhub DFS 模式）──

def check_acyclic(from_id: str, to_id: str) -> bool:
    """检查添加 from_id -> to_id 的边是否会产生环"""
    driver = get_driver()
    with driver.session() as session:
        result = session.run(
            """
            MATCH path = (target:Entity {entity_id: $to_id})-[*]->(start:Entity {entity_id: $from_id})
            RETURN count(path) > 0 AS has_cycle
            """,
            from_id=from_id, to_id=to_id,
        )
        record = result.single()
        return record["has_cycle"] if record else False
