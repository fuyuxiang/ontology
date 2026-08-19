"""
AI 智能本体构建服务 — 引导式自动化本体构建
基于 OntoChat/OntoAgent/Interrogatory LLM 方法论：
- 引导用户提供业务素材（文档、数据字典）
- AI 自动分析并追问关键业务问题
- 自动构建完整本体（实体、属性、关系）

平台层不内置任何具体行业/业务的场景与领域知识。若用户在「系统配置 → AI」中
配置了 `ai.scenarios`（推荐场景清单，JSON）或 `ai.domain_knowledge`（领域知识串），
构建流程会自动读入作为提示词补充；未配置时按通用建模流程执行。
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from collections.abc import Generator
from enum import StrEnum

from sqlalchemy.orm import Session

from app.config import settings
from app.services.copilot import build_ontology_context, get_llm_client
from app.services.ontology_constraints import build_constraint_prompt, validate_and_retry

logger = logging.getLogger(__name__)


class BuildPhase(StrEnum):
    SCENARIO = "scenario"
    MATERIALS = "materials"
    CLARIFY = "clarify"
    BUILDING = "building"
    DONE = "done"


class SessionState:
    def __init__(self, session_id: str, existing_context: str = ""):
        self.id = session_id
        self.phase = BuildPhase.SCENARIO
        self.scenario = ""
        self.scenario_detail = ""
        self.materials: list[dict] = []
        self.clarify_qa: list[dict] = []
        self.clarify_count = 0
        self.build_result: dict | None = None
        self.existing_context = existing_context
        self.messages: list[dict] = []

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "phase": self.phase.value,
            "scenario": self.scenario,
            "materials_count": len(self.materials),
            "clarify_count": self.clarify_count,
            "has_result": self.build_result is not None,
        }


# ── 内存会话存储 ──
_sessions: dict[str, SessionState] = {}


# ── 场景与领域知识（用户在「系统配置 → AI」中配置） ──


def load_scenarios(db: Session) -> dict[str, dict]:
    """从 system_config.key='ai.scenarios' 读用户配置的推荐场景清单。

    JSON 结构：{ "场景名": { "description": str,
                              "suggested_materials": [{"label": str, "required": bool}, ...],
                              "typical_questions": [str, ...] }, ... }
    """
    from app.models.system_config import SystemConfig
    row = db.query(SystemConfig).filter(SystemConfig.key == "ai.scenarios").first()
    if not row or not row.value:
        return {}
    try:
        data = json.loads(row.value)
        return data if isinstance(data, dict) else {}
    except (ValueError, TypeError):
        return {}


def load_domain_knowledge(db: Session) -> str:
    """从 system_config.key='ai.domain_knowledge' 读用户配置的领域知识串。"""
    from app.models.system_config import SystemConfig
    row = db.query(SystemConfig).filter(SystemConfig.key == "ai.domain_knowledge").first()
    if row and row.value:
        return row.value
    return ""


# ── Prompt 模板 ──

_SCENARIO_PROMPT = """你是一名资深的业务建模与本体建模专家。用户想要构建一个业务场景的本体模型。
请根据用户的描述，识别具体的业务场景，并给出简短确认（1-2句话）。
如果用户描述模糊，请用一个业务问题帮助明确（不要问技术问题，不要提"实体""属性""关系"等建模术语）。

请以JSON格式回复：
{"confirmed": true/false, "scenario": "识别到的场景名称", "message": "给用户的确认/追问消息"}
如果confirmed=false，说明需要进一步明确，message中包含追问。"""

_MATERIALS_PROMPT = """你是一名资深的业务建模与本体建模专家。用户要构建「{scenario}」场景的本体。
请告诉用户需要提供哪些业务材料来帮助AI自动构建本体。

要求：
1. 用业务语言描述需要什么材料（绝对不要提"实体""属性""关系""本体"等技术术语）
2. 区分"必选"和"推荐"材料
3. 说明每种材料的作用（用业务语言）
4. 告诉用户如果没有文档，也可以用文字简单描述业务情况
5. 语气友好专业，像一个懂业务的顾问

{scenario_hint}

请以JSON格式回复：
{{"message": "给用户的引导消息（markdown格式）", "materials": [{{"label": "材料名称", "required": true/false, "hint": "简短说明这个材料包含什么"}}]}}"""

_CLARIFY_PROMPT = """你是一名资深的业务建模与本体建模专家。用户要构建「{scenario}」场景的本体，已提供以下材料。
请分析材料内容，判断是否有关键业务信息缺失需要追问。

## 已提供材料摘要
{materials_summary}

## 领域知识补充
{domain_knowledge}

## 追问规则
分析材料后，如果以下类型的关键信息缺失，生成追问：
1. 业务对象的分类标准（如工单类型有哪些、客户等级怎么分）
2. 关键业务流程的状态流转（如工单从创建到关闭经过哪些步骤）
3. 核心指标的计算口径或判定标准
4. 业务规则的触发条件和处理逻辑

要求：
- 每次只问一个问题（单问题规则）
- 用业务语言提问，绝对不涉及"实体""属性""关系"等建模术语
- 问题要具体，不要泛泛而问
- 如果材料已经足够完整，不需要追问

请以JSON格式回复：
{{"need_clarify": true/false, "question": "追问内容（如果need_clarify=true）", "reason": "为什么需要这个信息（内部参考，不展示给用户）"}}"""

_BUILD_PROMPT = """你是一名资深的业务建模与本体建模专家。请基于以下业务材料和信息，自动构建完整的本体模型。

## 已有本体（避免重复创建，可建立关联）
{existing_context}

## 业务场景
{scenario}

## 业务材料内容
{materials_content}

## 用户补充的业务信息
{clarify_answers}

{domain_knowledge}

## 构建要求
1. 实体要求：
   - 英文名使用PascalCase
   - 中文名简洁明确
   - 层级判断：T1=核心对象（跨场景复用）、T2=领域对象（领域内共享）、T3=场景对象（仅当前场景使用）
   - 每个实体需要业务描述

2. 属性要求：
   - 名称使用snake_case
   - 类型：string/number/boolean/date/json/ref/computed/enum
   - 标注是否必填
   - 给出业务描述

3. 关系要求：
   - 明确源实体和目标实体
   - 关系类型：has_one/has_many/belongs_to/many_to_many
   - 基数：1:1/1:N/N:1/N:N
   - 关系名使用有业务含义的英文

4. 与已有本体的关系：
   - 如果新实体与已有实体有业务关联，建立关系
   - 不重复创建已有实体（通过name判断）

5. 完整性要求：
   - 确保覆盖材料中提到的所有核心业务对象
   - 每个实体至少3-5个关键属性
   - 实体间的业务关系要完整

严格返回JSON格式，不要包含其他文字：
{{"entities": [{{"name": "PascalCase英文名", "name_cn": "中文名", "tier": 1/2/3, "description": "业务描述", "attributes": [{{"name": "snake_case", "type": "string", "description": "说明", "required": true/false}}]}}], "relations": [{{"from_entity": "源实体name", "to_entity": "目标实体name", "name": "关系英文名", "rel_type": "has_many", "cardinality": "1:N"}}]}}"""


# ── 核心服务类 ──

class AIOntologyBuilder:
    """AI 引导式本体构建服务"""

    def __init__(self, db: Session):
        self.db = db
        self.client = get_llm_client()
        self.model = settings.LLM_MODEL

    def create_session(self) -> SessionState:
        session_id = str(uuid.uuid4())
        existing_ctx = build_ontology_context(self.db)
        state = SessionState(session_id, existing_ctx)
        _sessions[session_id] = state
        return state

    def get_session(self, session_id: str) -> SessionState | None:
        return _sessions.get(session_id)

    def process_message(
        self, session_id: str, message: str = "", files: list[dict] | None = None
    ) -> Generator[dict, None, None]:
        state = _sessions.get(session_id)
        if not state:
            yield {"type": "error", "content": "会话不存在"}
            return

        if message:
            state.messages.append({"role": "user", "content": message})
        if files:
            for f in files:
                state.materials.append(f)

        if state.phase == BuildPhase.SCENARIO:
            yield from self._handle_scenario(state, message)
        elif state.phase == BuildPhase.MATERIALS:
            yield from self._handle_materials(state, message)
        elif state.phase == BuildPhase.CLARIFY:
            yield from self._handle_clarify(state, message)
        elif state.phase == BuildPhase.BUILDING:
            yield from self._handle_build(state)

    def trigger_build(self, session_id: str) -> Generator[dict, None, None]:
        state = _sessions.get(session_id)
        if not state:
            yield {"type": "error", "content": "会话不存在"}
            return
        state.phase = BuildPhase.BUILDING
        yield from self._handle_build(state)

    # ── Phase handlers ──

    def _handle_scenario(self, state: SessionState, message: str) -> Generator[dict, None, None]:
        resp = self._call_llm(
            system=_SCENARIO_PROMPT,
            user=message,
        )
        try:
            data = self._parse_json(resp)
        except ValueError:
            yield {"type": "message", "content": resp, "done": True}
            return

        if data.get("confirmed"):
            state.scenario = data.get("scenario", message)
            state.phase = BuildPhase.MATERIALS
            yield {"type": "message", "content": data.get("message", ""), "done": True}
            yield {"type": "phase_change", "phase": "materials"}
            yield from self._generate_material_guidance(state)
        else:
            yield {"type": "message", "content": data.get("message", ""), "done": True}

    def _generate_material_guidance(self, state: SessionState) -> Generator[dict, None, None]:
        yield {"type": "thinking", "content": "正在为您准备材料收集引导..."}

        scenario_hint = ""
        scenarios = load_scenarios(self.db)
        if state.scenario in scenarios:
            info = scenarios[state.scenario]
            materials = info.get("suggested_materials", [])
            if materials:
                hint_lines = ["已知该场景的推荐材料："]
                for m in materials:
                    req = "必选" if m.get("required") else "推荐"
                    hint_lines.append(f"- [{req}] {m.get('label', '')}")
                scenario_hint = "\n".join(hint_lines)

        prompt = _MATERIALS_PROMPT.format(
            scenario=state.scenario,
            scenario_hint=scenario_hint,
        )
        resp = self._call_llm(system=prompt, user=f"场景：{state.scenario}")
        try:
            data = self._parse_json(resp)
            yield {
                "type": "message",
                "content": data.get("message", ""),
                "done": True,
            }
            if data.get("materials"):
                yield {"type": "suggestion", "suggestions": [
                    {"label": m["label"], "value": m["label"], "required": m.get("required", False)}
                    for m in data["materials"]
                ]}
        except ValueError:
            yield {"type": "message", "content": resp, "done": True}

    def _handle_materials(self, state: SessionState, message: str) -> Generator[dict, None, None]:
        if message:
            state.materials.append({"type": "text", "name": "用户补充描述", "content": message})

        if not state.materials:
            yield {"type": "message", "content": "请上传文件或输入文字描述业务情况。", "done": True}
            return

        state.phase = BuildPhase.CLARIFY
        yield {"type": "phase_change", "phase": "clarify"}
        yield {"type": "message", "content": "材料已收到，正在分析...", "done": True}
        yield from self._generate_clarify_question(state)

    def _handle_clarify(self, state: SessionState, message: str) -> Generator[dict, None, None]:
        if message:
            state.clarify_qa.append({"question": state.messages[-2]["content"] if len(state.messages) >= 2 else "", "answer": message})
            state.clarify_count += 1

        if state.clarify_count >= 3:
            state.phase = BuildPhase.BUILDING
            yield {"type": "phase_change", "phase": "building"}
            yield from self._handle_build(state)
            return

        yield from self._generate_clarify_question(state)

    def _generate_clarify_question(self, state: SessionState) -> Generator[dict, None, None]:
        yield {"type": "thinking", "content": "正在分析材料，判断是否需要追问..."}

        materials_summary = self._summarize_materials(state.materials)
        prompt = _CLARIFY_PROMPT.format(
            scenario=state.scenario,
            materials_summary=materials_summary,
            domain_knowledge=load_domain_knowledge(self.db) or "（无补充领域知识）",
        )

        previous_qa = ""
        if state.clarify_qa:
            qa_lines = [f"Q: {qa['question']}\nA: {qa['answer']}" for qa in state.clarify_qa]
            previous_qa = "\n\n## 已追问过的问题（不要重复）\n" + "\n".join(qa_lines)

        resp = self._call_llm(system=prompt, user=f"请分析材料并决定是否需要追问。{previous_qa}")
        try:
            data = self._parse_json(resp)
        except ValueError:
            state.phase = BuildPhase.BUILDING
            yield {"type": "phase_change", "phase": "building"}
            yield from self._handle_build(state)
            return

        if data.get("need_clarify") and data.get("question"):
            ai_msg = data["question"]
            state.messages.append({"role": "assistant", "content": ai_msg})
            yield {"type": "message", "content": ai_msg, "done": True}
            yield {"type": "suggestion", "suggestions": [
                {"label": "不确定，跳过", "value": "__skip__"},
                {"label": "材料够了，直接构建", "value": "__build__"},
            ]}
        else:
            state.phase = BuildPhase.BUILDING
            yield {"type": "phase_change", "phase": "building"}
            yield from self._handle_build(state)

    def _handle_build(self, state: SessionState) -> Generator[dict, None, None]:
        yield {"type": "build_progress", "step": "综合分析材料", "progress": 10}

        materials_content = self._format_materials_for_build(state.materials)
        clarify_answers = ""
        if state.clarify_qa:
            clarify_answers = "\n".join(
                f"- {qa['question']} → {qa['answer']}" for qa in state.clarify_qa
            )

        yield {"type": "build_progress", "step": "识别业务对象", "progress": 30}

        constraint_block = build_constraint_prompt(
            existing_entities=self._get_existing_entity_names(state.existing_context),
            domain_knowledge=load_domain_knowledge(self.db),
        )
        prompt = _BUILD_PROMPT.format(
            existing_context=state.existing_context or "（暂无已有本体）",
            scenario=state.scenario,
            materials_content=materials_content[:12000],
            clarify_answers=clarify_answers or "（无补充信息）",
            domain_knowledge=constraint_block,
        )

        yield {"type": "build_progress", "step": "构建本体模型", "progress": 50}

        resp = self._call_llm(
            system=prompt,
            user="请基于以上所有信息，构建完整的本体模型。",
            max_tokens=8192,
        )

        yield {"type": "build_progress", "step": "解析构建结果", "progress": 80}

        def retry_caller(retry_prompt: str) -> str:
            return self._call_llm(
                system=retry_prompt,
                user="请输出修正后的完整JSON。",
                max_tokens=8192,
            )

        result, warnings = validate_and_retry(retry_caller, resp, max_retries=5)
        if result is None:
            yield {"type": "error", "content": "AI 构建结果解析失败，已重试5次仍无法修正"}
            return
        if warnings:
            yield {"type": "build_warning", "content": f"输出存在部分校验问题：{warnings}"}

        entities = result.get("entities", [])
        relations = result.get("relations", [])

        conflicts = self._detect_conflicts(entities, state.existing_context)
        for entity in entities:
            entity["selected"] = True
            entity.setdefault("attributes", [])
            for attr in entity["attributes"]:
                attr.setdefault("required", False)

        state.build_result = {"entities": entities, "relations": relations}
        state.phase = BuildPhase.DONE

        yield {"type": "build_progress", "step": "完成", "progress": 100}
        yield {
            "type": "build_result",
            "result": state.build_result,
            "conflicts": conflicts,
            "summary": {
                "entity_count": len(entities),
                "relation_count": len(relations),
                "attr_count": sum(len(e.get("attributes", [])) for e in entities),
            },
        }

    # ── 工具方法 ──

    def _call_llm(self, system: str, user: str, max_tokens: int = 4096) -> str:
        last_err = None
        for attempt in range(3):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=0,
                    max_tokens=max_tokens,
                    timeout=60,
                )
                return resp.choices[0].message.content or ""
            except Exception as e:
                last_err = e
                logger.warning(f"LLM call attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    import time
                    time.sleep(2)
        raise last_err or RuntimeError("LLM call failed after 3 attempts")

    def _parse_json(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
            raise ValueError(f"Cannot parse JSON from: {text[:200]}") from e

    def _get_existing_entity_names(self, existing_context: str | None) -> list[str] | None:
        if not existing_context or existing_context == "（暂无已有本体）":
            return None
        names = re.findall(r"[A-Z][a-zA-Z0-9]+", existing_context)
        return names if names else None

    def _summarize_materials(self, materials: list[dict]) -> str:
        parts = []
        for m in materials:
            name = m.get("name", "未命名")
            content = m.get("content", "")
            preview = content[:2000] if content else "(空)"
            parts.append(f"### {name}\n{preview}")
        return "\n\n".join(parts) if parts else "（用户未提供任何材料）"

    def _format_materials_for_build(self, materials: list[dict]) -> str:
        parts = []
        for m in materials:
            name = m.get("name", "未命名")
            content = m.get("content", "")
            parts.append(f"### {name}\n{content}")
        return "\n\n".join(parts) if parts else "（无材料）"

    def _detect_conflicts(self, new_entities: list[dict], existing_context: str) -> list[dict]:
        conflicts = []
        existing_names = set()
        for line in existing_context.split("\n"):
            if line.startswith("- **") and "**" in line[4:]:
                name = line[4:line.index("**", 4)]
                existing_names.add(name.lower())

        for entity in new_entities:
            name = entity.get("name", "").lower()
            name_cn = entity.get("name_cn", "")
            if name in existing_names:
                conflicts.append({
                    "entity_name": entity.get("name"),
                    "entity_name_cn": name_cn,
                    "type": "duplicate",
                    "message": f"已存在同名实体 {entity.get('name')}",
                })
        return conflicts
