"""/object-bindings — ObjectType ↔ Asset 强类型绑定。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import require_user
from app.database import get_db
from app.models.user import User
from app.schemas.data_plane import (
    BindingCreate, BindingDetail, BindingUpdate, ExecuteRequestModel,
)
from app.services.data_plane.execute_service import ExecuteRequest, ExecuteService
from app.services.data_plane.object_binding_service import ObjectBindingService

router = APIRouter(prefix="/object-bindings", tags=["data-plane:bindings"])


@router.get("", response_model=list[BindingDetail])
def list_bindings(
    object_type_id: str | None = None,
    asset_id: str | None = None,
    role: str | None = None,
    status: str | None = "active",
    db: Session = Depends(get_db),
):
    return ObjectBindingService(db).list(
        object_type_id=object_type_id, asset_id=asset_id,
        role=role, status=status,
    )


@router.get("/{binding_id}", response_model=BindingDetail)
def get_binding(binding_id: str, db: Session = Depends(get_db)):
    b = ObjectBindingService(db).get(binding_id)
    if not b:
        raise HTTPException(404, "binding 不存在")
    return b


@router.post("", response_model=BindingDetail, status_code=201)
def create_binding(
    body: BindingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    try:
        return ObjectBindingService(db).create(
            object_type_id=body.object_type_id,
            asset_id=body.asset_id,
            role=body.role,
            field_mappings=[fm.model_dump() for fm in body.field_mappings],
            id_column=body.id_column,
            filter_expr=body.filter_expr,
            user_id=user.id,
        )
    except ValueError as e:
        raise HTTPException(409, str(e))
    except LookupError as e:
        raise HTTPException(404, str(e))


@router.put("/{binding_id}", response_model=BindingDetail)
def update_binding(binding_id: str, body: BindingUpdate, db: Session = Depends(get_db)):
    try:
        payload = body.model_dump(exclude_unset=True)
        if "field_mappings" in payload:
            payload["field_mappings"] = [fm if isinstance(fm, dict) else fm.model_dump()
                                          for fm in (payload["field_mappings"] or [])]
        return ObjectBindingService(db).update(binding_id, **payload)
    except LookupError as e:
        raise HTTPException(404, str(e))


@router.delete("/{binding_id}", status_code=204)
def delete_binding(binding_id: str, db: Session = Depends(get_db)):
    try:
        ObjectBindingService(db).delete(binding_id)
    except LookupError as e:
        raise HTTPException(404, str(e))


@router.post("/{binding_id}/test-resolve")
def test_resolve(binding_id: str, db: Session = Depends(get_db)):
    """通过 Asset + binding 取 5 行样本，让用户预览映射效果。"""
    b = ObjectBindingService(db).get(binding_id)
    if not b:
        raise HTTPException(404, "binding 不存在")
    sql = "SELECT * FROM <asset> LIMIT :lim"
    try:
        r = ExecuteService(db).execute(ExecuteRequest(
            asset_id=b.asset_id, sql=sql, params={"lim": 5},
            purpose="binding.test_resolve",
            bypass_cache=True,
        ))
        return {"columns": r.columns, "rows": r.rows, "field_mappings": b.field_mappings}
    except Exception as e:
        raise HTTPException(400, f"取样失败: {e}")
