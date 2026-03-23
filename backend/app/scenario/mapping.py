from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MappingRow:
    dataset: str
    source_system: str
    target_type: str
    subject_key: str
    mapped_predicate: str
    field_name: str
    value_type: str
    description: str


def load_mapping_rows(path: Path) -> list[MappingRow]:
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [
            MappingRow(
                dataset=str(row["dataset"]),
                source_system=str(row["source_system"]),
                target_type=str(row["target_type"]),
                subject_key=str(row["subject_key"]),
                mapped_predicate=str(row["mapped_predicate"]),
                field_name=str(row["field_name"]),
                value_type=str(row["value_type"]),
                description=str(row.get("description") or ""),
            )
            for row in reader
        ]
