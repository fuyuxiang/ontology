"""LineageEdge — 本体侧血缘边。

血缘范围严格限定在：Asset → ObjectType → Action 这一段。
不画上游（Connection→Asset 是 Asset 自身属性，不写边；数据仓库内部 ETL 不可见，不越界）。
不画下游平台外资源。

source_kind / target_kind 取值：asset | object_type | action | rule
relation 取值：binds_to（Asset→ObjectType）/ reads（ObjectType→Asset 调用读）/
              writes（ObjectType→Asset 写回）/ derives_from（Action 推导关系）
"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.identifiers import gen_uuid


class LineageEdge(Base):
    __tablename__ = "lineage_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    source_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    source_id: Mapped[str] = mapped_column(String(36), nullable=False)
    target_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    relation: Mapped[str] = mapped_column(String(40), nullable=False)
        # binds_to | reads | writes | derives_from

    via_module: Mapped[str | None] = mapped_column(String(40))
        # binding | execute | action | builder
    via_purpose: Mapped[str | None] = mapped_column(String(80))
        # 来自 ExecutionLog.purpose，仅白名单 purpose 写

    weight: Mapped[int] = mapped_column(Integer, default=1)
        # 调用频次（同一边重复 emit 时 +1）

    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "source_kind", "source_id", "target_kind", "target_id", "relation", "via_module",
            name="uq_lineage_edge",
        ),
    )


Index("ix_lineage_source", LineageEdge.source_kind, LineageEdge.source_id)
Index("ix_lineage_target", LineageEdge.target_kind, LineageEdge.target_id)
