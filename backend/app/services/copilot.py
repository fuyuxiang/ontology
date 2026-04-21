"""
AI Copilot 服务 — 本体感知的智能对话
- 使用 OpenAI 兼容接口调用 Claude 中转站
- 自动将本体 schema + 关系图注入 system prompt
- 支持 SSE 流式响应
"""
import logging

import httpx
from openai import OpenAI
from sqlalchemy.orm import Session

from app.config import settings
from app.models import OntologyEntity, EntityRelation, BusinessRule
from app.models.rule import EntityAction

logger = logging.getLogger(__name__)


def get_llm_client() -> OpenAI:
    client_kwargs = {
        "api_key": settings.LLM_API_KEY,
        "base_url": settings.LLM_API_BASE,
    }
    try:
        return OpenAI(**client_kwargs)
    except ImportError as exc:
        # Some environments export a SOCKS proxy, but the runtime does not
        # include socksio. Retrying without inheriting proxy env avoids a hard
        # failure during client construction and lets the API degrade gracefully.
        if "socksio" not in str(exc).lower():
            raise
        logger.warning("检测到 SOCKS 代理但未安装 socksio，改为忽略代理环境变量直连 LLM。")
        return OpenAI(
            **client_kwargs,
            http_client=httpx.Client(trust_env=False),
        )


def build_ontology_context(db: Session, entity_id: str | None = None) -> str:
    """构建本体感知的上下文"""
    entities = db.query(OntologyEntity).all()
    relations = db.query(EntityRelation).all()
    rules = db.query(BusinessRule).filter(BusinessRule.status == "active").all()

    ctx_parts = ["## 本体模型概览\n"]

    # 实体列表
    tier_names = {1: "核心", 2: "领域", 3: "场景"}
    for tier in [1, 2, 3]:
        tier_entities = [e for e in entities if e.tier == tier]
        if tier_entities:
            ctx_parts.append(f"### Tier {tier} {tier_names[tier]}对象")
            for e in tier_entities:
                attrs = [a.name for a in e.attributes]
                attr_str = ", ".join(attrs[:8]) if attrs else "无属性"
                ctx_parts.append(f"- **{e.name}** ({e.name_cn}): {attr_str}")

    # 关系
    ctx_parts.append("\n### 实体关系")
    for r in relations:
        from_e = next((e for e in entities if e.id == r.from_entity_id), None)
        to_e = next((e for e in entities if e.id == r.to_entity_id), None)
        if from_e and to_e:
            ctx_parts.append(f"- {from_e.name} --[{r.name} ({r.cardinality})]-> {to_e.name}")

    # 活跃规则（包含结构化信息）
    ctx_parts.append(f"\n### 活跃业务规则 ({len(rules)} 条)")
    for r in rules[:10]:
        entity = next((e for e in entities if e.id == r.entity_id), None)
        has_conditions = "可评估" if r.conditions_json else "仅描述"
        meta = r.rule_meta_json or {}
        risk = meta.get("risk_level", "")
        rule_id = meta.get("rule_id", "")
        ctx_parts.append(
            f"- [{has_conditions}] {r.name} (ID: {rule_id}, 风险级别: {risk}): "
            f"当 `{r.condition_expr}` 时 → {r.action_desc} (关联: {entity.name if entity else '?'})"
        )

    # 实体→数据源映射
    ctx_parts.append("\n### 实体数据源映射")
    for e in entities:
        ds_ref = (e.schema_json or {}).get("datasource_ref", "")
        pk = (e.schema_json or {}).get("primary_key", "")
        if ds_ref:
            ctx_parts.append(f"- {e.name} ({e.name_cn}) → 数据源: {ds_ref}, 主键: {pk}")

    # 动作类型
    actions = db.query(EntityAction).filter(EntityAction.status == "active").all()
    if actions:
        ctx_parts.append(f"\n### 可执行动作 ({len(actions)} 个)")
        for a in actions:
            meta = a.action_meta_json or {}
            action_name = meta.get("action_name", a.name)
            params = a.parameters_json or []
            param_str = ", ".join(p["name"] for p in params) if params else "无参数"
            ctx_parts.append(f"- {a.name} (英文名: {action_name}, 触发方式: {a.type}, 参数: {param_str})")

    # 如果指定了实体，加入详细信息
    if entity_id:
        entity = next((e for e in entities if e.id == entity_id), None)
        if entity:
            ctx_parts.append(f"\n### 当前聚焦实体: {entity.name} ({entity.name_cn})")
            ctx_parts.append(f"描述: {entity.description or '无'}")
            ctx_parts.append("属性:")
            for a in entity.attributes:
                ctx_parts.append(f"  - {a.name} ({a.type}): {a.description}")

    return "\n".join(ctx_parts)


SYSTEM_PROMPT = """你是"本体智能副驾"，一个专注于电信业务本体管理的 AI 助手。

你的能力：
1. 解释本体模型中的实体、属性、关系
2. 分析业务规则的触发条件和影响范围
3. 推荐策略并生成推理链（本体查询 → ML预测 → 规则匹配 → 策略输出）
4. 回答关于客户分群、FTTR订阅、营销活动等业务问题

回答规则：
- 用中文回答
- 引用具体的实体名称和属性名称
- 涉及策略推荐时，给出完整的推理链
- 简洁专业，避免废话

{ontology_context}
"""


def chat_stream(messages: list[dict], db: Session, entity_id: str | None = None):
    """流式对话，返回 SSE 事件生成器"""
    client = get_llm_client()
    context = build_ontology_context(db, entity_id)
    system_msg = SYSTEM_PROMPT.format(ontology_context=context)

    api_messages = [{"role": "system", "content": system_msg}]
    for m in messages:
        api_messages.append({"role": m["role"], "content": m["content"]})

    stream = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=api_messages,
        stream=True,
        max_tokens=2048,
        temperature=0.7,
    )

    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def chat_sync(messages: list[dict], db: Session, entity_id: str | None = None) -> str:
    """非流式对话，返回完整响应"""
    client = get_llm_client()
    context = build_ontology_context(db, entity_id)
    system_msg = SYSTEM_PROMPT.format(ontology_context=context)

    api_messages = [{"role": "system", "content": system_msg}]
    for m in messages:
        api_messages.append({"role": m["role"], "content": m["content"]})

    response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=api_messages,
        max_tokens=2048,
        temperature=0.7,
    )

    return response.choices[0].message.content or ""
