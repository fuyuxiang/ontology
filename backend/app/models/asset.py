"""Asset 模型 — 数据集成模块"资产"一级公民。

一份"指针 + 契约"，指向某 Connection 上的一张表/视图，或一份非结构化资源。
不存储业务行数据；只存元数据/契约/统计。

kind 三种：
- table     —— 数据仓库治理表 / 业务库的表（结构化主形态）
- sql_view  —— 受限的参数化视图（结构化）
- document  —— 非结构化资产，由 locator.source_type 区分 5 种形态：
              file | oss | directory | api | mq
"""
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.identifiers import gen_uuid


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    alias: Mapped[str | None] = mapped_column(String(120), unique=True)
        # 可选短别名（业务模块迁移高频使用：mnp.user_count / scenes.bb.overview）
    description: Mapped[str | None] = mapped_column(Text)

    kind: Mapped[str] = mapped_column(String(20), nullable=False)
        # table | sql_view | document
    connection_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("connections.id", ondelete="RESTRICT"), index=True
    )
        # table / sql_view 必填；document 当 source_type 是 file/directory 时可空

    locator: Mapped[dict] = mapped_column(JSON, nullable=False)
        # 严格按 kind 校验：
        # - table:    {"table": "..."}
        # - sql_view: {"base_asset_id": "...", "sql": "...", "required_params": [...], "dependencies": [...]}
        # - document: {"source_type": "file|oss|directory|api|mq", ...}

    # ── 结构化资产用 ──
    schema_snapshot: Mapped[list | None] = mapped_column(JSON)
        # [{"name":"user_id","type":"string","nullable":false,"is_pk":true,"comment":"..."}, ...]
    schema_synced_at: Mapped[datetime | None] = mapped_column(DateTime)
    primary_key: Mapped[list | None] = mapped_column(JSON, default=list)
    profile: Mapped[dict | None] = mapped_column(JSON)
        # {"row_count":40929,"max_updated_at":"...","null_ratio":{...},"sampled_at":"..."}

    # ── 非结构化资产用 ──
    document_source_type: Mapped[str | None] = mapped_column(String(20))
        # file | oss | directory | api | mq —— 与 locator.source_type 同步
    parsed_summary: Mapped[str | None] = mapped_column(Text)
        # 文档摘要 / 抽样前 N 行（限 50KB）
    embedding_index_ref: Mapped[str | None] = mapped_column(String(300))
        # 向量索引指针（外部向量库）

    # ── 治理/元信息 ──
    refresh_policy: Mapped[str] = mapped_column(String(20), default="on_demand")
        # on_demand | hourly | daily
    cache_ttl_seconds: Mapped[int] = mapped_column(Integer, default=0)
    sensitivity_tags: Mapped[dict | None] = mapped_column(JSON, default=dict)
        # 列级敏感度：{"phone":"pii","id_card":"pii","amount":"sensitive"}
    domain: Mapped[str | None] = mapped_column(String(60), index=True)
    tags: Mapped[list | None] = mapped_column(JSON, default=list)
    owner: Mapped[str | None] = mapped_column(String(120))

    status: Mapped[str] = mapped_column(String(20), default="active")
        # active | deprecated | broken

    # ── 兼容反查（迁移期用，M4 删除）──
    legacy_datasource_id: Mapped[str | None] = mapped_column(String(36), index=True)
    legacy_business_document_id: Mapped[str | None] = mapped_column(String(36), index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by: Mapped[str | None] = mapped_column(String(36))


Index("ix_assets_kind_status", Asset.kind, Asset.status)
Index("ix_assets_doc_source_type", Asset.document_source_type)
