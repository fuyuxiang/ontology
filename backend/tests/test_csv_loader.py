"""CSV 加载工具测试。"""

from pathlib import Path

from app.etl.csv_loader import read_csv_rows


def test_read_csv_rows_strips_utf8_bom_from_header(tmp_path: Path):
    """验证读取器会移除 UTF-8 BOM，避免表头字段名异常。"""
    csv_path = tmp_path / "bom.csv"
    csv_path.write_text("\ufeffsubs_id,latest_date\nU00001,2026-03-30 17:45:17\n", encoding="utf-8")

    rows = read_csv_rows(csv_path)

    assert rows == [{"subs_id": "U00001", "latest_date": "2026-03-30 17:45:17"}]
