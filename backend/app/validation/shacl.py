"""
模块功能：
- SHACL 校验封装，负责执行约束校验并输出报告文件。
- 该文件位于 `backend/app/validation/shacl.py`，负责执行 SHACL 校验并输出校验结果摘要，供语义服务和报告层复用。
- 文件中对外暴露或复用的主要函数包括：`run_shacl_validation`。
"""

from __future__ import annotations

from pathlib import Path

from rdflib import Graph

try:
    from pyshacl import validate
except ImportError:  # pragma: no cover
    validate = None


def run_shacl_validation(data_graph: Graph, shapes_path: Path, report_path: Path) -> dict[str, object]:
    """
    功能：
    - 对数据图执行 SHACL 校验，并返回可供前端展示的结果摘要。

    输入：
    - `data_graph`: 待执行校验或写入数据的 RDF 图对象。
    - `shapes_path`: SHACL 约束文件路径。
    - `report_path`: 校验报告输出路径。

    输出：
    - 返回值: 返回字典结构，包含本次处理产生的结果数据。
    """
    if validate is None:
        return {"status": "skipped", "reason": "pyshacl_not_installed"}
    if not shapes_path.exists():
        return {"status": "skipped", "reason": "shapes_not_found"}

    report_path.parent.mkdir(parents=True, exist_ok=True)
    graph_size = len(data_graph)
    advanced = graph_size <= 5000
    inference_mode = "rdfs" if graph_size <= 5000 else "none"
    conforms, report_graph, report_text = validate(
        data_graph,
        shacl_graph=str(shapes_path),
        advanced=advanced,
        inference=inference_mode,
    )
    report_graph.serialize(destination=report_path, format="turtle")
    return {
        "status": "ok",
        "conforms": bool(conforms),
        "reportPath": str(report_path),
        "reportText": report_text,
        "advanced": advanced,
        "inferenceMode": inference_mode,
    }
