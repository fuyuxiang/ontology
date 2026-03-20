from __future__ import annotations

from pathlib import Path

from rdflib import Graph

try:
    from pyshacl import validate
except ImportError:  # pragma: no cover
    validate = None


def run_shacl_validation(data_graph: Graph, shapes_path: Path, report_path: Path) -> dict[str, object]:
    if validate is None:
        return {"status": "skipped", "reason": "pyshacl_not_installed"}
    if not shapes_path.exists():
        return {"status": "skipped", "reason": "shapes_not_found"}

    report_path.parent.mkdir(parents=True, exist_ok=True)
    conforms, report_graph, report_text = validate(
        data_graph,
        shacl_graph=str(shapes_path),
        advanced=True,
        inference="rdfs",
    )
    report_graph.serialize(destination=report_path, format="turtle")
    return {
        "status": "ok",
        "conforms": bool(conforms),
        "reportPath": str(report_path),
        "reportText": report_text,
    }
