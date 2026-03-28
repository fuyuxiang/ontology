"""
模块功能：
- 图数据持久化仓储，负责 TriG 导出和 Oxigraph 存储同步。
- 该文件位于 `backend/app/graph/repository.py`，负责 RDF 数据集的持久化和查询访问，屏蔽底层存储细节。
- 文件中定义的核心类包括：`GraphRepository`。
"""

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
    """
    功能：
    - 封装语义图的落盘与查询能力。
    - 该类定义在 `backend/app/graph/repository.py` 中，用于组织与 `GraphRepository` 相关的数据或行为。
    """

    def __init__(self, settings: Settings) -> None:
        """
        功能：
        - 初始化当前对象并准备后续调用所需的依赖、状态和缓存。

        输入：
        - `settings`: 运行时配置对象，提供目录路径、命名空间和环境参数。

        输出：
        - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
        """
        self.settings = settings

    def persist(self, dataset: Dataset) -> dict[str, object]:
        """
        功能：
        - 将当前数据集序列化到文件，并尽量同步到 Oxigraph。

        输入：
        - `dataset`: 需要持久化或查询的 RDF 数据集对象。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
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
        """
        功能：
        - 在 Oxigraph 只读存储上执行查询，不可用时返回空值。

        输入：
        - `sparql`: 待提交到底层存储的 SPARQL 查询语句。
        - `graph_uris`: 需要读取或写入的 RDF 图对象。

        输出：
        - 返回值: 返回 `Any` 类型结果，供后续流程继续消费。
        """
        if Store is None or NamedNode is None:
            return None
        store = Store.read_only(str(self.settings.store_dir))
        default_graph = [NamedNode(uri) for uri in graph_uris]
        return store.query(sparql, default_graph=default_graph)
