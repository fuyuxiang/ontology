"""QualityMetric — Asset 治理质量指标。

由 ProbeService 触发探针后写入。前端"数据质量"页只读这张表。
不重做数据仓库的整体质量体系，只关注本体平台关心的指标：
- row_count / freshness_seconds / null_ratio / distinct_count / pk_uniqueness / schema_drift
"""
from datetime import datetime

from sqlalchemy import String, Float, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.identifiers import gen_uuid


class QualityMetric(Base):
    __tablename__ = "quality_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    asset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
        # row_count | freshness_seconds | null_ratio | distinct_count | pk_uniqueness | schema_drift
    column_name: Mapped[str | None] = mapped_column(String(120))
        # null_ratio / distinct_count / freshness 用
    value_numeric: Mapped[float | None] = mapped_column(Float)
    value_text: Mapped[str | None] = mapped_column(Text)
        # schema_drift 用：序列化的 diff JSON
    threshold: Mapped[float | None] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(20), default="ok")
        # ok | warning | error
    measured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


Index("ix_quality_asset_kind_time", QualityMetric.asset_id, QualityMetric.kind, QualityMetric.measured_at.desc())
