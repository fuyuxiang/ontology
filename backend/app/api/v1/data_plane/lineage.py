"""/lineage v2 — 本体侧血缘（Asset → ObjectType → Action）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.data_plane import LineageGraph
from app.services.data_plane.lineage_service import LineageService

router = APIRouter(prefix="/lineage", tags=["data-plane:lineage"])


@router.get("/overview", response_model=LineageGraph)
def get_overview(db: Session = Depends(get_db)):
    """全局血缘大图：所有非废弃边 + 节点元数据。"""
    return LineageService(db).get_overview()


@router.get("", response_model=LineageGraph)
def get_lineage(
    asset_id: str | None = Query(None),
    object_type_id: str | None = Query(None),
    depth: int = Query(2, ge=1, le=5),
    db: Session = Depends(get_db),
):
    if asset_id and object_type_id:
        raise HTTPException(400, "asset_id 与 object_type_id 二选一")
    if asset_id:
        return LineageService(db).get_for_asset(asset_id, depth=depth)
    if object_type_id:
        return LineageService(db).get_for_object_type(object_type_id, depth=depth)
    raise HTTPException(400, "asset_id 或 object_type_id 必填")
