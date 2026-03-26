"""命名空间工具，负责创建和绑定 RDF 前缀。"""

from __future__ import annotations

from rdflib import Graph, Namespace

from app.config.settings import Settings


def make_namespaces(settings: Settings) -> dict[str, Namespace]:
    """根据运行时配置构造命名空间对象。"""
    return {
        "doim": Namespace(settings.doim_ns),
        "telecom": Namespace(settings.telecom_ns),
        "data": Namespace(settings.data_ns),
    }


def bind_prefixes(graph: Graph, settings: Settings) -> None:
    """为图对象绑定常用前缀，便于后续序列化输出。"""
    namespaces = make_namespaces(settings)
    graph.bind("doim", namespaces["doim"])
    graph.bind("telecom", namespaces["telecom"])
    graph.bind("data", namespaces["data"])
