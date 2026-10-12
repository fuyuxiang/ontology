"""/object-bindings — ObjectType ↔ Asset 强类型绑定。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.deps import require_user
from app.database import get_db
from app.models.user import User
from app.schemas.data_plane import (
    BindingCreate,
    BindingDetail,
    BindingUpdate,
)
from app.models.asset import Asset
from app.services.data_plane.entity_data_service import EntityDataService
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
        binding = ObjectBindingService(db).create(
            object_type_id=body.object_type_id,
            asset_id=body.asset_id,
            role=body.role,
            field_mappings=[fm.model_dump() for fm in body.field_mappings],
            id_column=body.id_column,
            filter_expr=body.filter_expr,
            primary_source_column=body.primary_source_column,
            enrichment_source_column=body.enrichment_source_column,
            user_id=user.id,
        )
        db.commit()
        return binding
    except ValueError as e:
        raise HTTPException(409, str(e)) from e
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(409, "对象已存在活动主绑定，请刷新后重新确认") from e


@router.put("/{binding_id}", response_model=BindingDetail)
def update_binding(binding_id: str, body: BindingUpdate, db: Session = Depends(get_db)):
    try:
        payload = body.model_dump(exclude_unset=True)
        if "field_mappings" in payload:
            payload["field_mappings"] = [fm if isinstance(fm, dict) else fm.model_dump()
                                          for fm in (payload["field_mappings"] or [])]
        binding = ObjectBindingService(db).update(binding_id, **payload)
        db.commit()
        return binding
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(409, "对象已存在活动主绑定，请刷新后重新确认") from e


@router.delete("/{binding_id}", status_code=204)
def delete_binding(binding_id: str, db: Session = Depends(get_db)):
    try:
        ObjectBindingService(db).delete(binding_id)
        db.commit()
    except LookupError as e:
        raise HTTPException(404, str(e)) from e


@router.post("/{binding_id}/test-resolve")
def test_resolve(binding_id: str, db: Session = Depends(get_db)):
    """通过 Asset + binding 取 5 行样本，让用户预览映射效果。"""
    b = ObjectBindingService(db).get(binding_id)
    if not b:
        raise HTTPException(404, "binding 不存在")
    try:
        class BindingPreview(EntityDataService):
            def resolve_entity_asset(self, entity_id):
                asset = db.get(Asset, b.asset_id)
                if b.status != "active" or not asset or asset.status != "active":
                    return None
                return asset, b
        r = BindingPreview(db)._query_primary_data(b.object_type_id, limit=5, purpose="binding.test_resolve")
        if r.get("error"):
            raise ValueError(r["error"])
        return {**r, "field_mappings": b.field_mappings}
    except Exception as e:
        raise HTTPException(400, f"取样失败: {e}") from e
