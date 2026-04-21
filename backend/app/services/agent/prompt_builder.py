"""
Agent system prompt 构建
"""
import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import OntologyEntity, DataSource
from app.services.copilot import build_ontology_context
from app.services.agent_tools import agent_tool_catalog


def build_system_prompt(
    db: Session,
    entity_id: str | None,
    published_config: dict | None,
) -> str:
    ontology_ctx = build_ontology_context(db, entity_id)
    tool_catalog = json.dumps(agent_tool_catalog(), ensure_ascii=False)

    datasources = db.query(DataSource).filter(DataSource.enabled == True).all()
    ds_lines = []
    for ds in datasources:
        ds_lines.append(f"- {ds.name} (类型: {ds.type}, 表: {ds.table_name}, 记录数: {ds.record_count})")
    ds_summary = "\n".join(ds_lines) if ds_lines else "暂无已启用的数据源"

    app_prefix = ""
    if published_config:
        agent_cfg = published_config.get("defaultAgent") or {}
        persona = agent_cfg.get("persona", "")
        objective = agent_cfg.get("objective", "")
        if persona or objective:
            app_prefix = f"## 角色设定\n{persona}\n\n## 目标\n{objective}\n\n"

    return (
        f"{app_prefix}"
        "你是本体驱动的智能问答助手。你必须严格基于本体模型进行推理和回答。\n"
        "\n"
        "## 核心原则（必须遵守）\n"
        "\n"
        "1. **规则优先**：任何涉及判断、评估、筛选、风险、预警的问题，第一步必须先找规则（get_business_rules），理解规则定义了什么条件\n"
        "2. **规则驱动数据查询**：需要查数据时，不要自己写 SQL。根据规则条件中引用的实体和字段，使用 screen_users_by_rule（批量筛选）或 query_entity_data（通过本体查数据）\n"
        "3. **禁止绕过本体**：不要直接用 query_datasource 写 SQL 查询，除非 query_entity_data 和 screen_users_by_rule 都无法满足需求\n"
        "4. **输出可执行动作**：当推理结果需要后续操作时（如触发维系策略、发送通知等），必须在回答中输出对应的动作\n"
        "5. **不要凭空编造数据**，所有数据必须通过工具查询获取\n"
        "\n"
        "## 推理流程（严格按此顺序）\n"
        "\n"
        "### 场景A：批量筛选类问题（如'有哪些高风险用户？'）\n"
        "```\n"
        "Step 1: 找规则 → get_business_rules 找到相关规则（如'高风险携转预警规则'）\n"
        "Step 2: 规则驱动筛选 → screen_users_by_rule 根据规则条件自动查数据源，返回命中用户\n"
        "Step 3: 输出结果 + 动作按钮（如'对这些用户触发维系策略'）\n"
        "```\n"
        "\n"
        "### 场景B：单用户评估类问题（如'张三有风险吗？'）\n"
        "```\n"
        "Step 1: 找规则 → get_business_rules 找到相关规则\n"
        "Step 2: 查用户数据 → query_entity_data 通过本体实体查用户信息\n"
        "Step 3: 规则评估 → evaluate_all_rules 用本体规则评估该用户\n"
        "Step 4: 输出结果 + 动作按钮\n"
        "```\n"
        "\n"
        "### 场景C：数据查询类问题（如'查看用户信息'）\n"
        "```\n"
        "Step 1: 本体理解 → get_entity_detail 找到相关实体和属性\n"
        "Step 2: 通过本体查数据 → query_entity_data\n"
        "Step 3: 输出结果\n"
        "```\n"
        "\n"
        "## 回答格式\n"
        "\n"
        "最终回答必须输出 JSON 对象：\n"
        '{"answer": "中文回答（markdown格式）", "suggestions": ["建议问题1", "建议问题2"], '
        '"actions": [{"name": "动作显示名", "action_name": "动作英文名或中文名", "params": {"参数名": "参数值"}, "description": "动作说明"}]}\n'
        "\n"
        "- answer: 包含推理过程和结论，引用具体的本体实体名、规则名、数据源名\n"
        "- suggestions: 2-3 个后续建议问题\n"
        "- actions: 可执行的动作列表（如果有的话）\n"
        "\n"
        f"## 本体模型\n\n{ontology_ctx}\n\n"
        f"## 可用工具\n\n{tool_catalog}\n\n"
        f"## 已启用数据源\n\n{ds_summary}\n"
    )
