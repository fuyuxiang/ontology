"""CSV 读取工具，负责以稳定编码方式加载原始数据行。"""

from __future__ import annotations

import csv
from pathlib import Path


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """读取 CSV 行数据，并兼容带 BOM 的 UTF-8 导出文件。"""

    # 兼容办公软件导出的 UTF-8 with BOM 文件，避免表头字段名被污染。
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))
