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
        description="返回系统中所有本体实体和关系的概览。用于了解数据模型结构。",
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
        description="获取本体实体的详细信息，包括属性列表和关联关系。",
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
    # ── 本体构建器（对话生成模式）专用工具 ──
    AgentToolSpec(
        name="list_business_datasources",
        description="列出当前可用的业务数据源（数据资产），按业务领域和关键字筛选；返回 display_card=asset_picker，前端会渲染为多选卡片让用户勾选。仅在用户描述完业务后、确认资产前调用。",
        parameters={
            "domain": {"type": "string", "description": "业务领域，如政企、宽带、退单。可为空字符串"},
            "keywords": {"type": "array", "items": {"type": "string"}, "description": "关键词列表（可选）"},
        },
        required=("domain",),
    ),
    AgentToolSpec(
        name="list_business_documents",
        description="列出业务文档库里的候选文档（Word/Excel/PDF），可按 domain 或已选 datasource_ids 关联过滤；返回 display_card=asset_picker。仅在用户已经选完数据源后、开始抽取前调用。",
        parameters={
            "domain": {"type": "string", "description": "业务领域，可为空"},
            "datasource_ids": {"type": "array", "items": {"type": "string"}, "description": "已选中的数据源 id 数组（可选）"},
        },
        required=("domain",),
    ),
    AgentToolSpec(
        name="analyze_assets_for_ontology",
        description="基于选中的数据源（表结构）+ 业务文档（解析文本）+ 业务上下文，让 LLM 抽取本体对象/属性/关系，并产出动作建议。返回 entities[]/relations[]/suggested_actions[]。仅在用户选完资产和文档后调用。",
        parameters={
            "datasource_ids": {"type": "array", "items": {"type": "string"}, "description": "选中的数据源 id 数组"},
            "document_ids": {"type": "array", "items": {"type": "string"}, "description": "选中的业务文档 id 数组"},
            "business_context": {"type": "string", "description": "用户描述的业务场景（前几轮对话总结）"},
        },
        required=("datasource_ids", "document_ids", "business_context"),
    ),
    # ── Tier 1: 数据查询（重构） ──
    AgentToolSpec(
        name="ontology_query_instances",
        description="查询本体实体的实例数据，支持条件过滤和分页。优先使用此工具。",
        parameters={
            "entity_name": {"type": "string", "description": "实体名称"},
            "filters": {"type": "object", "description": "过滤条件 {属性名: 值}"},
            "page": {"type": "integer", "description": "页码，默认 1"},
            "page_size": {"type": "integer", "description": "每页条数，默认 50，最大 200"},
        },
        required=("entity_name",),
    ),
    AgentToolSpec(
        name="ontology_get_attr_mapping",
        description="获取实体属性到物理数据库字段的映射关系，用于编写 SQL 前了解字段名。",
        parameters={
            "entity_names": {"type": "array", "items": {"type": "string"}, "description": "实体名称列表"},
        },
        required=("entity_names",),
    ),
    AgentToolSpec(
        name="ontology_complex_sql",
        description="执行复杂只读 SQL 查询（CTE/窗口函数/多表 JOIN）。需先通过 get_attr_mapping 获取字段名。仅允许 SELECT。",
        parameters={
            "sql": {"type": "string", "description": "SQL 语句（使用物理字段名）"},
            "params": {"type": "array", "items": {"type": "string"}, "description": "参数化查询的参数值列表"},
        },
        required=("sql",),
    ),
    # ── Tier 2: 逻辑/动作调用 ──
    AgentToolSpec(
        name="ontology_list_capabilities",
        description="列出当前本体可用的所有逻辑函数和动作函数，返回名称、描述、参数 schema。",
        parameters={
            "type": {"type": "string", "enum": ["logic", "action", "all"], "description": "过滤类型，默认 all"},
        },
    ),
    AgentToolSpec(
        name="ontology_run_logic",
        description="执行指定的逻辑函数，返回计算结果。函数名通过 list_capabilities 获取。",
        parameters={
            "callable_name": {"type": "string", "description": "函数名称"},
            "params": {"type": "object", "description": "函数所需参数"},
        },
        required=("callable_name",),
    ),
    AgentToolSpec(
        name="ontology_run_action",
        description="执行指定的动作函数（如生成报告、导出数据），可能有副作用。",
        parameters={
            "callable_name": {"type": "string", "description": "动作名称"},
            "params": {"type": "object", "description": "动作所需参数"},
        },
        required=("callable_name",),
        sensitive=True,
    ),
)


def agent_tool_definitions() -> list[dict[str, Any]]:
    """返回给 LLM 的 OpenAI tool schema 列表"""
    return [spec.openai_tool() for spec in AGENT_TOOL_SPECS]


def agent_tool_catalog() -> list[dict[str, Any]]:
    """返回给前端的工具目录"""
    return [spec.catalog_entry() for spec in AGENT_TOOL_SPECS]
