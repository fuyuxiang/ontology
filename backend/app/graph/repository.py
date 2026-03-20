from __future__ import annotations

from pathlib import Path

from rdflib import Dataset

from app.config.settings import Settings

try:
    from pyoxigraph import NamedNode, RdfFormat, Store
except ImportError:  # pragma: no cover
    NamedNode = None
    RdfFormat = None
    Store = None


class GraphRepository:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def persist(self, dataset: Dataset) -> dict[str, object]:
        self.settings.store_dir.mkdir(parents=True, exist_ok=True)
        self.settings.reports_dir.mkdir(parents=True, exist_ok=True)
        trig_path = self.settings.reports_dir / "dataset.trig"
        dataset.serialize(destination=trig_path, format="trig")

        if Store is None or RdfFormat is None:
            return {
                "storeBackend": "rdflib-only",
                "datasetPath": str(trig_path),
            }

        store = Store(str(self.settings.store_dir))
        store.clear()
        try:
            store.bulk_load(path=str(trig_path), format=RdfFormat.TRIG)
            store.optimize()
        except Exception as exc:  # pragma: no cover - defensive fallback
            return {
                "storeBackend": "rdflib-only",
                "datasetPath": str(trig_path),
                "storePath": str(self.settings.store_dir),
                "reason": "pyoxigraph_bulk_load_failed",
                "error": str(exc),
            }
        return {
            "storeBackend": "pyoxigraph",
            "datasetPath": str(trig_path),
            "storePath": str(self.settings.store_dir),
        }

    def query(self, sparql: str, graph_uris: list[str]):
        if Store is None or NamedNode is None:
            return None
        store = Store.read_only(str(self.settings.store_dir))
        default_graph = [NamedNode(uri) for uri in graph_uris]
        return store.query(sparql, default_graph=default_graph)
