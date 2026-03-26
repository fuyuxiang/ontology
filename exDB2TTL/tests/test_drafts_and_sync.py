"""草稿解析与后端同步流程测试。"""

from __future__ import annotations

import json
from pathlib import Path

from exDB2TTL.backend_sync import sync_backend_profile
from exDB2TTL.config import BackendSyncConfig, DatabaseConfig, LLMConfig, OntologyConfig, OutputConfig, ProjectConfig
from exDB2TTL.drafts import parse_draft_bundle
from exDB2TTL.models import DraftBundle


def test_parse_draft_bundle_accepts_backend_contract():
    """验证草稿解析器可以接受当前后端约定的字段集合。"""
    raw = json.dumps(
        {
            "telecom_ontology_ttl": "@prefix telecom: <http://example.com/telecom#> .\n",
            "telecom_shacl_ttl": "@prefix sh: <http://www.w3.org/ns/shacl#> .\n",
            "mapping_csv": (
                "table_name,subject_class_uri,subject_key_column,column_name,predicate_uri,"
                "object_kind,xsd_datatype,reference_table,reference_column,required,description\n"
            ),
            "rules_yaml": "risk_actions: {}\nfactor_rules: []\ndecision_rules: []\n",
            "business_rules_markdown": "# Notes\n",
        },
        ensure_ascii=False,
    )

    bundle = parse_draft_bundle(raw)

    assert bundle.telecom_ontology_ttl.startswith("@prefix telecom:")
    assert bundle.telecom_shacl_ttl.startswith("@prefix sh:")
    assert bundle.rules_yaml.startswith("risk_actions:")


def test_sync_backend_profile_writes_generated_contract(tmp_path: Path):
    """验证同步流程会写出后端可加载的 profile 文件集。"""
    backend_dir = tmp_path / "backend"
    (backend_dir / "ontology").mkdir(parents=True)
    (backend_dir / "rules").mkdir(parents=True)
    (backend_dir / "runtime").mkdir(parents=True)
    (backend_dir / "ontology" / "doim-core.ttl").write_text("@prefix doim: <http://purl.org/doim/1.0#> .\n", encoding="utf-8")

    output_dir = tmp_path / "out"
    output_dir.mkdir()
    (output_dir / "metadata.json").write_text("{}", encoding="utf-8")
    (output_dir / "drafts.json").write_text("{}", encoding="utf-8")
    (output_dir / "validation-summary.json").write_text("{}", encoding="utf-8")

    config = ProjectConfig(
        database=DatabaseConfig(dialect="csv", database_name="db", tables=["subscribers"]),
        llm=LLMConfig(base_url="https://api.example.com/v1", model="demo", api_key_env="DUMMY_KEY"),
        ontology=OntologyConfig(
            ontology_namespace="http://example.com/telecom#",
            data_namespace="http://example.com/telecom/data/",
        ),
        backend_sync=BackendSyncConfig(
            enabled=True,
            backend_project_dir=str(backend_dir),
            activate_profile=True,
        ),
        output=OutputConfig(directory=str(output_dir)),
        business_context={},
    )
    bundle = DraftBundle(
        telecom_ontology_ttl="@prefix telecom: <http://example.com/telecom#> .\n",
        telecom_shacl_ttl="@prefix sh: <http://www.w3.org/ns/shacl#> .\n",
        mapping_csv=(
            "table_name,subject_class_uri,subject_key_column,column_name,predicate_uri,"
            "object_kind,xsd_datatype,reference_table,reference_column,required,description\n"
        ),
        rules_yaml="risk_actions: {}\nfactor_rules: []\ndecision_rules: []\n",
        business_rules_markdown="# Rules\n",
    )

    synced = sync_backend_profile(config, output_dir, bundle)

    active_profile_path = Path(synced["active_profile_path"])
    manifest = json.loads(active_profile_path.read_text(encoding="utf-8"))
    assert manifest["telecom_ns"] == "http://example.com/telecom#"
    assert Path(manifest["ontology_domain_path"]).exists()
    assert Path(manifest["ontology_shapes_path"]).exists()
    assert Path(manifest["rules_path"]).exists()
