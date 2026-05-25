"""Connection 模型 — 数据集成模块"连接"一级公民。

替代旧 DataSource 中的物理连接相关字段。仅承载：
- 物理连接信息（host/port/database/driver/params）
- 凭据加密引用（credential_ref；明文不入库）
- 连接级权限与限流（writable / pool_size / rate_limit_qps）

不承载：表结构、文件、API、MQ 等"数据集"语义——那归 Asset。
"""
from datetime import datetime

from sqlalchemy import String, Integer, Boolean, Text, DateTime, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.identifiers import gen_uuid


class Connection(Base):
    __tablename__ = "connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
        # mysql | postgresql | oracle | sqlserver | hive | clickhouse
    host: Mapped[str] = mapped_column(String(200), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    database: Mapped[str] = mapped_column(String(120), default="")
    params: Mapped[dict | None] = mapped_column(JSON)
        # 额外驱动参数：charset / ssl_ca / schema / sid / jdbc_extra

    # ── 凭据：明文不入库，只存引用 ──
    credential_ref: Mapped[str] = mapped_column(String(300), default="")
        # local-fernet://<id> | vault://path | kms://key-id
    credential_type: Mapped[str] = mapped_column(String(30), default="local-fernet")

    # ── 连接级安全/限流 ──
    writable: Mapped[bool] = mapped_column(Boolean, default=False)
    pool_size: Mapped[int] = mapped_column(Integer, default=4)
    rate_limit_qps: Mapped[int] = mapped_column(Integer, default=20)

    # ── 状态/元信息 ──
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="active")
        # active | inactive | error
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_test_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    last_test_message: Mapped[str | None] = mapped_column(String(500))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by: Mapped[str | None] = mapped_column(String(36))


Index("ix_connections_type", Connection.type)
Index("ix_connections_status_enabled", Connection.status, Connection.enabled)
