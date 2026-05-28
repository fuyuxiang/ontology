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
from io import BytesIO
from typing import Any, Generator

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.services.copilot import get_llm_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/builder", tags=["builder"])


# ── 文档解析 ─────────────────────────────────────────────────────

def _parse_text(filename: str, raw: bytes) -> str:
    """解析单个文件，统一转纯文本喂给 LLM。"""
    name = (filename or "").lower()
    try:
        if name.endswith(".txt") or name.endswith(".md"):
            return raw.decode("utf-8", errors="ignore")

        if name.endswith(".csv"):
            try:
                import pandas as pd  # type: ignore
                df = pd.read_csv(BytesIO(raw))
                return f"CSV: {filename}\n列：{list(df.columns)}\n前 20 行：\n{df.head(20).to_string()}"
            except Exception:
                return raw.decode("utf-8", errors="ignore")

        if name.endswith(".xlsx") or name.endswith(".xls"):
            try:
                import pandas as pd  # type: ignore
                xls = pd.ExcelFile(BytesIO(raw))
                parts = []
                for sheet in xls.sheet_names[:5]:
                    df = xls.parse(sheet)
                    parts.append(f"Sheet: {sheet}\n列：{list(df.columns)}\n前 10 行：\n{df.head(10).to_string()}")
                return f"Excel: {filename}\n\n" + "\n\n".join(parts)
            except Exception as e:
                return f"Excel 解析失败: {e}"

        if name.endswith(".docx"):
            try:
                from docx import Document  # type: ignore
                doc = Document(BytesIO(raw))
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                tables_text = []
                for ti, t in enumerate(doc.tables[:5]):
                    rows = []
                    for row in t.rows[:30]:
                        rows.append(" | ".join(c.text.strip() for c in row.cells))
                    tables_text.append(f"[表 {ti+1}]\n" + "\n".join(rows))
                return f"Word: {filename}\n\n" + "\n".join(paragraphs) + ("\n\n" + "\n\n".join(tables_text) if tables_text else "")
            except Exception as e:
                return f"Word 解析失败: {e}"

        if name.endswith(".pdf"):
            try:
                import pdfplumber  # type: ignore
                with pdfplumber.open(BytesIO(raw)) as pdf:
                    pages = [p.extract_text() or "" for p in pdf.pages[:30]]
                return f"PDF: {filename}\n\n" + "\n\n".join(pages)
            except Exception as e:
                return f"PDF 解析失败: {e}"

        return raw.decode("utf-8", errors="ignore")
    except Exception as e:
        logger.exception("文档解析异常")
        return f"解析失败: {e}"


# ── LLM Prompt ──────────────────────────────────────────────────

_EXTRACT_PROMPT = """你是本体建模专家，需要从用户提供的业务文档中抽取本体草稿。

## 全平台术语规范（严格遵守）
- **对象**（Object）— 业务实体，如客户、订单
- **属性**（Property）— 对象上的字段
- **关系**（Relation）— 对象之间的关联
- **规则**（Rule）— 业务约束，如"客户连续 3 个月不下单视为流失风险"
- **动作**（Action）— 业务操作，如"触发挽留外呼"

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


def _call_llm_for_extract(content: str, filename: str) -> list[dict]:
    client = get_llm_client()
    messages = [
        {"role": "system", "content": _EXTRACT_PROMPT},
        {"role": "user", "content": f"## 文档：{filename}\n\n{content[:18000]}"},
    ]
    try:
        resp = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            temperature=0,
            max_tokens=6000,
            timeout=90,
        )
    except Exception as e:
        logger.error("LLM 调用失败: %s", e)
        raise
    text = (resp.choices[0].message.content or "").strip()
    # 清理 markdown 代码块
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
    if not isinstance(data, list):
        return []
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
    for f in files:
        if not f.filename:
            continue
        raw = await f.read()
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

            for filename, raw in docs:
                yield _emit({"type": "file_parsing", "file_name": filename})
                text = _parse_text(filename, raw)
                if text.startswith("解析失败") or text.startswith("Word 解析失败") or text.startswith("PDF 解析失败"):
                    yield _emit({"type": "file_failed", "file_name": filename, "error": text})
                    continue
                yield _emit({"type": "file_parsed", "file_name": filename, "text_length": len(text)})

                try:
                    events = _call_llm_for_extract(text, filename)
                except Exception as e:
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
                        entity_names.add(ev.get("name", ""))
                    elif t == "attr_proposed":
                        if ev.get("entity_name") not in entity_names:
                            continue
                    elif t == "relation_proposed":
                        if ev.get("from_entity") not in entity_names or ev.get("to_entity") not in entity_names:
                            continue
                    elif t in ("rule_suggested", "action_suggested"):
                        ev.setdefault("source_file", filename)
                    yield _emit(ev)

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


class _DraftObject(BaseModel):
    name: str
    displayName: str | None = None
    tier: int = 2
    namespace: str | None = None
    description: str | None = None
    primaryKey: str | None = None
    properties: list[_DraftProperty] = []
    backing_asset_ids: list[str] = []


class FinalizeRequest(BaseModel):
    objects: list[_DraftObject]


@router.post("/finalize")
def builder_finalize(body: FinalizeRequest, db: Session = Depends(get_db)):
    """把 builder 草稿一次性落库：每个对象创建 OntologyEntity + EntityAttribute；
    若 backing_asset_ids 非空，自动创建 primary ObjectBinding（含 field_mappings）。

    幂等：实体已存在时跳过；binding 已存在时也跳过。
    """
    from app.models.entity import EntityAttribute, OntologyEntity
    from app.repositories.asset_repo import AssetRepository
    from app.services.data_plane.object_binding_service import ObjectBindingService

    asset_repo = AssetRepository(db)
    binding_svc = ObjectBindingService(db)

    created_entities = 0
    created_bindings = 0
    skipped = 0

    for obj in body.objects:
        eid = (f"{obj.namespace}_{obj.name}" if obj.namespace else obj.name)
        existing = db.get(OntologyEntity, eid)
        if existing:
            skipped += 1
            entity = existing
        else:
            entity = OntologyEntity(
                id=eid, name=obj.name, name_cn=obj.displayName or obj.name,
                tier=int(obj.tier or 2), status="active",
                description=obj.description,
                schema_json={"primary_key": obj.primaryKey,
                             "backing_asset_ids": obj.backing_asset_ids},
            )
            db.add(entity)
            db.flush()
            created_entities += 1

        # 属性（按 name 去重）
        attr_by_name: dict[str, EntityAttribute] = {a.name: a for a in entity.attributes}
        for p in obj.properties:
            if p.name in attr_by_name:
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
        for idx, asset_id in enumerate(obj.backing_asset_ids):
            asset = asset_repo.get_by_id(asset_id)
            if not asset:
                continue
            role = "primary" if idx == 0 else "enrichment"
            existing_binding = binding_svc.repo.find_existing(entity.id, asset_id, role)
            if existing_binding:
                continue
            field_mappings = []
            for p in obj.properties:
                if p.source_asset_id == asset_id and p.source_column:
                    attr = attr_by_name.get(p.name)
                    if attr:
                        field_mappings.append({
                            "attribute_id": attr.id,
                            "source_column": p.source_column,
                            "transform": None,
                        })
            try:
                binding_svc.create(
                    object_type_id=entity.id,
                    asset_id=asset_id,
                    role=role,
                    field_mappings=field_mappings,
                    id_column=obj.primaryKey,
                )
                created_bindings += 1
            except Exception:
                logger.exception("create binding failed for %s", entity.id)

    db.commit()
    return {
        "created_entities": created_entities,
        "created_bindings": created_bindings,
        "skipped": skipped,
        "total": len(body.objects),
    }
