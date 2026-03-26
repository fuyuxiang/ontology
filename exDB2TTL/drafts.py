"""LLM 草稿包解析与序列化工具。"""

from __future__ import annotations

import csv
import io
import json

from .models import DraftBundle


def parse_draft_bundle(raw_text: str) -> DraftBundle:
    """从模型响应中提取并校验草稿包。"""
    payload = json.loads(_extract_json_object(raw_text))
    required = ["mapping_csv", "rules_yaml"]
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"LLM output missing required keys: {', '.join(missing)}")

    telecom_ontology_ttl = _first_present(payload, "telecom_ontology_ttl", "ontology_ttl")
    telecom_shacl_ttl = _first_present(payload, "telecom_shacl_ttl", "shacl_ttl")
    bundle = DraftBundle(
        telecom_ontology_ttl=telecom_ontology_ttl,
        telecom_shacl_ttl=telecom_shacl_ttl,
        mapping_csv=str(payload["mapping_csv"]).strip(),
        rules_yaml=str(payload["rules_yaml"]).strip(),
        business_rules_markdown=str(payload.get("business_rules_markdown", "")).strip(),
    )
    _validate_mapping_header(bundle.mapping_csv)
    return bundle


def serialize_draft_bundle(bundle: DraftBundle) -> str:
    """将草稿包序列化为稳定的 JSON 文本。"""
    return json.dumps(
        {
            "telecom_ontology_ttl": bundle.telecom_ontology_ttl,
            "telecom_shacl_ttl": bundle.telecom_shacl_ttl,
            "mapping_csv": bundle.mapping_csv,
            "rules_yaml": bundle.rules_yaml,
            "business_rules_markdown": bundle.business_rules_markdown,
        },
        ensure_ascii=False,
        indent=2,
    )


def _extract_json_object(text: str) -> str:
    """从混合文本中截取首个完整 JSON 对象。"""
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
    """校验生成映射表的列头是否符合约定。"""
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


def _first_present(payload: dict[str, object], *keys: str) -> str:
    """按优先级读取第一个存在的键。"""
    for key in keys:
        if key in payload:
            return str(payload[key]).strip()
    raise ValueError(f"LLM output missing required keys: {', '.join(keys)}")
