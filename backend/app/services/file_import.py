"""
文件导入服务：支持 JSON（V1.1 本体规范）和 OWL/TTL 格式
"""
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.action import EntityAction
from app.models.entity import EntityAttribute, OntologyEntity
from app.models.relation import EntityRelation
from app.utils.identifiers import gen_uuid


@dataclass
class ImportResult:
    entities_created: int = 0
    entities_skipped: int = 0
    attributes_created: int = 0
    relations_created: int = 0
    rules_created: int = 0
    actions_created: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ── JSON 类型映射 ──
_JSON_TYPE_MAP = {
    "string": "string", "number": "number", "boolean": "boolean",
    "datetime": "date", "enum": "string", "reference": "ref",
    "array": "json", "object": "json", "integer": "integer", "date": "date", "json": "json", "ref": "ref",
}


def _normalize_json_contract(data: dict) -> dict:
    """Accept the studio's exported structure as well as V1.1 import names."""
    data = dict(data)
    if "object_types" not in data and "objects" in data:
        data["object_types"] = data.pop("objects")
    if "link_types" not in data and "relations" in data:
        data["link_types"] = [{**relation, "source_type": relation.get("source_type", relation.get("source")),
                               "target_type": relation.get("target_type", relation.get("target"))} for relation in data.pop("relations")]
    if "action_types" not in data and "actions" in data:
        data["action_types"] = data.pop("actions")
    return data


def persist_import_actions(actions: list[dict], entity_ids: dict[str, str], ontology_id: str | None, db: Session) -> tuple[int, list[str]]:
    """Persist explicit executable definitions, retaining legacy business hints."""
    from app.schemas.action import ActionCreate, ACTION_TYPES
    from app.api.v1.actions import _validate_action_scope
    from app.services.action_executors import get_executor
    created, warnings = 0, []
    for specification in actions:
        kind = specification.get("action_type") or specification.get("type")
        target = specification.get("target_object") or specification.get("entity_name")
        category = specification.get("category", "domain")
        if kind not in ACTION_TYPES:
            # effects/automatic is an incomplete business suggestion, not an
            # executor. Preserve it on the target definition for later editing.
            entity = db.get(OntologyEntity, entity_ids.get(target)) if target else None
            if entity:
                hints = list((entity.config_json or {}).get("pending_action_specs", []))
                if specification not in hints:
                    entity.config_json = {**(entity.config_json or {}), "pending_action_specs": [*hints, specification]}
            warnings.append(f"动作 {specification.get('name', '')} 尚未指定六类执行器及配置，保留为待配置建议，未注册可执行动作")
            continue
        if category == "domain" and target not in entity_ids:
            raise ValueError(f"动作 {specification.get('name')} 必须指定当前本体的 target_object")
        configuration = specification.get("type_config") or {}
        missing = [name for name, field in get_executor(kind).get_config_schema().items()
                   if field.get("required") and configuration.get(name) in (None, "")]
        if missing:
            raise ValueError(f"动作 {specification.get('name')} 配置缺少必填字段: {', '.join(missing)}")
        validated = ActionCreate(
            name=specification.get("display_name") or specification["name"], description=specification.get("description"),
            category=category, entity_id=entity_ids.get(target) if category == "domain" else None,
            ontology_id=ontology_id, action_type=kind, type_config=specification.get("type_config") or {},
            parameters_json=specification.get("parameters_json", specification.get("parameters")),
            output_schema=specification.get("output_schema"), status="active",
        )
        existing = db.query(EntityAction).filter_by(ontology_id=ontology_id, entity_id=validated.entity_id, name=validated.name).first()
        values = _validate_action_scope(db, validated.model_dump(), existing)
        if existing:
            for key, value in values.items(): setattr(existing, key, value)
        else:
            db.add(EntityAction(**values)); created += 1
    return created, warnings

# ── 解析器实际消费的顶层字段；其余字段一律不会被导入 ──
_SUPPORTED_TOP_LEVEL_KEYS = {
    "scenario", "object_types", "link_types", "action_types", "data_sources",
}


def _collect_ignored_top_level(data: dict) -> list[str]:
    """返回文件中存在但解析器不消费的顶层字段名，用于向用户明示丢弃内容。"""
    return sorted(k for k in data if k not in _SUPPORTED_TOP_LEVEL_KEYS)


def _ignored_warning(data: dict) -> list[str]:
    ignored = _collect_ignored_top_level(data)
    if not ignored:
        return []
    return [f"以下顶层字段不在导入范围内，已忽略：{'、'.join(ignored)}"]


def parse_json_ontology(data: dict, namespace: str, db: Session, *, ontology_id: str | None = None) -> ImportResult:
    """按 V1.1 本体 JSON Schema 规范解析，复用 import_schema.py 的逻辑。"""
    data = _normalize_json_contract(data)
    result = ImportResult()
    result.warnings.extend(_ignored_warning(data))

    if not namespace:
        scenario = data.get("scenario", {})
        namespace = scenario.get("namespace", "")

    # ── 构建数据源逻辑名→物理表名映射 ──
    ds_logical_to_physical: dict[str, str] = {}
    for ds_def in data.get("data_sources", []):
        source_id = ds_def.get("source_id", "")
        tables = ds_def.get("tables", [])
        if source_id and tables:
            # 取第一个表的 table_name 作为物理名
            table_name = tables[0].get("table_name", "")
            if table_name:
                ds_logical_to_physical[source_id] = table_name

    def _resolve_ds_ref(logical_ref: str) -> str:
        """将逻辑数据源名翻译为物理表名，找不到则原样返回"""
        return ds_logical_to_physical.get(logical_ref, logical_ref) if logical_ref else ""

    # ── object_types → OntologyEntity + EntityAttribute ──
    entity_map: dict[str, str] = {}
    for obj in data.get("object_types", []):
        eid = f"{namespace}_{obj['name']}" if namespace else obj["name"]
        raw_ds_ref = obj.get("datasource_ref", "")
        resolved_ds_ref = _resolve_ds_ref(raw_ds_ref)

        existing = db.query(OntologyEntity).filter_by(ontology_id=ontology_id, name=obj["name"]).first()
        if existing:
            eid = existing.id
            entity_map[obj["name"]] = eid
            # 更新已有实体的 datasource_ref（可能之前是逻辑名）
            schema = existing.config_json or {}
            old_ref = schema.get("datasource_ref", "")
            if raw_ds_ref and old_ref != resolved_ds_ref:
                schema["datasource_ref"] = resolved_ds_ref
                existing.config_json = schema
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(existing, "config_json")
            result.entities_skipped += 1
            continue

        if ontology_id:
            eid = gen_uuid()
        entity = OntologyEntity(
            id=eid,
            name=obj["name"],
            name_cn=obj.get("display_name", obj["name"]),
            tier=obj.get("tier", 3),
            status="active",
            description=obj.get("description", ""),
            ontology_id=ontology_id,
            config_json={
                "namespace": namespace,
                "primary_key": obj.get("primary_key"),
                "datasource_ref": resolved_ds_ref,
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

    # Imported source fields use the same authoritative ObjectBinding write
    # path as the studio editor; compatibility columns alone are not grounding.
    from app.api.v1.entities import _sync_attribute_mappings
    from app.schemas.entity import AttributeMappingUpdate
    for obj in data.get("object_types", []):
        entity_id = entity_map.get(obj["name"])
        if not entity_id:
            continue
        attributes = {attr.name: attr for attr in db.query(EntityAttribute).filter_by(entity_id=entity_id).all()}
        mapped = []
        for property_definition in obj.get("properties", []):
            table = property_definition.get("source_table") or _resolve_ds_ref(obj.get("datasource_ref", ""))
            field = property_definition.get("source_field")
            if table and field:
                mapped.append(AttributeMappingUpdate(attribute_id=attributes[property_definition["name"]].id,
                              source_table=table, source_field=field, asset_id=property_definition.get("source_asset_id")))
        if mapped:
            _sync_attribute_mappings(db, db.get(OntologyEntity, entity_id), mapped, None)

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
        from_id = entity_map.get(source)
        to_id = entity_map.get(target)
        if not from_id:
            found = db.query(OntologyEntity).filter_by(name=source, ontology_id=ontology_id).first()
            from_id = found.id if found else None
        if not to_id:
            found = db.query(OntologyEntity).filter_by(name=target, ontology_id=ontology_id).first()
            to_id = found.id if found else None

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
            source_field=link.get("source_field", link.get("sourceField")),
            target_field=link.get("target_field", link.get("targetField")),
        )
        db.add(rel)
        result.relations_created += 1

    action_specs = preview_json_ontology(data, namespace)["actions"]
    result.actions_created, action_warnings = persist_import_actions(action_specs, entity_map, ontology_id, db)
    result.warnings.extend(action_warnings)

    return result


# ── 共享解析小函数（落库与预览两条路径复用，保证口径一致）──

# v5 link_types cardinality → 平台基数。注意 many_to_one 归一为 N:1（与落库一致）
_CARDINALITY_MAP = {
    "one_to_many": "1:N", "many_to_one": "N:1",
    "one_to_one": "1:1", "many_to_many": "N:N",
}


def _normalize_cardinality(raw: str) -> str:
    """归一基数；已是 1:N / N:1 / 1:1 / N:N 形式则原样返回，未知默认 1:N。"""
    if raw in ("1:N", "N:1", "1:1", "N:N"):
        return raw
    return _CARDINALITY_MAP.get(raw, "1:N")


def _build_ds_logical_to_physical(data: dict) -> dict[str, str]:
    """构建数据源逻辑名→物理表名映射（取每个 source 的第一张表）。"""
    mapping: dict[str, str] = {}
    for ds_def in data.get("data_sources", []):
        source_id = ds_def.get("source_id", "")
        tables = ds_def.get("tables", [])
        if source_id and tables:
            table_name = tables[0].get("table_name", "")
            if table_name:
                mapping[source_id] = table_name
    return mapping


def preview_json_ontology(data: dict, namespace: str) -> dict:
    """纯解析：把 v5 本体 JSON 解析成内存草稿结构，不接触数据库、不落库。

    供模版构建预览使用。解析口径与 parse_json_ontology 保持一致（类型映射、
    基数归一、数据源逻辑名→物理表映射、动作关联实体推断）。
    """
    data = _normalize_json_contract(data)
    if not namespace:
        namespace = data.get("scenario", {}).get("namespace", "")

    warnings: list[str] = _ignored_warning(data)
    ds_map = _build_ds_logical_to_physical(data)

    # ── object_types → objects（含属性，物理表映射）──
    objects: list[dict] = []
    object_names: set[str] = set()
    obj_ds_table: dict[str, str] = {}  # object name → 物理表名（属性 source_table 兜底用）
    property_count = 0
    for obj in data.get("object_types", []):
        name = obj["name"]
        object_names.add(name)
        ds_table = ds_map.get(obj.get("datasource_ref", ""), obj.get("datasource_ref", ""))
        obj_ds_table[name] = ds_table

        props: list[dict] = []
        for prop in obj.get("properties", []):
            props.append({
                "name": prop["name"],
                "display_name": prop.get("display_name", prop["name"]),
                "type": _JSON_TYPE_MAP.get(prop.get("type", "string"), "string"),
                "raw_type": prop.get("type", "string"),
                "required": prop.get("required", False),
                "description": prop.get("description", ""),
                "source_table": prop.get("source_table") or ds_table or None,
                "source_field": prop.get("source_field"),
            })
        property_count += len(props)

        objects.append({
            "name": name,
            "display_name": obj.get("display_name", name),
            "tier": obj.get("tier", 3),
            "namespace": obj.get("namespace", namespace) or None,
            "primary_key": obj.get("primary_key"),
            "description": obj.get("description", ""),
            "properties": props,
        })

    # ── link_types → relations（按对象名引用；缺失实体的关系跳过）──
    relations: list[dict] = []
    for link in data.get("link_types", []):
        source = link.get("source_type", "")
        target = link.get("target_type", "")
        if source not in object_names or target not in object_names:
            warnings.append(
                f"关系 {link.get('name', '')}（{source} -> {target}）跳过：两端对象未在 object_types 中定义"
            )
            continue
        relations.append({
            "name": link.get("name", ""),
            "display_name": link.get("display_name", link.get("name", "")),
            "source": source,
            "target": target,
            "cardinality": _normalize_cardinality(link.get("cardinality", "")),
            "description": link.get("description", ""),
            "source_field": link.get("source_field") or link.get("sourceField"),
            "target_field": link.get("target_field") or link.get("targetField"),
        })

    # ── action_types → actions（关联实体推断：effects.target > 名称/描述匹配 > 首个对象）──
    actions: list[dict] = []
    obj_name_list = list(object_names)
    for act in data.get("action_types", []):
        target_object = act.get("target_object") or act.get("entity_name")
        for eff in act.get("effects", []):
            t = eff.get("target", "")
            if t in object_names:
                target_object = t
                break
        if not target_object:
            for obj_name in obj_name_list:
                if obj_name.lower() in act.get("description", "").lower() \
                        or obj_name.lower() in act["name"].lower():
                    target_object = obj_name
                    break
        if not target_object and obj_name_list:
            target_object = obj_name_list[0]
        actions.append({
            "name": act["name"],
            "display_name": act.get("display_name", act["name"]),
            "trigger": act.get("trigger", "automatic"),
            "target_object": target_object,
            "description": act.get("description", ""),
            "action_type": act.get("action_type") or act.get("type"),
            "category": act.get("category", "domain"),
            "type_config": act.get("type_config"),
            "parameters_json": act.get("parameters_json", act.get("parameters")),
            "output_schema": act.get("output_schema"),
        })

    # ── data_sources（逻辑名 → 物理表）──
    data_sources: list[dict] = []
    for ds_def in data.get("data_sources", []):
        data_sources.append({
            "source_id": ds_def.get("source_id", ""),
            "physical_table": ds_map.get(ds_def.get("source_id", ""), ""),
            "display_name": ds_def.get("display_name", ""),
        })

    return {
        "objects": objects,
        "relations": relations,
        "actions": actions,
        "data_sources": data_sources,
        "warnings": warnings,
        "summary": {
            "object_count": len(objects),
            "relation_count": len(relations),
            "property_count": property_count,
            "action_count": len(actions),
        },
    }



def _resolve_entity_from_conditions(
    conditions: list[dict], entity_map: dict[str, str], namespace: str
) -> str | None:
    """从条件字段前缀（如 'SubscriberContract.is_contract_active'）解析关联实体ID"""
    for cond in conditions:
        field = cond.get("field", "")
        if "." in field:
            entity_name = field.split(".")[0]
            if entity_name in entity_map:
                return entity_map[entity_name]
    return None


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


def _load_owl_graph(content: bytes, fmt: str):
    """Read both RDF/XML and the OWL/XML exported by the local editor.

    OWL/XML is an axiom syntax, not RDF/XML. Translate the named vocabulary
    axioms consumed by this importer explicitly; never infer data bindings from
    OWL object properties. Unsupported reasoning/individual axioms are reported.
    """
    from urllib.parse import urljoin
    from xml.etree import ElementTree as ET
    from rdflib import Graph, Literal, OWL, RDF, RDFS, URIRef

    graph = Graph()
    warnings: list[str] = []
    root = None
    if fmt in {"xml", "application/rdf+xml", "owl", "owlxml"}:
        root = ET.fromstring(content)
    if root is None or root.tag != f"{{{_OWL}}}Ontology":
        graph.parse(data=content, format=fmt)
        return graph, warnings

    def tag(element):
        return element.tag.rsplit("}", 1)[-1]

    base = root.get("{http://www.w3.org/XML/1998/namespace}base") or root.get("ontologyIRI", "")
    prefixes = {"owl": _OWL, "rdf": _RDF, "rdfs": _RDFS, "xsd": _XSD}
    for element in root:
        if tag(element) == "Prefix":
            prefixes[element.get("name", "").rstrip(":")] = element.get("IRI", "")

    def iri(element):
        value = element.get("IRI") or element.get("abbreviatedIRI") or (element.text or "").strip()
        if not value:
            raise ValueError(f"OWL/XML 的 {tag(element)} 缺少 IRI")
        # Also accept the editor's annotation subjects (IRI text uses its prefix).
        if ":" in value and value.split(":", 1)[0] in prefixes:
            prefix, local = value.split(":", 1)
            return URIRef(prefixes[prefix] + local)
        return URIRef(urljoin(base, value))

    declaration_types = {"Class": OWL.Class, "DataProperty": OWL.DatatypeProperty, "ObjectProperty": OWL.ObjectProperty, "AnnotationProperty": OWL.AnnotationProperty}
    pairs = {
        "SubClassOf": ("Class", "Class", RDFS.subClassOf),
        "DataPropertyDomain": ("DataProperty", "Class", RDFS.domain),
        "DataPropertyRange": ("DataProperty", "Datatype", RDFS.range),
        "ObjectPropertyDomain": ("ObjectProperty", "Class", RDFS.domain),
        "ObjectPropertyRange": ("ObjectProperty", "Class", RDFS.range),
    }
    unsupported: set[str] = set()
    for axiom in root:
        name = tag(axiom)
        children = [child for child in axiom if tag(child) != "Annotation"]
        if name == "Prefix":
            continue
        if name == "Declaration" and len(children) == 1 and tag(children[0]) in declaration_types:
            graph.add((iri(children[0]), RDF.type, declaration_types[tag(children[0])]))
        elif name in pairs and len(children) == 2 and (tag(children[0]), tag(children[1])) == pairs[name][:2]:
            graph.add((iri(children[0]), pairs[name][2], iri(children[1])))
            for child in children:
                if tag(child) in declaration_types:
                    graph.add((iri(child), RDF.type, declaration_types[tag(child)]))
        elif name == "AnnotationAssertion" and len(children) == 3 and tag(children[0]) == "AnnotationProperty" and tag(children[2]) == "Literal":
            literal = children[2]
            language = literal.get("{http://www.w3.org/XML/1998/namespace}lang")
            datatype = literal.get("datatypeIRI")
            value = Literal(literal.text or "", lang=language, datatype=URIRef(datatype) if datatype and not language else None)
            graph.add((iri(children[1]), iri(children[0]), value))
        else:
            unsupported.add(name)
    if unsupported:
        warnings.append("以下 OWL/XML 公理保留在 OWL 文件中，未转成业务本体定义：" + "、".join(sorted(unsupported)))
    return graph, warnings


def parse_owl_ontology(content: bytes, fmt: str, db: Session, *, ontology_id: str | None = None) -> ImportResult:
    """解析 OWL/XML 或 TTL 文件。"""
    from rdflib import OWL, RDF, RDFS, Graph

    result = ImportResult()
    g, warnings = _load_owl_graph(content, fmt)
    result.warnings.extend(warnings)

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

        eid = gen_uuid() if ontology_id else name
        existing = db.query(OntologyEntity).filter_by(ontology_id=ontology_id, name=name).first()
        if existing:
            entity_map[uri] = existing.id
            result.entities_skipped += 1
            continue

        entity = OntologyEntity(
            id=eid, name=name, name_cn=name_cn,
            tier=3, status="active", description=description,
            ontology_id=ontology_id,
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

        if db.query(EntityAttribute).filter_by(entity_id=entity_id, name=prop_name).first():
            continue
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


def preview_owl_ontology(content: bytes, fmt: str, namespace: str = "") -> dict:
    """纯解析：把 OWL/XML 或 TTL 文件解析成内存草稿结构，不接触数据库、不落库。

    供模版构建预览使用。解析口径与 parse_owl_ontology 保持一致
    （owl:Class→对象、DatatypeProperty→属性、ObjectProperty/subClassOf→关系），
    返回结构与 preview_json_ontology / preview_excel_ontology 完全一致。
    """
    from rdflib import OWL, RDF, RDFS, Graph

    g, warnings = _load_owl_graph(content, fmt)

    # ── owl:Class → objects ──
    objects: list[dict] = []
    by_uri: dict[str, dict] = {}  # URI → object 草稿
    for cls in g.subjects(RDF.type, OWL.Class):
        uri = str(cls)
        name = _local_name(uri)
        if not name or name.startswith("_:"):
            continue
        if uri in by_uri:
            continue
        labels = list(g.objects(cls, RDFS.label))
        comments = list(g.objects(cls, RDFS.comment))
        obj = {
            "name": name,
            "display_name": str(labels[0]) if labels else name,
            "tier": 3,
            "namespace": namespace or None,
            "primary_key": None,
            "description": str(comments[0]) if comments else "",
            "properties": [],
        }
        by_uri[uri] = obj
        objects.append(obj)

    # ── owl:DatatypeProperty → 属性（按 rdfs:domain 挂到对象）──
    property_count = 0
    for prop in g.subjects(RDF.type, OWL.DatatypeProperty):
        domains = list(g.objects(prop, RDFS.domain))
        if not domains:
            continue
        obj = by_uri.get(str(domains[0]))
        if not obj:
            continue
        prop_name = _local_name(str(prop))
        if any(p["name"] == prop_name for p in obj["properties"]):
            continue
        ranges = list(g.objects(prop, RDFS.range))
        attr_type = _XSD_TYPE_MAP.get(str(ranges[0]), "string") if ranges else "string"
        labels = list(g.objects(prop, RDFS.label))
        obj["properties"].append({
            "name": prop_name,
            "display_name": str(labels[0]) if labels else prop_name,
            "type": attr_type,
            "raw_type": str(ranges[0]) if ranges else "string",
            "required": False,
            "description": str(labels[0]) if labels else prop_name,
            "source_table": None,
            "source_field": prop_name,
        })
        property_count += 1

    # ── 关系：subClassOf（父子）+ ObjectProperty（业务关系）──
    relations: list[dict] = []
    seen_rel: set[tuple[str, str, str]] = set()

    def _add_rel(src_uri: str, tgt_uri: str, name: str, display: str, card: str, desc: str) -> None:
        src, tgt = by_uri.get(src_uri), by_uri.get(tgt_uri)
        if not src or not tgt:
            return
        key = (src["name"], tgt["name"], name)
        if key in seen_rel:
            return
        seen_rel.add(key)
        relations.append({
            "name": name,
            "display_name": display or name,
            "source": src["name"],
            "target": tgt["name"],
            "cardinality": _normalize_cardinality(card),
            "description": desc,
        })

    for sub, _, parent in g.triples((None, RDFS.subClassOf, None)):
        _add_rel(
            str(sub), str(parent), "subClassOf", "子类",
            "N:1", f"{_local_name(str(sub))} 是 {_local_name(str(parent))} 的子类",
        )

    for prop in g.subjects(RDF.type, OWL.ObjectProperty):
        domains = list(g.objects(prop, RDFS.domain))
        ranges = list(g.objects(prop, RDFS.range))
        if not domains or not ranges:
            continue
        prop_name = _local_name(str(prop))
        labels = list(g.objects(prop, RDFS.label))
        _add_rel(
            str(domains[0]), str(ranges[0]), prop_name,
            str(labels[0]) if labels else prop_name,
            "1:N", str(labels[0]) if labels else prop_name,
        )

    return {
        "objects": objects,
        "relations": relations,
        "actions": [],
        "data_sources": [],
        "warnings": warnings,
        "summary": {
            "object_count": len(objects),
            "relation_count": len(relations),
            "property_count": property_count,
            "action_count": 0,
        },
    }
