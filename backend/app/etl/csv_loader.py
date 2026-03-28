"""
模块功能：
- CSV 读取工具，负责以稳定编码方式加载原始数据行。
- 该文件位于 `backend/app/etl/csv_loader.py`，负责读取 CSV 原始文件并做基础清洗，为上游 ETL 和语义构图提供行数据。
- 文件中对外暴露或复用的主要函数包括：`read_csv_rows`。
"""

from __future__ import annotations

import csv
from pathlib import Path


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """
    功能：
    - 读取 CSV 行数据，并兼容带 BOM 的 UTF-8 导出文件。

    输入：
    - `path`: 待读取或写入的路径对象。

    输出：
    - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
    """

    # 兼容办公软件导出的 UTF-8 with BOM 文件，避免表头字段名被污染。
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))
