"""
工作流 App / 审批 — Pydantic schemas
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── 设计态 CRUD ──────────────────────────────────────────

class AppCreate(BaseModel):
    code: str = Field(..., max_length=100)
    name: str = Field(..., max_length=200)
    description: str | None = None
    scene_code: str | None = None
    canvas_json: dict[str, Any] | None = None


class AppUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    scene_code: str | None = None
    canvas_json: dict[str, Any] | None = None


class AppBrief(BaseModel):
    id: str
    code: str
    name: str
    description: str | None
    status: str
    scene_code: str | None
    published_version: int
    created_at: datetime | None
    updated_at: datetime | None

    class Config:
        from_attributes = True


class AppDetail(AppBrief):
    canvas_json: dict[str, Any] | None
    published_json: dict[str, Any] | None

    class Config:
        from_attributes = True


# ── 发布 ─────────────────────────────────────────────────

class PublishResult(BaseModel):
    app_id: str
    version: int
    published_json: dict[str, Any]


# ── 工具注册 ─────────────────────────────────────────────

class ToolSpec(BaseModel):
    name: str
    description: str
    sensitive: bool = False
    parameters: dict[str, Any] = {}
    required: list[str] = []


# ── 审批 ─────────────────────────────────────────────────

class ApprovalBrief(BaseModel):
    id: str
    app_id: str
    session_id: str
    tool_name: str
    tool_args: dict[str, Any] | None
    status: str
    created_by: str
    resolved_by: str | None
    created_at: datetime | None
    resolved_at: datetime | None

    class Config:
        from_attributes = True


class ApprovalAction(BaseModel):
    comment: str | None = None
