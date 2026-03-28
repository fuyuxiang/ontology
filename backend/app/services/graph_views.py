"""
模块功能：
- 前端图谱展示构建器。
- 该文件位于 `backend/app/services/graph_views.py`，负责把后端记录转换为前端可消费的概览图和实体局部图数据。
- 文件中对外暴露或复用的主要函数包括：`build_overview_graph`, `build_entity_graph`, `_add_overview_node`, `_overview_related_node_id`, `_rows_match_relation`。
"""

from __future__ import annotations

import math
from typing import Any, Callable
from urllib.parse import quote

from app.scenario.config import RelationConfig, ScenarioConfig


OVERVIEW_CLUSTER_OFFSETS: dict[str, tuple[float, float]] = {
    "porting_query": (0.0, -78.0),
    "contract_info": (80.0, -34.0),
    "charge_info": (88.0, 42.0),
    "arrear_info": (0.0, 94.0),
    "customer_service": (-88.0, 42.0),
    "retention_action": (-80.0, -34.0),
    "voice_usage": (-96.0, 0.0),
}


def build_overview_graph(
    *,
    records: dict[str, dict[str, Any]],
    source_rows: dict[str, list[dict[str, Any]]],
    scenario: ScenarioConfig,
) -> dict[str, Any]:
    """
    功能：
    - 构建首页概览图，只抽样展示每个主实体的一组代表性关联节点。

    输入：
    - `records`: 按实体标识组织的聚合记录集合。
    - `source_rows`: 按数据集分组的原始或清洗后行数据。
    - `scenario`: 当前激活的场景配置对象。

    输出：
    - 返回值: 返回字典结构，包含本次处理产生的结果数据。
    """
    primary_items = list(records.values())
    if not primary_items:
        return {
            "nodes": [],
            "edges": [],
            "totalPrimaryEntities": 0,
            "totalInteractions": 0,
            "displayedPrimaryEntities": 0,
        }

    nodes_by_id: dict[str, dict[str, Any]] = {}
    position_accumulators: dict[str, dict[str, float]] = {}
    edges_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    cols = max(4, math.ceil(math.sqrt(len(primary_items))))
    cluster_width = 260.0
    cluster_height = 220.0
    margin_x = 160.0
    margin_y = 150.0

    for index, record in enumerate(primary_items):
        row = index // cols
        col = index % cols
        center_x = margin_x + col * cluster_width
        center_y = margin_y + row * cluster_height
        sampled_rows: dict[str, dict[str, Any]] = {
            scenario.primary_dataset: record["primary"],
        }
        sampled_node_ids: dict[str, str] = {}
        primary_node_id = record["nodeId"]
        sampled_node_ids[scenario.primary_dataset] = primary_node_id
        _add_overview_node(
            nodes_by_id,
            position_accumulators,
            primary_node_id,
            record["displayName"],
            scenario.primary_node_type,
            center_x,
            center_y,
        )

        for dataset_key in scenario.graph_datasets:
            related_rows = record["related"].get(dataset_key, [])
            if not related_rows:
                continue
            related = related_rows[0]
            sampled_rows[dataset_key] = related
            related_node_id = _overview_related_node_id(scenario, dataset_key, related)
            sampled_node_ids[dataset_key] = related_node_id
            offset_x, offset_y = OVERVIEW_CLUSTER_OFFSETS.get(dataset_key, (0.0, 0.0))
            _add_overview_node(
                nodes_by_id,
                position_accumulators,
                related_node_id,
                str(related.get("_label") or scenario.datasets[dataset_key].entity_label),
                scenario.datasets[dataset_key].node_type,
                center_x + offset_x,
                center_y + offset_y,
            )

        for relation in scenario.relations:
            source_row = sampled_rows.get(relation.source_dataset)
            target_row = sampled_rows.get(relation.target_dataset)
            if source_row is None or target_row is None:
                continue
            if not _rows_match_relation(scenario, relation, source_row, target_row):
                continue
            source_id = sampled_node_ids.get(relation.source_dataset)
            target_id = sampled_node_ids.get(relation.target_dataset)
            if source_id is None or target_id is None:
                continue
            edges_by_key[(source_id, target_id, relation.label)] = {
                "source": source_id,
                "target": target_id,
                "label": relation.label,
            }

    nodes = []
    for node_id, node in nodes_by_id.items():
        accumulator = position_accumulators[node_id]
        count = max(accumulator["count"], 1.0)
        nodes.append(
            {
                **node,
                "x": accumulator["x"] / count,
                "y": accumulator["y"] / count,
            }
        )

    return {
        "nodes": nodes,
        "edges": list(edges_by_key.values()),
        "totalPrimaryEntities": len(records),
        "totalInteractions": sum(len(source_rows.get(key, [])) for key in scenario.interaction_datasets),
        "displayedPrimaryEntities": len(primary_items),
    }


def build_entity_graph(
    *,
    record: dict[str, Any],
    inference: dict[str, Any],
    runtime_case: dict[str, Any] | None,
    scenario: ScenarioConfig,
    node_id_for_row: Callable[[str, dict[str, Any]], str],
    relation_label_for: Callable[[str, str], str],
) -> dict[str, Any]:
    """
    功能：
    - 构建单个实体的详情图谱。

    输入：
    - `record`: 单个实体或业务对象的聚合记录。
    - `inference`: 按实体组织的推理结果集合。
    - `runtime_case`: 单个动作执行记录。
    - `scenario`: 当前激活的场景配置对象。
    - `node_id_for_row`: 函数执行所需的 `node_id_for_row` 参数。
    - `relation_label_for`: 函数执行所需的 `relation_label_for` 参数。

    输出：
    - 返回值: 返回字典结构，包含本次处理产生的结果数据。
    """
    primary_node = {
        "id": record["nodeId"],
        "label": record["displayName"],
        "type": scenario.primary_node_type,
    }
    nodes = [primary_node]
    edges = []

    result_node = {
        "id": f"risk:{record['entityId']}",
        "label": f"{inference['riskLevel']} 风险",
        "type": "RiskResult",
    }
    action_node = {
        "id": f"action:{record['entityId']}",
        "label": inference["recommendedAction"],
        "type": "Action",
    }
    nodes.extend([result_node, action_node])
    edges.append({"source": primary_node["id"], "target": result_node["id"], "label": "推理输出"})
    edges.append({"source": result_node["id"], "target": action_node["id"], "label": "推荐动作"})

    for dataset_key in scenario.graph_datasets:
        for row in record["related"].get(dataset_key, [])[:2]:
            node_id = node_id_for_row(dataset_key, row)
            nodes.append(
                {
                    "id": node_id,
                    "label": str(row.get("_label") or scenario.datasets[dataset_key].entity_label),
                    "type": scenario.datasets[dataset_key].node_type,
                }
            )
            edges.append(
                {
                    "source": primary_node["id"],
                    "target": node_id,
                    "label": relation_label_for(scenario.primary_dataset, dataset_key),
                }
            )

    for factor in inference["factors"]:
        node_id = f"factor:{factor.code}"
        nodes.append({"id": node_id, "label": factor.label, "type": "Inference"})
        edges.append({"source": primary_node["id"], "target": node_id, "label": "命中风险因子"})
        edges.append({"source": node_id, "target": result_node["id"], "label": "支撑结论"})

    for rule_label in inference["rules"]:
        node_id = f"rule:{rule_label.encode('utf-8').hex()}"
        nodes.append({"id": node_id, "label": rule_label, "type": "Inference"})
        edges.append({"source": primary_node["id"], "target": node_id, "label": "命中规则"})
        edges.append({"source": node_id, "target": result_node["id"], "label": "触发推理"})

    if runtime_case:
        case_node_id = f"case:{record['entityId']}"
        nodes.append(
            {
                "id": case_node_id,
                "label": f"{runtime_case['state']} Case",
                "type": "Case",
            }
        )
        edges.append({"source": primary_node["id"], "target": case_node_id, "label": "运营处置"})

        for task in runtime_case.get("tasks", [])[:3]:
            task_node_id = f"task:{task['id']}"
            nodes.append(
                {
                    "id": task_node_id,
                    "label": f"{task['title']} [{task['status']}]",
                    "type": "Task",
                }
            )
            edges.append({"source": case_node_id, "target": task_node_id, "label": "任务"})

        for action in runtime_case.get("availableActions", [])[:3]:
            action_def_node_id = f"action-definition:{action['id']}"
            nodes.append(
                {
                    "id": action_def_node_id,
                    "label": action["label"],
                    "type": "ActionDefinition",
                }
            )
            edges.append({"source": case_node_id, "target": action_def_node_id, "label": "可执行动作"})

        for timeline_item in runtime_case.get("timeline", [])[:4]:
            event_node_id = f"timeline:{record['entityId']}:{quote(str(timeline_item['time']), safe='')}"
            nodes.append(
                {
                    "id": event_node_id,
                    "label": timeline_item["title"],
                    "type": "Event",
                }
            )
            edges.append({"source": case_node_id, "target": event_node_id, "label": "时间线"})

    return {"nodes": nodes, "edges": edges}


def _add_overview_node(
    nodes_by_id: dict[str, dict[str, Any]],
    position_accumulators: dict[str, dict[str, float]],
    node_id: str,
    label: str,
    node_type: str,
    x: float,
    y: float,
) -> None:
    """
    功能：
    - 添加overviewnode。

    输入：
    - `nodes_by_id`: 字典参数 `nodes_by_id`，承载键值形式的输入数据。
    - `position_accumulators`: 字典参数 `position_accumulators`，承载键值形式的输入数据。
    - `node_id`: 函数执行所需的 `node_id` 参数。
    - `label`: 函数执行所需的 `label` 参数。
    - `node_type`: 函数执行所需的 `node_type` 参数。
    - `x`: 函数执行所需的 `x` 参数。
    - `y`: 函数执行所需的 `y` 参数。

    输出：
    - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
    """
    nodes_by_id.setdefault(
        node_id,
        {
            "id": node_id,
            "label": label,
            "type": node_type,
        },
    )
    accumulator = position_accumulators.setdefault(node_id, {"x": 0.0, "y": 0.0, "count": 0.0})
    accumulator["x"] += x
    accumulator["y"] += y
    accumulator["count"] += 1.0


def _overview_related_node_id(scenario: ScenarioConfig, dataset_key: str, row: dict[str, Any]) -> str:
    """
    功能：
    - 处理与 `_overview_related_node_id` 相关的逻辑。

    输入：
    - `scenario`: 当前激活的场景配置对象。
    - `dataset_key`: 需要持久化或查询的 RDF 数据集对象。
    - `row`: 单行源数据或中间对象数据。

    输出：
    - 返回值: 返回字符串结果，供调用方继续展示、拼接或查询。
    """
    label = str(row.get("_label") or scenario.datasets[dataset_key].entity_label)
    return f"overview:{scenario.datasets[dataset_key].node_type.lower()}:{quote(label, safe='')}"


def _rows_match_relation(
    scenario: ScenarioConfig,
    relation: RelationConfig,
    source_row: dict[str, Any],
    target_row: dict[str, Any],
) -> bool:
    """
    功能：
    - 处理与 `_rows_match_relation` 相关的逻辑。

    输入：
    - `scenario`: 当前激活的场景配置对象。
    - `relation`: 函数执行所需的 `relation` 参数。
    - `source_row`: 字典参数 `source_row`，承载键值形式的输入数据。
    - `target_row`: 字典参数 `target_row`，承载键值形式的输入数据。

    输出：
    - 返回值: 返回布尔值，表示条件是否成立或当前操作是否允许。
    """
    source_field = scenario.datasets[relation.source_dataset].join_keys[relation.source_join_key]
    target_field = scenario.datasets[relation.target_dataset].join_keys[relation.target_join_key]
    source_value = source_row.get(source_field)
    target_value = target_row.get(target_field)
    if source_value in (None, "") or target_value in (None, ""):
        return False
    return str(source_value) == str(target_value)
