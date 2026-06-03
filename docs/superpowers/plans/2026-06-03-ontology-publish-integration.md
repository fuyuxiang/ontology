# 本体发布与技能/流程联动 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 本体版本发布后自动检测结构性破坏变更，在受影响的流程（AipScene）和 Agent 上标记"依赖已过期"通知。

**Architecture:** 在现有 approve 端点中追加影响分析逻辑，通过 diff 新旧版本实体快照识别删除/改名，扫描下游引用并更新 stale 标记字段。新增 impact 预览端点和 acknowledge 端点。前端在列表和详情页展示告警。

**Tech Stack:** Python/FastAPI/SQLAlchemy (backend), Vue 3/TypeScript (frontend), pytest (tests)

---

## File Structure

**Backend - 新增/修改:**
- Modify: `backend/app/models/scene.py` — AipScene 增加 stale 字段
- Modify: `backend/app/models/agent.py` — Agent 增加 stale 字段
- Create: `backend/app/services/ontology_impact.py` — 影响分析核心逻辑
- Modify: `backend/app/api/v1/ontology_publish.py` — approve 端点追加调用 + impact 端点
- Modify: `backend/app/api/v1/aip_scenes.py` — acknowledge 端点
- Modify: `backend/app/api/v1/agents.py` — acknowledge 端点
- Create: `backend/tests/test_ontology_impact.py` — 影响分析测试

**Frontend - 修改:**
- Modify: `frontend/src/api/agents.ts` — 增加 acknowledge API
- Modify: `frontend/src/views/aip/` — 场景列表/详情增加告警展示
- Modify: `frontend/src/views/agents/` — Agent 列表/详情增加告警展示
- Modify: `frontend/src/views/ontology/OntologyPublishView.vue` — 增加影响预览按钮

---

### Task 1: 数据模型 — AipScene 增加 stale 字段

**Files:**
- Modify: `backend/app/models/scene.py:14-42`

- [ ] **Step 1: 添加字段到 AipScene 模型**

在 `AipScene` 类中，`published_version_id` 字段后添加：

```python
# 本体依赖追踪
ontology_version_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
ontology_stale: Mapped[bool] = mapped_column(Boolean, default=False)
ontology_stale_detail: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
```

- [ ] **Step 2: 生成数据库迁移**

```bash
cd backend
python -c "from app.database import engine, Base; from app.models.scene import AipScene; Base.metadata.create_all(engine)"
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/scene.py
git commit -m "feat(model): add ontology stale tracking fields to AipScene"
```

---

### Task 2: 数据模型 — Agent 增加 stale 字段

**Files:**
- Modify: `backend/app/models/agent.py:27-45`

- [ ] **Step 1: 添加字段到 Agent 模型**

在 `Agent` 类中，`entity_ids` 字段后添加：

```python
# 本体依赖追踪
ontology_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
ontology_stale: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
ontology_stale_detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
```

需要在文件顶部 import 中确保有 `Boolean`：
```python
from sqlalchemy import String, Text, JSON, DateTime, ForeignKey, Boolean
```

- [ ] **Step 2: 同步数据库**

```bash
cd backend
python -c "from app.database import engine, Base; from app.models.agent import Agent; Base.metadata.create_all(engine)"
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/agent.py
git commit -m "feat(model): add ontology stale tracking fields to Agent"
```

---

### Task 3: 核心逻辑 — 影响分析服务（测试先行）

**Files:**
- Create: `backend/tests/test_ontology_impact.py`
- Create: `backend/app/services/ontology_impact.py`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_ontology_impact.py
import pytest
from app.services.ontology_impact import compute_breaking_changes, find_affected_scenes, find_affected_agents


class TestComputeBreakingChanges:
    def test_deleted_entity(self):
        old_entities = [
            {"source_entity_id": "e1", "name": "Customer"},
            {"source_entity_id": "e2", "name": "Contract"},
        ]
        new_entities = [
            {"source_entity_id": "e1", "name": "Customer"},
        ]
        changes = compute_breaking_changes(old_entities, new_entities)
        assert len(changes) == 1
        assert changes[0]["entity_name"] == "Contract"
        assert changes[0]["change_type"] == "deleted"
        assert changes[0]["source_entity_id"] == "e2"

    def test_renamed_entity(self):
        old_entities = [
            {"source_entity_id": "e1", "name": "OldCustomer"},
        ]
        new_entities = [
            {"source_entity_id": "e1", "name": "Customer"},
        ]
        changes = compute_breaking_changes(old_entities, new_entities)
        assert len(changes) == 1
        assert changes[0]["change_type"] == "renamed"
        assert changes[0]["entity_name"] == "OldCustomer"
        assert changes[0]["new_name"] == "Customer"

    def test_no_changes(self):
        old_entities = [
            {"source_entity_id": "e1", "name": "Customer"},
        ]
        new_entities = [
            {"source_entity_id": "e1", "name": "Customer"},
        ]
        changes = compute_breaking_changes(old_entities, new_entities)
        assert changes == []

    def test_first_publish_no_old_version(self):
        changes = compute_breaking_changes([], [
            {"source_entity_id": "e1", "name": "Customer"},
        ])
        assert changes == []


class TestFindAffectedScenes:
    def test_scene_with_deleted_entity_binding(self):
        scenes = [
            {"id": "s1", "ontology_bindings": ["Customer", "Contract"]},
            {"id": "s2", "ontology_bindings": ["Order"]},
        ]
        changes = [{"entity_name": "Contract", "change_type": "deleted", "source_entity_id": "e2"}]
        affected = find_affected_scenes(scenes, changes)
        assert affected == ["s1"]

    def test_scene_with_renamed_entity_binding(self):
        scenes = [
            {"id": "s1", "ontology_bindings": ["OldCustomer"]},
        ]
        changes = [{"entity_name": "OldCustomer", "change_type": "renamed", "new_name": "Customer", "source_entity_id": "e1"}]
        affected = find_affected_scenes(scenes, changes)
        assert affected == ["s1"]

    def test_no_affected_scenes(self):
        scenes = [
            {"id": "s1", "ontology_bindings": ["Order"]},
        ]
        changes = [{"entity_name": "Contract", "change_type": "deleted", "source_entity_id": "e2"}]
        affected = find_affected_scenes(scenes, changes)
        assert affected == []


class TestFindAffectedAgents:
    def test_agent_with_deleted_entity_id(self):
        agents = [
            {"id": "a1", "entity_ids": ["e1", "e2"]},
            {"id": "a2", "entity_ids": ["e3"]},
        ]
        changes = [{"entity_name": "Contract", "change_type": "deleted", "source_entity_id": "e2"}]
        affected = find_affected_agents(agents, changes)
        assert affected == ["a1"]

    def test_agent_with_empty_entity_ids(self):
        agents = [
            {"id": "a1", "entity_ids": None},
            {"id": "a2", "entity_ids": []},
        ]
        changes = [{"entity_name": "Contract", "change_type": "deleted", "source_entity_id": "e2"}]
        affected = find_affected_agents(agents, changes)
        assert affected == []
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend && python -m pytest tests/test_ontology_impact.py -v
```

预期: FAIL — `ModuleNotFoundError: No module named 'app.services.ontology_impact'`

- [ ] **Step 3: 实现影响分析服务**

```python
# backend/app/services/ontology_impact.py
"""
本体发布影响分析 — 计算破坏性变更并标记受影响的下游对象
"""
from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.scene import AipScene
from app.models.agent import Agent
from app.models.version import OntologyVersion, OntologyVersionEntity


def compute_breaking_changes(
    old_entities: list[dict],
    new_entities: list[dict],
) -> list[dict]:
    if not old_entities:
        return []

    new_by_source = {e["source_entity_id"]: e["name"] for e in new_entities}
    changes = []

    for old in old_entities:
        sid = old["source_entity_id"]
        if sid not in new_by_source:
            changes.append({
                "entity_name": old["name"],
                "change_type": "deleted",
                "source_entity_id": sid,
            })
        elif new_by_source[sid] != old["name"]:
            changes.append({
                "entity_name": old["name"],
                "change_type": "renamed",
                "new_name": new_by_source[sid],
                "source_entity_id": sid,
            })

    return changes


def find_affected_scenes(
    scenes: list[dict],
    changes: list[dict],
) -> list[str]:
    affected_names = {c["entity_name"] for c in changes}
    result = []
    for scene in scenes:
        bindings = scene.get("ontology_bindings") or []
        if any(name in affected_names for name in bindings):
            result.append(scene["id"])
    return result


def find_affected_agents(
    agents: list[dict],
    changes: list[dict],
) -> list[str]:
    affected_ids = {c["source_entity_id"] for c in changes}
    result = []
    for agent in agents:
        entity_ids = agent.get("entity_ids") or []
        if any(eid in affected_ids for eid in entity_ids):
            result.append(agent["id"])
    return result


def mark_stale_dependents(
    old_version: OntologyVersion | None,
    new_version: OntologyVersion,
    db: Session,
) -> dict:
    old_entities = []
    if old_version:
        old_entities = [
            {"source_entity_id": ve.source_entity_id, "name": ve.name}
            for ve in old_version.entities
        ]

    new_entities = [
        {"source_entity_id": ve.source_entity_id, "name": ve.name}
        for ve in new_version.entities
    ]

    changes = compute_breaking_changes(old_entities, new_entities)
    if not changes:
        return {"breaking_changes": [], "affected_scenes": 0, "affected_agents": 0}

    stale_detail = {
        "version_id": new_version.id,
        "published_at": datetime.utcnow().isoformat(),
        "breaking_changes": changes,
    }

    scenes = db.query(AipScene).filter(AipScene.ontology_bindings.isnot(None)).all()
    scene_dicts = [{"id": s.id, "ontology_bindings": s.ontology_bindings} for s in scenes]
    affected_scene_ids = find_affected_scenes(scene_dicts, changes)

    if affected_scene_ids:
        db.query(AipScene).filter(AipScene.id.in_(affected_scene_ids)).update(
            {"ontology_stale": True, "ontology_stale_detail": stale_detail},
            synchronize_session="fetch",
        )

    agents = db.query(Agent).filter(Agent.entity_ids.isnot(None)).all()
    agent_dicts = [{"id": a.id, "entity_ids": a.entity_ids} for a in agents]
    affected_agent_ids = find_affected_agents(agent_dicts, changes)

    if affected_agent_ids:
        db.query(Agent).filter(Agent.id.in_(affected_agent_ids)).update(
            {"ontology_stale": True, "ontology_stale_detail": stale_detail},
            synchronize_session="fetch",
        )

    return {
        "breaking_changes": changes,
        "affected_scenes": len(affected_scene_ids),
        "affected_agents": len(affected_agent_ids),
    }
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd backend && python -m pytest tests/test_ontology_impact.py -v
```

预期: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ontology_impact.py backend/tests/test_ontology_impact.py
git commit -m "feat: add ontology impact analysis service with tests"
```

---

### Task 4: API — approve 端点集成影响分析

**Files:**
- Modify: `backend/app/api/v1/ontology_publish.py:265-288`

- [ ] **Step 1: 在 approve 端点中追加影响分析调用**

在 `approve_version` 函数中，`db.commit()` 之前添加影响分析逻辑：

```python
from app.services.ontology_impact import mark_stale_dependents

@router.post("/versions/{version_id}/approve")
def approve_version(version_id: str, db: Session = Depends(get_db), user: User | None = Depends(get_current_user)):
    v = _get_version(version_id, db)
    if v.status != "pending_approval":
        raise HTTPException(400, "只有待审批状态可以通过")

    # 获取当前活跃版本（即将被替换的旧版本）
    old_active = db.query(OntologyVersion).filter(
        OntologyVersion.is_active == True, OntologyVersion.id != v.id
    ).first()

    db.query(OntologyVersion).filter(OntologyVersion.is_active == True).update({"is_active": False})
    v.status = "published"
    v.is_active = True
    v.published_at = datetime.utcnow()
    v.approved_by = user.id if user else None

    published_entity_ids = [ve.source_entity_id for ve in v.entities]
    if published_entity_ids:
        db.query(OntologyEntity).filter(
            OntologyEntity.status == "published"
        ).update({"status": "active"})
        db.query(OntologyEntity).filter(
            OntologyEntity.id.in_(published_entity_ids)
        ).update({"status": "published"})

    # 影响分析：标记受影响的下游对象
    impact = mark_stale_dependents(old_active, v, db)

    db.commit()
    return {
        "message": f"版本 v{v.version_number} 已发布",
        "status": "published",
        "impact": impact,
    }
```

- [ ] **Step 2: 验证发布流程仍正常工作**

```bash
cd backend && python -m pytest tests/ -v -k "publish or impact"
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/v1/ontology_publish.py
git commit -m "feat: integrate impact analysis into ontology publish approve endpoint"
```

---

### Task 5: API — 新增 impact 预览端点

**Files:**
- Modify: `backend/app/api/v1/ontology_publish.py`

- [ ] **Step 1: 添加 impact 端点**

在 `consistency_check` 端点后添加：

```python
@router.get("/versions/{version_id}/impact")
def preview_impact(version_id: str, db: Session = Depends(get_db)):
    """预览某版本发布后的影响面（不执行实际标记）"""
    v = _get_version(version_id, db)

    old_active = db.query(OntologyVersion).filter(
        OntologyVersion.is_active == True, OntologyVersion.id != v.id
    ).first()

    old_entities = []
    if old_active:
        old_entities = [
            {"source_entity_id": ve.source_entity_id, "name": ve.name}
            for ve in old_active.entities
        ]

    new_entities = [
        {"source_entity_id": ve.source_entity_id, "name": ve.name}
        for ve in v.entities
    ]

    from app.services.ontology_impact import compute_breaking_changes, find_affected_scenes, find_affected_agents

    changes = compute_breaking_changes(old_entities, new_entities)
    if not changes:
        return {"breaking_changes": [], "affected_scenes": [], "affected_agents": []}

    scenes = db.query(AipScene).filter(AipScene.ontology_bindings.isnot(None)).all()
    scene_dicts = [{"id": s.id, "ontology_bindings": s.ontology_bindings, "name": s.name} for s in scenes]
    affected_scene_ids = find_affected_scenes(scene_dicts, changes)
    affected_scenes_info = [{"id": s.id, "name": s.name} for s in scenes if s.id in set(affected_scene_ids)]

    from app.models.agent import Agent
    agents = db.query(Agent).filter(Agent.entity_ids.isnot(None)).all()
    agent_dicts = [{"id": a.id, "entity_ids": a.entity_ids, "name": a.name} for a in agents]
    affected_agent_ids = find_affected_agents(agent_dicts, changes)
    affected_agents_info = [{"id": a.id, "name": a.name} for a in agents if a.id in set(affected_agent_ids)]

    return {
        "breaking_changes": changes,
        "affected_scenes": affected_scenes_info,
        "affected_agents": affected_agents_info,
    }
```

需在文件顶部追加 import：
```python
from app.models.scene import AipScene
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/v1/ontology_publish.py
git commit -m "feat: add impact preview endpoint for ontology publish"
```

---

### Task 6: API — 新增 acknowledge 端点

**Files:**
- Modify: `backend/app/api/v1/aip_scenes.py`
- Modify: `backend/app/api/v1/agents.py`

- [ ] **Step 1: 在 aip_scenes.py 添加 acknowledge 端点**

```python
@router.post("/{scene_id}/acknowledge-stale")
def acknowledge_stale(scene_id: str, db: Session = Depends(get_db)):
    scene = db.query(AipScene).filter(AipScene.id == scene_id).first()
    if not scene:
        raise HTTPException(404, "场景不存在")
    if not scene.ontology_stale:
        return {"message": "该场景没有过期标记"}

    active_version = db.query(OntologyVersion).filter(OntologyVersion.is_active == True).first()
    scene.ontology_stale = False
    scene.ontology_stale_detail = None
    scene.ontology_version_id = active_version.id if active_version else None
    db.commit()
    return {"message": "已确认，过期标记已清除"}
```

需在文件中追加 import：
```python
from app.models.version import OntologyVersion
```

- [ ] **Step 2: 在 agents.py 添加 acknowledge 端点**

```python
@router.post("/{agent_id}/acknowledge-stale")
def acknowledge_stale(agent_id: str, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(404, "Agent 不存在")
    if not agent.ontology_stale:
        return {"message": "该 Agent 没有过期标记"}

    from app.models.version import OntologyVersion
    active_version = db.query(OntologyVersion).filter(OntologyVersion.is_active == True).first()
    agent.ontology_stale = False
    agent.ontology_stale_detail = None
    agent.ontology_version_id = active_version.id if active_version else None
    db.commit()
    return {"message": "已确认，过期标记已清除"}
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/v1/aip_scenes.py backend/app/api/v1/agents.py
git commit -m "feat: add acknowledge-stale endpoints for scenes and agents"
```

---

### Task 7: 前端 — API 层增加 acknowledge 和 impact 调用

**Files:**
- Modify: `frontend/src/api/agents.ts`
- Create or modify: `frontend/src/api/aip.ts`

- [ ] **Step 1: agents.ts 增加 acknowledgeStale**

在 `agentsApi` 对象中添加：

```typescript
acknowledgeStale: (id: string) =>
  client.post(`/agents/${id}/acknowledge-stale`).then(r => r.data),
```

- [ ] **Step 2: aip.ts 增加 acknowledgeStale 和 previewImpact**

```typescript
export const sceneStaleApi = {
  acknowledgeStale: (sceneId: string) =>
    post(`/aip-scenes/${sceneId}/acknowledge-stale`),

  previewImpact: (versionId: string) =>
    get(`/ontology-publish/versions/${versionId}/impact`),
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/agents.ts frontend/src/api/aip.ts
git commit -m "feat(frontend): add stale acknowledge and impact preview API calls"
```

---

### Task 8: 前端 — 场景列表/详情增加告警展示

**Files:**
- 需根据实际场景列表组件路径修改（`frontend/src/views/aip/` 下相关 Vue 文件）

- [ ] **Step 1: 在场景列表项中展示 stale 徽标**

在场景列表的每个条目渲染中，添加条件渲染：

```vue
<span
  v-if="scene.ontology_stale"
  class="stale-badge"
  @click.stop="showStaleDetail(scene)"
>
  本体依赖已更新
</span>
```

样式：
```css
.stale-badge {
  display: inline-block;
  padding: 2px 8px;
  font-size: 12px;
  color: #d97706;
  background: #fef3c7;
  border-radius: 4px;
  cursor: pointer;
}
```

- [ ] **Step 2: 在场景详情页添加顶部横幅**

```vue
<div v-if="scene.ontology_stale" class="stale-banner">
  <span class="stale-banner__text">
    该场景依赖的本体实体已发生变更
  </span>
  <button class="btn-link" @click="showBreakingChanges = true">查看变更</button>
  <button class="btn-secondary btn-sm" @click="acknowledgeStale">确认已知</button>
</div>
```

`acknowledgeStale` 方法调用 `sceneStaleApi.acknowledgeStale(scene.id)` 并刷新页面数据。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/aip/
git commit -m "feat(frontend): show ontology stale warning in scene list and detail"
```

---

### Task 9: 前端 — Agent 列表/详情增加告警展示

**Files:**
- Modify: `frontend/src/views/agents/AgentDetailView.vue`
- Modify: Agent 列表组件

- [ ] **Step 1: Agent 列表添加 stale 徽标**

与 Task 8 相同模式，在 Agent 列表条目中：

```vue
<span v-if="agent.ontology_stale" class="stale-badge">
  本体依赖已更新
</span>
```

- [ ] **Step 2: Agent 详情页添加横幅**

```vue
<div v-if="agent.ontology_stale" class="stale-banner">
  <span class="stale-banner__text">
    该 Agent 依赖的本体实体已发生变更
  </span>
  <button class="btn-link" @click="showBreakingChanges = true">查看变更</button>
  <button class="btn-secondary btn-sm" @click="acknowledgeStale">确认已知</button>
</div>
```

`acknowledgeStale` 调用 `agentsApi.acknowledgeStale(agent.id)` 并刷新。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/agents/
git commit -m "feat(frontend): show ontology stale warning in agent list and detail"
```

---

### Task 10: 前端 — 发布页增加影响预览

**Files:**
- Modify: `frontend/src/views/ontology/OntologyPublishView.vue`

- [ ] **Step 1: 添加"预览影响"按钮**

在版本详情的操作区（提交审批按钮附近）添加：

```vue
<button
  v-if="detail && detail.status === 'draft'"
  class="btn-outline"
  @click="previewImpact"
>
  预览影响
</button>
```

- [ ] **Step 2: 实现预览弹窗**

```vue
<div v-if="showImpact" class="impact-dialog">
  <h3>发布影响预览</h3>
  <div v-if="!impactData.breaking_changes.length" class="impact-empty">
    无破坏性变更，可安全发布
  </div>
  <template v-else>
    <h4>破坏性变更 ({{ impactData.breaking_changes.length }})</h4>
    <ul>
      <li v-for="c in impactData.breaking_changes" :key="c.entity_name">
        <strong>{{ c.entity_name }}</strong> —
        <span v-if="c.change_type === 'deleted'">已删除</span>
        <span v-else>改名为 {{ c.new_name }}</span>
      </li>
    </ul>
    <h4>受影响的场景 ({{ impactData.affected_scenes.length }})</h4>
    <ul>
      <li v-for="s in impactData.affected_scenes" :key="s.id">{{ s.name }}</li>
    </ul>
    <h4>受影响的 Agent ({{ impactData.affected_agents.length }})</h4>
    <ul>
      <li v-for="a in impactData.affected_agents" :key="a.id">{{ a.name }}</li>
    </ul>
  </template>
  <button class="btn-secondary" @click="showImpact = false">关闭</button>
</div>
```

`previewImpact` 方法调用 `sceneStaleApi.previewImpact(detail.id)` 并将结果赋值给 `impactData`。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/ontology/OntologyPublishView.vue
git commit -m "feat(frontend): add impact preview to ontology publish page"
```

---

### Task 11: 端到端验证

- [ ] **Step 1: 启动后端验证 API 正常**

```bash
cd backend && python -m uvicorn app.main:app --reload --port 8000
```

手动验证：
1. 创建一个版本，添加实体，提交并审批发布
2. 创建第二个版本，移除一个实体，提交审批
3. 调用 `/ontology-publish/versions/{id}/impact` 确认返回受影响列表
4. 审批发布后检查对应 Scene/Agent 的 `ontology_stale` 已变为 true
5. 调用 acknowledge 端点确认标记被清除

- [ ] **Step 2: 启动前端验证 UI 正常**

```bash
cd frontend && npm run dev
```

检查：
1. 场景列表中 stale 场景有橙色徽标
2. 点击场景详情可看到横幅和"确认已知"按钮
3. 发布页"预览影响"按钮正常弹窗

- [ ] **Step 3: 最终 Commit**

```bash
git add -A
git commit -m "feat: complete ontology publish integration with stale tracking"
```
