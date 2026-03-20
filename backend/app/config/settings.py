from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    project_dir: Path
    data_dir: Path
    mappings_dir: Path
    ontology_dir: Path
    runtime_dir: Path
    store_dir: Path
    reports_dir: Path
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
    doim_ns = "http://purl.org/doim/1.0#"
    telecom_ns = "http://example.com/telecom#"
    data_ns = "http://example.com/telecom/data/"
    default_query = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX doim: <http://purl.org/doim/1.0#>
PREFIX telecom: <http://example.com/telecom#>
SELECT ?subscriberId ?name ?riskLevel ?city ?plan
WHERE {
  ?s a telecom:Subscriber ;
     telecom:subscriberId ?subscriberId ;
     rdfs:label ?name ;
     telecom:city ?city ;
     telecom:planName ?plan ;
     telecom:inferredRiskLevel ?riskLevel .
}
ORDER BY DESC(?riskLevel) ?subscriberId
"""
    return Settings(
        project_dir=project_dir,
        data_dir=project_dir / "data" / "raw",
        mappings_dir=project_dir / "mappings",
        ontology_dir=project_dir / "ontology",
        runtime_dir=project_dir / "runtime",
        store_dir=project_dir / "runtime" / "store",
        reports_dir=project_dir / "runtime" / "reports",
        host=os.getenv("ONTOLOGY_HOST", "127.0.0.1"),
        port=int(os.getenv("ONTOLOGY_PORT", "8088")),
        doim_ns=doim_ns,
        telecom_ns=telecom_ns,
        data_ns=data_ns,
        base_graph_uri="urn:doim:poc:base",
        deductions_graph_uri="urn:doim:poc:deductions",
        default_query=default_query,
    )

