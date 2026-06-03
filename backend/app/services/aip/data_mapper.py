"""
AIP 数据映射器 — 根据边上的 mapping 配置，从 context 中组装下游节点的输入。

边的 mapping 格式（存在 edge.data.mapping 中）:
[
  {"source_field": "node_a.output.name", "target_field": "customer_name"},
  {"source_field": "node_b.result[0].id",  "target_field": "order_id"},
  {"source_field": "$input.user_id",        "target_field": "user_id"},
]

支持的路径语法:
- "node_id.field.subfield"  — 从某节点输出中取字段
- "$input.field"            — 从场景 input_params 中取
- "$context.field"          — 从全局 context 平铺字段中取
- "literal:some_value"      — 硬编码字面量
"""
from __future__ import annotations

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)


def resolve_node_input(
    node_id: str,
    incoming_edges: list[dict],
    context: dict[str, Any],
) -> dict[str, Any]:
    """根据入边上的 mapping 配置，从 context 组装当前节点的结构化输入。

    如果边上没有 mapping，返回空 dict（退化为原模板语法）。
    """
    mapped: dict[str, Any] = {}

    for edge in incoming_edges:
        edge_data = edge.get("data") or {}
        mappings = edge_data.get("mapping") or []
        if not mappings:
            continue

        source_node = edge.get("source", "")

        for m in mappings:
            source_path = m.get("source_field", "")
            target_field = m.get("target_field", "")
            if not source_path or not target_field:
                continue

            value = _resolve_path(source_path, source_node, context)
            if value is not None:
                mapped[target_field] = value

    return mapped


def _resolve_path(path: str, default_source: str, context: dict) -> Any:
    """解析路径表达式，从 context 中取值。"""
    if path.startswith("literal:"):
        return path[8:]

    if path.startswith("$input."):
        field = path[7:]
        input_params = context.get("input_params", {})
        return _deep_get(input_params, field)

    if path.startswith("$context."):
        field = path[9:]
        return _deep_get(context, field)

    # "node_id.field.subfield" 或 "field.subfield"（相对于 default_source）
    parts = path.split(".", 1)
    if parts[0] in context and isinstance(context.get(parts[0]), dict):
        node_id = parts[0]
        remainder = parts[1] if len(parts) > 1 else ""
    else:
        node_id = default_source
        remainder = path

    node_output = context.get(node_id)
    if node_output is None:
        return None

    if not remainder:
        return node_output

    return _deep_get(node_output, remainder)


def _deep_get(obj: Any, path: str) -> Any:
    """支持 dot 分隔和数组索引的深度取值，如 'result[0].name'。"""
    if not path:
        return obj

    tokens = _tokenize_path(path)
    cur = obj
    for token in tokens:
        if cur is None:
            return None
        if isinstance(token, int):
            if isinstance(cur, (list, tuple)) and 0 <= token < len(cur):
                cur = cur[token]
            else:
                return None
        else:
            if isinstance(cur, dict):
                cur = cur.get(token)
            else:
                return None
    return cur


_PATH_TOKEN_RE = re.compile(r'(\w+)|\[(\d+)\]')


def _tokenize_path(path: str) -> list[str | int]:
    """将 'result[0].name' 分解为 ['result', 0, 'name']"""
    tokens: list[str | int] = []
    for segment in path.split("."):
        for match in _PATH_TOKEN_RE.finditer(segment):
            if match.group(1):
                tokens.append(match.group(1))
            elif match.group(2):
                tokens.append(int(match.group(2)))
    return tokens


def get_incoming_edges(node_id: str, edges: list[dict]) -> list[dict]:
    """获取指向某节点的所有入边。"""
    return [e for e in edges if e.get("target") == node_id]


def get_outgoing_edges(node_id: str, edges: list[dict]) -> list[dict]:
    """获取某节点的所有出边。"""
    return [e for e in edges if e.get("source") == node_id]
