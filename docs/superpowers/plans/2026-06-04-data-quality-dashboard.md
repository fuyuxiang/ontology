# 数据质量仪表盘 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the existing configuration-heavy data quality page with a pure-display dashboard showing overall health score, per-entity scorecards, quality trends, and recent anomaly events — with quality rules auto-mounted when assets are bound to entities.

**Architecture:** Add auto-rule-mounting logic to ObjectBindingService, create a new dashboard aggregation API endpoint, then rewrite the frontend DataQualityPage as a polished read-only dashboard with ring chart, entity scorecards, trend chart (ECharts), and anomaly timeline.

**Tech Stack:** FastAPI + SQLAlchemy (backend), Vue 3 + TypeScript + ECharts (frontend)

---

### Task 1: Auto-Mount Quality Rules on Binding Creation

**Files:**
- Modify: `backend/app/services/data_plane/object_binding_service.py`
- Create: `backend/tests/test_quality_auto_mount.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_quality_auto_mount.py
"""Test: binding creation auto-mounts quality rules."""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from app.services.data_plane.object_binding_service import ObjectBindingService


def _make_entity_with_attrs(attrs):
    entity = MagicMock()
    entity.id = "entity-001"
    entity.name = "TestEntity"
    entity.attributes = []
    entity.schema_json = {"primary_key": "user_id"}
    for a in attrs:
        attr = MagicMock()
        attr.name = a["name"]
        attr.required = a.get("required", False)
        attr.constraints_json = a.get("constraints_json")
        entity.attributes.append(attr)
    return entity


def test_auto_mount_creates_rules_for_required_attrs():
    """Required attributes get null_ratio_max rules."""
    db = MagicMock()
    entity = _make_entity_with_attrs([
        {"name": "email", "required": True},
        {"name": "nickname", "required": False},
    ])
    db.get.return_value = entity

    # Mock QualityRuleService
    with patch("app.services.data_plane.object_binding_service.QualityRuleService") as MockSvc:
        mock_svc = MockSvc.return_value
        mock_svc.list_rules.return_value = []

        from app.services.data_plane.object_binding_service import _auto_mount_quality_rules
        _auto_mount_quality_rules(db, "asset-001", "entity-001")

        # Should create: row_count_min + freshness + null_ratio(email) + pk_uniqueness(user_id)
        calls = mock_svc.create_rule.call_args_list
        kinds = [c.kwargs.get("kind") or c[1].get("kind") for c in calls]
        assert "row_count_min" in kinds
        assert "freshness" in kinds
        assert "null_ratio_max" in kinds
        assert "pk_uniqueness" in kinds


def test_auto_mount_skips_existing_rules():
    """If rules already exist for this asset, don't duplicate."""
    db = MagicMock()
    entity = _make_entity_with_attrs([{"name": "email", "required": True}])
    entity.schema_json = {"primary_key": "user_id"}
    db.get.return_value = entity

    with patch("app.services.data_plane.object_binding_service.QualityRuleService") as MockSvc:
        mock_svc = MockSvc.return_value
        # Simulate existing rule
        existing = MagicMock()
        existing.kind = "row_count_min"
        existing.column_name = None
        mock_svc.list_rules.return_value = [existing]

        from app.services.data_plane.object_binding_service import _auto_mount_quality_rules
        _auto_mount_quality_rules(db, "asset-001", "entity-001")

        # row_count_min should NOT be created again
        calls = mock_svc.create_rule.call_args_list
        kinds = [c.kwargs.get("kind") or c[1].get("kind") for c in calls]
        assert "row_count_min" not in kinds
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/fuyuxiang/Documents/100-主业/130-东方国信/13.代码仓库/ontology/backend && python -m pytest tests/test_quality_auto_mount.py -v`
Expected: ImportError (`_auto_mount_quality_rules` doesn't exist)

- [ ] **Step 3: Implement auto-mount function**

Add to end of `backend/app/services/data_plane/object_binding_service.py`:

```python
def _auto_mount_quality_rules(db: Session, asset_id: str, object_type_id: str) -> None:
    """Auto-mount quality rules based on entity attributes when a binding is created."""
    from app.models.entity import OntologyEntity
    from app.services.data_plane.quality_rule_service import QualityRuleService

    entity = db.get(OntologyEntity, object_type_id)
    if not entity:
        return

    svc = QualityRuleService(db)
    existing = svc.list_rules(asset_id)
    existing_keys = {(r.kind, r.column_name) for r in existing}

    pk = (entity.schema_json or {}).get("primary_key", "")

    rules_to_create = []

    # Universal: row_count_min
    if ("row_count_min", None) not in existing_keys:
        rules_to_create.append({"name": "行数非空", "kind": "row_count_min", "column_name": None, "severity": "failure"})

    # Universal: freshness (use pk column as proxy)
    if ("freshness", pk) not in existing_keys and pk:
        rules_to_create.append({"name": f"{pk} 新鲜度", "kind": "freshness", "column_name": pk, "severity": "warning"})

    # PK uniqueness
    if pk and ("pk_uniqueness", pk) not in existing_keys:
        rules_to_create.append({"name": f"{pk} 唯一性", "kind": "pk_uniqueness", "column_name": pk, "severity": "failure"})

    # Required attributes → null_ratio_max
    for attr in entity.attributes:
        if attr.required and ("null_ratio_max", attr.name) not in existing_keys:
            rules_to_create.append({
                "name": f"{attr.name} 非空",
                "kind": "null_ratio_max",
                "column_name": attr.name,
                "severity": "warning",
            })

    for r in rules_to_create:
        try:
            svc.create_rule(asset_id=asset_id, **r)
        except Exception as e:
            logger.warning("Auto-mount rule failed: %s — %s", r, e)
```

- [ ] **Step 4: Call auto-mount from `create` method**

In the `create` method of `ObjectBindingService`, add after `self.db.commit()` and before `self.bus.emit(...)`:

```python
        # Auto-mount quality rules
        try:
            _auto_mount_quality_rules(self.db, asset_id, object_type_id)
        except Exception as e:
            logger.warning("Auto-mount quality rules failed: %s", e)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/fuyuxiang/Documents/100-主业/130-东方国信/13.代码仓库/ontology/backend && python -m pytest tests/test_quality_auto_mount.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/fuyuxiang/Documents/100-主业/130-东方国信/13.代码仓库/ontology && git add backend/app/services/data_plane/object_binding_service.py backend/tests/test_quality_auto_mount.py && git commit -m "feat: auto-mount quality rules when asset is bound to entity

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Dashboard Aggregation API

**Files:**
- Modify: `backend/app/api/v1/data_plane/quality.py`
- Create: `backend/tests/test_quality_dashboard_api.py`

- [ ] **Step 1: Write the test**

```python
# backend/tests/test_quality_dashboard_api.py
"""Test dashboard aggregation logic."""
from unittest.mock import MagicMock, patch
from app.api.v1.data_plane.quality import _build_dashboard_data


def test_dashboard_calculates_overall_score():
    """Score = pass_count / total_count * 100"""
    db = MagicMock()

    # Mock: 2 entities, each with some rules
    with patch("app.api.v1.data_plane.quality._get_entity_quality_data") as mock_get:
        mock_get.side_effect = [
            {"entity_id": "e1", "entity_name": "User", "score": 80, "rule_count": 5, "pass_count": 4,
             "dimensions": {"null_ratio": "healthy", "pk_uniqueness": "healthy", "freshness": "warning", "row_count": "healthy", "schema": "unknown"}},
            {"entity_id": "e2", "entity_name": "Order", "score": 100, "rule_count": 3, "pass_count": 3,
             "dimensions": {"null_ratio": "healthy", "pk_uniqueness": "healthy", "freshness": "healthy", "row_count": "healthy", "schema": "unknown"}},
        ]

        result = _build_dashboard_data(db, ["e1", "e2"])

    assert result["overall_score"] == 88  # (4+3)/(5+3)*100 = 87.5 → 88
    assert result["summary"]["healthy"] >= 1
    assert len(result["entities"]) == 2


def test_dashboard_empty_when_no_entities():
    db = MagicMock()
    result = _build_dashboard_data(db, [])
    assert result["overall_score"] == 100
    assert result["entities"] == []
    assert result["recent_issues"] == []
```

- [ ] **Step 2: Implement dashboard endpoint**

Add to `backend/app/api/v1/data_plane/quality.py`:

```python
from app.models.object_binding import ObjectBinding


class DashboardEntity(BaseModel):
    entity_id: str
    entity_name: str
    score: int
    dimensions: dict
    rule_count: int
    pass_count: int


class DashboardTrend(BaseModel):
    date: str
    score: int
    warnings: int
    failures: int


class DashboardIssue(BaseModel):
    id: str
    entity_name: str
    asset_name: str
    rule_kind: str
    column_name: str | None
    severity: str
    value: float | None
    threshold: float | None
    message: str
    occurred_at: datetime


class DashboardResponse(BaseModel):
    overall_score: int
    summary: dict
    entities: list[DashboardEntity]
    trend: list[DashboardTrend]
    recent_issues: list[DashboardIssue]


def _get_entity_quality_data(db: Session, entity_id: str, svc: QualityRuleService) -> dict:
    """Aggregate quality data for one entity across all its bound assets."""
    from app.models.entity import OntologyEntity
    entity = db.get(OntologyEntity, entity_id)
    if not entity:
        return None

    bindings = db.query(ObjectBinding).filter(
        ObjectBinding.object_type_id == entity_id,
        ObjectBinding.status == "active",
    ).all()

    if not bindings:
        return None

    total_rules = 0
    pass_rules = 0
    dim_status = {"null_ratio": "unknown", "pk_uniqueness": "unknown", "freshness": "unknown", "row_count": "unknown", "schema": "unknown"}
    dim_map = {"null_ratio_max": "null_ratio", "pk_uniqueness": "pk_uniqueness", "freshness": "freshness", "row_count_min": "row_count", "row_count_max": "row_count", "schema_stable": "schema"}

    for b in bindings:
        rules = svc.list_rules(b.asset_id)
        for r in rules:
            if not r.enabled:
                continue
            total_rules += 1
            st = svc.latest_status(r.id)
            status = st.status if st else "unknown"
            if status == "healthy":
                pass_rules += 1
            dim_key = dim_map.get(r.kind)
            if dim_key:
                if STATUS_RANK.get(status, 0) > STATUS_RANK.get(dim_status[dim_key], 0):
                    dim_status[dim_key] = status

    score = round(pass_rules / total_rules * 100) if total_rules > 0 else 100
    return {
        "entity_id": entity_id,
        "entity_name": entity.name,
        "score": score,
        "dimensions": dim_status,
        "rule_count": total_rules,
        "pass_count": pass_rules,
    }


def _build_dashboard_data(db: Session, entity_ids: list[str]) -> dict:
    svc = QualityRuleService(db)
    entities = []
    total_rules = 0
    total_pass = 0
    summary = {"healthy": 0, "warning": 0, "failure": 0, "unknown": 0}

    for eid in entity_ids:
        data = _get_entity_quality_data(db, eid, svc)
        if not data:
            continue
        entities.append(data)
        total_rules += data["rule_count"]
        total_pass += data["pass_count"]
        # Count entity-level status
        worst = max(data["dimensions"].values(), key=lambda s: STATUS_RANK.get(s, 0))
        summary[worst] = summary.get(worst, 0) + 1

    overall_score = round(total_pass / total_rules * 100) if total_rules > 0 else 100
    entities.sort(key=lambda e: e["score"])

    # Recent issues: latest HealthStatus entries with status != healthy
    from app.models.quality_rule import HealthStatus, QualityRule
    from app.models.asset import Asset
    issues_raw = (
        db.query(HealthStatus, QualityRule, Asset)
        .join(QualityRule, HealthStatus.rule_id == QualityRule.id)
        .join(Asset, HealthStatus.asset_id == Asset.id)
        .filter(HealthStatus.status.in_(["warning", "failure"]))
        .order_by(HealthStatus.ran_at.desc())
        .limit(20)
        .all()
    )

    recent_issues = []
    for hs, rule, asset in issues_raw:
        # Find entity name via binding
        binding = db.query(ObjectBinding).filter(
            ObjectBinding.asset_id == asset.id, ObjectBinding.status == "active"
        ).first()
        from app.models.entity import OntologyEntity
        entity_name = ""
        if binding:
            ent = db.get(OntologyEntity, binding.object_type_id)
            entity_name = ent.name if ent else ""
        recent_issues.append({
            "id": hs.id,
            "entity_name": entity_name,
            "asset_name": asset.alias or asset.name,
            "rule_kind": rule.kind,
            "column_name": rule.column_name,
            "severity": hs.status,
            "value": hs.value_numeric,
            "threshold": (rule.params or {}).get("max") or (rule.params or {}).get("min"),
            "message": hs.message or "",
            "occurred_at": hs.ran_at,
        })

    # Trend: placeholder (would need daily snapshots in production)
    trend = []

    return {
        "overall_score": overall_score,
        "summary": summary,
        "entities": entities,
        "trend": trend,
        "recent_issues": recent_issues,
    }


@router.get("/dashboard", response_model=DashboardResponse)
def quality_dashboard(db: Session = Depends(get_db)):
    """Dashboard: overall score, entity scorecards, trend, recent issues."""
    entity_ids = [
        r[0] for r in db.query(ObjectBinding.object_type_id).filter(
            ObjectBinding.status == "active"
        ).distinct().all()
    ]
    data = _build_dashboard_data(db, entity_ids)
    return data


@router.post("/evaluate-all")
def evaluate_all_rules(db: Session = Depends(get_db)):
    """Trigger evaluation of all enabled quality rules."""
    count = _svc(db).evaluate_all()
    return {"evaluated": count}
```

- [ ] **Step 3: Run tests**

Run: `cd /Users/fuyuxiang/Documents/100-主业/130-东方国信/13.代码仓库/ontology/backend && python -m pytest tests/test_quality_dashboard_api.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
cd /Users/fuyuxiang/Documents/100-主业/130-东方国信/13.代码仓库/ontology && git add backend/app/api/v1/data_plane/quality.py backend/tests/test_quality_dashboard_api.py && git commit -m "feat: add quality dashboard aggregation API endpoint

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Frontend API Layer

**Files:**
- Modify: `frontend/src/api/quality.ts`

- [ ] **Step 1: Update quality API with dashboard endpoint**

Replace `frontend/src/api/quality.ts` with:

```typescript
import { get, post } from './client'

export interface DashboardEntity {
  entity_id: string
  entity_name: string
  score: number
  dimensions: Record<string, string>
  rule_count: number
  pass_count: number
}

export interface DashboardTrend {
  date: string
  score: number
  warnings: number
  failures: number
}

export interface DashboardIssue {
  id: string
  entity_name: string
  asset_name: string
  rule_kind: string
  column_name: string | null
  severity: string
  value: number | null
  threshold: number | null
  message: string
  occurred_at: string
}

export interface QualityDashboard {
  overall_score: number
  summary: { healthy: number; warning: number; failure: number; unknown: number }
  entities: DashboardEntity[]
  trend: DashboardTrend[]
  recent_issues: DashboardIssue[]
}

export const qualityApi = {
  dashboard() {
    return get<QualityDashboard>('/data-plane/quality/dashboard')
  },

  evaluateAll() {
    return post<{ evaluated: number }>('/data-plane/quality/evaluate-all')
  },
}
```

- [ ] **Step 2: Commit**

```bash
cd /Users/fuyuxiang/Documents/100-主业/130-东方国信/13.代码仓库/ontology && git add frontend/src/api/quality.ts && git commit -m "feat(frontend): update quality API for dashboard endpoint

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Frontend — Quality Dashboard Page (Complete Rewrite)

**Files:**
- Rewrite: `frontend/src/views/datasource/pages/DataQualityPage.vue`
- Delete: `frontend/src/views/datasource/tabs/DataQualityTab.vue` (no longer needed)

- [ ] **Step 1: Rewrite DataQualityPage.vue**

The full dashboard page with: score ring, entity scorecards, trend chart, anomaly timeline. This is a large component (~250 lines) that replaces the old configuration page.

Key sections:
- Left column (65%): Score ring + Entity scorecard list
- Right column (35%): Trend chart (ECharts) + Recent issues timeline
- Single "立即检测" button in header
- Auto-refresh every 60s
- Responsive: stacks vertically below 1280px

The component uses:
- ECharts for the trend line chart (or a lightweight gauge for the ring)
- CSS grid/flexbox for the left-right layout
- The `qualityApi.dashboard()` call on mount + interval

- [ ] **Step 2: Install ECharts if not present**

Run: `cd frontend && grep echarts package.json`
If not found: `npm install echarts vue-echarts`

- [ ] **Step 3: Remove DataQualityTab.vue reference**

The old page imported `DataQualityTab`. The new page is self-contained.

- [ ] **Step 4: Verify build**

Run: `cd frontend && npx vue-tsc --noEmit`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
cd /Users/fuyuxiang/Documents/100-主业/130-东方国信/13.代码仓库/ontology && git add frontend/src/views/datasource/pages/DataQualityPage.vue && git commit -m "feat(frontend): rewrite data quality page as read-only dashboard

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Frontend — Dashboard Styles

**Files:**
- Create: `frontend/src/views/datasource/pages/quality-dashboard.css`

- [ ] **Step 1: Create dedicated stylesheet**

Styles for: `.qd-page` layout, `.qd-score-ring` (SVG circle), `.qd-scorecard` rows, `.qd-trend` chart container, `.qd-timeline` event list, responsive breakpoints, dark mode support.

Key design tokens:
- Score ring: SVG circle with stroke-dasharray animation
- Scorecard rows: 52px height, bar chart fill animation
- Dimension dots: 8px colored circles
- Timeline: left border with colored dots
- Colors: green #10b981, orange #f59e0b, red #ef4444, gray #9ca3af

- [ ] **Step 2: Commit**

```bash
cd /Users/fuyuxiang/Documents/100-主业/130-东方国信/13.代码仓库/ontology && git add frontend/src/views/datasource/pages/quality-dashboard.css && git commit -m "feat(frontend): add quality dashboard styles with ring chart and scorecard

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```
