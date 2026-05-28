"""/mapping — 半自动 ObjectType ↔ Asset 映射推荐 + 落库。"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.data_plane.mapping_suggest_service import MappingSuggestService
from app.services.data_plane.object_binding_service import ObjectBindingService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mapping", tags=["data-plane:mapping"])


# ── Schemas ─────────────────────────────────────────
class SuggestRequest(BaseModel):
    object_type_id: str
    asset_id: str
    use_llm: bool = True
    top_k: int = 3


class SuggestAssetsRequest(BaseModel):
    object_type_id: str


class FieldMapping(BaseModel):
    attribute_id: str
    source_column: str
    transform: str | None = None


class ApplyRequest(BaseModel):
    object_type_id: str
    asset_id: str
    field_mappings: list[FieldMapping]
    id_column: str | None = None
    filter_expr: str | None = None
    role: str = "primary"


# ── Endpoints ───────────────────────────────────────
@router.post("/suggest_assets")
def suggest_assets(body: SuggestAssetsRequest, db: Session = Depends(get_db)):
    """扫所有数据资产，按属性覆盖率排序推荐给 ObjectType。"""
    try:
        return MappingSuggestService(db).suggest_assets(object_type_id=body.object_type_id)
    except LookupError as e:
        raise HTTPException(404, str(e))


@router.get("/coverage")
def list_coverage(db: Session = Depends(get_db)):
    """列出所有 ObjectType 的属性映射覆盖率（侧栏徽章用）。"""
    from app.models.entity import OntologyEntity, EntityAttribute
    rows = []
    entities = db.query(OntologyEntity).all()
    for e in entities:
        attrs = e.attributes
        total = len(attrs)
        mapped = sum(1 for a in attrs if a.source_field)
        rows.append({
            "object_type_id": e.id,
            "total": total,
            "mapped": mapped,
        })
    return rows


@router.post("/suggest")
def suggest(body: SuggestRequest, db: Session = Depends(get_db)):
    """启发式 + LLM 推荐：返每属性 top-K 候选列。"""
    try:
        return MappingSuggestService(db).suggest(
            object_type_id=body.object_type_id, asset_id=body.asset_id,
            use_llm=body.use_llm, top_k=body.top_k,
        )
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/apply")
def apply(body: ApplyRequest, db: Session = Depends(get_db),
          user: User | None = Depends(get_current_user)):
    """提交确认结果：写 / 更新 ObjectBinding（role=primary），同时反写 EntityAttribute。"""
    svc = ObjectBindingService(db)
    fm_payload = [m.model_dump() for m in body.field_mappings]
    role = body.role or "primary"
    if role not in ("primary", "enrichment", "document_evidence"):
        raise HTTPException(400, f"非法 role: {role}")
    try:
        existing = svc.repo.find_existing(body.object_type_id, body.asset_id, role)
        if existing:
            binding = svc.update(
                existing.id,
                field_mappings=fm_payload,
                id_column=body.id_column,
                filter_expr=body.filter_expr,
            )
            action = "updated"
        else:
            binding = svc.create(
                object_type_id=body.object_type_id, asset_id=body.asset_id,
                role=role,
                field_mappings=fm_payload,
                id_column=body.id_column,
                filter_expr=body.filter_expr,
                user_id=user.id if user else None,
            )
            action = "created"
        return {
            "action": action,
            "binding_id": binding.id,
            "field_mappings_count": len(fm_payload),
        }
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
