"""样例 RDF 物化工具，用于把元数据和映射表转换为示例图。"""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from rdflib import Graph, Literal, RDF, URIRef, XSD

from .config import OntologyConfig
from .models import DatabaseMetadata


@dataclass(frozen=True)
class MappingRow:
    """映射 CSV 中的一行定义。"""

    table_name: str
    subject_class_uri: str
    subject_key_column: str
    column_name: str
    predicate_uri: str
    object_kind: str
    xsd_datatype: str
    reference_table: str
    reference_column: str
    required: str
    description: str


def materialize_sample_graph(metadata: DatabaseMetadata, mapping_csv: str, ontology: OntologyConfig) -> Graph:
    """根据样例数据和字段映射生成一份 RDF 样例图。"""
    graph = Graph()
    graph.bind("rdf", RDF)
    graph.bind("xsd", XSD)

    mappings = _parse_mapping(mapping_csv)
    rows_by_table: dict[str, list[MappingRow]] = defaultdict(list)
    for row in mappings:
        rows_by_table[row.table_name].append(row)

    table_lookup = {table.name: table for table in metadata.tables}
    fk_lookup: dict[tuple[str, str], tuple[str, str]] = {}
    for table in metadata.tables:
        for fk in table.foreign_keys:
            fk_lookup[(table.name, fk.column_name)] = (fk.target_table, fk.target_column)

    for table in metadata.tables:
        mapping_rows = rows_by_table.get(table.name, [])
        if not mapping_rows:
            continue

        subject_class_uri = mapping_rows[0].subject_class_uri
        subject_key_column = mapping_rows[0].subject_key_column

        for row_index, source_row in enumerate(table.sample_rows):
            subject = _make_subject_uri(
                data_namespace=ontology.data_namespace,
                table_name=table.name,
                row=source_row,
                subject_key_column=subject_key_column,
                row_index=row_index,
            )
            graph.add((subject, RDF.type, URIRef(subject_class_uri)))

            for mapping in mapping_rows:
                value = source_row.get(mapping.column_name)
                if value in (None, ""):
                    continue
                predicate = URIRef(mapping.predicate_uri)

                if mapping.object_kind == "literal":
                    graph.add((subject, predicate, _literal_from_value(value, mapping.xsd_datatype)))
                    continue

                target_table = mapping.reference_table
                target_column = mapping.reference_column
                if not target_table or not target_column:
                    # 若映射未显式给出引用目标，则尝试复用数据库外键元数据补全。
                    target = fk_lookup.get((table.name, mapping.column_name))
                    if target:
                        target_table, target_column = target
                if not target_table or not target_column:
                    target_table = "resource"
                    target_column = mapping.column_name

                graph.add(
                    (
                        subject,
                        predicate,
                        _make_reference_uri(ontology.data_namespace, target_table, str(value)),
                    )
                )

    return graph


def _parse_mapping(mapping_csv: str) -> list[MappingRow]:
    """解析映射 CSV 文本。"""
    reader = csv.DictReader(io.StringIO(mapping_csv))
    return [
        MappingRow(
            table_name=(row.get("table_name") or "").strip(),
            subject_class_uri=(row.get("subject_class_uri") or "").strip(),
            subject_key_column=(row.get("subject_key_column") or "").strip(),
            column_name=(row.get("column_name") or "").strip(),
            predicate_uri=(row.get("predicate_uri") or "").strip(),
            object_kind=(row.get("object_kind") or "").strip(),
            xsd_datatype=(row.get("xsd_datatype") or "").strip(),
            reference_table=(row.get("reference_table") or "").strip(),
            reference_column=(row.get("reference_column") or "").strip(),
            required=(row.get("required") or "").strip(),
            description=(row.get("description") or "").strip(),
        )
        for row in reader
    ]


def _make_subject_uri(
    data_namespace: str,
    table_name: str,
    row: dict[str, Any],
    subject_key_column: str,
    row_index: int,
) -> URIRef:
    """为样例行生成主体 URI。"""
    key_value = row.get(subject_key_column)
    if key_value in (None, ""):
        key_value = f"row-{row_index + 1}"
    return _make_reference_uri(data_namespace, table_name, str(key_value))


def _make_reference_uri(data_namespace: str, table_name: str, key_value: str) -> URIRef:
    """根据表名与键值生成资源 URI。"""
    safe_table = quote(table_name, safe="")
    safe_value = quote(key_value, safe="")
    return URIRef(f"{data_namespace.rstrip('/')}/{safe_table}/{safe_value}")


def _literal_from_value(value: Any, datatype_uri: str) -> Literal:
    """按目标数据类型构造字面量节点。"""
    if not datatype_uri:
        return Literal(value)
    datatype = URIRef(datatype_uri)
    if datatype == XSD.integer:
        return Literal(int(value), datatype=datatype)
    if datatype == XSD.decimal:
        return Literal(str(value), datatype=datatype)
    if datatype == XSD.double:
        return Literal(float(value), datatype=datatype)
    if datatype == XSD.boolean:
        normalized = str(value).strip().lower()
        return Literal(normalized in {"1", "true", "yes", "y"}, datatype=datatype)
    return Literal(str(value), datatype=datatype)
