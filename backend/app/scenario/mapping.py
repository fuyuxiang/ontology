"""字段映射配置加载器，负责把 CSV 映射表转成结构化对象。"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MappingRow:
    """一行字段映射定义。"""

    dataset: str
    target_type: str
    field_name: str
    mapped_predicate: str
    value_type: str


REQUIRED_MAPPING_COLUMNS = [
    "dataset",
    "target_type",
    "field_name",
    "mapped_predicate",
    "value_type",
]


def load_mapping_rows(path: Path) -> list[MappingRow]:
    """读取映射 CSV，并校验列头是否符合约定。"""
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = list(reader.fieldnames or [])
        if header != REQUIRED_MAPPING_COLUMNS:
            raise ValueError(
                f"mapping header mismatch. Expected {REQUIRED_MAPPING_COLUMNS}, got {header}"
            )
        return [
            MappingRow(
                dataset=str(row["dataset"]),
                target_type=str(row["target_type"]),
                field_name=str(row["field_name"]),
                mapped_predicate=str(row["mapped_predicate"]),
                value_type=str(row["value_type"]),
            )
            for row in reader
        ]
