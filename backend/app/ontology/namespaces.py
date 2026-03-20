from __future__ import annotations

from rdflib import Graph, Namespace

from app.config.settings import Settings


def make_namespaces(settings: Settings) -> dict[str, Namespace]:
    return {
        "doim": Namespace(settings.doim_ns),
        "telecom": Namespace(settings.telecom_ns),
        "data": Namespace(settings.data_ns),
    }


def bind_prefixes(graph: Graph, settings: Settings) -> None:
    namespaces = make_namespaces(settings)
    graph.bind("doim", namespaces["doim"])
    graph.bind("telecom", namespaces["telecom"])
    graph.bind("data", namespaces["data"])

