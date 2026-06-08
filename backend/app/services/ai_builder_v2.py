"""AI Builder V2 — LLM 驱动的本体构建服务"""
from __future__ import annotations

import json
import logging
import re
from typing import Generator

from openai import OpenAI
from sqlalchemy.orm import Session

from app.config import settings
from app.models.asset import Asset
from app.services import dwd_catalog, minio_docs

logger = logging.getLogger(__name__)


def _get_llm_client(db: Session | None = None) -> OpenAI:
    from app.services.llm_resolver import get_llm_client
    return get_llm_client(db=db, scene="ontology")


def _get_model_name(db: Session | None = None) -> str:
    from app.services.llm_resolver import get_model_name
    return get_model_name(db=db, scene="ontology")


def _extract_json(text: str) -> str:
    """从 LLM 返回中提取 JSON，处理 think 标签和 markdown 代码块。"""
    text = re.sub(r"<think>[\s\S]*?</think>", "", text).strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return match.group(0)
    return text


def match_domain(business_desc: str, db: Session | None = None) -> dict:
    domains = dwd_catalog.get_domains(db)
    domain_list = "\n".join(f"- {d}" for d in domains)

    prompt = f"""你是一名深耕中国联通业务体系的运营商领域专家兼本体建模专家，熟悉联通在公众客户、政企客户、网络资源、产品中心、订单中心、计费账务、客户服务、渠道运营、智慧家庭、物联网、云网融合、数据中台和智慧运营等领域的业务对象、流程规则和系统边界。根据用户的业务描述，从以下一级主题域中选择最相关的1-3个：

可选主题域：
{domain_list}

用户业务描述：{business_desc}

请返回 JSON 格式（不要返回其他内容）：
{{"domains": ["最相关主题域1", "最相关主题域2"], "reason": "选择理由"}}"""

    client = _get_llm_client()
    resp = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    content = resp.choices[0].message.content or "{}"
    content = _extract_json(content)
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("match_domain JSON 解析失败，原始返回: %s", resp.choices[0].message.content)
        result = {"domains": domains[:2] if len(domains) >= 2 else domains, "reason": "解析失败，返回默认"}
    result["all_domains"] = domains
    return result


def recommend_tables(business_desc: str, tables: list[dict], db: Session | None = None) -> list[str]:
    """根据业务描述和表的 schema 信息，用 LLM 推荐相关的数据表"""
    if not tables:
        return []

    table_summaries = []
    for t in tables[:50]:
        schema = dwd_catalog.get_table_schema(t["table_name"], db)
        fields_preview = ", ".join(f["field_name"] + "(" + (f["field_desc"] or "") + ")" for f in schema[:10])
        table_summaries.append(f"- {t['table_name']}: {t['table_desc'] or '无描述'} | 字段: {fields_preview}")

    tables_text = "\n".join(table_summaries)
    table_names = [t["table_name"] for t in tables[:50]]

    prompt = f"""你是一名深耕中国联通业务体系的运营商领域专家兼本体建模专家，熟悉联通在公众客户、政企客户、网络资源、产品中心、订单中心、计费账务、客户服务、渠道运营、智慧家庭、物联网、云网融合、数据中台和智慧运营等领域的业务对象、流程规则和系统边界。根据用户的业务描述，从以下候选数据表中选出与该业务最相关的表。

业务描述：{business_desc}

候选数据表（表名: 描述 | 主要字段）：
{tables_text}

请选出与业务场景最相关的表，返回 JSON 格式（不要返回其他内容）：
{{"recommended": ["表名1", "表名2", ...], "reason": "选择理由"}}"""

    client = _get_llm_client()
    resp = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    content = resp.choices[0].message.content or "{}"
    content = _extract_json(content)
    try:
        result = json.loads(content)
        recommended = [t for t in result.get("recommended", []) if t in table_names]
        return recommended
    except json.JSONDecodeError:
        logger.warning("recommend_tables JSON 解析失败: %s", resp.choices[0].message.content)
        return []


def extract_ontology_stream(
    table_names: list[str],
    document_keys: list[str],
    business_desc: str,
    db: Session | None = None,
) -> Generator[str, None, None]:
    tables_schema = {}
    for tn in table_names:
        schema = dwd_catalog.get_table_schema(tn, db)
        tables_schema[tn] = {"fields": schema}

    yield f"data: {json.dumps({'event': 'progress', 'message': f'已加载 {len(table_names)} 张表的 schema'})}\n\n"

    doc_texts = {}
    for key in document_keys:
        try:
            text = minio_docs.get_document_content(key)
            doc_texts[key] = text[:3000]
        except Exception as e:
            doc_texts[key] = f"[读取失败: {e}]"

    yield f"data: {json.dumps({'event': 'progress', 'message': f'已解析 {len(document_keys)} 篇文档'})}\n\n"

    schema_json = json.dumps(tables_schema, ensure_ascii=False, indent=2)
    doc_summary = "\n\n".join(f"### {k}\n{v[:2000]}" for k, v in doc_texts.items())

    prompt = f"""你是一名深耕中国联通业务体系的运营商领域专家兼本体建模专家，熟悉联通在公众客户、政企客户、网络资源、产品中心、订单中心、计费账务、客户服务、渠道运营、智慧家庭、物联网、云网融合、数据中台和智慧运营等领域的业务对象、流程规则和系统边界。根据以下结构化数据表 schema 和业务文档，提取本体的实体、属性和关系。

规则：
- 实体必须和结构化数据中的表对应（一张表对应一个实体）
- 每个实体的属性来自对应表的字段
- 非结构化文档仅用于补充实体和关系的中文名称和业务含义
- 关系描述实体间的业务关联，需要有明确的业务逻辑支撑
- 属性类型映射：varchar→string, int/bigint→integer, decimal/float→number, date/datetime→date, text→string

结构化数据（主要依据）：
{schema_json}

非结构化文档（补充信息）：
{doc_summary if doc_summary else "无"}

业务场景描述：{business_desc}

输出严格 JSON 格式（不要有其他内容）：
{{
  "entities": [
    {{
      "name": "PascalCase英文名",
      "displayName": "中文名",
      "table": "对应表名",
      "description": "业务含义",
      "properties": [
        {{"name": "字段英文名", "displayName": "字段中文名", "type": "string|integer|number|date|boolean", "required": true/false}}
      ]
    }}
  ],
  "relations": [
    {{"name": "camelCase英文名", "displayName": "中文名", "source": "源实体name", "target": "目标实体name", "cardinality": "1:1|1:N|N:N", "description": "关系说明"}}
  ]
}}"""

    yield f"data: {json.dumps({'event': 'progress', 'message': '正在调用大模型提取实体和关系...'})}\n\n"

    client = _get_llm_client()
    resp = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        stream=True,
    )

    full_content = ""
    for chunk in resp:
        delta = chunk.choices[0].delta
        if delta.content:
            full_content += delta.content
            yield f"data: {json.dumps({'event': 'token', 'content': delta.content})}\n\n"

    full_content = _extract_json(full_content)

    try:
        result = json.loads(full_content)
    except json.JSONDecodeError:
        yield f"data: {json.dumps({'event': 'result', 'data': {'entities': [], 'relations': [], 'asset_ids': []}, 'raw': full_content})}\n\n"
        yield "data: [DONE]\n\n"
        return

    # Resolve table_names to Asset IDs and attach backing info
    table_asset_map: dict[str, str] = {}
    all_asset_ids: list[str] = []
    if db:
        for tn in table_names:
            asset = (
                db.query(Asset)
                .filter(Asset.status == "active", Asset.kind.in_(["table", "sql_view"]))
                .filter(Asset.locator["table"].as_string() == tn)
                .first()
            )
            if not asset:
                asset = (
                    db.query(Asset)
                    .filter(Asset.status == "active", Asset.kind.in_(["table", "sql_view"]),
                            Asset.name == tn)
                    .first()
                )
            if asset:
                table_asset_map[tn] = asset.id
                all_asset_ids.append(asset.id)

    for ent in result.get("entities", []):
        table_for_ent = ent.get("table", "")
        asset_id = table_asset_map.get(table_for_ent)
        if asset_id:
            ent["backing_asset_ids"] = [asset_id]
        elif all_asset_ids:
            ent["backing_asset_ids"] = list(all_asset_ids)
        else:
            ent["backing_asset_ids"] = []

        if asset_id and db:
            asset_obj = db.get(Asset, asset_id)
            schema_cols = asset_obj.schema_snapshot or [] if asset_obj else []
            col_names = {c.get("name", "").lower() for c in schema_cols}
            for prop in ent.get("properties", []):
                prop_name = (prop.get("name") or "").lower()
                if prop_name in col_names:
                    prop["source_asset_id"] = asset_id
                    prop["source_column"] = prop.get("name")

    result["asset_ids"] = all_asset_ids
    yield f"data: {json.dumps({'event': 'result', 'data': result})}\n\n"
    yield "data: [DONE]\n\n"
