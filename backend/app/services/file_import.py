"""
文件导入服务：支持 JSON（V1.1 本体规范）和 OWL/TTL 格式
"""
import json
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.entity import OntologyEntity, EntityAttribute, gen_uuid
from app.models.relation import EntityRelation
from app.models.rule import BusinessRule, EntityAction


@dataclass
class ImportResult:
    entities_created: int = 0
    entities_skipped: int = 0
    attributes_created: int = 0
    relations_created: int = 0
    rules_created: int = 0
    actions_created: int = 0
    errors: list[str] = field(default_factory=list)


# ── JSON 类型映射 ──
_JSON_TYPE_MAP = {
    "string": "string", "number": "number", "boolean": "boolean",
    "datetime": "date", "enum": "string", "reference": "ref",
    "array": "json", "object": "json",
}


def parse_json_ontology(data: dict, namespace: str, db: Session) -> ImportResult:
    """按 V1.1 本体 JSON Schema 规范解析，复用 import_schema.py 的逻辑。"""
    result = ImportResult()

    if not namespace:
        scenario = data.get("scenario", {})
        namespace = scenario.get("namespace", "")

    # ── object_types → OntologyEntity + EntityAttribute ──
    entity_map: dict[str, str] = {}
    for obj in data.get("object_types", []):
        eid = f"{namespace}_{obj['name']}" if namespace else obj["name"]

        existing = db.query(OntologyEntity).filter(OntologyEntity.id == eid).first()
        if existing:
            entity_map[obj["name"]] = eid
            result.entities_skipped += 1
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
        result.entities_created += 1

        # 属性
        for prop in obj.get("properties", []):
            constraints: dict = {}
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
                type=_JSON_TYPE_MAP.get(prop.get("type", "string"), "string"),
                description=prop.get("description", prop.get("display_name", "")),
                required=prop.get("required", False),
                example=prop.get("default"),
                constraints_json=constraints if constraints else None,
            )
            db.add(attr)
            result.attributes_created += 1

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
            result.attributes_created += 1

    db.flush()

    # ── link_types → EntityRelation ──
    cardinality_map = {
        "one_to_many": "1:N", "many_to_one": "N:1",
        "one_to_one": "1:1", "many_to_many": "N:N",
    }
    for link in data.get("link_types", []):
        source = link.get("source_type", "")
        target = link.get("target_type", "")
        source_ns = link.get("source_namespace", namespace)
        target_ns = link.get("target_namespace", namespace)
        from_id = f"{source_ns}_{source}" if source_ns else source
        to_id = f"{target_ns}_{target}" if target_ns else target

        # namespace 感知的实体查找
        if not db.get(OntologyEntity, from_id):
            if db.get(OntologyEntity, source):
                from_id = source
            else:
                found = db.query(OntologyEntity).filter(OntologyEntity.name == source).first()
                from_id = found.id if found else from_id
        if not db.get(OntologyEntity, to_id):
            if db.get(OntologyEntity, target):
                to_id = target
            else:
                found = db.query(OntologyEntity).filter(OntologyEntity.name == target).first()
                to_id = found.id if found else to_id

        if not db.get(OntologyEntity, from_id) or not db.get(OntologyEntity, to_id):
            result.errors.append(f"关系 {source} -> {target} 跳过（实体未找到）")
            continue

        # 跳过已存在的关系
        existing = db.query(EntityRelation).filter(
            EntityRelation.from_entity_id == from_id,
            EntityRelation.to_entity_id == to_id,
            EntityRelation.name == link["name"],
        ).first()
        if existing:
            continue

        card = cardinality_map.get(link.get("cardinality", ""), link.get("cardinality", "1:N"))
        rel = EntityRelation(
            from_entity_id=from_id, to_entity_id=to_id,
            name=link["name"], rel_type=link.get("directionality", "directed"),
            cardinality=card, description=link.get("description"),
        )
        db.add(rel)
        result.relations_created += 1

    # ── action_types → EntityAction ──
    for act in data.get("action_types", []):
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
            result.actions_created += 1

    # ── business_rules → BusinessRule ──
    for rule in data.get("business_rules", []):
        entity_id = None
        # 尝试从 applies_to 或 category 关联实体
        applies_to = rule.get("applies_to_objects", [])
        if applies_to:
            for obj_name in applies_to:
                if obj_name in entity_map:
                    entity_id = entity_map[obj_name]
                    break
        if not entity_id:
            entity_id = list(entity_map.values())[0] if entity_map else None
        if not entity_id:
            continue

        condition = rule.get("condition", {})
        condition_expr = json.dumps(condition, ensure_ascii=False) if condition else ""
        actions = rule.get("actions", [])
        action_desc = "; ".join(
            a.get("description", a.get("action", "")) for a in actions
        ) if actions else rule.get("description", "")

        priority_val = rule.get("priority", 5)
        if isinstance(priority_val, int):
            priority = "high" if priority_val <= 2 else "medium" if priority_val <= 5 else "low"
        else:
            priority = str(priority_val)

        br = BusinessRule(
            entity_id=entity_id,
            name=rule.get("display_name", rule.get("rule_id", "")),
            condition_expr=condition_expr,
            action_desc=action_desc,
            status="active",
            priority=priority,
        )
        db.add(br)
        result.rules_created += 1

    return result


# ── OWL/TTL 解析 ──
_OWL = "http://www.w3.org/2002/07/owl#"
_RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
_RDFS = "http://www.w3.org/2000/01/rdf-schema#"
_XSD = "http://www.w3.org/2001/XMLSchema#"

_XSD_TYPE_MAP = {
    f"{_XSD}string": "string", f"{_XSD}normalizedString": "string",
    f"{_XSD}integer": "number", f"{_XSD}int": "number", f"{_XSD}long": "number",
    f"{_XSD}float": "number", f"{_XSD}double": "number", f"{_XSD}decimal": "number",
    f"{_XSD}boolean": "boolean",
    f"{_XSD}dateTime": "date", f"{_XSD}date": "date", f"{_XSD}time": "date",
}


def _local_name(uri: str) -> str:
    """从 URI 提取 local name。"""
    if "#" in uri:
        return uri.split("#")[-1]
    return uri.rsplit("/", 1)[-1]


def parse_owl_ontology(content: bytes, fmt: str, db: Session) -> ImportResult:
    """解析 OWL/XML 或 TTL 文件。"""
    from rdflib import Graph, RDF, RDFS, OWL, URIRef

    result = ImportResult()
    g = Graph()
    g.parse(data=content, format=fmt)

    entity_map: dict[str, str] = {}  # URI -> entity_id

    # ── owl:Class → OntologyEntity ──
    for cls in g.subjects(RDF.type, OWL.Class):
        uri = str(cls)
        name = _local_name(uri)
        if not name or name.startswith("_:"):
            continue

        # rdfs:label 作为中文名
        labels = list(g.objects(cls, RDFS.label))
        name_cn = str(labels[0]) if labels else name

        # rdfs:comment 作为描述
        comments = list(g.objects(cls, RDFS.comment))
        description = str(comments[0]) if comments else ""

        eid = name
        existing = db.query(OntologyEntity).filter(OntologyEntity.id == eid).first()
        if existing:
            entity_map[uri] = eid
            result.entities_skipped += 1
            continue

        entity = OntologyEntity(
            id=eid, name=name, name_cn=name_cn,
            tier=3, status="active", description=description,
        )
        db.add(entity)
        entity_map[uri] = eid
        result.entities_created += 1

    db.flush()

    # ── rdfs:subClassOf → 父子关系 ──
    for sub, _, parent in g.triples((None, RDFS.subClassOf, None)):
        sub_uri, parent_uri = str(sub), str(parent)
        if sub_uri not in entity_map or parent_uri not in entity_map:
            continue
        from_id = entity_map[sub_uri]
        to_id = entity_map[parent_uri]
        existing = db.query(EntityRelation).filter(
            EntityRelation.from_entity_id == from_id,
            EntityRelation.to_entity_id == to_id,
            EntityRelation.name == "subClassOf",
        ).first()
        if not existing:
            rel = EntityRelation(
                from_entity_id=from_id, to_entity_id=to_id,
                name="subClassOf", rel_type="subclass",
                cardinality="N:1", description=f"{_local_name(sub_uri)} 是 {_local_name(parent_uri)} 的子类",
            )
            db.add(rel)
            result.relations_created += 1

    # ── owl:DatatypeProperty → EntityAttribute ──
    for prop in g.subjects(RDF.type, OWL.DatatypeProperty):
        prop_uri = str(prop)
        prop_name = _local_name(prop_uri)

        # rdfs:domain → 关联实体
        domains = list(g.objects(prop, RDFS.domain))
        if not domains:
            continue
        domain_uri = str(domains[0])
        entity_id = entity_map.get(domain_uri)
        if not entity_id:
            continue

        # rdfs:range → 类型
        ranges = list(g.objects(prop, RDFS.range))
        attr_type = "string"
        if ranges:
            attr_type = _XSD_TYPE_MAP.get(str(ranges[0]), "string")

        labels = list(g.objects(prop, RDFS.label))
        description = str(labels[0]) if labels else prop_name

        attr = EntityAttribute(
            entity_id=entity_id,
            name=prop_name,
            type=attr_type,
            description=description,
            required=False,
        )
        db.add(attr)
        result.attributes_created += 1

    # ── owl:ObjectProperty → EntityRelation ──
    for prop in g.subjects(RDF.type, OWL.ObjectProperty):
        prop_uri = str(prop)
        prop_name = _local_name(prop_uri)

        domains = list(g.objects(prop, RDFS.domain))
        ranges = list(g.objects(prop, RDFS.range))
        if not domains or not ranges:
            continue

        from_id = entity_map.get(str(domains[0]))
        to_id = entity_map.get(str(ranges[0]))
        if not from_id or not to_id:
            continue

        existing = db.query(EntityRelation).filter(
            EntityRelation.from_entity_id == from_id,
            EntityRelation.to_entity_id == to_id,
            EntityRelation.name == prop_name,
        ).first()
        if existing:
            continue

        labels = list(g.objects(prop, RDFS.label))
        desc = str(labels[0]) if labels else prop_name

        rel = EntityRelation(
            from_entity_id=from_id, to_entity_id=to_id,
            name=prop_name, rel_type="has_many",
            cardinality="1:N", description=desc,
        )
        db.add(rel)
        result.relations_created += 1

    return result
