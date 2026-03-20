from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ColumnMeta:
    name: str
    data_type: str
    nullable: bool
    primary_key: bool = False
    default: str | None = None
    comment: str | None = None
    enum_values: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ForeignKeyMeta:
    column_name: str
    target_table: str
    target_column: str
    constraint_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TableMeta:
    name: str
    columns: list[ColumnMeta]
    primary_keys: list[str]
    foreign_keys: list[ForeignKeyMeta] = field(default_factory=list)
    comment: str | None = None
    sample_rows: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return payload


@dataclass
class DatabaseMetadata:
    database_name: str
    dialect: str
    schema: str | None
    tables: list[TableMeta]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DraftBundle:
    telecom_ontology_ttl: str
    telecom_shacl_ttl: str
    mapping_csv: str
    rules_yaml: str
    business_rules_markdown: str = ""


@dataclass
class ValidationArtifacts:
    ontology_parse_ok: bool
    shacl_parse_ok: bool
    rules_parse_ok: bool
    sample_triples: int
    shacl_conforms: bool | None
    shacl_report_text: str | None
    shacl_report_path: str | None
    rules_validation_error: str | None = None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
