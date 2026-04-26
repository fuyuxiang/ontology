"""
Agent 工具定义 — 智能问答可用的工具 schema
供 LLM function calling 和前端工具目录共同使用
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentToolSpec:
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    required: tuple[str, ...] = ()
    sensitive: bool = False

    def openai_tool(self) -> dict[str, Any]:
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

    def catalog_entry(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputs": list(self.parameters.keys()),
        }


AGENT_TOOL_SPECS: tuple[AgentToolSpec, ...] = (
    AgentToolSpec(
        name="describe_ontology_model",
        description="返回系统中所有本体实体、关系和业务规则的概览。用于了解数据模型结构。",
    ),
    AgentToolSpec(
        name="list_datasources",
        description="列出所有已启用的数据源及其关联的数据表名称、类型和记录数。",
    ),
    AgentToolSpec(
        name="get_table_schema",
        description="获取指定数据源关联表的列元数据（列名、类型、是否主键、注释）。",
        parameters={
            "datasource_name": {"type": "string", "description": "数据源名称（即表名）"},
        },
        required=("datasource_name",),
    ),
    AgentToolSpec(
        name="query_datasource",
        description="对指定数据源执行只读 SQL 查询，返回查询结果。仅允许 SELECT 语句。",
        parameters={
            "datasource_name": {"type": "string", "description": "数据源名称（即表名）"},
            "sql": {"type": "string", "description": "要执行的 SELECT SQL 语句"},
            "limit": {"type": "integer", "description": "最大返回行数，默认 50，最大 200"},
        },
        required=("datasource_name", "sql"),
    ),
    AgentToolSpec(
        name="get_entity_detail",
        description="获取本体实体的详细信息，包括属性列表、关联关系和相关规则。",
        parameters={
            "entity_name": {"type": "string", "description": "实体英文名称"},
        },
        required=("entity_name",),
    ),
    AgentToolSpec(
        name="query_entity_data",
        description="通过本体实体名查询真实实例数据。自动解析实体对应的数据源和表，无需手写SQL。支持按属性过滤。优先使用此工具而非 query_datasource。",
        parameters={
            "entity_name": {"type": "string", "description": "本体实体英文名称（如 CbssSubscriber）"},
            "filters": {"type": "object", "description": "过滤条件，键为属性名，值为期望值（如 {\"user_id\": \"123\", \"user_status\": \"1\"}）"},
            "fields": {"type": "array", "items": {"type": "string"}, "description": "要返回的属性列表（可选，默认返回全部）"},
            "limit": {"type": "integer", "description": "最大返回行数，默认 20，最大 200"},
        },
        required=("entity_name",),
    ),
    AgentToolSpec(
        name="get_business_rules",
        description="查询业务规则列表，可按关联实体和状态过滤。",
        parameters={
            "entity_name": {"type": "string", "description": "按关联实体名称过滤（可选）"},
            "status": {"type": "string", "description": "规则状态过滤，默认 active", "enum": ["active", "inactive", "all"]},
        },
    ),
    AgentToolSpec(
        name="evaluate_rule",
        description="对指定用户评估一条业务规则，基于真实数据源查询条件并返回是否触发、匹配条件明细和置信度。",
        parameters={
            "rule_name": {"type": "string", "description": "规则名称（如'高风险携转预警规则'）"},
            "user_id": {"type": "string", "description": "待评估的用户ID"},
        },
        required=("rule_name", "user_id"),
    ),
    AgentToolSpec(
        name="evaluate_all_rules",
        description="对指定用户评估所有活跃的结构化规则，返回每条规则的触发结果和综合风险等级。",
        parameters={
            "user_id": {"type": "string", "description": "待评估的用户ID"},
        },
        required=("user_id",),
    ),
    AgentToolSpec(
        name="screen_users_by_rule",
        description="根据规则批量筛选用户。先找到规则，再根据规则条件自动构建SQL查询数据源，返回命中规则的用户列表。用于回答'有哪些高风险用户'等批量筛选类问题。",
        parameters={
            "rule_name": {"type": "string", "description": "规则名称（如'高风险携转预警规则'）"},
            "limit": {"type": "integer", "description": "最大返回用户数，默认 50"},
        },
        required=("rule_name",),
    ),
    AgentToolSpec(
        name="execute_action",
        description="执行或模拟执行一个业务动作（如携转风险评估、触发维系策略），返回执行结果和预期效果。",
        parameters={
            "action_name": {"type": "string", "description": "动作名称（如'触发维系策略'或英文名'TriggerRetentionStrategy'）"},
            "params": {"type": "object", "description": "动作所需参数（如 {\"user_id\": \"123\", \"risk_level\": \"high\"}）"},
            "dry_run": {"type": "boolean", "description": "是否模拟执行，默认 true"},
        },
        required=("action_name",),
        sensitive=True,
    ),
)


def agent_tool_definitions() -> list[dict[str, Any]]:
    """返回给 LLM 的 OpenAI tool schema 列表"""
    return [spec.openai_tool() for spec in AGENT_TOOL_SPECS]


def agent_tool_catalog() -> list[dict[str, Any]]:
    """返回给前端的工具目录"""
    return [spec.catalog_entry() for spec in AGENT_TOOL_SPECS]
