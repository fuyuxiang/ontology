"""
本体构建器后端 API — 支持文档抽取（extract）模式。
- POST /builder/extract  SSE 流式抽取，从 Word/Excel/PDF/CSV/MD/TXT 文档中
  让 LLM 流式产出 entity_proposed / attr_proposed / relation_proposed
  / rule_suggested / action_suggested 五类事件。
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from collections.abc import Generator

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.core.deps import require_user
from app.core.permissions import has_permission
from app.models.user import User
from app.services.copilot import get_llm_client
from app.services.llm_resolver import get_model_name

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/builder", tags=["builder"])


# ── 文档解析 ─────────────────────────────────────────────────────

def _parse_text(filename: str, raw: bytes) -> str:
    from app.services.doc_builder import parse_file_content
    text = parse_file_content(filename, raw)
    if not text.strip():
        raise ValueError("文档未包含可提取文本")
    return text


# ── LLM Prompt ──────────────────────────────────────────────────

_EXTRACT_PROMPT = """你是本体建模专家，需要从用户提供的业务文档中抽取本体草稿。

## 全平台术语规范（严格遵守）
- **对象**（Object）— 业务实体，如客户、订单
- **属性**（Property）— 对象上的字段
- **关系**（Relation）— 对象之间的关联
- **规则**（Rule）— 业务约束，如"订单金额必须大于零"
- **动作**（Action）— 业务操作，如"发送审核通知"

## 输入
你将看到一份业务文档的纯文本（可能含有表格、章节）。请通读全文，识别业务对象、属性、关系，
并捕捉文档里隐含的规则与动作建议。

## 输出格式
严格返回 JSON 数组，每个元素是一条事件，type 取以下五种之一：
1. {"type":"entity_proposed","name":"PascalCase英文名","display_name":"中文名","tier":1|2|3,"primary_key":"id","description":"业务描述","icon":"emoji"}
2. {"type":"attr_proposed","entity_name":"必须与上方某个 entity 的 name 一致","name":"snake_case","display_name":"中文","type":"string|number|date|boolean|enum","required":true|false,"description":"说明"}
3. {"type":"relation_proposed","name":"snake_case","display_name":"中文","from_entity":"对象英文名","to_entity":"对象英文名","cardinality":"1:1|1:N|N:N","description":"说明"}
4. {"type":"rule_suggested","name":"中文规则名","description":"业务说明","condition_hint":"触发条件的人话描述","action_hint":"动作描述","target_entity":"建议挂到的对象英文名","source_file":"来源文件名"}
5. {"type":"action_suggested","name":"中文动作名","description":"业务说明","trigger_hint":"何时触发","effect_hint":"产生什么效果","target_entity":"建议挂到的对象英文名","source_file":"来源文件名"}

## 要求
- tier 划分：T1=核心（客户、产品）/ T2=领域（工单、设备）/ T3=场景（分析结果、预警）
- 关系两端必须能在 entity_proposed 里找到同名对象
- 每个对象至少 3 个属性；必有 1 个 required=true 作为主键候选
- **规则、动作只放进 rule_suggested / action_suggested**，不要落入对象的属性
- 不要包含其他文字，只返回 JSON 数组
"""


def _call_llm_for_extract(content: str, filename: str, db: Session | None = None) -> list[dict]:
    client = get_llm_client(db=db, scene="ontology")
    messages = [
        {"role": "system", "content": _EXTRACT_PROMPT},
        {"role": "user", "content": f"## 文档：{filename}\n\n{content}"},
    ]
    try:
        resp = client.chat.completions.create(
            model=get_model_name(db, "ontology"),
            messages=messages,
            temperature=0,
            max_tokens=6000,
            timeout=90,
        )
    except Exception as e:
        logger.error("LLM 调用失败: %s", e)
        raise
    text = (resp.choices[0].message.content or "").strip()
    # 清理 think 标签和 markdown 代码块
    text = re.sub(r"<think>[\s\S]*?</think>", "", text).strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n", "", text)
        text = re.sub(r"\n```\s*$", "", text)
    # 直接尝试 JSON 数组
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # 容错：找首个 [ 与末个 ]
        start = text.find("[")
        end = text.rfind("]")
        if start < 0 or end < 0:
            raise
        data = json.loads(text[start: end + 1])
    if isinstance(data, dict) and "events" in data:
        data = data["events"]
    if not isinstance(data, list) or not any(isinstance(event, dict) and event.get("type") == "entity_proposed" for event in data):
        raise ValueError("文档没有生成有效对象事件")
    return [e for e in data if isinstance(e, dict) and "type" in e]


# ── SSE 端点 ─────────────────────────────────────────────────────

@router.post("/extract")
async def extract_from_documents(
    session_id: str = Form(""),
    scenario: str = Form(""),
    files: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
):
    """SSE 流式从业务文档抽取本体草稿。"""
    # 先把所有文件读出来（上下文里持久化），避免 yield 时句柄关掉
    docs: list[tuple[str, bytes]] = []
    from app.services.data_plane.storage_policy import storage_policy
    policy = storage_policy(db)
    for f in files:
        if not f.filename:
            continue
        if f.filename.rsplit(".", 1)[-1].lower() not in policy["allowed"]:
            raise HTTPException(422, "存储配置不允许该文档类型")
        raw = await f.read(policy["max_bytes"] + 1)
        if len(raw) > policy["max_bytes"]:
            raise HTTPException(413, "文档超过配置的上传大小限制")
        if raw:
            docs.append((f.filename, raw))

    def _emit(ev: dict) -> str:
        return f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"

    def event_stream() -> Generator[str, None, None]:
        try:
            yield _emit({"type": "extract_started", "session_id": session_id, "file_count": len(docs)})

            if not docs:
                yield _emit({"type": "error", "content": "未收到任何文件"})
                yield "data: [DONE]\n\n"
                return

            # 维护已抛出的对象 name，用于关系/属性合法性校验
            entity_names: set[str] = set()
            failed_files: list[str] = []

            for filename, raw in docs:
                yield _emit({"type": "file_parsing", "file_name": filename})
                try:
                    text = _parse_text(filename, raw)
                except Exception as exc:
                    failed_files.append(filename)
                    yield _emit({"type": "file_failed", "file_name": filename, "error": str(exc)})
                    continue
                yield _emit({"type": "file_parsed", "file_name": filename, "text_length": len(text)})

                try:
                    events = _call_llm_for_extract(text, filename, db)
                except Exception as e:
                    failed_files.append(filename)
                    yield _emit({"type": "file_failed", "file_name": filename, "error": f"LLM 抽取失败: {e}"})
                    continue

                # 先发对象，再发属性，最后发关系，避免前端拿到孤立属性
                ordered = sorted(events, key=lambda ev: {
                    "entity_proposed": 0,
                    "attr_proposed": 1,
                    "relation_proposed": 2,
                    "rule_suggested": 3,
                    "action_suggested": 4,
                }.get(ev.get("type"), 9))

                for ev in ordered:
                    t = ev.get("type")
                    if t == "entity_proposed":
                        if not ev.get("name"):
                            raise ValueError("抽取返回了未命名对象")
                        entity_names.add(ev.get("name", ""))
                    elif t == "attr_proposed":
                        if ev.get("entity_name") not in entity_names:
                            raise ValueError("抽取属性引用了不存在的对象")
                    elif t == "relation_proposed":
                        if ev.get("from_entity") not in entity_names or ev.get("to_entity") not in entity_names:
                            raise ValueError("抽取关系引用了不存在的对象")
                    elif t in ("rule_suggested", "action_suggested"):
                        ev.setdefault("source_file", filename)
                    yield _emit(ev)

            if failed_files:
                yield _emit({"type":"error", "content":"以下文档未完成抽取，请修复后重新提交：" + "、".join(failed_files)})
                yield "data: [DONE]\n\n"
                return
            yield _emit({"type": "extract_finished"})
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.exception("extract failed")
            yield _emit({"type": "error", "content": str(e)})
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── 对话生成（chat）── 走 AgentService 的 tool calling ────────────

_CHAT_SYSTEM_PROMPT = """你是本体构建器的「场景 Copilot」。你的任务是引导用户从业务场景出发，
联动数据资产与业务文档，生成本体对象、属性、关系、规则建议、动作建议。

## 全平台术语
对象（Object）/ 属性（Property）/ 派生属性（Derived Property）/ 关系（Relation）/ 规则（Rule）/ 动作（Action）。

## 你必须严格按这四阶段推进
1. **business-clarify**：用户描述完业务后，用 1-2 句话总结确认。如果模糊，用一句业务问题澄清（不要提"实体""属性"这些建模术语）。
2. **asset-select**：业务清晰后，调用 `list_business_datasources(domain, keywords)` 得到候选数据源，
   你的回答里只需说一句"为你匹配到了候选数据源，请勾选要纳入本体的资产"。
   不要把数据源名称重复贴出来——前端会渲染 display_card=asset_picker。
3. **doc-select**：用户回答"已选好数据源 [...id列表]"后，调用 `list_business_documents(domain, datasource_ids)` 得到候选文档。
   同样让前端渲染 display_card 让用户勾选。
4. **synthesize**：用户回答"已选好文档 [...id列表]"后，调用
   `analyze_assets_for_ontology(datasource_ids, document_ids, business_context)` 抽取本体草稿。
   返回结果会同时携带规则与动作建议，用户进入审核页时统一处理。

## 几条铁律
- 一次只问一个问题；澄清不超过 2 轮
- 列资产时一定调 list_business_datasources（不要凭印象编名字）
- 列文档时一定调 list_business_documents
- 抽取本体一定调 analyze_assets_for_ontology
- 工具结果里的 display_card 字段保持原样回传，前端会自动渲染
"""


@router.post("/chat")
async def builder_chat(
    session_id: str = Form(""),
    message: str = Form(""),
    db: Session = Depends(get_db),
):
    """对话生成模式 — 用 AgentService 跑 LLM + tool calling，流式 SSE。"""
    from app.services.agent.orchestrator import AgentService

    def _emit(ev: dict) -> str:
        return f"data: {json.dumps(ev, ensure_ascii=False, default=str)}\n\n"

    def event_stream() -> Generator[str, None, None]:
        try:
            agent = AgentService(db, system_prompt_prefix=_CHAT_SYSTEM_PROMPT)
            for ev in agent.ask(message or "（用户没有发送内容，请引导他描述业务场景）"):
                yield _emit(ev)
        except Exception as e:
            logger.exception("builder chat failed")
            yield _emit({"type": "error", "content": str(e)})
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── AI 辅助：属性补全 ─────────────────────────────────────────────

class SuggestAttrProperty(BaseModel):
    name: str
    displayName: str | None = None
    type: str = "string"
    required: bool = False


class SuggestAttrRequest(BaseModel):
    object_name: str
    display_name: str | None = None
    tier: int = 2
    description: str | None = None
    existing_properties: list[SuggestAttrProperty] = []


def _parse_suggestion_list(text: str) -> list[dict]:
    """An explicit empty array is valid; malformed/non-array output is a failure."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("["), text.rfind("]")
        try:
            if start < 0 or end < start:
                raise ValueError("missing array")
            data = json.loads(text[start:end + 1])
        except (ValueError, TypeError):
            raise HTTPException(502, "模型没有返回有效建议数组，请重试") from None
    if not isinstance(data, list):
        raise HTTPException(502, "模型没有返回建议数组，请重试")
    return data


_SUGGEST_ATTR_PROMPT = """你是本体建模专家。给定一个业务对象的基本信息和已有属性，请建议缺失的重要属性。

## 输入
- 对象名（英文 + 中文）
- 对象层级（T1/T2/T3）
- 已有属性列表

## 输出格式
严格返回 JSON 数组，每个元素：
{"name":"snake_case英文名","displayName":"中文名","type":"string|number|date|boolean|enum","required":true|false,"description":"一句话说明"}

## 要求
- 只建议不在已有属性列表中的属性
- 建议 3~8 个最核心的属性
- 属性名用 snake_case，中文名用业务术语
- required=true 只用于业务上必须有值的字段
- 不要包含其他文字，只返回 JSON 数组
"""


@router.post("/suggest-attributes")
def suggest_attributes(body: SuggestAttrRequest, db: Session = Depends(get_db)):
    """AI 补全属性：根据对象信息和已有属性，让 LLM 建议缺失属性。"""
    existing_names = {p.name for p in body.existing_properties}
    existing_desc = "\n".join(
        f"  - {p.name} ({p.displayName or p.name}, {p.type}, {'必填' if p.required else '可选'})"
        for p in body.existing_properties
    ) or "  （暂无）"

    user_msg = (
        f"对象：{body.object_name}（{body.display_name or body.object_name}）\n"
        f"层级：T{body.tier}\n"
        f"描述：{body.description or '无'}\n\n"
        f"已有属性：\n{existing_desc}"
    )

    client = get_llm_client(db=db, scene="ontology")
    try:
        resp = client.chat.completions.create(
            model=get_model_name(db, "ontology"),
            messages=[
                {"role": "system", "content": _SUGGEST_ATTR_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.1,
            max_tokens=2000,
            timeout=30,
        )
    except Exception as e:
        logger.error("suggest-attributes LLM 调用失败: %s", e)
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=502, content={"detail": f"LLM 调用失败: {e}"})

    text = (resp.choices[0].message.content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n", "", text)
        text = re.sub(r"\n```\s*$", "", text)

    data = _parse_suggestion_list(text)
    if any(not isinstance(item, dict) or not isinstance(item.get("name"), str) or not item["name"].strip()
           or not isinstance(item.get("type", "string"), str)
           or item.get("type", "string") not in {"string", "number", "date", "boolean", "enum"}
           or ("required" in item and not isinstance(item["required"], bool)) for item in data):
        raise HTTPException(502, "模型返回了无效属性建议，请重试")

    # 过滤已有属性
    suggested = [
        item for item in data
        if isinstance(item, dict) and item.get("name") and item["name"] not in existing_names
    ]
    return {"suggested_properties": suggested}


# ── AI 辅助：关系推断 ─────────────────────────────────────────────

class SuggestRelObject(BaseModel):
    name: str
    displayName: str | None = None
    tier: int = 2
    properties: list[str] = []


class SuggestRelExisting(BaseModel):
    source: str
    target: str
    name: str | None = None


class SuggestRelRequest(BaseModel):
    objects: list[SuggestRelObject]
    existing_relations: list[SuggestRelExisting] = []


_SUGGEST_REL_PROMPT = """你是本体建模专家。给定一组业务对象及其属性，请推断对象之间可能存在的关系。

## 输入
- 对象列表（含名称、层级、属性名）

## 输出格式
严格返回 JSON 数组，每个元素：
{"name":"snake_case英文名","displayName":"中文名","source":"源对象英文名","target":"目标对象英文名","cardinality":"1:1|1:N|N:N","relationType":"ObjectProperty|SymmetricProperty|TransitiveProperty|FunctionalProperty","semanticType":"composition|event|inheritance|dependency|association","description":"一句话说明"}

## 判断依据
1. 两个对象有同名外键属性（如都有 customer_id）→ 关联关系
2. 层级包含关系（T1 包含 T2）→ 组合关系
3. 业务语义（预警、工单、事件）→ 事件关系
4. 继承关系（子类型）→ 继承关系

## 要求
- source 和 target 必须是输入对象中的 name
- 不要重复已有的关系
- 最多建议 5 条最核心的关系
- 不要包含其他文字，只返回 JSON 数组
"""


@router.post("/suggest-relations")
def suggest_relations(body: SuggestRelRequest, db: Session = Depends(get_db)):
    """AI 推断关系：根据对象信息让 LLM 推断可能的关系。"""
    if len(body.objects) < 2:
        return {"suggested_relations": []}

    existing_pairs = {(r.source, r.target) for r in body.existing_relations}

    obj_desc = "\n".join(
        f"  - {o.name}（{o.displayName or o.name}，T{o.tier}）属性：{', '.join(o.properties) or '无'}"
        for o in body.objects
    )
    user_msg = f"对象列表：\n{obj_desc}"

    client = get_llm_client(db=db, scene="ontology")
    try:
        resp = client.chat.completions.create(
            model=get_model_name(db, "ontology"),
            messages=[
                {"role": "system", "content": _SUGGEST_REL_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.1,
            max_tokens=2000,
            timeout=30,
        )
    except Exception as e:
        logger.error("suggest-relations LLM 调用失败: %s", e)
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=502, content={"detail": f"LLM 调用失败: {e}"})

    text = (resp.choices[0].message.content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n", "", text)
        text = re.sub(r"\n```\s*$", "", text)

    data = _parse_suggestion_list(text)
    obj_names = {o.name for o in body.objects}
    if any(not isinstance(item, dict) or not isinstance(item.get("name"), str) or not item["name"].strip()
           or not isinstance(item.get("source"), str) or not isinstance(item.get("target"), str)
           or item.get("source") not in obj_names or item.get("target") not in obj_names
           or not isinstance(item.get("cardinality", "1:N"), str)
           or item.get("cardinality", "1:N") not in {"1:1", "1:N", "N:N"} for item in data):
        raise HTTPException(502, "模型返回了无效关系建议，请重试")

    # 过滤已有关系 + 校验 source/target 存在
    obj_names = {o.name for o in body.objects}
    suggested = []
    for item in data:
        if not isinstance(item, dict):
            continue
        src, tgt = item.get("source"), item.get("target")
        if not src or not tgt:
            continue
        if src not in obj_names or tgt not in obj_names:
            continue
        if (src, tgt) in existing_pairs or (tgt, src) in existing_pairs:
            continue
        suggested.append(item)

    return {"suggested_relations": suggested}


# ── AI 辅助：数据源自动映射 ───────────────────────────────────────

class AutoMapProperty(BaseModel):
    name: str
    type: str = "string"
    description: str | None = None


class AutoMapObject(BaseModel):
    id: str
    name: str = ""
    displayName: str = ""
    properties: list[AutoMapProperty] = []


class AutoMapRequest(BaseModel):
    objects: list[AutoMapObject]
    asset_ids: list[str] | None = None
    scope: str | None = None


class _AttrAdapter:
    """轻量 adapter，让 Pydantic 属性能传给 _heuristic_score()。"""
    __slots__ = ("name", "type", "description")
    def __init__(self, name: str, type_: str, desc: str | None):
        self.name = name
        self.type = type_
        self.description = desc or ""


@router.post("/auto-map")
async def auto_map(body: AutoMapRequest, db: Session = Depends(get_db)):
    """智能映射：根据 scope 或 asset_ids 匹配最优表和列。

    三层匹配逻辑：
    1. 确定候选资产范围（scope → connection_id 筛选，或 asset_ids 指定，或全部结构化资产）
    2. 对象名 → 表名 匹配，为每个对象找出最相关的表
    3. 属性 → 列 匹配，在匹配到的表内做列级映射
    """
    from app.models.asset import Asset
    from app.services.data_plane.mapping_suggest_service import _heuristic_score

    if not body.objects:
        return {"mappings": {}}

    # 第一层：确定候选资产范围
    query = db.query(Asset).filter(
        Asset.kind.in_(["table", "sql_view"]),
        Asset.status == "active",
    )
    if body.asset_ids:
        query = query.filter(Asset.id.in_(body.asset_ids))
    elif body.scope:
        query = query.filter(Asset.connection_id == body.scope)

    assets = query.all()
    if not assets:
        return {"mappings": {}}

    # 构建 asset 索引: [(asset_id, table_name, schema)]
    asset_index: list[tuple[str, str, list[dict]]] = []
    for a in assets:
        schema = a.schema_snapshot or []
        if schema:
            asset_index.append((a.id, a.alias or a.name, schema))

    if not asset_index:
        return {"mappings": {}}

    result: dict[str, dict] = {}

    for obj in body.objects:
        property_names = [prop.name for prop in obj.properties]
        if any(not name.strip() for name in property_names) or len(property_names) != len(set(property_names)):
            raise HTTPException(422, f"对象 {obj.name} 的属性名称为空或重复")
        obj_label = obj.displayName or obj.name or obj.id

        # 第二层：对象名 → 表名 匹配，找出 top-N 相关表
        table_scores: list[tuple[int, float]] = []
        for idx, (_asset_id, table_name, _schema) in enumerate(asset_index):
            name_sim = _table_name_similarity(obj_label, obj.name, table_name)
            table_scores.append((idx, name_sim))

        table_scores.sort(key=lambda x: x[1], reverse=True)
        # 取 top 5 候选表（至少 0.2 分以上）
        top_tables = [(idx, score) for idx, score in table_scores[:5] if score >= 0.2]
        if not top_tables:
            # 退化：取前 10 张表全部尝试
            top_tables = table_scores[:10]

        # 第三层：属性 → 列 匹配
        best_total_score = 0.0
        best_result = None
        matched_tables_for_obj: list[dict] = []

        for idx, table_sim in top_tables:
            asset_id, table_name, schema = asset_index[idx]
            obj_score = 0.0
            obj_mappings: dict[str, dict] = {}

            for prop in obj.properties:
                adapter = _AttrAdapter(prop.name, prop.type, prop.description)
                best_s = 0.0
                best_col = None
                for col in schema:
                    s, _r = _heuristic_score(adapter, col)
                    if s > best_s:
                        best_s = s
                        best_col = col.get("name")
                if best_col and best_s > 0:
                    obj_mappings[prop.name] = {
                        "column": best_col,
                        "score": round(best_s, 3),
                        "asset_id": asset_id,
                    }
                    obj_score += best_s

            combined_score = obj_score + table_sim * len(obj.properties) * 0.3
            matched_tables_for_obj.append({
                "asset_id": asset_id,
                "table_name": table_name,
                "columns": [col.get("name", "") for col in schema],
                "score": round(combined_score, 3),
            })

            if combined_score > best_total_score:
                best_total_score = combined_score
                best_result = {"asset_id": asset_id, "mappings": obj_mappings}

        # 按分数排序，返回 top 相关表
        matched_tables_for_obj.sort(key=lambda x: x["score"], reverse=True)
        top_matched = matched_tables_for_obj[:5]

        if best_result:
            result[obj.id] = {
                "asset_id": best_result["asset_id"],
                "matched_tables": top_matched,
                "property_mappings": best_result["mappings"],
            }
        else:
            result[obj.id] = {
                "asset_id": None,
                "matched_tables": top_matched,
                "property_mappings": {},
            }

    return {"mappings": result}


def _table_name_similarity(obj_display: str, obj_name: str, table_name: str) -> float:
    """计算对象名与表名的相似度。综合中文名匹配和英文名匹配。"""
    import re
    from difflib import SequenceMatcher

    table_lower = table_name.lower().replace("_", "").replace("-", "")
    scores: list[float] = []

    if obj_name:
        obj_lower = obj_name.lower().replace("_", "").replace("-", "")
        if obj_lower == table_lower:
            return 1.0
        if obj_lower in table_lower or table_lower in obj_lower:
            scores.append(0.8)
        scores.append(SequenceMatcher(None, obj_lower, table_lower).ratio())

    if obj_display:
        display_lower = obj_display.lower()
        if display_lower in table_lower or table_lower in display_lower:
            scores.append(0.7)
        # 拆分 token 比较
        obj_tokens = set(re.findall(r'[一-鿿]+|[a-z0-9]+', display_lower))
        table_tokens = set(re.findall(r'[一-鿿]+|[a-z0-9]+', table_lower))
        if obj_tokens and table_tokens:
            overlap = len(obj_tokens & table_tokens)
            if overlap:
                scores.append(overlap / max(len(obj_tokens), len(table_tokens)) * 0.75)

    return max(scores) if scores else 0.0


# ── AI 辅助：字段推荐 ────────────────────────────────────────────────

class SuggestColumnsRequest(BaseModel):
    asset_id: str
    properties: list[dict]  # [{name, type?, description?}]


@router.post("/suggest-columns")
def suggest_columns(body: SuggestColumnsRequest, db: Session = Depends(get_db)):
    """给定属性列表 + 资产 ID，返回每属性的字段推荐排序。"""
    from app.services.data_plane.asset_service import AssetService
    from app.services.data_plane.mapping_suggest_service import _heuristic_score

    asset = AssetService(db).get(body.asset_id)
    if not asset:
        raise HTTPException(404, "资产不存在")

    columns = asset.schema_snapshot or []
    results = []

    for prop in body.properties:
        from types import SimpleNamespace
        attr = SimpleNamespace(
            name=prop.get("name", ""),
            type=prop.get("type", ""),
            description=prop.get("description", ""),
        )

        candidates = []
        for col in columns:
            score, reason = _heuristic_score(attr, col)
            if score > 0.1:
                tier = "high" if score >= 0.7 else "medium" if score >= 0.4 else "low"
                candidates.append({
                    "column": col.get("name", ""),
                    "column_type": col.get("type"),
                    "comment": col.get("comment"),
                    "score": round(score, 3),
                    "tier": tier,
                    "reason": reason,
                })

        candidates.sort(key=lambda c: c["score"], reverse=True)
        results.append({
            "property_name": prop.get("name", ""),
            "candidates": candidates[:5],
        })

    return {"suggestions": results}


# ── 水合演练（hydrate）── 验证本体草稿与真实数据的映射 ──────────────

@router.post("/hydrate")
async def builder_hydrate(body: dict, db: Session = Depends(get_db)):
    """SSE 流式水合演练：验证本体草稿与真实数据的映射。"""
    from app.services.builder.hydration_service import HydrationRequest, HydrationService

    try:
        req = HydrationRequest(**body)
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=422, content={"detail": str(e)})

    def _emit(ev: dict) -> str:
        return f"data: {json.dumps(ev, ensure_ascii=False, default=str)}\n\n"

    def event_stream() -> Generator[str, None, None]:
        try:
            yield _emit({"type": "hydrate_started", "session_id": req.session_id})
            svc = HydrationService(db)
            for ev in svc.run(req):
                yield _emit(ev)
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.exception("hydrate failed")
            yield _emit({"type": "error", "content": str(e)})
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── M3: 发布草稿 → OntologyEntity + EntityAttribute + ObjectBinding ─────

class _DraftProperty(BaseModel):
    name: str
    displayName: str | None = None
    type: str = "string"
    required: bool = False
    description: str | None = None
    source_asset_id: str | None = None
    source_column: str | None = None
    transform: str | None = None


class _DraftRelation(BaseModel):
    name: str
    displayName: str | None = None
    source: str
    target: str
    cardinality: str = "1:N"
    relationType: str = "ObjectProperty"
    sourceField: str | None = None
    targetField: str | None = None
    description: str | None = None


class _DraftEnrichment(BaseModel):
    asset_id: str
    primary_source_column: str | None = None
    enrichment_source_column: str | None = None


class _DraftObject(BaseModel):
    name: str
    displayName: str | None = None
    tier: int = 2
    namespace: str | None = None
    description: str | None = None
    primaryKey: str | None = None
    properties: list[_DraftProperty] = []
    backing_asset_ids: list[str] = []
    enrichment_bindings: list[_DraftEnrichment] = []


class FinalizeRequest(BaseModel):
    objects: list[_DraftObject]
    relations: list[_DraftRelation] = []
    # 本批发布对象统一归属的场景 code 列表（与已存在场景做并集写入）
    scenario_codes: list[str] = []
    # 归属本体 ID（从本体详情新建对象时传入）
    ontology_id: str | None = None
    actions: list[dict] = []
    document_session_id: str | None = None


@router.post("/finalize")
def builder_finalize(body: FinalizeRequest, db: Session = Depends(get_db), user: User = Depends(require_user)):
    from app.schemas.action import ACTION_TYPES
    if any((action.get("action_type") or action.get("type")) in ACTION_TYPES for action in body.actions) and not has_permission(user, "rule:write", db):
        raise HTTPException(403, "导入可执行动作需要 rule:write 权限")
    try:
        from app.services.doc_mapping_persist_service import validate_kept_mappings
        preserved = validate_kept_mappings(body, db, user.id)
        result = finalize_draft(body, db, preserve_entity_ids=preserved)
        if preserved:
            from app.models.builder_document_session import BuilderDocumentSession
            from app.services.doc_mapping_persist_service import binding_fingerprint
            record = db.get(BuilderDocumentSession, body.document_session_id)
            db.flush()
            receipt = (record.payload or {})["mapping_receipt"]
            record.payload = {**record.payload, "mapping_receipt": {**receipt, "kept_entities": {
                entity_id: binding_fingerprint(db, entity_id) for entity_id in preserved}}}
        db.commit()
        return result
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "构建内容发生并发冲突；请重新读取当前本体后重试保存") from exc
    except Exception:
        db.rollback()
        raise


def finalize_draft(body: FinalizeRequest, db: Session, *, sync_bindings: bool = True,
                   preserve_entity_ids: set[str] | None = None, preserve_definitions: bool = False):
    """把 builder 草稿一次性落库：每个对象创建 OntologyEntity + EntityAttribute；
    若 backing_asset_ids 非空，自动创建 primary ObjectBinding（含 field_mappings）。

    幂等：同一本体内以名称更新定义和映射，不重复创建实体或绑定。
    """
    from app.models.entity import EntityAttribute, OntologyEntity
    from app.repositories.asset_repo import AssetRepository
    from app.services.data_plane.object_binding_service import ObjectBindingService

    asset_repo = AssetRepository(db)
    binding_svc = ObjectBindingService(db)
    preserve_entity_ids = preserve_entity_ids or set()

    # 本批发布统一归属的场景（去重、去空）
    batch_scenarios = [c for c in dict.fromkeys(body.scenario_codes) if c]

    # 如果指定了 ontology_id，自动把对应 scenario 的 code 加入 batch_scenarios
    if body.ontology_id:
        from app.models.scenario import ScenarioDict
        scenario = db.get(ScenarioDict, body.ontology_id)
        if not scenario:
            raise HTTPException(404, "目标本体不存在")
        if scenario.code not in batch_scenarios:
            batch_scenarios.append(scenario.code)

    if not body.objects:
        raise HTTPException(422, "没有可保存的对象")
    names = [obj.name for obj in body.objects]
    if any(not name.strip() for name in names) or len(set(names)) != len(names):
        raise HTTPException(422, "对象名称不能为空或重复")
    for relation in body.relations:
        if relation.source not in names or relation.target not in names:
            raise HTTPException(422, f"关系 {relation.name} 引用了本批次之外的对象")
    # 在任何数据库写入之前核对所有资产及字段，禁止部分成功被报告为完整成功。
    for obj in body.objects:
        if len(obj.backing_asset_ids) != len(set(obj.backing_asset_ids)):
            raise HTTPException(422, f"对象 {obj.name} 的来源资产不能重复")
        property_names = [prop.name for prop in obj.properties]
        if any(not name.strip() for name in property_names) or len(property_names) != len(set(property_names)):
            raise HTTPException(422, f"对象 {obj.name} 的属性名称为空或重复")
        if obj.backing_asset_ids:
            primary = next((prop for prop in obj.properties if prop.name == obj.primaryKey), None)
            if not primary or primary.source_asset_id != obj.backing_asset_ids[0] or not primary.source_column:
                raise HTTPException(422, f"对象 {obj.name} 的主键必须映射到首个数据资产字段")
        join_ids = [rule.asset_id for rule in obj.enrichment_bindings]
        if len(join_ids) != len(set(join_ids)) or any(asset_id not in obj.backing_asset_ids[1:] for asset_id in join_ids):
            raise HTTPException(422, f"对象 {obj.name} 的 enrichment 规则重复或不是已绑定补充资产")
        for asset_id in obj.backing_asset_ids:
            asset = asset_repo.get_by_id(asset_id)
            if not asset or asset.status != "active":
                raise HTTPException(422, f"资产不可用: {asset_id}")
            columns = {column.get("name") for column in (asset.schema_snapshot or [])}
            for prop in obj.properties:
                if prop.source_asset_id == asset_id and prop.source_column and prop.source_column not in columns:
                    raise HTTPException(422, f"资产 {asset_id} 中不存在字段 {prop.source_column}")
        for prop in obj.properties:
            if prop.transform:
                from app.services.data_plane.mapping_transform import validate_transform
                validate_transform(prop.transform)
                if prop.name == obj.primaryKey:
                    raise ValueError("主键属性不能配置 transform")
            if prop.source_column and prop.source_asset_id not in obj.backing_asset_ids:
                raise HTTPException(422, f"属性 {obj.name}.{prop.name} 的来源资产未绑定")

    created_entities = 0
    created_bindings = 0
    skipped = 0
    # 对象名 → 实际落库的 entity.id（命中已有实体时为其真实 id，非重新拼接的 eid），
    # 供后续关系持久化引用，避免外键指向不存在的 id
    entity_id_map: dict[str, str] = {}

    for obj in body.objects:
        # name 唯一性属于本体；裸 name/namespace 不是全局实体标识。
        existing = db.query(OntologyEntity).filter(
            OntologyEntity.name == obj.name,
            OntologyEntity.ontology_id == body.ontology_id,
        ).first()
        if existing and existing.id in preserve_entity_ids and preserve_definitions:
            entity_id_map[obj.name] = existing.id
            skipped += 1
            continue
        eid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"ontology:{body.ontology_id or 'legacy'}:{obj.namespace or ''}:{obj.name}"))
        if existing:
            skipped += 1
            entity = existing
            entity.name_cn = obj.displayName or obj.name
            entity.description = obj.description
            entity.tier = int(obj.tier or 2)
            entity.config_json = {**(entity.config_json or {}), "primary_key": obj.primaryKey,
                                  "backing_asset_ids": obj.backing_asset_ids}
        else:
            entity = OntologyEntity(
                id=eid, name=obj.name, name_cn=obj.displayName or obj.name,
                tier=int(obj.tier or 2), status="active",
                description=obj.description,
                ontology_id=body.ontology_id,
                config_json={"primary_key": obj.primaryKey,
                             "backing_asset_ids": obj.backing_asset_ids},
            )
            db.add(entity)
            db.flush()
            created_entities += 1

        # 记录对象名 → 实际 entity.id（关系持久化引用真实 id）
        entity_id_map[obj.name] = entity.id

        # 场景归属：与对象已有 scenario_codes 做并集，保持顺序
        if batch_scenarios:
            merged = list(dict.fromkeys([*(entity.scenario_codes or []), *batch_scenarios]))
            entity.scenario_codes = merged
            db.flush()

        # 属性（按 name 去重）
        attr_by_name: dict[str, EntityAttribute] = {a.name: a for a in entity.attributes}
        # The supplied definition for each object is complete; retained objects
        # outside this batch are untouched. Remove obsolete bindings before a
        # new primary is created, using the same cleanup path as the data UI.
        preserving = entity.id in preserve_entity_ids
        if sync_bindings and not preserving:
            binding_svc.prepare_data_replacement(entity.id, {
                (asset_id, "primary" if index == 0 else "enrichment")
                for index, asset_id in enumerate(obj.backing_asset_ids)})
        removed_attributes = [attribute for name, attribute in attr_by_name.items() if name not in {prop.name for prop in obj.properties}]
        if removed_attributes:
            removed_ids = {attribute.id for attribute in removed_attributes}
            for binding in binding_svc.list(object_type_id=entity.id, status=None):
                mappings = [mapping for mapping in binding.field_mappings or [] if mapping.get("attribute_id") not in removed_ids]
                if len(mappings) != len(binding.field_mappings or []):
                    # The old set is suspended until its replacement is validated.
                    # Clearing a removed attribute here must not validate stale joins.
                    binding.field_mappings = mappings
            for attribute in removed_attributes:
                entity.attributes.remove(attribute)
                attr_by_name.pop(attribute.name)
            db.flush()
        for p in obj.properties:
            if p.name in attr_by_name:
                attr = attr_by_name[p.name]
                attr.type = p.type
                attr.required = p.required
                attr.description = p.description or p.displayName or p.name
                continue
            attr = EntityAttribute(
                entity_id=entity.id, name=p.name, type=p.type,
                description=p.description or p.displayName or p.name,
                required=p.required,
            )
            db.add(attr)
            db.flush()
            attr_by_name[p.name] = attr
        db.flush()

        # ObjectBinding（每个 backing_asset_id 一个 primary，role 区分）
        for idx, asset_id in enumerate([] if preserving else obj.backing_asset_ids):
            asset = asset_repo.get_by_id(asset_id)
            if not asset:
                raise HTTPException(422, f"资产不存在: {asset_id}")
            role = "primary" if idx == 0 else "enrichment"
            existing_binding = binding_svc.repo.find_existing(entity.id, asset_id, role)
            join_rule = next((rule for rule in obj.enrichment_bindings if rule.asset_id == asset_id), None)
            join_config = ({"primary_source_column": join_rule.primary_source_column if join_rule else None,
                            "enrichment_source_column": join_rule.enrichment_source_column if join_rule else None} if role == "enrichment" else {})
            field_mappings = []
            for p in obj.properties:
                if p.source_asset_id == asset_id and p.source_column:
                    attr = attr_by_name.get(p.name)
                    if attr:
                        field_mappings.append({
                            "attribute_id": attr.id,
                            "source_column": p.source_column,
                            "transform": p.transform,
                        })
            primary_property = next((p for p in obj.properties if p.name == obj.primaryKey), None)
            id_column = primary_property.source_column if primary_property and primary_property.source_asset_id == asset_id else None
            try:
                if existing_binding:
                    # Saving an explicitly checked mapping resolves schema-change
                    # review; otherwise hydration's schema refresh can leave the
                    # valid binding unmirrored and the next publish unusable.
                    binding_svc.update(existing_binding.id, field_mappings=field_mappings,
                                       status="active", review_reason=None, **join_config,
                                       **({"id_column": id_column} if id_column else {}))
                else:
                    binding_svc.create(
                        object_type_id=entity.id, asset_id=asset_id, role=role,
                        field_mappings=field_mappings, id_column=id_column, **join_config,
                    )
                    created_bindings += 1
            except (ValueError, LookupError) as exc:
                db.rollback()
                raise HTTPException(422, str(exc)) from exc
            except Exception:
                db.rollback()
                raise
        if preserving:
            for binding in binding_svc.list(object_type_id=entity.id, status=None):
                binding_svc._remove_auto_rules(binding)
                binding_svc._remount_asset_rules(binding.asset_id)

    # ── 关系持久化 ──
    from app.models.relation import EntityRelation

    created_relations = 0

    for rel in body.relations:
        from_eid = entity_id_map.get(rel.source)
        to_eid = entity_id_map.get(rel.target)
        if not from_eid or not to_eid:
            continue
        existing_rel = db.query(EntityRelation).filter(
            EntityRelation.from_entity_id == from_eid,
            EntityRelation.to_entity_id == to_eid,
            EntityRelation.name == rel.name,
        ).first()
        if existing_rel:
            existing_rel.rel_type = rel.relationType or "ObjectProperty"
            existing_rel.cardinality = rel.cardinality or "1:N"
            existing_rel.description = rel.description or rel.displayName or rel.name
            existing_rel.source_field = rel.sourceField
            existing_rel.target_field = rel.targetField
            continue
        new_rel = EntityRelation(
            from_entity_id=from_eid,
            to_entity_id=to_eid,
            name=rel.name,
            rel_type=rel.relationType or "ObjectProperty",
            cardinality=rel.cardinality or "1:N",
            source_field=rel.sourceField,
            target_field=rel.targetField,
            description=rel.description or rel.displayName or rel.name,
        )
        db.add(new_rel)
        created_relations += 1

    db.flush()
    from app.services.file_import import persist_import_actions
    created_actions, action_warnings = persist_import_actions(body.actions, entity_id_map, body.ontology_id, db)
    return {
        "created_entities": created_entities,
        "created_bindings": created_bindings,
        "created_relations": created_relations,
        "created_actions": created_actions,
        "warnings": action_warnings,
        "skipped": skipped,
        "total": len(body.objects),
        "entity_ids": entity_id_map,
        "ontology_id": body.ontology_id,
        "state": "saved",
    }
