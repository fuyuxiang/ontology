"""
Agent system prompt 构建
"""
import json

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.services.agent_tools import agent_tool_catalog
from app.services.copilot import build_ontology_context


def build_system_prompt(
    db: Session,
    entity_id: str | None,
    published_config: dict | None,
) -> str:
    ontology_ctx = build_ontology_context(db, entity_id)
    tool_catalog = json.dumps(agent_tool_catalog(), ensure_ascii=False)

    assets = db.query(Asset).filter(
        Asset.status == "active",
        Asset.kind.in_(["table", "sql_view"]),
    ).all()
    ds_lines = []
    for a in assets:
        table = (a.locator or {}).get("table", "")
        desc = a.description or ""
        ds_lines.append(f"- {a.name} (表: {table}, 描述: {desc})")
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
        "1. **本体优先**：需要查数据时，优先使用 query_entity_data 通过本体实体查数据，不要自己写 SQL\n"
        "2. **禁止绕过本体**：不要直接用 query_datasource 写 SQL 查询，除非 query_entity_data 无法满足需求\n"
        "3. **输出可执行动作**：当推理结果需要后续操作时（如触发维系策略、发送通知等），必须在回答中输出对应的动作\n"
        "4. **不要凭空编造数据**，所有数据必须通过工具查询获取\n"
        "\n"
        "## 推理流程\n"
        "\n"
        "### 场景A：数据查询类问题（如'查看用户信息'）\n"
        "```\n"
        "Step 1: 本体理解 → get_entity_detail 找到相关实体和属性\n"
        "Step 2: 通过本体查数据 → query_entity_data\n"
        "Step 3: 输出结果\n"
        "```\n"
        "\n"
        "### 场景B：分析类问题（如'退单根因分布？'）\n"
        "```\n"
        "Step 1: 数据采集 → query_entity_data 查询相关实体数据\n"
        "Step 2: 逻辑分析 → call_function 执行逻辑函数进行计算\n"
        "Step 3: 结论输出 → 综合分析结果给出结论，输出相关动作\n"
        "```\n"
        "\n"
        "## 回答格式\n"
        "\n"
        "最终回答必须输出 JSON 对象：\n"
        '{"answer": "中文回答（markdown格式）", "suggestions": ["建议问题1", "建议问题2"], '
        '"actions": [{"name": "动作显示名", "action_name": "动作英文名或中文名", "params": {"参数名": "参数值"}, "description": "动作说明"}]}\n'
        "\n"
        "- answer: 包含推理过程和结论，引用具体的本体实体名、数据源名\n"
        "- suggestions: 2-3 个后续建议问题\n"
        "- actions: 可执行的动作列表（如果有的话）\n"
        "\n"
        f"## 本体模型\n\n{ontology_ctx}\n\n"
        f"## 可用工具\n\n{tool_catalog}\n\n"
        f"## 已启用数据源\n\n{ds_summary}\n"
    )
