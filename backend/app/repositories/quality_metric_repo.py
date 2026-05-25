"""QualityMetric 仓库。"""
from __future__ import annotations

from datetime import datetime

from app.models.quality_metric import QualityMetric
from app.repositories.base import BaseRepository


class QualityMetricRepository(BaseRepository[QualityMetric]):
    model = QualityMetric

    def list_for_asset(
        self,
        asset_id: str,
        *,
        kind: str | None = None,
        column_name: str | None = None,
        since: datetime | None = None,
        limit: int = 200,
    ) -> list[QualityMetric]:
        q = self.db.query(QualityMetric).filter(QualityMetric.asset_id == asset_id)
        if kind:
            q = q.filter(QualityMetric.kind == kind)
        if column_name:
            q = q.filter(QualityMetric.column_name == column_name)
        if since:
            q = q.filter(QualityMetric.measured_at >= since)
        return q.order_by(QualityMetric.measured_at.desc()).limit(limit).all()

    def latest(self, asset_id: str, kind: str, column_name: str | None = None) -> QualityMetric | None:
        q = self.db.query(QualityMetric).filter(
            QualityMetric.asset_id == asset_id,
            QualityMetric.kind == kind,
        )
        if column_name:
            q = q.filter(QualityMetric.column_name == column_name)
        return q.order_by(QualityMetric.measured_at.desc()).first()
