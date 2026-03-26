"""生成产物校验流程，包括 Turtle 解析、规则校验和 SHACL 验证。"""

from __future__ import annotations

from pathlib import Path

from rdflib import Graph

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

from .config import ProjectConfig
from .materialize import materialize_sample_graph
from .models import DatabaseMetadata, DraftBundle, ValidationArtifacts

try:
    from pyshacl import validate
except ImportError:  # pragma: no cover
    validate = None


def validate_bundle(
    config: ProjectConfig,
    metadata: DatabaseMetadata,
    bundle: DraftBundle,
    output_dir: Path,
) -> ValidationArtifacts:
    """对草稿包执行结构、语法和样例数据验证。"""
    errors: list[str] = []
    ontology_graph = Graph()
    shacl_graph = Graph()

    ontology_parse_ok = _safe_parse_graph(ontology_graph, bundle.telecom_ontology_ttl, errors, "telecom_ontology_ttl")
    shacl_parse_ok = _safe_parse_graph(shacl_graph, bundle.telecom_shacl_ttl, errors, "telecom_shacl_ttl")
    rules_parse_ok, rules_validation_error = _validate_rules_yaml(bundle.rules_yaml, output_dir, errors)

    sample_graph = materialize_sample_graph(metadata, bundle.mapping_csv, config.ontology)
    sample_data_path = output_dir / "sample-data.ttl"
    sample_graph.serialize(destination=sample_data_path, format="turtle")

    shacl_conforms: bool | None = None
    shacl_report_text: str | None = None
    shacl_report_path: str | None = None
    if ontology_parse_ok and shacl_parse_ok and validate is not None:
        report_path = output_dir / "shacl-report.ttl"
        conforms, report_graph, report_text = validate(
            sample_graph,
            shacl_graph=shacl_graph,
            ont_graph=ontology_graph,
            advanced=True,
            inference="rdfs",
        )
        report_graph.serialize(destination=report_path, format="turtle")
        shacl_conforms = bool(conforms)
        shacl_report_text = report_text
        shacl_report_path = str(report_path)
    elif validate is None:
        errors.append("pyshacl is not installed, SHACL execution skipped")

    return ValidationArtifacts(
        ontology_parse_ok=ontology_parse_ok,
        shacl_parse_ok=shacl_parse_ok,
        rules_parse_ok=rules_parse_ok,
        sample_triples=len(sample_graph),
        shacl_conforms=shacl_conforms,
        shacl_report_text=shacl_report_text,
        shacl_report_path=shacl_report_path,
        rules_validation_error=rules_validation_error,
        errors=errors,
    )


def _safe_parse_graph(graph: Graph, turtle_text: str, errors: list[str], label: str) -> bool:
    """安全解析 Turtle 文本，并把异常写入错误列表。"""
    try:
        graph.parse(data=turtle_text, format="turtle")
    except Exception as exc:
        errors.append(f"{label} parse failed: {exc}")
        return False
    return True


def _validate_rules_yaml(rules_yaml: str, output_dir: Path, errors: list[str]) -> tuple[bool, str | None]:
    """校验规则 YAML，并优先复用后端已有规则加载器。"""
    rules_path = output_dir / "porting-risk.yaml"
    rules_path.write_text(rules_yaml + "\n", encoding="utf-8")

    loader = _load_backend_ruleset_loader()
    try:
        if loader is not None:
            loader(rules_path)
        else:
            if yaml is None:
                raise RuntimeError("PyYAML is required to validate rules_yaml")
            payload = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
            _validate_rules_shape(payload)
    except Exception as exc:
        message = f"rules_yaml validation failed: {exc}"
        errors.append(message)
        return False, str(exc)
    return True, None


def _load_backend_ruleset_loader():
    """尝试加载后端的规则加载器，确保生成格式与后端实现一致。"""
    try:
        from backend.app.rules.decision_table import load_decision_table
    except ImportError:  # pragma: no cover
        return None
    return load_decision_table


def _validate_rules_shape(payload: object) -> None:
    """在缺少后端加载器时做最小结构校验。"""
    if not isinstance(payload, dict):
        raise ValueError("rules_yaml must parse to a mapping")
    for key in ("risk_actions", "factor_rules", "decision_rules"):
        if key not in payload:
            raise ValueError(f"rules_yaml missing top-level key: {key}")
