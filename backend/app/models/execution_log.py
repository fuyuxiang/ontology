"""ExecutionLog — 唯一执行入口 /execute 的审计日志。

每次 ExecuteService.execute（含命中缓存、被拦截）必写一条。
不存 SQL 全文（仅前 500 字符 + sql_hash），避免敏感数据泄露与表膨胀。
params 中 sensitivity_tags 命中的字段值在 params_redacted 里遮罩。
"""
from datetime import datetime

from sqlalchemy import String, Integer, Boolean, Text, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.identifiers import gen_uuid


class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    asset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("assets.id", ondelete="SET NULL"), index=True
    )
    connection_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("connections.id", ondelete="SET NULL"), index=True
    )
    purpose: Mapped[str] = mapped_column(String(80), nullable=False)
        # 必填：mnp.dashboard / scene.bb.list / builder.preview / probe.null_ratio / action.write
    sql_hash: Mapped[str] = mapped_column(String(64), nullable=False)
        # sha256(sql + sorted(params))
    sql_preview: Mapped[str] = mapped_column(Text, default="")
        # 前 500 字符
    params_redacted: Mapped[dict | None] = mapped_column(JSON)

    rows_returned: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)

    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    block_reason: Mapped[str | None] = mapped_column(String(60))
        # ast_failed | not_whitelisted | rate_limited | dml_denied | timeout |
        # missing_params | cross_connection_join | dangerous_function

    user_id: Mapped[str | None] = mapped_column(String(36))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


Index("ix_exec_asset_started", ExecutionLog.asset_id, ExecutionLog.started_at.desc())
Index("ix_exec_purpose_started", ExecutionLog.purpose, ExecutionLog.started_at.desc())
Index("ix_exec_blocked", ExecutionLog.blocked)
