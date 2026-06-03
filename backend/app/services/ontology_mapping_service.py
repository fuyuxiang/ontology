"""本体→数据资产映射服务 — 两阶段 LLM 匹配"""
from __future__ import annotations

import copy
import json
import logging
import re
from typing import Generator

from openai import OpenAI

from app.config import settings
from app.services import dwd_catalog

logger = logging.getLogger(__name__)

_BATCH_SIZE = 100


def _get_llm_client() -> OpenAI:
    return OpenAI(base_url=settings.LLM_BASE_URL, api_key=settings.LLM_API_KEY)


def _extract_json(text: str) -> str:
    text = re.sub(r"<think>[\s\S]*?</think>", "", text).strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return match.group(0)
    return text


def _build_ontology_summary(ontology: dict) -> str:
    parts = []
    for e in ontology.get("entities", []):
        props = ", ".join(p.get("displayName", p["name"]) for p in e.get("properties", []))
        parts.append(f"- 实体: {e.get('displayName', e['name'])}({e['name']}), 属性: {props}")
    for r in ontology.get("relations", []):
        parts.append(f"- 关系: {r.get('displayName', r['name'])} ({r['source']} → {r['target']})")
    return "\n".join(parts)


def _filter_tables_prompt(ontology_summary: str, tables_text: str) -> str:
    return f"""你是数据资产匹配专家。根据以下本体信息，从数据表清单中筛选出最相关的候选表。

## 本体信息
{ontology_summary}

## 数据表清单
{tables_text}

## 要求
- 选出与本体实体最相关的表，每个实体至少匹配1张候选表
- 输出 JSON 格式：{{"candidates": [{{"entity": "实体名", "tables": ["表名1", "表名2"]}}]}}
- 宁可多选不要漏选，后续会做精确匹配"""


def get_all_tables_summary() -> list[dict]:
    from sqlalchemy import text as sa_text
    from app.services.dwd_catalog import _get_engine
    with _get_engine().connect() as conn:
        rows = conn.execute(sa_text(
            "SELECT table_name, table_desc FROM dwd_table_list ORDER BY serial_number"
        ))
        return [{"table_name": r[0], "table_desc": r[1] or ""} for r in rows]


_MAPPING_PROMPT_TEMPLATE = """你是本体映射专家。将本体中的实体、属性、关系精确映射到数据表及字段。

## 本体
{ontology_json}

## 候选表结构
{candidate_schemas}

## 映射规则
- 每个实体映射到最匹配的一张表
- 每个属性映射到表中最匹配的字段（考虑名称语义相似度和类型兼容性）
- 关系映射需指出源表关联字段和目标表关联字段
- 无法匹配的属性/关系，field 设为 null
- 为每个映射给出 confidence（0-1）

## 输出严格 JSON 格式
{{
  "entities": [
    {{
      "name": "实体name",
      "table": "对应表名",
      "confidence": 0.9,
      "properties": [
        {{"name": "属性name", "field": "字段名或null", "fieldType": "字段类型或null", "confidence": 0.9}}
      ]
    }}
  ],
  "relations": [
    {{
      "name": "关系name",
      "source": "源实体name",
      "target": "目标实体name",
      "sourceField": "源表关联字段或null",
      "sourceTable": "源表名或null",
      "targetField": "目标表关联字段或null",
      "targetTable": "目标表名或null",
      "confidence": 0.8
    }}
  ]
}}"""


def map_entities_and_relations(ontology: dict, candidate_table_names: list[str]) -> dict:
    schemas = {}
    for tn in candidate_table_names:
        fields = dwd_catalog.get_table_schema(tn)
        schemas[tn] = [
            {"field_name": f["field_name"], "field_desc": f["field_desc"], "field_type": f["field_type"]}
            for f in fields
        ]

    ontology_json = json.dumps(ontology, ensure_ascii=False, indent=2)
    candidate_schemas = json.dumps(schemas, ensure_ascii=False, indent=2)

    prompt = _MAPPING_PROMPT_TEMPLATE.format(
        ontology_json=ontology_json,
        candidate_schemas=candidate_schemas,
    )

    client = _get_llm_client()
    resp = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    content = _extract_json(resp.choices[0].message.content or "{}")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        logger.warning("map_entities_and_relations 解析失败: %s", content[:200])
        return {"entities": [], "relations": []}


def _merge_mapping_into_ontology(ontology: dict, mapping: dict) -> dict:
    entity_map = {e["name"]: e for e in mapping.get("entities", [])}
    for entity in ontology.get("entities", []):
        mapped = entity_map.get(entity["name"])
        if mapped:
            entity["table"] = mapped.get("table")
            entity["confidence"] = mapped.get("confidence", 0)
            prop_map = {p["name"]: p for p in mapped.get("properties", [])}
            for prop in entity.get("properties", []):
                mp = prop_map.get(prop["name"])
                if mp:
                    prop["field"] = mp.get("field")
                    prop["fieldType"] = mp.get("fieldType")
                    prop["confidence"] = mp.get("confidence", 0)
                else:
                    prop["field"] = None
                    prop["fieldType"] = None
                    prop["confidence"] = 0
        else:
            entity["table"] = None
            entity["confidence"] = 0
            for prop in entity.get("properties", []):
                prop["field"] = None
                prop["fieldType"] = None
                prop["confidence"] = 0

    rel_map = {r["name"]: r for r in mapping.get("relations", [])}
    for rel in ontology.get("relations", []):
        mr = rel_map.get(rel["name"])
        if mr:
            rel["sourceField"] = mr.get("sourceField")
            rel["sourceTable"] = mr.get("sourceTable")
            rel["targetField"] = mr.get("targetField")
            rel["targetTable"] = mr.get("targetTable")
            rel["confidence"] = mr.get("confidence", 0)
        else:
            rel["sourceField"] = None
            rel["sourceTable"] = None
            rel["targetField"] = None
            rel["targetTable"] = None
            rel["confidence"] = 0

    return ontology


def map_ontology_stream(ontology: dict) -> Generator[str, None, None]:
    ontology = copy.deepcopy(ontology)

    yield f"data: {json.dumps({'event': 'progress', 'stage': 'filtering', 'message': '正在筛选候选表...'})}\n\n"

    try:
        all_tables = get_all_tables_summary()
    except Exception as e:
        yield f"data: {json.dumps({'event': 'error', 'message': f'数据资产服务不可用，请检查连接后重试: {e}'})}\n\n"
        return

    ontology_summary = _build_ontology_summary(ontology)
    client = _get_llm_client()

    all_candidates: dict[str, list[str]] = {}
    for i in range(0, len(all_tables), _BATCH_SIZE):
        batch = all_tables[i:i + _BATCH_SIZE]
        tables_text = "\n".join(f"- {t['table_name']}: {t['table_desc']}" for t in batch)
        prompt = _filter_tables_prompt(ontology_summary, tables_text)

        try:
            resp = client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            content = _extract_json(resp.choices[0].message.content or "{}")
            result = json.loads(content)
            for item in result.get("candidates", []):
                entity = item["entity"]
                all_candidates.setdefault(entity, []).extend(item.get("tables", []))
        except Exception as e:
            logger.warning("filter batch %d failed: %s", i, e)

    valid_names = {t["table_name"] for t in all_tables}
    candidate_table_names = list(set(
        t for tables in all_candidates.values() for t in tables if t in valid_names
    ))

    yield f"data: {json.dumps({'event': 'progress', 'stage': 'filtering', 'message': f'筛选出 {len(candidate_table_names)} 张候选表'})}\n\n"

    if not candidate_table_names:
        yield f"data: {json.dumps({'event': 'error', 'message': '未能匹配到任何候选表，请检查数据资产或重试'})}\n\n"
        return

    yield f"data: {json.dumps({'event': 'progress', 'stage': 'mapping', 'message': '正在精确映射实体和字段...'})}\n\n"

    mapping = map_entities_and_relations(ontology, candidate_table_names)
    merged = _merge_mapping_into_ontology(ontology, mapping)

    yield f"data: {json.dumps({'event': 'progress', 'stage': 'mapping', 'message': '映射完成'})}\n\n"
    yield f"data: {json.dumps({'event': 'result', 'data': merged, 'candidate_tables': candidate_table_names})}\n\n"
    yield "data: [DONE]\n\n"
