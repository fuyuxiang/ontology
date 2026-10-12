"""AI Builder V2 — LLM 驱动的本体构建服务"""
from __future__ import annotations

import json
import logging
import re
from collections.abc import Generator

from openai import OpenAI
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.services import asset_catalog, minio_docs

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


def recommend_tables(business_desc: str, tables: list[dict], db: Session | None = None) -> list[str]:
    """根据业务描述和表的 schema 信息，用 LLM 推荐相关的数据表"""
    if not tables:
        return []

    table_summaries = []
    for t in tables[:50]:
        schema = asset_catalog.get_table_schema(t["asset_id"], db)
        fields_preview = ", ".join(f["field_name"] + "(" + (f["field_desc"] or "") + ")" for f in schema[:10])
        table_summaries.append(f"- {t['asset_id']} ({t['table_name']}): {t['table_desc'] or '无描述'} | 字段: {fields_preview}")

    tables_text = "\n".join(table_summaries)
    table_names = [t["asset_id"] for t in tables[:50]]

    prompt = f"""你是一名资深的业务建模与本体建模专家。根据用户的业务描述，从以下候选数据表中选出与该业务最相关的表。

业务描述：{business_desc}

候选数据表（表名: 描述 | 主要字段）：
{tables_text}

请选出与业务场景最相关的表，返回 JSON 格式（不要返回其他内容）：
{{"recommended": ["asset_id1", "asset_id2", ...], "reason": "选择理由"}}"""

    client = _get_llm_client(db)
    resp = client.chat.completions.create(
        model=_get_model_name(db),
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
        raise ValueError("模型未返回有效的资产推荐 JSON，请重试")


def read_document_content(key: str, db: Session | None = None, user_id: str | None = None) -> str:
    if key.startswith("asset:"):
        from app.services.data_plane.asset_service import AssetService
        if db is None:
            raise ValueError("缺少资产数据会话")
        asset = db.get(Asset, key[6:])
        if not asset or asset.kind != "document" or asset.status != "active":
            raise ValueError("文档资产不存在或不可用")
        if asset.document_source_type == "directory" or asset.document_source_type in ("s3", "oss") and not (asset.locator or {}).get("key"):
            raise ValueError("请选择有明确文件或对象 key 的文档资产，文件清单不是文档正文")
        text = AssetService(db).read_document_content(asset)
        if not text.strip():
            raise ValueError("文档资产未返回可抽取正文")
        return text
    if key.startswith("doc-upload:"):
        from app.services.doc_builder import get_session
        parts = key.split(":", 2)
        if len(parts) != 3 or db is None or not user_id:
            raise ValueError("本地文档引用无效或缺少登录账户")
        session = get_session(parts[1], db, user_id)
        if not session:
            raise ValueError("本地文档会话不存在或不可访问")
        file = next((item for item in session["files"] if item["name"] == parts[2]), None)
        if not file:
            raise ValueError("本地文档已不存在")
        return file["content"]
    text = minio_docs.get_document_content(key, db)
    if not text.strip() or text.startswith("["):
        raise ValueError(f"文档 {key} 无法读取或解析: {text[:200]}")
    return text


def extract_ontology_stream(
    table_names: list[str], document_keys: list[str], business_desc: str,
    db: Session | None = None, user_id: str | None = None,
) -> Generator[str, None, None]:
    try:
        yield from _extract_ontology_stream(table_names, document_keys, business_desc, db, user_id)
    except Exception as exc:
        logger.exception("ontology extraction failed")
        yield f"data: {json.dumps({'event':'error','message':str(exc)})}\n\n"
        yield "data: [DONE]\n\n"


def _extract_ontology_stream(
    table_names: list[str],
    document_keys: list[str],
    business_desc: str,
    db: Session | None = None,
    user_id: str | None = None,
) -> Generator[str, None, None]:
    tables_schema = {}
    for tn in table_names:
        schema = asset_catalog.get_table_schema(tn, db)
        asset = asset_catalog._find_asset(db, tn)
        tables_schema[tn] = {"table_name": asset_catalog._table_name(asset) if asset else tn, "fields": schema}

    yield f"data: {json.dumps({'event': 'progress', 'message': f'已加载 {len(table_names)} 张表的 schema'})}\n\n"

    doc_texts = {}
    for key in document_keys:
        try:
            text = read_document_content(key, db, user_id)
            doc_texts[key] = text
        except Exception as e:
            yield f"data: {json.dumps({'event':'error','message':f'读取文档失败: {e}'})}\n\n"
            yield "data: [DONE]\n\n"
            return

    yield f"data: {json.dumps({'event': 'progress', 'message': f'已解析 {len(document_keys)} 篇文档'})}\n\n"

    schema_json = json.dumps(tables_schema, ensure_ascii=False, indent=2)
    doc_summary = "\n\n".join(f"### {k}\n{v}" for k, v in doc_texts.items())

    prompt = f"""你是一名资深的业务建模与本体建模专家。根据以下结构化数据表 schema 和业务文档，提取本体的实体、属性和关系。

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
      "table": "输入结构的asset_id键",
      "asset_id": "对应asset_id",
      "primaryKey": "主键属性名",
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

    client = _get_llm_client(db)
    resp = client.chat.completions.create(
        model=_get_model_name(db),
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
        yield f"data: {json.dumps({'event': 'error', 'message': '模型未返回有效本体 JSON，请重新提取'})}\n\n"
        yield "data: [DONE]\n\n"
        return

    # Resolve table_names to Asset IDs and attach backing info
    table_asset_map: dict[str, str] = {}
    all_asset_ids: list[str] = []
    if db:
        for tn in table_names:
            try:
                asset = asset_catalog._find_asset(db, tn)
                if not asset:
                    raise ValueError(f"数据表 {tn} 尚未注册为可用资产")
            except ValueError as exc:
                yield f"data: {json.dumps({'event':'error','message':str(exc)})}\n\n"
                yield "data: [DONE]\n\n"
                return
            table_asset_map[tn] = asset.id
            all_asset_ids.append(asset.id)
        # 兼容模型返回物理表名，但同名表必须返回明确 asset_id。
        for aid in all_asset_ids:
            physical = asset_catalog._table_name(db.get(Asset, aid))
            matches = [candidate for candidate in all_asset_ids if asset_catalog._table_name(db.get(Asset, candidate)) == physical]
            if len(matches) == 1:
                table_asset_map[physical] = aid

    entities = result.get("entities") if isinstance(result, dict) else None
    if not isinstance(entities, list) or not entities:
        raise ValueError("模型未返回任何有效对象，请重新提取")
    names = [entity.get("name") for entity in entities if isinstance(entity, dict)]
    if len(names) != len(entities) or any(not name for name in names) or len(set(names)) != len(names):
        raise ValueError("模型对象名称缺失或重复，请重新提取")
    for relation in result.get("relations", []):
        if relation.get("source") not in names or relation.get("target") not in names:
            raise ValueError("模型关系引用了未定义对象，请重新提取")
    for ent in entities:
        if not isinstance(ent.get("properties"), list) or not ent["properties"]:
            raise ValueError(f"对象 {ent['name']} 未定义属性，请重新提取")
        table_for_ent = ent.get("table", "")
        asset_id = table_asset_map.get(ent.get("asset_id")) or table_asset_map.get(table_for_ent)
        if asset_id:
            ent["backing_asset_ids"] = [asset_id]
            ent["asset_id"] = asset_id
        else:
            raise ValueError(f"对象 {ent['name']} 未关联所选数据资产，请重新提取")

        if asset_id and db:
            asset_obj = db.get(Asset, asset_id)
            schema_cols = asset_obj.schema_snapshot or [] if asset_obj else []
            col_names = {c.get("name", "").lower() for c in schema_cols}
            for prop in ent.get("properties", []):
                requested = prop.get("source_column") or prop.get("source_field") or prop.get("field") or prop.get("name")
                physical = next((column.get("name") for column in schema_cols if column.get("name", "").lower() == (requested or "").lower()), None)
                if physical:
                    prop["source_asset_id"] = asset_id
                    prop["source_column"] = physical

    result["asset_ids"] = all_asset_ids
    yield f"data: {json.dumps({'event': 'result', 'data': result})}\n\n"
    yield "data: [DONE]\n\n"
