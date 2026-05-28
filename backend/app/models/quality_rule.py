"""QualityRule / HealthStatus — Palantir Foundry 风格的数据健康度模型。

QualityRule：用户在资产上挂的"必须满足的契约"
HealthStatus：每次评估留痕，最新一条 = 当前状态；按 (rule_id, ran_at) 时间序列保存

资产级聚合状态 = 该资产所有 enabled rule 的最差当前状态
（healthy < warning < failure，unknown 不影响聚合）
"""
from datetime import datetime

from sqlalchemy import String, Float, Boolean, Text, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.identifiers import gen_uuid


# 规则种类（Palantir 风格的契约）
RULE_KINDS = (
    "freshness",        # 新鲜度：max_age_seconds（基于 schema_snapshot 列上的 freshness 探针）
    "row_count_min",    # 行数下限：min 阈值
    "row_count_max",    # 行数上限
    "null_ratio_max",   # 列空值率上限：column + max
    "pk_uniqueness",    # 主键唯一性：column 不重复（dup=0）
    "schema_stable",    # Schema 不漂移
)

# 状态聚合优先级（数字越大越严重）
STATUS_RANK = {"unknown": 0, "healthy": 1, "warning": 2, "failure": 3}


class QualityRule(Base):
    __tablename__ = "quality_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    asset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
        # see RULE_KINDS
    column_name: Mapped[str | None] = mapped_column(String(120))
        # null_ratio_max / pk_uniqueness / freshness 等"列级规则"用
    params: Mapped[dict] = mapped_column(JSON, default=dict)
        # {threshold: 0.05} 等规则参数
    severity: Mapped[str] = mapped_column(String(20), default="warning")
        # warning | failure  —— 触发阈值时的级别
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by: Mapped[str | None] = mapped_column(String(36))


Index("ix_quality_rule_asset_kind", QualityRule.asset_id, QualityRule.kind)


class HealthStatus(Base):
    __tablename__ = "health_statuses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    rule_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("quality_rules.id", ondelete="CASCADE"), index=True, nullable=False
    )
    asset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
        # healthy | warning | failure | unknown
    value_numeric: Mapped[float | None] = mapped_column(Float)
    message: Mapped[str | None] = mapped_column(Text)
    ran_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


Index("ix_health_rule_time", HealthStatus.rule_id, HealthStatus.ran_at.desc())
Index("ix_health_asset_time", HealthStatus.asset_id, HealthStatus.ran_at.desc())
