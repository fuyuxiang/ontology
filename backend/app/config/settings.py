from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ACTIVE_PROFILE_PATH = Path("runtime/generated-profile/active-profile.json")
DEFAULT_DOIM_NS = "http://purl.org/doim/1.0#"
DEFAULT_TELECOM_NS = "http://example.com/telecom#"
DEFAULT_DATA_NS = "http://example.com/telecom/data/"


@dataclass(frozen=True)
class Settings:
    project_dir: Path
    data_dir: Path
    mappings_dir: Path
    mapping_path: Path
    ontology_dir: Path
    rules_dir: Path
    scenarios_dir: Path
    runtime_dir: Path
    store_dir: Path
    reports_dir: Path
    ontology_core_path: Path
    ontology_domain_path: Path
    ontology_shapes_path: Path
    rules_path: Path
    scenario_path: Path
    host: str
    port: int
    doim_ns: str
    telecom_ns: str
    data_ns: str
    base_graph_uri: str
    deductions_graph_uri: str
    default_query: str


def get_settings() -> Settings:
    project_dir = Path(__file__).resolve().parents[2]
    ontology_dir = project_dir / "ontology"
    rules_dir = project_dir / "rules"
    profile = _load_active_profile(project_dir)

    doim_ns = os.getenv("ONTOLOGY_DOIM_NS", str(profile.get("doim_ns") or DEFAULT_DOIM_NS))
    telecom_ns = os.getenv("ONTOLOGY_TELECOM_NS", str(profile.get("telecom_ns") or DEFAULT_TELECOM_NS))
    data_ns = os.getenv("ONTOLOGY_DATA_NS", str(profile.get("data_ns") or DEFAULT_DATA_NS))

    return Settings(
        project_dir=project_dir,
        data_dir=project_dir / "data" / "raw",
        mappings_dir=project_dir / "mappings",
        mapping_path=_resolve_path(
            project_dir,
            os.getenv("ONTOLOGY_MAPPING_PATH"),
            profile.get("mapping_path"),
            project_dir / "mappings" / "doim_mapping.csv",
        ),
        ontology_dir=ontology_dir,
        rules_dir=rules_dir,
        scenarios_dir=project_dir / "scenarios",
        runtime_dir=project_dir / "runtime",
        store_dir=project_dir / "runtime" / "store",
        reports_dir=project_dir / "runtime" / "reports",
        ontology_core_path=_resolve_path(
            project_dir,
            os.getenv("ONTOLOGY_CORE_PATH"),
            profile.get("ontology_core_path"),
            ontology_dir / "doim-core.ttl",
        ),
        ontology_domain_path=_resolve_path(
            project_dir,
            os.getenv("ONTOLOGY_DOMAIN_PATH"),
            profile.get("ontology_domain_path"),
            ontology_dir / "telecom-porting.ttl",
        ),
        ontology_shapes_path=_resolve_path(
            project_dir,
            os.getenv("ONTOLOGY_SHAPES_PATH"),
            profile.get("ontology_shapes_path"),
            ontology_dir / "telecom-shapes.ttl",
        ),
        rules_path=_resolve_path(
            project_dir,
            os.getenv("ONTOLOGY_RULES_PATH"),
            profile.get("rules_path"),
            rules_dir / "porting-risk.yaml",
        ),
        scenario_path=_resolve_path(
            project_dir,
            os.getenv("ONTOLOGY_SCENARIO_PATH"),
            profile.get("scenario_path"),
            project_dir / "scenarios" / "telecom-porting.yaml",
        ),
        host=os.getenv("ONTOLOGY_HOST", "127.0.0.1"),
        port=int(os.getenv("ONTOLOGY_PORT", "8088")),
        doim_ns=doim_ns,
        telecom_ns=telecom_ns,
        data_ns=data_ns,
        base_graph_uri="urn:doim:poc:base",
        deductions_graph_uri="urn:doim:poc:deductions",
        default_query=_build_default_query(doim_ns, telecom_ns),
    )


def _load_active_profile(project_dir: Path) -> dict[str, Any]:
    if os.getenv("ONTOLOGY_IGNORE_ACTIVE_PROFILE", "").strip().lower() in {"1", "true", "yes"}:
        return {}
    path = project_dir / ACTIVE_PROFILE_PATH
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _resolve_path(project_dir: Path, env_value: str | None, profile_value: Any, default: Path) -> Path:
    raw = env_value or (str(profile_value).strip() if profile_value else "")
    if not raw:
        return default
    path = Path(raw)
    if path.is_absolute():
        return path
    return (project_dir / path).resolve()


def _build_default_query(doim_ns: str, telecom_ns: str) -> str:
    return f"""PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX doim: <{doim_ns}>
PREFIX telecom: <{telecom_ns}>
SELECT ?userId ?deviceNumber ?riskLevel ?areaId
WHERE {{
  ?s a telecom:User ;
     telecom:userId ?userId ;
     telecom:deviceNumber ?deviceNumber ;
     telecom:inferredRiskLevel ?riskLevel .
  OPTIONAL {{ ?s telecom:areaId ?areaId }}
}}
ORDER BY DESC(?riskLevel) ?userId
"""
