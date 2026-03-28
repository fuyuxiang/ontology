"""
模块功能：
- 监督式 agent 使用的对象模型目录。
- 该文件位于 `backend/app/object_catalog.py`，定义对象模型目录，向前端和 agent 描述系统支持的对象类型。
- 文件中对外暴露或复用的主要函数包括：`build_object_model`。
"""

from __future__ import annotations

from typing import Any


def build_object_model(*, primary_entity_label: str, primary_node_type: str) -> list[dict[str, Any]]:
    """
    功能：
    - 返回稳定对象模型定义，仅主实体标签随场景变化。

    输入：
    - `primary_entity_label`: 函数执行所需的 `primary_entity_label` 参数。
    - `primary_node_type`: 函数执行所需的 `primary_node_type` 参数。

    输出：
    - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
    """
    return [
        {
            "key": "User",
            "label": primary_entity_label,
            "ontologyType": primary_node_type,
            "identityField": "entityId",
            "description": "主业务对象，聚合风险推理结果、运营处置状态与关键展示字段。",
            "attributes": [
                "entityId",
                "displayName",
                "riskLevel",
                "recommendedAction",
                "alertState",
                "caseState",
                "areaId",
            ],
        },
        {
            "key": "RiskAlert",
            "label": "风险告警",
            "ontologyType": "RiskAlert",
            "identityField": "objectId",
            "description": "围绕主业务对象生成的风险告警对象，可用于定位风险等级与建议动作。",
            "attributes": [
                "entityId",
                "displayName",
                "riskLevel",
                "recommendedAction",
                "alertState",
                "caseId",
            ],
        },
        {
            "key": "RetentionCase",
            "label": "运营 Case",
            "ontologyType": "RetentionCase",
            "identityField": "caseId",
            "description": "运营运行时中的处置主对象，承载队列、优先级、状态与可执行动作。",
            "attributes": [
                "caseId",
                "entityId",
                "state",
                "risk_level",
                "priority",
                "queue_name",
                "owner_role",
            ],
        },
        {
            "key": "Task",
            "label": "运营任务",
            "ontologyType": "Task",
            "identityField": "id",
            "description": "围绕 Case 生成的待办任务对象，用于驱动执行闭环。",
            "attributes": [
                "id",
                "case_id",
                "entity_id",
                "action_id",
                "status",
                "assignee_role",
                "queue_name",
            ],
        },
        {
            "key": "InteractionEvent",
            "label": "交互事件",
            "ontologyType": "Interaction",
            "identityField": "objectId",
            "description": "从交互类数据集中抽出的关键事件对象，用于问答与追踪用户行为信号。",
            "attributes": [
                "objectId",
                "datasetKey",
                "entityId",
                "displayName",
                "eventTime",
                "summary",
                "sourceSystem",
            ],
        },
        {
            "key": "RuleHit",
            "label": "规则命中",
            "ontologyType": "Rule",
            "identityField": "objectId",
            "description": "规则命中统计对象，用于回答规则命中排行与解释类问题。",
            "attributes": ["objectId", "rule", "count"],
        },
        {
            "key": "ActionDefinition",
            "label": "动作定义",
            "ontologyType": "ActionDefinition",
            "identityField": "id",
            "description": "监督 agent 可建议但不默认直接执行的动作类型。",
            "attributes": [
                "id",
                "label",
                "description",
                "allowed_roles",
                "allowed_states",
                "allowed_risk_levels",
            ],
        },
    ]
