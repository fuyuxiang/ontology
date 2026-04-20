"""
工作流 App + 审批任务 模型
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Integer, DateTime, JSON, ForeignKey, Index
from sqlalchemy.sql import func

from app.database import Base


def _uuid():
    return str(uuid.uuid4())


class WorkflowApp(Base):
    __tablename__ = "workflow_apps"

    id = Column(String(36), primary_key=True, default=_uuid)
    code = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    canvas_json = Column(JSON, nullable=True)
    published_json = Column(JSON, nullable=True)
    published_version = Column(Integer, default=0)
    status = Column(String(20), default="draft")
    scene_code = Column(String(100), nullable=True, index=True)
    created_by = Column(String(100), default="admin")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class ApprovalTask(Base):
    __tablename__ = "approval_tasks"

    id = Column(String(36), primary_key=True, default=_uuid)
    app_id = Column(String(36), ForeignKey("workflow_apps.id"), nullable=False)
    session_id = Column(String(36), nullable=False, index=True)
    tool_name = Column(String(100), nullable=False)
    tool_args = Column(JSON, nullable=True)
    status = Column(String(20), default="pending")
    created_by = Column(String(100), default="system")
    resolved_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=func.now())
    resolved_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_approval_status", "status"),
    )


# ── 智能编排中心 ──

def gen_uuid():
    return str(uuid.uuid4())


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")
    namespace = Column(String(50), default="")
    group_name = Column(String(50), default="未分组")
    nodes_json = Column(JSON, default=list)
    edges_json = Column(JSON, default=list)
    trigger_config = Column(JSON, default=dict)
    status = Column(String(20), default="draft")  # draft/published/disabled
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(50), default="admin")


class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    workflow_id = Column(String(36), nullable=False, index=True)
    workflow_name = Column(String(100), default="")
    status = Column(String(20), default="running")  # running/completed/failed/cancelled
    input_params = Column(JSON, default=dict)
    node_results = Column(JSON, default=dict)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    triggered_by = Column(String(50), default="manual")
    error_message = Column(Text, nullable=True)
