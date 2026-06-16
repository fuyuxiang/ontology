"""AssetUsage — Asset 反向引用台账。

记录"这个 Asset 被哪些上层资源（ObjectBinding / BuilderSession / Rule / Action）使用"，
用于：
- 删除 Asset 前的引用计数检查
- AssetDetailDrawer 右面板"被谁用了"展示
- 数据质量影响分析（schema 漂移时反查影响范围）
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.identifiers import gen_uuid


class AssetUsage(Base):
    __tablename__ = "asset_usage"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    asset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    used_by_kind: Mapped[str] = mapped_column(String(40), nullable=False)
        # object_binding | builder_session | rule | action | sql_view
    used_by_id: Mapped[str] = mapped_column(String(36), nullable=False)
    note: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("asset_id", "used_by_kind", "used_by_id", name="uq_asset_usage"),
    )


Index("ix_asset_usage_used_by", AssetUsage.used_by_kind, AssetUsage.used_by_id)
