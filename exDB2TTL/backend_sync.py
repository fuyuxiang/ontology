from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from .config import ProjectConfig
from .models import DraftBundle


PROFILE_DIR = Path("runtime/generated-profile")


def sync_backend_profile(
    config: ProjectConfig,
    output_dir: Path,
    bundle: DraftBundle,
) -> dict[str, str]:
    backend_dir = _resolve_backend_dir(config.backend_sync.backend_project_dir)
    if not backend_dir.exists():
        raise FileNotFoundError(f"Backend project directory not found: {backend_dir}")

    source_doim_core = backend_dir / "ontology" / "doim-core.ttl"
    if not source_doim_core.exists():
        raise FileNotFoundError(f"Backend DOIM core ontology not found: {source_doim_core}")

    profile_root = backend_dir / PROFILE_DIR
    ontology_dir = profile_root / "ontology"
    rules_dir = profile_root / "rules"
    artifacts_dir = profile_root / "artifacts"
    ontology_dir.mkdir(parents=True, exist_ok=True)
    rules_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    ontology_core_path = ontology_dir / "doim-core.ttl"
    ontology_domain_path = ontology_dir / "telecom-porting.ttl"
    ontology_shapes_path = ontology_dir / "telecom-shapes.ttl"
    rules_path = rules_dir / "porting-risk.yaml"
    mapping_path = artifacts_dir / "mapping.csv"
    notes_path = artifacts_dir / "business-rules.md"

    ontology_core_path.write_text(source_doim_core.read_text(encoding="utf-8"), encoding="utf-8")
    ontology_domain_path.write_text(bundle.telecom_ontology_ttl + "\n", encoding="utf-8")
    ontology_shapes_path.write_text(bundle.telecom_shacl_ttl + "\n", encoding="utf-8")
    rules_path.write_text(bundle.rules_yaml + "\n", encoding="utf-8")
    mapping_path.write_text(bundle.mapping_csv + "\n", encoding="utf-8")
    if bundle.business_rules_markdown:
        notes_path.write_text(bundle.business_rules_markdown + "\n", encoding="utf-8")

    for artifact_name in ("metadata.json", "drafts.json", "validation-summary.json", "sample-data.ttl", "shacl-report.ttl"):
        source = output_dir / artifact_name
        if source.exists():
            target = artifacts_dir / artifact_name
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    manifest = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "doim_ns": "http://purl.org/doim/1.0#",
        "telecom_ns": config.ontology.ontology_namespace,
        "data_ns": config.ontology.data_namespace,
        "ontology_core_path": str(ontology_core_path.resolve()),
        "ontology_domain_path": str(ontology_domain_path.resolve()),
        "ontology_shapes_path": str(ontology_shapes_path.resolve()),
        "rules_path": str(rules_path.resolve()),
        "mapping_path": str(mapping_path.resolve()),
    }

    manifest_path = profile_root / "profile.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    active_profile_path = profile_root / "active-profile.json"
    if config.backend_sync.activate_profile:
        active_profile_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "backend_dir": str(backend_dir.resolve()),
        "profile_root": str(profile_root.resolve()),
        "manifest_path": str(manifest_path.resolve()),
        "active_profile_path": str(active_profile_path.resolve()),
        "ontology_core_path": str(ontology_core_path.resolve()),
        "ontology_domain_path": str(ontology_domain_path.resolve()),
        "ontology_shapes_path": str(ontology_shapes_path.resolve()),
        "rules_path": str(rules_path.resolve()),
        "mapping_path": str(mapping_path.resolve()),
    }


def _resolve_backend_dir(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return (Path.cwd() / path).resolve()
