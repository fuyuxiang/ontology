"""
模块功能：
- 基础 RDF 图物化。
- 该文件位于 `backend/app/services/graph_materializer.py`，负责把行数据和场景映射物化为 RDF 三元组，构建基础语义图。
- 文件中对外暴露或复用的主要函数包括：`materialize_base_graph`, `resolve_curie`, `literal_for_value`, `relation_id`, `add_relation`, `tag_entity`。
"""

from __future__ import annotations

from decimal import Decimal

from rdflib import Graph, Literal, RDF, RDFS, URIRef, XSD

from app.config.settings import Settings
from app.ontology.namespaces import make_namespaces
from app.scenario.config import ScenarioConfig
from app.scenario.mapping import MappingRow
from app.services.data_pipeline import infer_target_type


def materialize_base_graph(
    *,
    graph: Graph,
    settings: Settings,
    scenario: ScenarioConfig,
    source_rows: dict[str, list[dict[str, object]]],
    dataset_indexes: dict[str, dict[str, dict[str, list[dict[str, object]]]]],
    mapping_by_dataset: dict[str, list[MappingRow]],
    batch_id: str,
) -> None:
    """
    功能：
    - 把原始行数据和场景关系映射为基础 RDF 图。

    输入：
    - `graph`: 需要读取或写入的 RDF 图对象。
    - `settings`: 运行时配置对象，提供目录路径、命名空间和环境参数。
    - `scenario`: 当前激活的场景配置对象。
    - `source_rows`: 按数据集分组的原始或清洗后行数据。
    - `dataset_indexes`: 为跨数据集关联建立的多级索引。
    - `mapping_by_dataset`: 按数据集分组的字段映射配置。
    - `batch_id`: 当前导入或推理批次标识。

    输出：
    - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
    """
    for dataset_key, rows in source_rows.items():
        target_type = infer_target_type(mapping_by_dataset, dataset_key)
        target_class = resolve_curie(settings, target_type)
        for row in rows:
            resource = row["_entity_uri"]
            assert isinstance(resource, URIRef)
            tag_entity(graph, settings, resource, scenario.datasets[dataset_key].source_system, batch_id)
            graph.add((resource, RDF.type, target_class))

            label = row.get("_label")
            if label:
                graph.add((resource, RDFS.label, Literal(str(label))))

            for mapping in mapping_by_dataset.get(dataset_key, []):
                value = row.get(mapping.field_name)
                if value in (None, ""):
                    continue
                predicate = resolve_curie(settings, mapping.mapped_predicate)
                graph.add((resource, predicate, literal_for_value(value, mapping.value_type)))

    for relation in scenario.relations:
        source_dataset_config = scenario.datasets[relation.source_dataset]
        source_rows_for_relation = source_rows.get(relation.source_dataset, [])
        target_index = dataset_indexes.get(relation.target_dataset, {}).get(relation.target_join_key, {})
        source_field = source_dataset_config.join_keys[relation.source_join_key]

        for source_row in source_rows_for_relation:
            join_value = source_row.get(source_field)
            if join_value in (None, ""):
                continue
            source_uri = source_row["_entity_uri"]
            assert isinstance(source_uri, URIRef)
            for target_row in target_index.get(str(join_value), []):
                target_uri = target_row["_entity_uri"]
                assert isinstance(target_uri, URIRef)
                add_relation(
                    graph=graph,
                    settings=settings,
                    source=source_uri,
                    predicate=resolve_curie(settings, relation.predicate),
                    target=target_uri,
                    relation_id=relation_id(relation.source_dataset, source_row, relation.target_dataset, target_row),
                    label=relation.label,
                    source_system=relation.source_system,
                    batch_id=batch_id,
                )


def resolve_curie(settings: Settings, curie: str) -> URIRef:
    """
    功能：
    - 把 CURIE 形式的谓词或类型解析为完整 URI。

    输入：
    - `settings`: 运行时配置对象，提供目录路径、命名空间和环境参数。
    - `curie`: 函数执行所需的 `curie` 参数。

    输出：
    - 返回值: 返回 RDF 资源 URI。
    """
    namespace, local = curie.split(":", 1)
    if namespace == "rdf":
        return URIRef(str(RDF[local]))
    if namespace == "rdfs":
        return URIRef(str(RDFS[local]))
    return URIRef(str(make_namespaces(settings)[namespace][local]))


def literal_for_value(value: object, value_type: str) -> Literal:
    """
    功能：
    - 按映射值类型构造 RDF Literal。

    输入：
    - `value`: 待解析、转换或比较的原始值。
    - `value_type`: 函数执行所需的 `value_type` 参数。

    输出：
    - 返回值: 返回 RDF 字面量对象。
    """
    lowered = value_type.lower()
    if lowered in {"int", "integer"}:
        return Literal(int(value), datatype=XSD.integer)
    if lowered == "decimal":
        return Literal(Decimal(str(value)), datatype=XSD.decimal)
    if lowered in {"bool", "boolean"}:
        return Literal(bool(value), datatype=XSD.boolean)
    return Literal(value)


def relation_id(
    source_dataset: str,
    source_row: dict[str, object],
    target_dataset: str,
    target_row: dict[str, object],
) -> str:
    """
    功能：
    - 为关系节点构造稳定 ID。

    输入：
    - `source_dataset`: 函数执行所需的 `source_dataset` 参数。
    - `source_row`: 字典参数 `source_row`，承载键值形式的输入数据。
    - `target_dataset`: 函数执行所需的 `target_dataset` 参数。
    - `target_row`: 字典参数 `target_row`，承载键值形式的输入数据。

    输出：
    - 返回值: 返回字符串结果，供调用方继续展示、拼接或查询。
    """
    source_bits = [source_dataset, str(source_row["_row_index"])]
    target_bits = [target_dataset, str(target_row["_row_index"])]
    return "-".join(source_bits + target_bits)


def add_relation(
    *,
    graph: Graph,
    settings: Settings,
    source: URIRef,
    predicate: URIRef,
    target: URIRef,
    relation_id: str,
    label: str,
    source_system: str,
    batch_id: str,
) -> None:
    """
    功能：
    - 同时写入实体间关系边和关系对象节点，便于查询与溯源。

    输入：
    - `graph`: 需要读取或写入的 RDF 图对象。
    - `settings`: 运行时配置对象，提供目录路径、命名空间和环境参数。
    - `source`: 函数执行所需的 `source` 参数。
    - `predicate`: 函数执行所需的 `predicate` 参数。
    - `target`: 函数执行所需的 `target` 参数。
    - `relation_id`: 函数执行所需的 `relation_id` 参数。
    - `label`: 函数执行所需的 `label` 参数。
    - `source_system`: 数据来源系统名称。
    - `batch_id`: 当前导入或推理批次标识。

    输出：
    - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
    """
    namespaces = make_namespaces(settings)
    doim = namespaces["doim"]
    relation = URIRef(f"{settings.data_ns}relation/{relation_id}")
    tag_entity(graph, settings, relation, source_system, batch_id)
    graph.add((source, predicate, target))
    graph.add((source, doim.relatedTo, target))
    graph.add((relation, RDF.type, doim.Relation))
    graph.add((relation, RDFS.label, Literal(label)))
    graph.add((relation, doim.fromEntity, source))
    graph.add((relation, doim.toEntity, target))
    graph.add((relation, doim.predicateUri, Literal(str(predicate))))


def tag_entity(graph: Graph, settings: Settings, resource: URIRef, source_system: str, batch_id: str) -> None:
    """
    功能：
    - 为实体补充来源系统和导入批次标记。

    输入：
    - `graph`: 需要读取或写入的 RDF 图对象。
    - `settings`: 运行时配置对象，提供目录路径、命名空间和环境参数。
    - `resource`: 需要写入标记的 RDF 资源。
    - `source_system`: 数据来源系统名称。
    - `batch_id`: 当前导入或推理批次标识。

    输出：
    - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
    """
    namespaces = make_namespaces(settings)
    doim = namespaces["doim"]
    graph.add((resource, doim.sourceSystem, Literal(source_system)))
    graph.add((resource, doim.loadBatch, Literal(batch_id)))
