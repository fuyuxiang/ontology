"""
模块功能：
- 命名空间工具，负责创建和绑定 RDF 前缀。
- 该文件位于 `backend/app/ontology/namespaces.py`，负责创建和绑定 RDF 命名空间，统一图谱中的前缀定义。
- 文件中对外暴露或复用的主要函数包括：`make_namespaces`, `bind_prefixes`。
"""

from __future__ import annotations

from rdflib import Graph, Namespace

from app.config.settings import Settings


def make_namespaces(settings: Settings) -> dict[str, Namespace]:
    """
    功能：
    - 根据运行时配置构造命名空间对象。

    输入：
    - `settings`: 运行时配置对象，提供目录路径、命名空间和环境参数。

    输出：
    - 返回值: 返回字典结构，包含本次处理产生的结果数据。
    """
    return {
        "doim": Namespace(settings.doim_ns),
        "telecom": Namespace(settings.telecom_ns),
        "data": Namespace(settings.data_ns),
    }


def bind_prefixes(graph: Graph, settings: Settings) -> None:
    """
    功能：
    - 为图对象绑定常用前缀，便于后续序列化输出。

    输入：
    - `graph`: 需要读取或写入的 RDF 图对象。
    - `settings`: 运行时配置对象，提供目录路径、命名空间和环境参数。

    输出：
    - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
    """
    namespaces = make_namespaces(settings)
    graph.bind("doim", namespaces["doim"])
    graph.bind("telecom", namespaces["telecom"])
    graph.bind("data", namespaces["data"])
