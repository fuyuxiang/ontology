"""技能生成服务 — 基于本体资产通过 LLM 生成完整技能定义"""
from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Generator

from openai import OpenAI
from sqlalchemy.orm import Session

from app.config import settings
from app.models.entity import OntologyEntity, EntityAttribute
from app.models.relation import EntityRelation
from app.models.rule import BusinessRule, EntityAction
from app.models.function import OntologyFunction
from app.services.skill_sandbox import validate_code

logger = logging.getLogger(__name__)

_sessions: dict[str, dict] = {}

ROLE_PREFIX = (
    "你是一名深耕中国联通业务体系的运营商领域专家兼本体建模专家，"
    "熟悉联通在公众客户、政企客户、网络资源、产品中心、订单中心、计费账务、"
    "客户服务、渠道运营、智慧家庭、物联网、云网融合、数据中台和智慧运营等领域的"
    "业务对象、流程规则和系统边界。"
)

GENERATE_SYSTEM_PROMPT = ROLE_PREFIX + """你的任务是基于用户提供的本体资产和业务需求，生成一个可被AI Agent调用的完整技能定义。

输出必须为严格JSON格式（不包含其他文字），包含以下字段：
{
  "name": "技能名称（英文，PascalCase）",
  "name_zh": "技能中文名",
  "description": "技能描述（1-2句话）",
  "input_schema": { "type": "object", "properties": {...}, "required": [...] },
  "output_schema": { "type": "object", "properties": {...} },
  "prompt_template": "Agent调用该技能时的系统Prompt（指导推理方向）",
  "tools": [
    {
      "name": "工具函数名（snake_case）",
      "description": "工具描述",
      "parameters": { "type": "object", "properties": {...} },
      "code": "完整Python函数代码（def function_name(...):\\n    ...）"
    }
  ],
  "test_cases": [
    { "input": {...}, "expected_output_contains": "预期输出中应包含的关键字段或值" }
  ]
}"""

CHAT_SYSTEM_PROMPT = ROLE_PREFIX + """你正在帮助用户细化一个AI技能的需求。用户已选择了一些本体资产（实体、规则、函数、动作），你需要通过提问帮助明确：
1. 这个技能的使用场景是什么
2. 期望的输入和输出是什么
3. 关键的判断逻辑和规则
4. 有无特殊约束条件

每次只问一个问题，用业务语言提问。当你认为信息足够时，输出一段需求摘要（以"## 需求摘要"开头）。"""


def _get_llm_client(db=None) -> OpenAI:
    from app.services.llm_resolver import get_llm_client
    return get_llm_client(db=db, scene="agent")


def create_session(asset_ids: dict, db: Session) -> dict:
    """Create a generation session with selected ontology assets."""
    assets_context = _load_assets_context(asset_ids, db)
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "id": session_id,
        "asset_ids": asset_ids,
        "assets_context": assets_context,
        "history": [],
        "summary": "",
    }
    return _sessions[session_id]


def chat_stream(session_id: str, message: str) -> Generator[str, None, None]:
    """SSE streaming chat for requirement refinement."""
    session = _sessions.get(session_id)
    if not session:
        yield f"data: {json.dumps({'event': 'error', 'message': 'session not found'})}\n\n"
        return

    messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]

    if not session["history"]:
        first_msg = f"我选择了以下本体资产来构建技能：\n\n{session['assets_context']}\n\n请帮我细化这个技能的需求。"
        messages.append({"role": "user", "content": first_msg})
        session["history"].append({"role": "user", "content": first_msg})
    else:
        for h in session["history"]:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": message})
        session["history"].append({"role": "user", "content": message})

    client = _get_llm_client()
    try:
        resp = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            temperature=0.3,
            stream=True,
        )
    except Exception as e:
        yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
        return

    full_content = ""
    for chunk in resp:
        delta = chunk.choices[0].delta
        if delta.content:
            full_content += delta.content
            yield f"data: {json.dumps({'event': 'token', 'content': delta.content})}\n\n"

    session["history"].append({"role": "assistant", "content": full_content})

    if "## 需求摘要" in full_content:
        session["summary"] = full_content.split("## 需求摘要")[-1].strip()
        yield f"data: {json.dumps({'event': 'summary_ready', 'summary': session['summary']})}\n\n"

    yield "data: [DONE]\n\n"


def generate_skill(session_id: str) -> dict:
    """Generate full skill definition from session context."""
    session = _sessions.get(session_id)
    if not session:
        raise ValueError("Session not found")

    user_content = f"""## 关联本体资产
{session['assets_context']}

## 业务需求摘要
{session.get('summary', '用户未提供额外说明')}

请生成完整的技能定义JSON。"""

    client = _get_llm_client()
    resp = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": GENERATE_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
    )

    raw = resp.choices[0].message.content or "{}"
    raw = re.sub(r"<think>[\s\S]*?</think>", "", raw).strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    try:
        skill_def = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", raw)
        skill_def = json.loads(match.group(0)) if match else {}

    for tool in skill_def.get("tools", []):
        violations = validate_code(tool.get("code", ""))
        if violations:
            tool["_warnings"] = violations

    return skill_def


def regenerate_section(session_id: str, section: str, current_draft: dict) -> dict:
    """Regenerate a specific section of the skill definition."""
    session = _sessions.get(session_id)
    if not session:
        raise ValueError("Session not found")

    prompt = f"""当前技能定义如下：
{json.dumps(current_draft, ensure_ascii=False, indent=2)}

请重新生成 "{section}" 部分，保持其他部分不变。只返回该部分的JSON值。"""

    client = _get_llm_client()
    resp = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": GENERATE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )

    raw = resp.choices[0].message.content or "{}"
    raw = re.sub(r"<think>[\s\S]*?</think>", "", raw).strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"[\[{][\s\S]*[\]}]", raw)
        return json.loads(match.group(0)) if match else {}


def _load_assets_context(asset_ids: dict, db: Session) -> str:
    """Load ontology assets into a text context for LLM."""
    parts = []

    entity_ids = asset_ids.get("entities", [])
    if entity_ids:
        entities = db.query(OntologyEntity).filter(OntologyEntity.id.in_(entity_ids)).all()
        for e in entities:
            attrs = db.query(EntityAttribute).filter(EntityAttribute.entity_id == e.id).all()
            attr_lines = "\n".join(f"  - {a.name}({a.name_zh}): {a.data_type}" for a in attrs)
            parts.append(f"### 实体: {e.name}({e.name_zh})\n{attr_lines}")

    rule_ids = asset_ids.get("rules", [])
    if rule_ids:
        rules = db.query(BusinessRule).filter(BusinessRule.id.in_(rule_ids)).all()
        for r in rules:
            parts.append(f"### 规则: {r.name}\n条件: {r.condition}\n动作: {r.action_expr}")

    func_ids = asset_ids.get("functions", [])
    if func_ids:
        funcs = db.query(OntologyFunction).filter(OntologyFunction.id.in_(func_ids)).all()
        for f in funcs:
            parts.append(f"### 函数: {f.name}({f.name_zh})\n表达式: {f.expression}")

    action_ids = asset_ids.get("actions", [])
    if action_ids:
        actions = db.query(EntityAction).filter(EntityAction.id.in_(action_ids)).all()
        for a in actions:
            parts.append(f"### 动作: {a.name}({a.name_zh})\n类型: {a.action_type}")

    return "\n\n".join(parts) if parts else "（未选择任何资产）"
