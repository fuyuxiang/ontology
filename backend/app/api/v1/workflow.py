"""
工作流 App CRUD + 发布 + 工具注册 + 审批 路由
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.workflow import WorkflowApp, ApprovalTask
from app.schemas.workflow import (
    AppCreate, AppUpdate, AppBrief, AppDetail,
    PublishResult, ToolSpec, ApprovalBrief, ApprovalAction,
)
from app.services.workflow_service import publish_app, resolve_approval
from app.services.agent_tools import AGENT_TOOL_SPECS

router = APIRouter(prefix="/workflow", tags=["workflow"])


# ── 设计态 CRUD ──────────────────────────────────────────

@router.post("/apps", response_model=AppBrief)
def create_app(body: AppCreate, db: Session = Depends(get_db)):
    existing = db.query(WorkflowApp).filter(WorkflowApp.code == body.code).first()
    if existing:
        raise HTTPException(400, f"App code '{body.code}' already exists")
    app = WorkflowApp(
        id=str(uuid.uuid4()),
        code=body.code,
        name=body.name,
        description=body.description,
        scene_code=body.scene_code,
        canvas_json=body.canvas_json or {"nodes": [], "edges": []},
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


@router.get("/apps", response_model=list[AppBrief])
def list_apps(
    status: str | None = None,
    scene_code: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(WorkflowApp)
    if status:
        q = q.filter(WorkflowApp.status == status)
    if scene_code:
        q = q.filter(WorkflowApp.scene_code == scene_code)
    return q.order_by(WorkflowApp.updated_at.desc()).all()


@router.get("/apps/{app_id}", response_model=AppDetail)
def get_app(app_id: str, db: Session = Depends(get_db)):
    app = db.query(WorkflowApp).filter(WorkflowApp.id == app_id).first()
    if not app:
        raise HTTPException(404, "App not found")
    return app


@router.put("/apps/{app_id}", response_model=AppBrief)
def update_app(app_id: str, body: AppUpdate, db: Session = Depends(get_db)):
    app = db.query(WorkflowApp).filter(WorkflowApp.id == app_id).first()
    if not app:
        raise HTTPException(404, "App not found")
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(app, field, val)
    db.commit()
    db.refresh(app)
    return app


@router.delete("/apps/{app_id}")
def delete_app(app_id: str, db: Session = Depends(get_db)):
    app = db.query(WorkflowApp).filter(WorkflowApp.id == app_id).first()
    if not app:
        raise HTTPException(404, "App not found")
    db.delete(app)
    db.commit()
    return {"ok": True}


# ── 发布 ─────────────────────────────────────────────────

@router.post("/apps/{app_id}/publish", response_model=PublishResult)
def publish(app_id: str, db: Session = Depends(get_db)):
    try:
        app = publish_app(db, app_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return PublishResult(
        app_id=app.id,
        version=app.published_version,
        published_json=app.published_json,
    )


@router.get("/published/{scene_code}", response_model=dict[str, Any])
def get_published_by_scene(scene_code: str, db: Session = Depends(get_db)):
    app = (
        db.query(WorkflowApp)
        .filter(WorkflowApp.scene_code == scene_code, WorkflowApp.status == "published")
        .order_by(WorkflowApp.published_version.desc())
        .first()
    )
    if not app or not app.published_json:
        raise HTTPException(404, "No published app for this scene")
    return app.published_json


# ── 工具注册 ─────────────────────────────────────────────

@router.get("/tools", response_model=list[ToolSpec])
def list_tools():
    return [
        ToolSpec(
            name=s.name,
            description=s.description,
            sensitive=getattr(s, "sensitive", False),
            parameters=s.parameters,
            required=list(s.required),
        )
        for s in AGENT_TOOL_SPECS
    ]


# ── 审批 ─────────────────────────────────────────────────

@router.get("/approvals", response_model=list[ApprovalBrief])
def list_approvals(
    status: str = "pending",
    session_id: str | None = None,
    app_id: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(ApprovalTask).filter(ApprovalTask.status == status)
    if session_id:
        q = q.filter(ApprovalTask.session_id == session_id)
    if app_id:
        q = q.filter(ApprovalTask.app_id == app_id)
    return q.order_by(ApprovalTask.created_at.desc()).all()


@router.post("/approvals/{task_id}/approve", response_model=ApprovalBrief)
def approve_task(task_id: str, body: ApprovalAction | None = None, db: Session = Depends(get_db)):
    try:
        return resolve_approval(db, task_id, "approved")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/approvals/{task_id}/reject", response_model=ApprovalBrief)
def reject_task(task_id: str, body: ApprovalAction | None = None, db: Session = Depends(get_db)):
    try:
        return resolve_approval(db, task_id, "rejected")
    except ValueError as e:
        raise HTTPException(400, str(e))
