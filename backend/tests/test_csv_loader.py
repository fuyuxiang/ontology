from pathlib import Path

from app.etl.csv_loader import read_csv_rows


def test_read_csv_rows_strips_utf8_bom_from_header(tmp_path: Path):
    csv_path = tmp_path / "bom.csv"
    csv_path.write_text("\ufeffsubs_id,latest_date\nU00001,2026-03-30 17:45:17\n", encoding="utf-8")

    rows = read_csv_rows(csv_path)

    assert rows == [{"subs_id": "U00001", "latest_date": "2026-03-30 17:45:17"}]
