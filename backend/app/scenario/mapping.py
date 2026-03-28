"""
模块功能：
- 字段映射配置加载器，负责把 CSV 映射表转成结构化对象。
- 该文件位于 `backend/app/scenario/mapping.py`，负责装载字段映射配置，把场景映射文件转换为可执行的数据结构。
- 文件中定义的核心类包括：`MappingRow`。
- 文件中对外暴露或复用的主要函数包括：`load_mapping_rows`。
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MappingRow:
    """
    功能：
    - 一行字段映射定义。
    - 该类定义在 `backend/app/scenario/mapping.py` 中，用于组织与 `MappingRow` 相关的数据或行为。
    - 类中声明的主要字段包括：`dataset`, `target_type`, `field_name`, `mapped_predicate`, `value_type`。
    """

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
    """
    功能：
    - 读取映射 CSV，并校验列头是否符合约定。

    输入：
    - `path`: 待读取或写入的路径对象。

    输出：
    - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
    """
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
