"""
模块功能：
- 监督式 agent 工具定义的单一配置来源。
- 该文件位于 `backend/app/agent_tools.py`，集中维护监督式 agent 可见的工具定义，保证前端展示与 LLM schema 一致。
- 文件中定义的核心类包括：`AgentToolSpec`。
- 文件中对外暴露或复用的主要函数包括：`agent_tool_catalog`, `agent_tool_definitions`。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentToolSpec:
    """
    功能：
    - 同时描述前端展示、LLM tool schema 与服务端工具标识。
    - 该类定义在 `backend/app/agent_tools.py` 中，用于组织与 `AgentToolSpec` 相关的数据或行为。
    - 类中声明的主要字段包括：`name`, `description`, `inputs`, `parameters`, `required`。
    """

    name: str
    description: str
    inputs: tuple[str, ...] = ()
    parameters: dict[str, Any] = field(default_factory=dict)
    required: tuple[str, ...] = ()

    def catalog_entry(self) -> dict[str, Any]:
        """
        功能：
        - 生成用于前端展示的工具目录项。

        输入：
        - 无。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        return {
            "name": self.name,
            "description": self.description,
            "inputs": list(self.inputs),
        }

    def openai_tool(self) -> dict[str, Any]:
        """
        功能：
        - 生成符合 OpenAI tool schema 的工具定义。

        输入：
        - 无。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": list(self.required),
                    "additionalProperties": False,
                },
            },
        }


AGENT_TOOL_SPECS: tuple[AgentToolSpec, ...] = (
    AgentToolSpec(
        name="describe_object_model",
        description="返回系统内的对象类型定义。",
    ),
    AgentToolSpec(
        name="query_objects",
        description="按对象类型、搜索词和过滤条件查询对象实例。",
        inputs=("object_type", "limit", "search", "filters"),
        parameters={
            "object_type": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            "search": {"type": "string"},
            "filters": {"type": "object"},
        },
        required=("object_type",),
    ),
    AgentToolSpec(
        name="get_object",
        description="按对象类型与对象标识读取单个对象详情。",
        inputs=("object_type", "object_id"),
        parameters={
            "object_type": {"type": "string"},
            "object_id": {"type": "string"},
        },
        required=("object_type", "object_id"),
    ),
    AgentToolSpec(
        name="run_semantic_query",
        description="对统一语义图执行 SPARQL 查询。",
        inputs=("query",),
        parameters={"query": {"type": "string"}},
        required=("query",),
    ),
    AgentToolSpec(
        name="get_summary",
        description="读取当前概览指标、风险分布与运营工作台汇总。",
    ),
    AgentToolSpec(
        name="execute_action",
        description="对运营对象执行动作。监督模式下通常需要人工确认。",
        inputs=(
            "action_id",
            "case_id",
            "entity_id",
            "actor_role",
            "actor_id",
            "actor_area_id",
            "parameters",
        ),
        parameters={
            "action_id": {"type": "string"},
            "case_id": {"type": "string"},
            "entity_id": {"type": "string"},
            "parameters": {"type": "object"},
        },
        required=("action_id",),
    ),
)


def agent_tool_catalog() -> list[dict[str, Any]]:
    """
    功能：
    - 返回给前端的工具目录。

    输入：
    - 无。

    输出：
    - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
    """
    return [spec.catalog_entry() for spec in AGENT_TOOL_SPECS]


def agent_tool_definitions() -> list[dict[str, Any]]:
    """
    功能：
    - 返回给 LLM 的 tool schema。

    输入：
    - 无。

    输出：
    - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
    """
    return [spec.openai_tool() for spec in AGENT_TOOL_SPECS]
