# 文档构建 — 本体→数据资产映射 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在文档构建流程中，本体抽取完成后自动触发两阶段 LLM 映射，将实体/属性/关系精确匹配到 DWD 元数据表的表和字段。

**Architecture:** 新建独立的 `ontology_mapping_service.py` 服务，通过 `POST /api/v1/doc-builder/mapping` 端点以 SSE 流式返回映射结果。前端在 DocBuilderView 中插入新的映射步骤组件 `StepDocMapping.vue`。

**Tech Stack:** Python/FastAPI (后端), Vue 3 + TypeScript (前端), OpenAI SDK (LLM), SQLAlchemy (DWD 查询)

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `backend/app/services/ontology_mapping_service.py` | 新增 | 两阶段 LLM 映射核心逻辑 |
| `backend/app/api/v1/ontology_mapping.py` | 新增 | 映射 API 路由（SSE 流式） |
| `backend/app/main.py` | 修改 | 注册新路由 |
| `frontend/src/views/builder/components/doc/StepDocMapping.vue` | 新增 | 映射步骤 UI 组件 |
| `frontend/src/views/builder/DocBuilderView.vue` | 修改 | 插入映射步骤 |
| `backend/tests/test_ontology_mapping.py` | 新增 | 后端映射服务测试 |

---

## Task 1: 后端映射服务 — 候选表筛选（第一阶段）

**Files:**
- Create: `backend/app/services/ontology_mapping_service.py`
- Reference: `backend/app/services/dwd_catalog.py`, `backend/app/services/ai_builder_v2.py`
- Test: `backend/tests/test_ontology_mapping.py`

- [ ] **Step 1: 创建映射服务文件，实现候选表筛选逻辑**

```python
# backend/app/services/ontology_mapping_service.py
"""本体→数据资产映射服务 — 两阶段 LLM 匹配"""
from __future__ import annotations

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
    """获取 dwd_table_list 全量表名+表描述"""
    from sqlalchemy import text as sa_text
    from app.services.dwd_catalog import _get_engine
    with _get_engine().connect() as conn:
        rows = conn.execute(sa_text(
            "SELECT table_name, table_desc FROM dwd_table_list ORDER BY serial_number"
        ))
        return [{"table_name": r[0], "table_desc": r[1] or ""} for r in rows]


def filter_candidate_tables(ontology: dict) -> list[dict]:
    """第一阶段：从全量表中筛选候选表"""
    all_tables = get_all_tables_summary()
    ontology_summary = _build_ontology_summary(ontology)
    client = _get_llm_client()

    all_candidates: dict[str, list[str]] = {}

    for i in range(0, len(all_tables), _BATCH_SIZE):
        batch = all_tables[i:i + _BATCH_SIZE]
        tables_text = "\n".join(f"- {t['table_name']}: {t['table_desc']}" for t in batch)
        prompt = _filter_tables_prompt(ontology_summary, tables_text)

        resp = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        content = _extract_json(resp.choices[0].message.content or "{}")
        try:
            result = json.loads(content)
            for item in result.get("candidates", []):
                entity = item["entity"]
                tables = item.get("tables", [])
                all_candidates.setdefault(entity, []).extend(tables)
        except (json.JSONDecodeError, KeyError):
            logger.warning("filter_candidate_tables 解析失败: %s", content[:200])

    # 去重，收集所有候选表名
    unique_table_names = list(set(t for tables in all_candidates.values() for t in tables))
    # 验证表名确实存在
    valid_names = {t["table_name"] for t in all_tables}
    unique_table_names = [t for t in unique_table_names if t in valid_names]

    return [{"table_name": tn, "entity_candidates": all_candidates} for tn in unique_table_names]
```

- [ ] **Step 2: 运行基本导入验证**

Run: `cd backend && python -c "from app.services.ontology_mapping_service import filter_candidate_tables; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/ontology_mapping_service.py
git commit -m "feat(mapping): add ontology mapping service with candidate table filtering"
```

---

## Task 2: 后端映射服务 — 精确映射（第二阶段）

**Files:**
- Modify: `backend/app/services/ontology_mapping_service.py`

- [ ] **Step 1: 在 ontology_mapping_service.py 中添加精确映射函数**

在文件末尾追加：

```python
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
    """第二阶段：精确映射实体/属性/关系到表和字段"""
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
    """将映射结果合并回原始本体 JSON"""
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/ontology_mapping_service.py
git commit -m "feat(mapping): add precise entity/property/relation mapping logic"
```

---

## Task 3: 后端映射服务 — SSE 流式接口

**Files:**
- Modify: `backend/app/services/ontology_mapping_service.py`

- [ ] **Step 1: 添加流式映射入口函数**

在 `ontology_mapping_service.py` 末尾追加：

```python
def map_ontology_stream(ontology: dict) -> Generator[str, None, None]:
    """完整的映射流程，以 SSE 事件流输出"""
    import copy
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/ontology_mapping_service.py
git commit -m "feat(mapping): add SSE streaming entry point for full mapping flow"
```

---

## Task 4: 后端 API 路由

**Files:**
- Create: `backend/app/api/v1/ontology_mapping.py`
- Modify: `backend/app/main.py:224,440`

- [ ] **Step 1: 创建 API 路由文件**

```python
# backend/app/api/v1/ontology_mapping.py
"""本体→数据资产映射 API"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services import ontology_mapping_service

router = APIRouter(prefix="/doc-builder", tags=["doc-builder"])


class MappingRequest(BaseModel):
    session_id: str
    ontology: dict


@router.post("/mapping")
async def mapping(req: MappingRequest):
    return StreamingResponse(
        ontology_mapping_service.map_ontology_stream(req.ontology),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

- [ ] **Step 2: 在 main.py 中注册路由**

在 `backend/app/main.py` 的 import 区域（约第 224 行附近）添加：

```python
from app.api.v1.ontology_mapping import router as ontology_mapping_router
```

在路由注册区域（约第 440 行 `doc_builder_router` 之后）添加：

```python
app.include_router(ontology_mapping_router, prefix="/api/v1")
```

- [ ] **Step 3: 验证服务启动**

Run: `cd backend && python -c "from app.main import app; print('Routes:', len(app.routes))"`
Expected: 无报错，打印路由数量

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/ontology_mapping.py backend/app/main.py
git commit -m "feat(mapping): add POST /doc-builder/mapping SSE endpoint"
```

---

## Task 5: 前端映射步骤组件

**Files:**
- Create: `frontend/src/views/builder/components/doc/StepDocMapping.vue`

- [ ] **Step 1: 创建 StepDocMapping.vue**

```vue
<template>
  <div class="step-mapping">
    <h2 class="step-mapping__title">数据资产映射</h2>

    <!-- 加载状态 -->
    <div v-if="loading" class="step-mapping__loading">
      <div class="step-mapping__spinner"></div>
      <p>{{ progressMessage }}</p>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="errorMessage" class="step-mapping__error">
      <p>{{ errorMessage }}</p>
      <button class="step-mapping__btn" @click="startMapping">重试</button>
    </div>

    <!-- 映射结果 -->
    <div v-else-if="mappedOntology" class="step-mapping__result">
      <p class="step-mapping__sub">
        共映射 {{ mappedOntology.entities.length }} 个实体、{{ mappedOntology.relations.length }} 个关系
      </p>

      <!-- 实体映射表格 -->
      <div class="step-mapping__section">
        <h3>实体映射</h3>
        <table class="step-mapping__table">
          <thead>
            <tr>
              <th>实体名称</th>
              <th>匹配表</th>
              <th>置信度</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="e in mappedOntology.entities"
              :key="e.name"
              :class="{ 'step-mapping__row--warning': !e.table, 'step-mapping__row--low': e.confidence < 0.8 && e.table }"
            >
              <td>{{ e.displayName || e.name }}</td>
              <td>
                <select v-model="e.table" class="step-mapping__select">
                  <option :value="null">未匹配</option>
                  <option v-for="t in candidateTables" :key="t" :value="t">{{ t }}</option>
                </select>
              </td>
              <td>
                <span class="step-mapping__confidence" :class="confidenceClass(e.confidence)">
                  {{ e.table ? Math.round((e.confidence || 0) * 100) + '%' : '-' }}
                </span>
              </td>
              <td>
                <button class="step-mapping__btn-sm" @click="toggleExpand(e.name)">
                  {{ expanded[e.name] ? '收起' : '展开' }}
                </button>
              </td>
            </tr>
            <!-- 属性明细展开行 -->
            <template v-for="e in mappedOntology.entities" :key="'detail-' + e.name">
              <tr v-if="expanded[e.name]" class="step-mapping__detail-row">
                <td colspan="4">
                  <table class="step-mapping__sub-table">
                    <thead>
                      <tr><th>属性</th><th>匹配字段</th><th>字段类型</th><th>置信度</th></tr>
                    </thead>
                    <tbody>
                      <tr v-for="p in e.properties" :key="p.name">
                        <td>{{ p.displayName || p.name }}</td>
                        <td>
                          <select v-model="p.field" class="step-mapping__select step-mapping__select--sm">
                            <option :value="null">未匹配</option>
                            <option v-for="f in getFieldsForTable(e.table)" :key="f.field_name" :value="f.field_name">
                              {{ f.field_name }} ({{ f.field_desc || '' }})
                            </option>
                          </select>
                        </td>
                        <td>{{ p.fieldType || '-' }}</td>
                        <td>
                          <span class="step-mapping__confidence" :class="confidenceClass(p.confidence)">
                            {{ p.field ? Math.round((p.confidence || 0) * 100) + '%' : '-' }}
                          </span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <!-- 关系映射表格 -->
      <div class="step-mapping__section" v-if="mappedOntology.relations.length">
        <h3>关系映射</h3>
        <table class="step-mapping__table">
          <thead>
            <tr><th>关系</th><th>源表.字段</th><th>目标表.字段</th><th>置信度</th></tr>
          </thead>
          <tbody>
            <tr v-for="r in mappedOntology.relations" :key="r.name" :class="{ 'step-mapping__row--low': r.confidence < 0.8 }">
              <td>{{ r.displayName || r.name }} ({{ r.source }}→{{ r.target }})</td>
              <td>{{ r.sourceTable ? `${r.sourceTable}.${r.sourceField}` : '-' }}</td>
              <td>{{ r.targetTable ? `${r.targetTable}.${r.targetField}` : '-' }}</td>
              <td>
                <span class="step-mapping__confidence" :class="confidenceClass(r.confidence)">
                  {{ Math.round((r.confidence || 0) * 100) }}%
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 操作按钮 -->
      <div class="step-mapping__actions">
        <button class="step-mapping__btn step-mapping__btn--secondary" @click="startMapping">重新匹配</button>
        <button class="step-mapping__btn" :disabled="!allEntitiesMapped" @click="onConfirm">确认并继续</button>
      </div>
      <p v-if="!allEntitiesMapped" class="step-mapping__hint">所有实体必须完成映射后才能继续</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'

const props = defineProps<{
  sessionId: string
  ontology: any
}>()

const emit = defineEmits<{
  next: [ontology: any]
}>()

const loading = ref(false)
const progressMessage = ref('')
const errorMessage = ref('')
const mappedOntology = ref<any>(null)
const candidateTables = ref<string[]>([])
const tableFields = reactive<Record<string, any[]>>({})
const expanded = reactive<Record<string, boolean>>({})

const allEntitiesMapped = computed(() => {
  if (!mappedOntology.value) return false
  return mappedOntology.value.entities.every((e: any) => e.table != null)
})

function confidenceClass(c: number | undefined) {
  if (!c) return 'step-mapping__confidence--none'
  if (c >= 0.8) return 'step-mapping__confidence--high'
  return 'step-mapping__confidence--low'
}

function toggleExpand(name: string) {
  expanded[name] = !expanded[name]
}

function getFieldsForTable(tableName: string | null): any[] {
  if (!tableName) return []
  return tableFields[tableName] || []
}

async function fetchTableFields(tableNames: string[]) {
  for (const tn of tableNames) {
    if (tableFields[tn]) continue
    try {
      const resp = await fetch(`/api/v1/ai-builder/tables/${tn}/schema`)
      if (resp.ok) {
        tableFields[tn] = await resp.json()
      }
    } catch { /* skip */ }
  }
}

async function startMapping() {
  loading.value = true
  errorMessage.value = ''
  progressMessage.value = '正在筛选候选表...'

  try {
    const resp = await fetch('/api/v1/doc-builder/mapping', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: props.sessionId, ontology: props.ontology }),
    })

    const reader = resp.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const raw = line.slice(6)
        if (raw === '[DONE]') break
        try {
          const evt = JSON.parse(raw)
          if (evt.event === 'progress') {
            progressMessage.value = evt.message
          } else if (evt.event === 'error') {
            errorMessage.value = evt.message
            loading.value = false
            return
          } else if (evt.event === 'result') {
            mappedOntology.value = evt.data
            candidateTables.value = evt.candidate_tables || []
            await fetchTableFields(candidateTables.value)
          }
        } catch { /* skip non-json */ }
      }
    }
  } catch (e: any) {
    errorMessage.value = `请求失败: ${e.message}`
  }

  loading.value = false
}

function onConfirm() {
  emit('next', mappedOntology.value)
}

onMounted(() => {
  startMapping()
})
</script>

<style scoped>
.step-mapping { padding: 24px; max-width: 1000px; margin: 0 auto; }
.step-mapping__title { font-size: 18px; font-weight: 600; margin-bottom: 8px; }
.step-mapping__sub { color: #666; margin-bottom: 16px; }
.step-mapping__loading { text-align: center; padding: 60px 0; }
.step-mapping__spinner { width: 32px; height: 32px; border: 3px solid #e0e0e0; border-top-color: #4a6fa5; border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 12px; }
@keyframes spin { to { transform: rotate(360deg); } }
.step-mapping__error { text-align: center; padding: 40px 0; color: #d32f2f; }
.step-mapping__section { margin-bottom: 24px; }
.step-mapping__section h3 { font-size: 14px; font-weight: 600; margin-bottom: 8px; }
.step-mapping__table { width: 100%; border-collapse: collapse; font-size: 13px; }
.step-mapping__table th, .step-mapping__table td { padding: 8px 12px; border: 1px solid #e0e0e0; text-align: left; }
.step-mapping__table th { background: #f5f5f5; font-weight: 600; }
.step-mapping__row--warning { background: #fff3e0; }
.step-mapping__row--low { background: #fffde7; }
.step-mapping__sub-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.step-mapping__sub-table th, .step-mapping__sub-table td { padding: 4px 8px; border: 1px solid #eee; }
.step-mapping__sub-table th { background: #fafafa; }
.step-mapping__detail-row td { padding: 0 !important; }
.step-mapping__select { padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 12px; max-width: 200px; }
.step-mapping__select--sm { max-width: 180px; }
.step-mapping__confidence--high { color: #2e7d32; font-weight: 600; }
.step-mapping__confidence--low { color: #f57c00; font-weight: 600; }
.step-mapping__confidence--none { color: #999; }
.step-mapping__actions { display: flex; gap: 12px; justify-content: flex-end; margin-top: 20px; }
.step-mapping__btn { padding: 8px 20px; background: #4a6fa5; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; }
.step-mapping__btn:disabled { background: #ccc; cursor: not-allowed; }
.step-mapping__btn--secondary { background: #fff; color: #4a6fa5; border: 1px solid #4a6fa5; }
.step-mapping__btn-sm { padding: 2px 8px; font-size: 11px; background: #f0f0f0; border: 1px solid #ddd; border-radius: 4px; cursor: pointer; }
.step-mapping__hint { color: #d32f2f; font-size: 12px; text-align: right; margin-top: 8px; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/builder/components/doc/StepDocMapping.vue
git commit -m "feat(mapping): add StepDocMapping.vue frontend component"
```

---

## Task 6: 前端集成 — 修改 DocBuilderView

**Files:**
- Modify: `frontend/src/views/builder/DocBuilderView.vue`

- [ ] **Step 1: 修改 DocBuilderView.vue**

将整个文件内容替换为：

```vue
<template>
  <div class="ai-builder">
    <div class="ai-builder__steps">
      <div v-for="(s, i) in steps" :key="i" class="ai-builder__step" :class="{ 'ai-builder__step--active': step === i, 'ai-builder__step--done': step > i }">
        <div class="ai-builder__step-num">{{ step > i ? '✓' : i + 1 }}</div>
        <div class="ai-builder__step-label">{{ s }}</div>
      </div>
    </div>

    <div class="ai-builder__content">
      <StepDocUpload v-if="step === 0" @next="onUploadDone" />
      <StepDocChat v-else-if="step === 1" :session-id="sessionId" :business-desc="businessDesc" @next="onChatDone" />
      <StepDocMapping v-else-if="step === 2" :session-id="sessionId" :ontology="extractionResult!" @next="onMappingDone" />
      <StepDocReview v-else-if="step === 3" :result="mappedResult!" @prev="step = 2" @confirm="onConfirm" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useBuilderStore } from '../../store/builder'
import StepDocUpload from './components/doc/StepDocUpload.vue'
import StepDocChat from './components/doc/StepDocChat.vue'
import StepDocMapping from './components/doc/StepDocMapping.vue'
import StepDocReview from './components/doc/StepDocReview.vue'

const router = useRouter()
const store = useBuilderStore()

const steps = ['需求与文档', 'AI对话抽取', '资产映射', '确认入库']
const step = ref(0)
const sessionId = ref('')
const businessDesc = ref('')
const extractionResult = ref<any>(null)
const mappedResult = ref<any>(null)

function onUploadDone(payload: { sessionId: string; businessDesc: string }) {
  sessionId.value = payload.sessionId
  businessDesc.value = payload.businessDesc
  step.value = 1
}

function onChatDone(ontology: any) {
  extractionResult.value = ontology
  step.value = 2
}

function onMappingDone(ontology: any) {
  mappedResult.value = ontology
  step.value = 3
}

function onConfirm(ontology: any) {
  store.createSession({ ontologyName: `文档构建-${Date.now().toString(36).slice(-4)}`, buildMethod: 'chat' })
  const objects = ontology.entities.map((e: any, i: number) => ({
    id: `obj-${Date.now().toString(36)}-${i}`,
    name: e.name,
    displayName: e.displayName,
    tier: 1 as const,
    namespace: '',
    description: e.description || '',
    primaryKey: 'id',
    icon: '🔷',
    instanceCount: 0,
    table: e.table || undefined,
    tableConfidence: e.confidence || undefined,
    properties: (e.properties || []).map((p: any, j: number) => ({
      id: `prop-${Date.now().toString(36)}-${i}-${j}`,
      name: p.name,
      displayName: p.displayName || p.name,
      type: p.type || 'string',
      required: p.required ?? false,
      field: p.field || undefined,
      fieldType: p.fieldType || undefined,
      fieldConfidence: p.confidence || undefined,
    })),
    derivedProperties: [],
    rules: [],
    actions: [],
    approved: false,
  }))
  const relations = ontology.relations.map((r: any, i: number) => ({
    id: `rel-${Date.now().toString(36)}-${i}`,
    name: r.name,
    displayName: r.displayName,
    source: objects.find((o: any) => o.name === r.source)?.id || r.source,
    target: objects.find((o: any) => o.name === r.target)?.id || r.target,
    cardinality: r.cardinality || '1:N',
    description: r.description || r.displayName,
    relationType: 'ObjectProperty' as const,
    semanticType: 'association' as const,
    sourceField: r.sourceField || undefined,
    sourceTable: r.sourceTable || undefined,
    targetField: r.targetField || undefined,
    targetTable: r.targetTable || undefined,
    mappingConfidence: r.confidence || undefined,
  }))
  store.patchActive({ ontologyObjects: objects, ontologyRelations: relations })
  router.push('/studio')
}
</script>

<style scoped>
.ai-builder { height: 100%; display: flex; flex-direction: column; background: #fafafa; }
.ai-builder__steps { display: flex; align-items: center; justify-content: center; gap: 4px; padding: 16px 24px; background: #fff; border-bottom: 1px solid #e0e0e0; flex-shrink: 0; }
.ai-builder__step { display: flex; align-items: center; gap: 6px; padding: 6px 12px; font-size: 12px; color: #999; }
.ai-builder__step--active { color: #4a6fa5; font-weight: 600; }
.ai-builder__step--done { color: #2e7d32; }
.ai-builder__step-num { width: 22px; height: 22px; border-radius: 50%; border: 2px solid currentColor; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; }
.ai-builder__step--active .ai-builder__step-num { background: #4a6fa5; color: #fff; border-color: #4a6fa5; }
.ai-builder__step--done .ai-builder__step-num { background: #2e7d32; color: #fff; border-color: #2e7d32; }
.ai-builder__content { flex: 1; overflow-y: auto; }
</style>
```

- [ ] **Step 2: 验证前端编译**

Run: `cd frontend && npx vue-tsc --noEmit 2>&1 | head -20`
Expected: 无类型错误

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/builder/DocBuilderView.vue
git commit -m "feat(mapping): integrate mapping step into DocBuilderView flow"
```

---

## Task 7: 后端单元测试

**Files:**
- Create: `backend/tests/test_ontology_mapping.py`

- [ ] **Step 1: 编写测试**

```python
# backend/tests/test_ontology_mapping.py
"""ontology_mapping_service 单元测试"""
import json
from unittest.mock import patch, MagicMock

import pytest


SAMPLE_ONTOLOGY = {
    "entities": [
        {
            "name": "Customer",
            "displayName": "客户",
            "properties": [
                {"name": "customerName", "displayName": "客户名称", "type": "string", "required": True},
                {"name": "phone", "displayName": "手机号", "type": "string", "required": False},
            ],
        }
    ],
    "relations": [
        {"name": "belongsTo", "displayName": "属于", "source": "Order", "target": "Customer", "cardinality": "N:1"}
    ],
}


def test_build_ontology_summary():
    from app.services.ontology_mapping_service import _build_ontology_summary
    summary = _build_ontology_summary(SAMPLE_ONTOLOGY)
    assert "客户" in summary
    assert "Customer" in summary
    assert "客户名称" in summary
    assert "belongsTo" in summary


def test_merge_mapping_into_ontology():
    from app.services.ontology_mapping_service import _merge_mapping_into_ontology
    import copy

    ontology = copy.deepcopy(SAMPLE_ONTOLOGY)
    mapping = {
        "entities": [
            {
                "name": "Customer",
                "table": "dwd_crm_customer",
                "confidence": 0.92,
                "properties": [
                    {"name": "customerName", "field": "cust_name", "fieldType": "varchar", "confidence": 0.95},
                    {"name": "phone", "field": "mobile", "fieldType": "varchar", "confidence": 0.72},
                ],
            }
        ],
        "relations": [
            {
                "name": "belongsTo",
                "source": "Order",
                "target": "Customer",
                "sourceField": "cust_id",
                "sourceTable": "dwd_order_main",
                "targetField": "id",
                "targetTable": "dwd_crm_customer",
                "confidence": 0.88,
            }
        ],
    }

    result = _merge_mapping_into_ontology(ontology, mapping)

    assert result["entities"][0]["table"] == "dwd_crm_customer"
    assert result["entities"][0]["confidence"] == 0.92
    assert result["entities"][0]["properties"][0]["field"] == "cust_name"
    assert result["entities"][0]["properties"][1]["field"] == "mobile"
    assert result["relations"][0]["sourceField"] == "cust_id"
    assert result["relations"][0]["targetTable"] == "dwd_crm_customer"
    assert result["relations"][0]["confidence"] == 0.88


def test_merge_mapping_missing_entity():
    from app.services.ontology_mapping_service import _merge_mapping_into_ontology
    import copy

    ontology = copy.deepcopy(SAMPLE_ONTOLOGY)
    mapping = {"entities": [], "relations": []}

    result = _merge_mapping_into_ontology(ontology, mapping)

    assert result["entities"][0]["table"] is None
    assert result["entities"][0]["confidence"] == 0
    assert result["entities"][0]["properties"][0]["field"] is None


@patch("app.services.ontology_mapping_service.get_all_tables_summary")
@patch("app.services.ontology_mapping_service._get_llm_client")
@patch("app.services.ontology_mapping_service.map_entities_and_relations")
def test_map_ontology_stream_success(mock_map, mock_client, mock_tables):
    from app.services.ontology_mapping_service import map_ontology_stream

    mock_tables.return_value = [
        {"table_name": "dwd_crm_customer", "table_desc": "客户主表"},
    ]

    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = json.dumps({
        "candidates": [{"entity": "Customer", "tables": ["dwd_crm_customer"]}]
    })
    mock_client.return_value.chat.completions.create.return_value = mock_resp

    mock_map.return_value = {
        "entities": [{"name": "Customer", "table": "dwd_crm_customer", "confidence": 0.9, "properties": []}],
        "relations": [],
    }

    events = list(map_ontology_stream(SAMPLE_ONTOLOGY))
    result_events = [e for e in events if "result" in e]
    assert len(result_events) == 1
    assert "dwd_crm_customer" in result_events[0]


@patch("app.services.ontology_mapping_service.get_all_tables_summary")
def test_map_ontology_stream_db_error(mock_tables):
    from app.services.ontology_mapping_service import map_ontology_stream

    mock_tables.side_effect = Exception("Connection refused")

    events = list(map_ontology_stream(SAMPLE_ONTOLOGY))
    error_events = [e for e in events if "error" in e]
    assert len(error_events) == 1
    assert "数据资产服务不可用" in error_events[0]
```

- [ ] **Step 2: 运行测试**

Run: `cd backend && python -m pytest tests/test_ontology_mapping.py -v`
Expected: 全部 PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_ontology_mapping.py
git commit -m "test(mapping): add unit tests for ontology mapping service"
```

---

## Task 8: 端到端验证

- [ ] **Step 1: 启动后端验证 API 可访问**

Run: `cd backend && timeout 5 python -c "import uvicorn; from app.main import app; print('App loaded OK')" || true`

- [ ] **Step 2: 用 curl 测试 SSE 端点可响应**

Run:
```bash
curl -s -X POST http://localhost:8001/api/v1/doc-builder/mapping \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test","ontology":{"entities":[{"name":"Test","displayName":"测试","properties":[]}],"relations":[]}}' \
  --max-time 30 | head -5
```
Expected: 收到 SSE 事件流（`data: {...}`）

- [ ] **Step 3: 启动前端验证编译通过**

Run: `cd frontend && npm run build 2>&1 | tail -10`
Expected: 编译成功无错误

- [ ] **Step 4: Commit（如有修复）**

```bash
git add -A
git commit -m "fix(mapping): address integration issues from e2e verification"
```
