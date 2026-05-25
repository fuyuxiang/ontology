"""/execute — 唯一执行闸口 API。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.data_plane import (
    DryRunOut, ExecuteBlockedModel, ExecuteRequestModel, ExecuteResultModel,
)
from app.services.data_plane.execute_service import (
    ExecuteBlocked, ExecuteRequest, ExecuteService,
)

router = APIRouter(prefix="/execute", tags=["data-plane:execute"])


@router.post("", response_model=ExecuteResultModel,
             responses={400: {"model": ExecuteBlockedModel}})
def execute(
    body: ExecuteRequestModel,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    try:
        result = ExecuteService(db).execute(ExecuteRequest(
            asset_id=body.asset_id, sql=body.sql, params=body.params,
            purpose=body.purpose, timeout_ms=body.timeout_ms,
            bypass_cache=body.bypass_cache,
            user_id=user.id if user else None,
        ))
    except ExecuteBlocked as e:
        raise HTTPException(400, detail={"blocked": True, "reason": e.reason, "detail": e.detail})
    except LookupError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"execute failed: {e}")
    return ExecuteResultModel(
        columns=result.columns, rows=result.rows,
        rows_returned=result.rows_returned, duration_ms=result.duration_ms,
        cache_hit=result.cache_hit,
    )


@router.post("/dry-run", response_model=DryRunOut)
def dry_run(
    body: ExecuteRequestModel,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    try:
        return ExecuteService(db).dry_run(ExecuteRequest(
            asset_id=body.asset_id, sql=body.sql, params=body.params,
            purpose=body.purpose, timeout_ms=body.timeout_ms,
            bypass_cache=True,
            user_id=user.id if user else None,
        ))
    except ExecuteBlocked as e:
        raise HTTPException(400, detail={"blocked": True, "reason": e.reason, "detail": e.detail})
    except LookupError as e:
        raise HTTPException(404, str(e))
