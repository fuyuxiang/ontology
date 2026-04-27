"""
治理中心 API — 审计日志查询
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.audit import AuditLog

router = APIRouter(prefix="/governance", tags=["governance"])


class AuditLogItem(BaseModel):
    id: str
    timestamp: datetime
    user_id: str | None
    user_name: str | None
    action: str
    target_type: str
    target_id: str
    target_name: str
    changes_json: list | None

    model_config = {"from_attributes": True}


class AuditLogPage(BaseModel):
    items: list[AuditLogItem]
    total: int
    page: int
    page_size: int


@router.get("/audit-logs", response_model=AuditLogPage)
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=100),
    action: str | None = Query(None),
    target_type: str | None = Query(None),
    user_name: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action == action)
    if target_type:
        q = q.filter(AuditLog.target_type == target_type)
    if user_name:
        q = q.filter(AuditLog.user_name.ilike(f"%{user_name}%"))

    total = q.count()
    items = q.order_by(desc(AuditLog.timestamp)).offset((page - 1) * page_size).limit(page_size).all()

    return AuditLogPage(items=items, total=total, page=page, page_size=page_size)
