"""/quality v2 — 健康度规则与状态。

设计：QualityRule 是用户挂在 Asset 上的"契约"，HealthStatus 是评估留痕。
旧 /probe API（人手探针）保留，作为底层。
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.deps import require_user
from app.database import get_db
from app.models.quality_rule import RULE_KINDS, STATUS_RANK
from app.models.user import User
from app.services.data_plane.quality_rule_service import RULE_DEFAULTS, QualityRuleService

router = APIRouter(prefix="/quality", tags=["data-plane:quality"])


# ── Schemas ─────────────────────────────────────────
class RuleCreate(BaseModel):
    asset_id: str
    name: str
    kind: str
    column_name: str | None = None
    params: dict | None = None
    severity: str = "warning"
    description: str | None = None


class RuleUpdate(BaseModel):
    name: str | None = None
    params: dict | None = None
    severity: str | None = None
    enabled: bool | None = None
    description: str | None = None


class RuleOut(BaseModel):
    id: str
    asset_id: str
    name: str
    kind: str
    column_name: str | None
    params: dict
    severity: str
    enabled: bool
    description: str | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class HealthStatusOut(BaseModel):
    id: str
    rule_id: str
    asset_id: str
    status: str
    value_numeric: float | None
    message: str | None
    ran_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AssetHealth(BaseModel):
    asset_id: str
    asset_name: str
    asset_kind: str
    domain: str | None
    status: str  # healthy | warning | failure | unknown
    rule_count: int
    by_status: dict


class RuleWithStatus(BaseModel):
    rule: RuleOut
    latest: HealthStatusOut | None


# ── 规则 CRUD ────────────────────────────────────────
def _svc(db: Session) -> QualityRuleService:
    return QualityRuleService(db)


@router.get("/rule_kinds")
def list_rule_kinds():
    """返回可用规则种类 + 默认参数模板（前端建规则用）。"""
    return [{"kind": k, "defaults": RULE_DEFAULTS.get(k, {})} for k in RULE_KINDS]


@router.get("/rules", response_model=list[RuleOut])
def list_rules(asset_id: str | None = None, db: Session = Depends(get_db)):
    return _svc(db).list_rules(asset_id)


@router.post("/rules", response_model=RuleOut, status_code=201)
def create_rule(body: RuleCreate, db: Session = Depends(get_db),
                user: User = Depends(require_user)):
    try:
        return _svc(db).create_rule(user_id=user.id, **body.model_dump())
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.put("/rules/{rule_id}", response_model=RuleOut)
def update_rule(rule_id: str, body: RuleUpdate, db: Session = Depends(get_db)):
    try:
        return _svc(db).update_rule(rule_id, **body.model_dump(exclude_unset=True))
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(rule_id: str, db: Session = Depends(get_db)):
    try:
        _svc(db).delete_rule(rule_id)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e


# ── 评估 ────────────────────────────────────────────
@router.post("/rules/{rule_id}/evaluate", response_model=HealthStatusOut)
def evaluate_rule(rule_id: str, db: Session = Depends(get_db)):
    try:
        return _svc(db).evaluate(rule_id)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e


@router.post("/assets/{asset_id}/evaluate", response_model=list[HealthStatusOut])
def evaluate_asset(asset_id: str, db: Session = Depends(get_db)):
    return _svc(db).evaluate_asset(asset_id)


# ── 健康度查询 ──────────────────────────────────────
@router.get("/health/overview", response_model=list[AssetHealth])
def health_overview(db: Session = Depends(get_db)):
    """总览：所有有规则的资产 + 当前聚合状态。"""
    from app.models.asset import Asset
    from app.models.quality_rule import QualityRule
    asset_ids = [r[0] for r in db.query(QualityRule.asset_id).distinct().all()]
    if not asset_ids:
        return []
    assets = db.query(Asset).filter(Asset.id.in_(asset_ids)).all()
    svc = _svc(db)
    out: list[AssetHealth] = []
    for a in assets:
        agg = svc.asset_aggregate_status(a.id)
        out.append(AssetHealth(
            asset_id=a.id, asset_name=a.alias or a.name, asset_kind=a.kind,
            domain=a.domain,
            status=agg["status"], rule_count=agg["rule_count"], by_status=agg["by_status"],
        ))
    # 排序：failure > warning > unknown > healthy；同状态下按规则数倒序
    rank = {"failure": 0, "warning": 1, "unknown": 2, "healthy": 3}
    out.sort(key=lambda x: (rank.get(x.status, 9), -x.rule_count))
    return out


@router.get("/health/asset/{asset_id}")
def health_asset(asset_id: str, db: Session = Depends(get_db)) -> dict:
    """资产详情：资产基本信息 + 所有规则 + 各规则当前状态 + 聚合状态。"""
    from app.models.asset import Asset
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(404, "资产不存在")
    svc = _svc(db)
    rules = svc.list_rules(asset_id)
    payload = []
    for r in rules:
        latest = svc.latest_status(r.id)
        payload.append({
            "rule": RuleOut.model_validate(r).model_dump(),
            "latest": HealthStatusOut.model_validate(latest).model_dump() if latest else None,
        })
    agg = svc.asset_aggregate_status(asset_id)
    return {
        "asset": {
            "id": asset.id, "name": asset.name, "alias": asset.alias,
            "kind": asset.kind, "domain": asset.domain,
        },
        "aggregate": agg,
        "rules": payload,
    }


@router.get("/health/rules/{rule_id}/history", response_model=list[HealthStatusOut])
def rule_history(rule_id: str, limit: int = 100, db: Session = Depends(get_db)):
    return _svc(db).history(rule_id, limit=limit)


# ── Dashboard schemas ────────────────────────────────
class DashboardEntity(BaseModel):
    entity_id: str
    entity_name: str
    score: int
    dimensions: dict
    rule_count: int
    pass_count: int


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
    trend: list[dict]
    recent_issues: list[DashboardIssue]


# ── Dashboard helpers ────────────────────────────────
def _get_entity_quality_data(db: Session, entity_id: str, svc: QualityRuleService) -> dict | None:
    """Aggregate quality data for one entity across all its bound assets."""
    from app.models.entity import OntologyEntity
    from app.models.object_binding import ObjectBinding

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
            if dim_key and STATUS_RANK.get(status, 0) > STATUS_RANK.get(dim_status[dim_key], 0):
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


# ── Dashboard endpoints ──────────────────────────────
@router.get("/dashboard", response_model=DashboardResponse)
def quality_dashboard(db: Session = Depends(get_db)):
    """Dashboard: overall score, entity scorecards, trend, recent issues."""
    from app.models.object_binding import ObjectBinding

    entity_ids = [
        r[0] for r in db.query(ObjectBinding.object_type_id).filter(
            ObjectBinding.status == "active"
        ).distinct().all()
    ]

    svc = _svc(db)
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
        worst = max(data["dimensions"].values(), key=lambda s: STATUS_RANK.get(s, 0))
        summary[worst] = summary.get(worst, 0) + 1

    overall_score = round(total_pass / total_rules * 100) if total_rules > 0 else 100
    entities.sort(key=lambda e: e["score"])

    # Recent issues
    from app.models.asset import Asset as A
    from app.models.entity import OntologyEntity
    from app.models.object_binding import ObjectBinding as OB
    from app.models.quality_rule import HealthStatus as HS
    from app.models.quality_rule import QualityRule as QR

    issues_raw = (
        db.query(HS, QR, A)
        .join(QR, HS.rule_id == QR.id)
        .join(A, HS.asset_id == A.id)
        .filter(HS.status.in_(["warning", "failure"]))
        .order_by(HS.ran_at.desc())
        .limit(20)
        .all()
    )

    recent_issues = []
    for hs, rule, asset in issues_raw:
        binding = db.query(OB).filter(OB.asset_id == asset.id, OB.status == "active").first()
        entity_name = ""
        if binding:
            ent = db.get(OntologyEntity, binding.object_type_id)
            entity_name = ent.name if ent else ""
        recent_issues.append(DashboardIssue(
            id=hs.id,
            entity_name=entity_name,
            asset_name=asset.alias or asset.name,
            rule_kind=rule.kind,
            column_name=rule.column_name,
            severity=hs.status,
            value=hs.value_numeric,
            threshold=(rule.params or {}).get("max") or (rule.params or {}).get("min"),
            message=hs.message or "",
            occurred_at=hs.ran_at,
        ))

    return DashboardResponse(
        overall_score=overall_score,
        summary=summary,
        entities=[DashboardEntity(**e) for e in entities],
        trend=[],
        recent_issues=recent_issues,
    )


@router.post("/evaluate-all")
def evaluate_all_rules(db: Session = Depends(get_db)):
    """Trigger evaluation of all enabled quality rules."""
    count = _svc(db).evaluate_all()
    return {"evaluated": count}
