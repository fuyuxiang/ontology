"""
智能编排中心 — 工作流模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.identifiers import gen_uuid


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    namespace: Mapped[str] = mapped_column(String(50), default="")
    group_name: Mapped[str] = mapped_column(String(50), default="未分组")
    nodes_json: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    edges_json: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    trigger_config: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by: Mapped[str] = mapped_column(String(50), default="admin")


class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    workflow_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    workflow_name: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(20), default="running")
    input_params: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    node_results: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    triggered_by: Mapped[str] = mapped_column(String(50), default="manual")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
