"""元数据抽取测试。"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from exDB2TTL.config import DatabaseConfig
from exDB2TTL.metadata import _parse_mysql_enum_values, extract_metadata


def test_extract_metadata_from_csv_directory(tmp_path: Path):
    """验证 CSV 样例目录可以推断出基础元数据。"""
    _write_csv(
        tmp_path / "customers.csv",
        ["customer_id", "city", "active", "score"],
        [
            {"customer_id": "C001", "city": "Shanghai", "active": "true", "score": "98.5"},
            {"customer_id": "C002", "city": "Shenzhen", "active": "false", "score": "77.0"},
        ],
    )

    metadata = extract_metadata(
        DatabaseConfig(
            dialect="csv",
            database_name="sample_db",
            tables=["customers"],
            sample_csv_dir=str(tmp_path),
            sample_rows=5,
        )
    )

    table = metadata.tables[0]
    assert table.name == "customers"
    assert table.primary_keys == []
    assert [column.name for column in table.columns] == ["customer_id", "city", "active", "score"]
    assert [column.data_type for column in table.columns] == ["TEXT", "TEXT", "BOOLEAN", "REAL"]
    assert len(table.sample_rows) == 2


def test_sqlite_sample_rows_can_be_overridden_by_csv(tmp_path: Path):
    """验证存在同名 CSV 时会优先采用 CSV 样例数据。"""
    db_path = tmp_path / "sample.sqlite"
    connection = sqlite3.connect(db_path)
    connection.execute("CREATE TABLE customers (customer_id TEXT PRIMARY KEY, name TEXT NOT NULL)")
    connection.execute("INSERT INTO customers VALUES ('DB001', 'FromDB')")
    connection.commit()
    connection.close()

    _write_csv(
        tmp_path / "customers.csv",
        ["customer_id", "name"],
        [{"customer_id": "CSV001", "name": "FromCSV"}],
    )

    metadata = extract_metadata(
        DatabaseConfig(
            dialect="sqlite",
            database_name="sample_db",
            tables=["customers"],
            sqlite_path=str(db_path),
            sample_csv_dir=str(tmp_path),
            sample_rows=5,
        )
    )

    table = metadata.tables[0]
    assert table.primary_keys == ["customer_id"]
    assert table.sample_rows == [{"customer_id": "CSV001", "name": "FromCSV"}]


def test_parse_mysql_enum_values():
    """验证 MySQL ENUM 定义可以被正确拆解。"""
    assert _parse_mysql_enum_values("enum('paid','pending','cancelled')") == ["paid", "pending", "cancelled"]


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    """测试辅助函数：写入一份临时 CSV 文件。"""
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
