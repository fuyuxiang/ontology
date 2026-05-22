"""
AIP 场景平台 — 场景 / 版本 / 执行 / 触发器 数据模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, DateTime, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.identifiers import gen_uuid


class AipScene(Base):
    __tablename__ = "aip_scenes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    group_name: Mapped[str] = mapped_column(String(80), default="自定义")

    # 画布
    nodes_json: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    edges_json: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    # 编排上下文
    ontology_bindings: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    datasource_bindings: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    input_schema: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    output_schema: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    stats_json: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

    # 触发配置（同步存一份方便前端读，权威值在 aip_scene_triggers 表）
    trigger_config: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

    # 治理
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft/reviewing/published/archived
    version: Mapped[int] = mapped_column(Integer, default=0)
    published_version_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by: Mapped[str] = mapped_column(String(50), default="admin")


class AipSceneVersion(Base):
    __tablename__ = "aip_scene_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    scene_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_json: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="published")  # published/rolled_back
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow)
    published_by: Mapped[str] = mapped_column(String(50), default="admin")


class AipSceneExecution(Base):
    __tablename__ = "aip_scene_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    scene_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    scene_name: Mapped[str] = mapped_column(String(120), default="")
    scene_version: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running/success/failed/cancelled
    triggered_by: Mapped[str] = mapped_column(String(40), default="manual")  # manual/schedule/event/webhook/api/replay
    trigger_payload: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    input_params: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    node_results: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    final_output: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    trace_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)


class AipSceneTrigger(Base):
    __tablename__ = "aip_scene_triggers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    scene_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # schedule/event/webhook/manual
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # schedule
    cron_expr: Mapped[Optional[str]] = mapped_column(String(120), default="")
    timezone: Mapped[str] = mapped_column(String(60), default="Asia/Shanghai")
    schedule_payload: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

    # event
    event_entity: Mapped[Optional[str]] = mapped_column(String(120), default="")
    event_action: Mapped[Optional[str]] = mapped_column(String(20), default="")  # created/updated/deleted

    # webhook
    webhook_path: Mapped[Optional[str]] = mapped_column(String(120), default="")
    webhook_secret: Mapped[Optional[str]] = mapped_column(String(120), default="")

    last_fired_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    fire_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
