from __future__ import annotations

import csv
import io
import json

from .models import DraftBundle


def parse_draft_bundle(raw_text: str) -> DraftBundle:
    payload = json.loads(_extract_json_object(raw_text))
    required = ["ontology_ttl", "shacl_ttl", "mapping_csv", "business_rules_markdown"]
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"LLM output missing required keys: {', '.join(missing)}")

    bundle = DraftBundle(
        ontology_ttl=str(payload["ontology_ttl"]).strip(),
        shacl_ttl=str(payload["shacl_ttl"]).strip(),
        mapping_csv=str(payload["mapping_csv"]).strip(),
        business_rules_markdown=str(payload["business_rules_markdown"]).strip(),
    )
    _validate_mapping_header(bundle.mapping_csv)
    return bundle


def serialize_draft_bundle(bundle: DraftBundle) -> str:
    return json.dumps(
        {
            "ontology_ttl": bundle.ontology_ttl,
            "shacl_ttl": bundle.shacl_ttl,
            "mapping_csv": bundle.mapping_csv,
            "business_rules_markdown": bundle.business_rules_markdown,
        },
        ensure_ascii=False,
        indent=2,
    )


def _extract_json_object(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped

    start = stripped.find("{")
    if start < 0:
        raise ValueError("LLM output does not contain a JSON object")
    depth = 0
    for index in range(start, len(stripped)):
        char = stripped[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return stripped[start : index + 1]
    raise ValueError("LLM output contains an incomplete JSON object")


def _validate_mapping_header(mapping_csv: str) -> None:
    reader = csv.reader(io.StringIO(mapping_csv))
    try:
        header = next(reader)
    except StopIteration as exc:
        raise ValueError("mapping_csv is empty") from exc

    expected = [
        "table_name",
        "subject_class_uri",
        "subject_key_column",
        "column_name",
        "predicate_uri",
        "object_kind",
        "xsd_datatype",
        "reference_table",
        "reference_column",
        "required",
        "description",
    ]
    if header != expected:
        raise ValueError(f"mapping_csv header mismatch. Expected {expected}, got {header}")
