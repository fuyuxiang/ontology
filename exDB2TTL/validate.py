from __future__ import annotations

from pathlib import Path

from rdflib import Graph

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
    errors: list[str] = []
    ontology_graph = Graph()
    shacl_graph = Graph()

    ontology_parse_ok = _safe_parse_graph(ontology_graph, bundle.ontology_ttl, errors, "ontology_ttl")
    shacl_parse_ok = _safe_parse_graph(shacl_graph, bundle.shacl_ttl, errors, "shacl_ttl")

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
        sample_triples=len(sample_graph),
        shacl_conforms=shacl_conforms,
        shacl_report_text=shacl_report_text,
        shacl_report_path=shacl_report_path,
        errors=errors,
    )


def _safe_parse_graph(graph: Graph, turtle_text: str, errors: list[str], label: str) -> bool:
    try:
        graph.parse(data=turtle_text, format="turtle")
    except Exception as exc:
        errors.append(f"{label} parse failed: {exc}")
        return False
    return True
