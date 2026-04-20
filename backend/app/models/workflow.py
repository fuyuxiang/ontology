"""
Workflow 数据模型 — 智能编排中心
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, JSON
from app.database import Base


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
