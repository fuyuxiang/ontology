# Doc Builder Mapping Persist Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After document builder LLM mapping, persist results as ObjectBinding records so mapping management can see and manage them immediately.

**Architecture:** Add a new Step (映射确认) between the existing StepDocMapping and StepDocReview in DocBuilderView. Backend exposes two new endpoints: preview (resolves table→Asset, detects conflicts) and apply (creates ObjectBindings). Frontend adds Step3MappingPersist component with conflict resolution and asset registration UX.

**Tech Stack:** FastAPI (backend), Vue 3 + TypeScript (frontend), SQLAlchemy ORM, Ant Design Vue components

---

### Task 1: Backend — Add `find_table_by_name` to AssetRepository

**Files:**
- Modify: `backend/app/repositories/asset_repo.py:55-65`
- Test: `backend/tests/test_asset_repo_find_table.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_asset_repo_find_table.py
from unittest.mock import MagicMock
from app.repositories.asset_repo import AssetRepository


def test_find_table_by_name_returns_matching_asset(db_session):
    from app.models.asset import Asset
    asset = Asset(
        id="asset-1", name="客户表", kind="table",
        locator={"table": "dwd_customer_info"}, connection_id="conn-1",
    )
    db_session.add(asset)
    db_session.commit()

    repo = AssetRepository(db_session)
    result = repo.find_table_by_name("dwd_customer_info")
    assert result is not None
    assert result.id == "asset-1"


def test_find_table_by_name_returns_none_when_not_found(db_session):
    repo = AssetRepository(db_session)
    result = repo.find_table_by_name("nonexistent_table")
    assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_asset_repo_find_table.py -v`
Expected: FAIL — `AttributeError: 'AssetRepository' object has no attribute 'find_table_by_name'`

- [ ] **Step 3: Write minimal implementation**

Add to `backend/app/repositories/asset_repo.py` after `find_table_by_connection_table`:

```python
    def find_table_by_name(self, table_name: str) -> Asset | None:
        """按表名查 table 资产（不限 connection）。"""
        return (
            self.db.query(Asset)
            .filter(
                Asset.kind == "table",
                Asset.locator["table"].as_string() == table_name,
            )
            .first()
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_asset_repo_find_table.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/repositories/asset_repo.py backend/tests/test_asset_repo_find_table.py
git commit -m "feat: add find_table_by_name to AssetRepository"
```

---

### Task 2: Backend — Mapping Persist Service

**Files:**
- Create: `backend/app/services/doc_mapping_persist_service.py`
- Test: `backend/tests/test_doc_mapping_persist_service.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_doc_mapping_persist_service.py
from unittest.mock import patch, MagicMock
from app.services.doc_mapping_persist_service import preview_mappings, apply_mappings


def test_preview_finds_asset_and_no_conflict(db_session):
    from app.models.asset import Asset
    from app.models.entity import OntologyEntity
    asset = Asset(id="a1", name="客户表", kind="table", locator={"table": "dwd_customer"}, connection_id="c1")
    entity = OntologyEntity(id="e1", name="Customer", display_name="客户")
    db_session.add_all([asset, entity])
    db_session.commit()

    mapping_result = {
        "entities": [{
            "name": "Customer", "table": "dwd_customer", "confidence": 0.9,
            "properties": [{"name": "phone", "field": "mobile", "confidence": 0.85}]
        }]
    }
    result = preview_mappings(mapping_result, db_session)
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["asset_id"] == "a1"
    assert item["asset_registered"] is True
    assert item["conflict"] is None


def test_preview_detects_unregistered_asset(db_session):
    from app.models.entity import OntologyEntity
    entity = OntologyEntity(id="e1", name="Customer", display_name="客户")
    db_session.add(entity)
    db_session.commit()

    mapping_result = {
        "entities": [{"name": "Customer", "table": "dwd_missing", "confidence": 0.7, "properties": []}]
    }
    result = preview_mappings(mapping_result, db_session)
    assert result["items"][0]["asset_registered"] is False
    assert result["items"][0]["asset_id"] is None


def test_preview_detects_conflict(db_session):
    from app.models.asset import Asset
    from app.models.entity import OntologyEntity
    from app.models.object_binding import ObjectBinding
    asset = Asset(id="a1", name="客户表", kind="table", locator={"table": "dwd_customer"}, connection_id="c1")
    entity = OntologyEntity(id="e1", name="Customer", display_name="客户")
    binding = ObjectBinding(id="b1", object_type_id="e1", asset_id="a1", role="primary", field_mappings=[])
    db_session.add_all([asset, entity, binding])
    db_session.commit()

    mapping_result = {
        "entities": [{"name": "Customer", "table": "dwd_customer", "confidence": 0.9, "properties": []}]
    }
    result = preview_mappings(mapping_result, db_session)
    assert result["items"][0]["conflict"] is not None
    assert result["items"][0]["conflict"]["existing_binding_id"] == "b1"


def test_apply_creates_binding(db_session):
    from app.models.asset import Asset
    from app.models.entity import OntologyEntity, EntityAttribute
    asset = Asset(id="a1", name="客户表", kind="table", locator={"table": "dwd_customer"}, connection_id="c1")
    entity = OntologyEntity(id="e1", name="Customer", display_name="客户")
    attr = EntityAttribute(id="attr1", entity_id="e1", name="phone", display_name="电话", data_type="string")
    db_session.add_all([asset, entity, attr])
    db_session.commit()

    items = [{
        "entity_id": "e1",
        "asset_id": "a1",
        "conflict_action": None,
        "register_asset": False,
        "table_name": "dwd_customer",
        "field_mappings": [{"attribute_id": "attr1", "source_column": "mobile"}],
    }]
    result = apply_mappings(items, db_session)
    assert result["created"] == 1
    assert len(result["binding_ids"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_doc_mapping_persist_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.doc_mapping_persist_service'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/doc_mapping_persist_service.py
"""文档构建映射结果持久化服务 — preview + apply"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.entity import OntologyEntity, EntityAttribute
from app.models.object_binding import ObjectBinding
from app.repositories.asset_repo import AssetRepository
from app.repositories.object_binding_repo import ObjectBindingRepository
from app.services.data_plane.object_binding_service import ObjectBindingService


def preview_mappings(mapping_result: dict, db: Session) -> dict:
    asset_repo = AssetRepository(db)
    binding_repo = ObjectBindingRepository(db)
    items = []

    for entity_map in mapping_result.get("entities", []):
        entity_name = entity_map["name"]
        table_name = entity_map.get("table")
        confidence = entity_map.get("confidence", 0)

        entity = db.query(OntologyEntity).filter(OntologyEntity.name == entity_name).first()
        entity_id = entity.id if entity else None

        asset = asset_repo.find_table_by_name(table_name) if table_name else None
        asset_id = asset.id if asset else None
        asset_registered = asset is not None

        conflict = None
        if entity_id and asset_id:
            existing = binding_repo.find_existing(entity_id, asset_id, "primary")
            if existing:
                conflict = {
                    "existing_binding_id": existing.id,
                    "existing_asset_name": asset.name if asset else None,
                }

        field_mappings = []
        for prop in entity_map.get("properties", []):
            attr = None
            if entity_id:
                attr = db.query(EntityAttribute).filter(
                    EntityAttribute.entity_id == entity_id,
                    EntityAttribute.name == prop["name"],
                ).first()
            field_mappings.append({
                "attribute_name": prop["name"],
                "attribute_id": attr.id if attr else None,
                "source_column": prop.get("field"),
                "confidence": prop.get("confidence", 0),
            })

        items.append({
            "entity_name": entity_name,
            "entity_id": entity_id,
            "table_name": table_name,
            "asset_id": asset_id,
            "asset_registered": asset_registered,
            "confidence": confidence,
            "conflict": conflict,
            "field_mappings": field_mappings,
        })

    return {"items": items}


def apply_mappings(items: list[dict], db: Session) -> dict:
    binding_svc = ObjectBindingService(db)
    created = 0
    updated = 0
    skipped = 0
    binding_ids = []

    for item in items:
        entity_id = item["entity_id"]
        asset_id = item.get("asset_id")
        conflict_action = item.get("conflict_action")
        register_asset = item.get("register_asset", False)
        table_name = item.get("table_name")
        field_mappings = item.get("field_mappings", [])

        if not entity_id:
            skipped += 1
            continue

        if register_asset and not asset_id:
            asset_id = _register_asset(table_name, db)

        if not asset_id:
            skipped += 1
            continue

        existing = ObjectBindingRepository(db).find_existing(entity_id, asset_id, "primary")
        if existing:
            if conflict_action == "overwrite":
                binding_svc.update(existing.id, field_mappings=field_mappings)
                updated += 1
                binding_ids.append(existing.id)
            else:
                skipped += 1
            continue

        binding = binding_svc.create(
            object_type_id=entity_id,
            asset_id=asset_id,
            role="primary",
            field_mappings=field_mappings,
        )
        created += 1
        binding_ids.append(binding.id)

    return {"created": created, "updated": updated, "skipped": skipped, "binding_ids": binding_ids}


def _register_asset(table_name: str, db: Session) -> str | None:
    if not table_name:
        return None
    from app.services.data_plane.asset_service import AssetService
    svc = AssetService(db)
    asset = svc.create(
        name=table_name,
        kind="table",
        locator={"table": table_name},
        connection_id=_get_dwd_connection_id(db),
    )
    return asset.id


def _get_dwd_connection_id(db: Session) -> str | None:
    from app.models import DataSource
    ds = db.query(DataSource).filter(
        DataSource.enabled == True,
        DataSource.database == "dwd",
    ).first()
    if ds:
        from app.models.data_plane import Connection
        conn = db.query(Connection).filter(Connection.legacy_datasource_id == ds.id).first()
        return conn.id if conn else None
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_doc_mapping_persist_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/doc_mapping_persist_service.py backend/tests/test_doc_mapping_persist_service.py
git commit -m "feat: add doc mapping persist service (preview + apply)"
```

---

### Task 3: Backend — API Endpoints for Preview and Apply

**Files:**
- Modify: `backend/app/api/v1/doc_builder.py`
- Test: `backend/tests/test_doc_builder_api_mapping.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_doc_builder_api_mapping.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_mapping_preview_endpoint(db_session, mocker):
    mocker.patch(
        "app.services.doc_mapping_persist_service.preview_mappings",
        return_value={"items": [{"entity_name": "Customer", "asset_id": "a1", "asset_registered": True, "conflict": None}]},
    )
    resp = client.post("/api/v1/doc-builder/mapping/preview", json={
        "session_id": "s1",
        "mapping_result": {"entities": [{"name": "Customer", "table": "dwd_customer", "confidence": 0.9, "properties": []}]},
    })
    assert resp.status_code == 200
    assert resp.json()["items"][0]["entity_name"] == "Customer"


def test_mapping_apply_endpoint(db_session, mocker):
    mocker.patch(
        "app.services.doc_mapping_persist_service.apply_mappings",
        return_value={"created": 1, "updated": 0, "skipped": 0, "binding_ids": ["b1"]},
    )
    resp = client.post("/api/v1/doc-builder/mapping/apply", json={
        "session_id": "s1",
        "items": [{"entity_id": "e1", "asset_id": "a1", "conflict_action": None, "register_asset": False, "table_name": "dwd_customer", "field_mappings": []}],
    })
    assert resp.status_code == 200
    assert resp.json()["created"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_doc_builder_api_mapping.py -v`
Expected: FAIL — 404 (endpoints don't exist)

- [ ] **Step 3: Write minimal implementation**

Add to `backend/app/api/v1/doc_builder.py`:

```python
from app.database import get_db
from fastapi import Depends
from sqlalchemy.orm import Session
from app.services import doc_mapping_persist_service


class MappingPreviewRequest(BaseModel):
    session_id: str
    mapping_result: dict


class MappingApplyItem(BaseModel):
    entity_id: str | None = None
    asset_id: str | None = None
    conflict_action: str | None = None
    register_asset: bool = False
    table_name: str | None = None
    field_mappings: list[dict] = []


class MappingApplyRequest(BaseModel):
    session_id: str
    items: list[MappingApplyItem]


@router.post("/mapping/preview")
async def mapping_preview(req: MappingPreviewRequest, db: Session = Depends(get_db)):
    return doc_mapping_persist_service.preview_mappings(req.mapping_result, db)


@router.post("/mapping/apply")
async def mapping_apply(req: MappingApplyRequest, db: Session = Depends(get_db)):
    return doc_mapping_persist_service.apply_mappings(
        [item.model_dump() for item in req.items], db
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_doc_builder_api_mapping.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/doc_builder.py backend/tests/test_doc_builder_api_mapping.py
git commit -m "feat: add /doc-builder/mapping/preview and /apply endpoints"
```

---

### Task 4: Frontend — API Client Functions

**Files:**
- Modify: `frontend/src/api/docBuilder.ts`

- [ ] **Step 1: Add type definitions and API functions**

Append to `frontend/src/api/docBuilder.ts`:

```typescript
import { post } from './client'

export interface MappingPreviewItem {
  entity_name: string
  entity_id: string | null
  table_name: string | null
  asset_id: string | null
  asset_registered: boolean
  confidence: number
  conflict: { existing_binding_id: string; existing_asset_name: string } | null
  field_mappings: Array<{
    attribute_name: string
    attribute_id: string | null
    source_column: string | null
    confidence: number
  }>
}

export interface MappingPreviewResponse {
  items: MappingPreviewItem[]
}

export interface MappingApplyItem {
  entity_id: string | null
  asset_id: string | null
  conflict_action: 'overwrite' | 'keep' | null
  register_asset: boolean
  table_name: string | null
  field_mappings: Array<{ attribute_id: string; source_column: string | null }>
}

export interface MappingApplyResponse {
  created: number
  updated: number
  skipped: number
  binding_ids: string[]
}

export function previewMappingPersist(sessionId: string, mappingResult: any): Promise<{ data: MappingPreviewResponse }> {
  return post('/doc-builder/mapping/preview', { session_id: sessionId, mapping_result: mappingResult })
}

export function applyMappingPersist(sessionId: string, items: MappingApplyItem[]): Promise<{ data: MappingApplyResponse }> {
  return post('/doc-builder/mapping/apply', { session_id: sessionId, items })
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit src/api/docBuilder.ts`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/docBuilder.ts
git commit -m "feat: add mapping persist API client functions"
```

---

### Task 5: Frontend — Step3MappingPersist Component

**Files:**
- Create: `frontend/src/views/builder/components/doc/StepDocMappingPersist.vue`

- [ ] **Step 1: Create the component**

```vue
<template>
  <div class="step-persist">
    <h2 class="step-persist__title">映射确认</h2>
    <p class="step-persist__sub">确认本体与数据资产的映射关系，落库后可在映射管理中查看和修改</p>

    <div v-if="loading" class="step-persist__loading">
      <a-spin tip="正在解析映射..." />
    </div>

    <template v-else>
      <div class="step-persist__stats">
        <span class="step-persist__stat">已匹配 <strong>{{ registeredCount }}</strong> / {{ items.length }} 实体</span>
        <span v-if="conflictCount" class="step-persist__stat step-persist__stat--warn">冲突 {{ conflictCount }}</span>
        <span v-if="unregisteredCount" class="step-persist__stat step-persist__stat--err">未注册 {{ unregisteredCount }}</span>
      </div>

      <div class="step-persist__body">
        <aside class="step-persist__sidebar">
          <div
            v-for="(item, idx) in items" :key="idx"
            class="step-persist__entity"
            :class="{
              'step-persist__entity--active': selectedIdx === idx,
              'step-persist__entity--conflict': item.conflict,
              'step-persist__entity--unregistered': !item.asset_registered,
            }"
            @click="selectedIdx = idx"
          >
            <span class="step-persist__entity-icon">
              {{ item.conflict ? '⚠' : !item.asset_registered ? '✗' : '✓' }}
            </span>
            <span class="step-persist__entity-name">{{ item.entity_name }}</span>
            <span class="step-persist__entity-conf">{{ Math.round(item.confidence * 100) }}%</span>
          </div>
        </aside>

        <div class="step-persist__main">
          <template v-if="selected">
            <div class="step-persist__detail-header">
              <h3>{{ selected.entity_name }}</h3>
              <code>{{ selected.table_name || '无匹配表' }}</code>
            </div>

            <div v-if="!selected.asset_registered" class="step-persist__alert step-persist__alert--warn">
              <span>该表未注册为数据资产</span>
              <a-button size="small" type="primary" :loading="registering" @click="registerAsset(selectedIdx)">
                一键注册
              </a-button>
              <a-button size="small" @click="skipItem(selectedIdx)">跳过</a-button>
            </div>

            <div v-if="selected.conflict" class="step-persist__alert step-persist__alert--conflict">
              <span>已存在绑定（{{ selected.conflict.existing_asset_name }}）</span>
              <a-radio-group v-model:value="conflictActions[selectedIdx]" size="small">
                <a-radio-button value="overwrite">覆盖</a-radio-button>
                <a-radio-button value="keep">保留旧的</a-radio-button>
              </a-radio-group>
            </div>

            <a-table
              :columns="fieldColumns"
              :data-source="selected.field_mappings"
              :pagination="false"
              size="small"
              row-key="attribute_name"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'source_column'">
                  <span v-if="record.source_column">{{ record.source_column }}</span>
                  <span v-else class="step-persist__unmapped">未映射</span>
                </template>
                <template v-if="column.key === 'confidence'">
                  <span :class="confClass(record.confidence)">
                    {{ record.source_column ? Math.round(record.confidence * 100) + '%' : '-' }}
                  </span>
                </template>
              </template>
            </a-table>
          </template>
        </div>
      </div>

      <div class="step-persist__actions">
        <a-button @click="emit('prev')">上一步</a-button>
        <a-button type="primary" :loading="applying" @click="doApply">确认映射并落库</a-button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { message } from 'ant-design-vue'
import {
  previewMappingPersist,
  applyMappingPersist,
  type MappingPreviewItem,
  type MappingApplyItem,
} from '../../../../api/docBuilder'

const props = defineProps<{
  sessionId: string
  mappingResult: any
}>()

const emit = defineEmits<{
  (e: 'prev'): void
  (e: 'next'): void
}>()

const loading = ref(true)
const applying = ref(false)
const registering = ref(false)
const items = ref<MappingPreviewItem[]>([])
const selectedIdx = ref(0)
const conflictActions = reactive<Record<number, string>>({})
const skippedIndices = ref<Set<number>>(new Set())

const selected = computed(() => items.value[selectedIdx.value] || null)
const registeredCount = computed(() => items.value.filter(i => i.asset_registered).length)
const conflictCount = computed(() => items.value.filter(i => i.conflict).length)
const unregisteredCount = computed(() => items.value.filter(i => !i.asset_registered).length)

const fieldColumns = [
  { title: '属性', dataIndex: 'attribute_name', key: 'attribute_name' },
  { title: '映射字段', dataIndex: 'source_column', key: 'source_column' },
  { title: '置信度', dataIndex: 'confidence', key: 'confidence', width: 80 },
]

function confClass(c: number) {
  if (c >= 0.8) return 'step-persist__conf--high'
  if (c >= 0.5) return 'step-persist__conf--mid'
  return 'step-persist__conf--low'
}

async function loadPreview() {
  loading.value = true
  try {
    const { data } = await previewMappingPersist(props.sessionId, props.mappingResult)
    items.value = data.items
    items.value.forEach((item, idx) => {
      if (item.conflict) conflictActions[idx] = 'overwrite'
    })
  } catch (e: any) {
    message.error('加载映射预览失败: ' + (e.message || '未知错误'))
  }
  loading.value = false
}

async function registerAsset(idx: number) {
  registering.value = true
  const item = items.value[idx]
  try {
    const applyItems: MappingApplyItem[] = [{
      entity_id: item.entity_id,
      asset_id: null,
      conflict_action: null,
      register_asset: true,
      table_name: item.table_name,
      field_mappings: [],
    }]
    await applyMappingPersist(props.sessionId, applyItems)
    await loadPreview()
    message.success(`已注册资产: ${item.table_name}`)
  } catch (e: any) {
    message.error('注册失败: ' + (e.message || ''))
  }
  registering.value = false
}

function skipItem(idx: number) {
  skippedIndices.value.add(idx)
}

async function doApply() {
  applying.value = true
  try {
    const applyItems: MappingApplyItem[] = items.value
      .map((item, idx) => {
        if (skippedIndices.value.has(idx)) return null
        if (!item.asset_id) return null
        return {
          entity_id: item.entity_id,
          asset_id: item.asset_id,
          conflict_action: item.conflict ? (conflictActions[idx] || 'keep') : null,
          register_asset: false,
          table_name: item.table_name,
          field_mappings: item.field_mappings
            .filter(fm => fm.attribute_id)
            .map(fm => ({ attribute_id: fm.attribute_id!, source_column: fm.source_column })),
        } as MappingApplyItem
      })
      .filter(Boolean) as MappingApplyItem[]

    const { data } = await applyMappingPersist(props.sessionId, applyItems)
    message.success(`映射落库完成: 创建 ${data.created}, 更新 ${data.updated}, 跳过 ${data.skipped}`)
    emit('next')
  } catch (e: any) {
    message.error('落库失败: ' + (e.message || ''))
  }
  applying.value = false
}

onMounted(loadPreview)
</script>

<style scoped>
.step-persist { padding: 24px; max-width: 1100px; margin: 0 auto; }
.step-persist__title { font-size: 18px; font-weight: 600; margin-bottom: 4px; }
.step-persist__sub { color: #666; font-size: 13px; margin-bottom: 16px; }
.step-persist__loading { text-align: center; padding: 60px 0; }
.step-persist__stats { display: flex; gap: 16px; margin-bottom: 16px; font-size: 13px; }
.step-persist__stat--warn { color: #f57c00; }
.step-persist__stat--err { color: #d32f2f; }
.step-persist__body { display: flex; gap: 16px; min-height: 400px; }
.step-persist__sidebar { width: 240px; border: 1px solid #e0e0e0; border-radius: 6px; overflow-y: auto; }
.step-persist__entity { display: flex; align-items: center; gap: 6px; padding: 10px 12px; cursor: pointer; font-size: 13px; border-bottom: 1px solid #f0f0f0; }
.step-persist__entity:hover { background: #f5f5f5; }
.step-persist__entity--active { background: #e3f2fd; }
.step-persist__entity--conflict { border-left: 3px solid #f57c00; }
.step-persist__entity--unregistered { border-left: 3px solid #d32f2f; }
.step-persist__entity-icon { width: 16px; text-align: center; }
.step-persist__entity-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.step-persist__entity-conf { color: #999; font-size: 11px; }
.step-persist__main { flex: 1; border: 1px solid #e0e0e0; border-radius: 6px; padding: 16px; }
.step-persist__detail-header { margin-bottom: 12px; }
.step-persist__detail-header h3 { margin: 0 0 4px; font-size: 15px; }
.step-persist__alert { display: flex; align-items: center; gap: 12px; padding: 8px 12px; border-radius: 4px; margin-bottom: 12px; font-size: 13px; }
.step-persist__alert--warn { background: #fff3e0; }
.step-persist__alert--conflict { background: #e3f2fd; }
.step-persist__unmapped { color: #999; font-style: italic; }
.step-persist__conf--high { color: #2e7d32; font-weight: 600; }
.step-persist__conf--mid { color: #f57c00; }
.step-persist__conf--low { color: #999; }
.step-persist__actions { display: flex; justify-content: space-between; margin-top: 20px; }
</style>
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx vue-tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/builder/components/doc/StepDocMappingPersist.vue
git commit -m "feat: add StepDocMappingPersist component"
```

---

### Task 6: Frontend — Wire Step into DocBuilderView

**Files:**
- Modify: `frontend/src/views/builder/DocBuilderView.vue`

- [ ] **Step 1: Update DocBuilderView to include new step**

Replace the full content of `DocBuilderView.vue`:

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
      <StepDocMappingPersist v-else-if="step === 3" :session-id="sessionId" :mapping-result="mappedResult!" @prev="step = 2" @next="onPersistDone" />
      <StepDocReview v-else-if="step === 4" :result="mappedResult!" @prev="step = 3" @confirm="onConfirm" />
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
import StepDocMappingPersist from './components/doc/StepDocMappingPersist.vue'
import StepDocReview from './components/doc/StepDocReview.vue'

const router = useRouter()
const store = useBuilderStore()

const steps = ['需求与文档', 'AI对话抽取', '资产映射', '映射确认', '确认入库']
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

function onPersistDone() {
  step.value = 4
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

- [ ] **Step 2: Verify frontend compiles**

Run: `cd frontend && npx vue-tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/builder/DocBuilderView.vue
git commit -m "feat: wire StepDocMappingPersist into DocBuilder flow (4→5 steps)"
```

---

### Task 7: Integration Test — Full Flow

**Files:**
- Test: `backend/tests/test_doc_mapping_persist_integration.py`

- [ ] **Step 1: Write integration test**

```python
# backend/tests/test_doc_mapping_persist_integration.py
"""End-to-end: preview → apply → verify ObjectBinding created."""
from fastapi.testclient import TestClient
from app.main import app
from app.models.asset import Asset
from app.models.entity import OntologyEntity, EntityAttribute
from app.models.object_binding import ObjectBinding

client = TestClient(app)


def test_full_flow_preview_then_apply(db_session):
    asset = Asset(id="a1", name="客户表", kind="table", locator={"table": "dwd_customer"}, connection_id="c1")
    entity = OntologyEntity(id="e1", name="Customer", display_name="客户")
    attr = EntityAttribute(id="attr1", entity_id="e1", name="phone", display_name="电话", data_type="string")
    db_session.add_all([asset, entity, attr])
    db_session.commit()

    preview_resp = client.post("/api/v1/doc-builder/mapping/preview", json={
        "session_id": "test-session",
        "mapping_result": {
            "entities": [{"name": "Customer", "table": "dwd_customer", "confidence": 0.9,
                          "properties": [{"name": "phone", "field": "mobile", "confidence": 0.85}]}]
        },
    })
    assert preview_resp.status_code == 200
    items = preview_resp.json()["items"]
    assert items[0]["asset_registered"] is True
    assert items[0]["field_mappings"][0]["attribute_id"] == "attr1"

    apply_resp = client.post("/api/v1/doc-builder/mapping/apply", json={
        "session_id": "test-session",
        "items": [{
            "entity_id": "e1", "asset_id": "a1", "conflict_action": None,
            "register_asset": False, "table_name": "dwd_customer",
            "field_mappings": [{"attribute_id": "attr1", "source_column": "mobile"}],
        }],
    })
    assert apply_resp.status_code == 200
    assert apply_resp.json()["created"] == 1

    binding = db_session.query(ObjectBinding).filter_by(object_type_id="e1", asset_id="a1").first()
    assert binding is not None
    assert binding.field_mappings[0]["source_column"] == "mobile"
```

- [ ] **Step 2: Run test**

Run: `cd backend && python -m pytest tests/test_doc_mapping_persist_integration.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_doc_mapping_persist_integration.py
git commit -m "test: add integration test for doc mapping persist flow"
```
