"""ProbeService — Asset 治理探针。

把 resolution.py 中现写的探针 SQL 抽成模板，统一通过 ExecuteService 跑。
所有结果落入 quality_metrics 表，由前端"数据质量"页只读展示。

模板使用 :param 占位（与 ExecuteService 一致），<asset> 由 ExecuteService 改写为表名。
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.quality_metric import QualityMetric
from app.repositories.asset_repo import AssetRepository
from app.repositories.quality_metric_repo import QualityMetricRepository
from app.services.data_plane.execute_service import ExecuteRequest, ExecuteService

logger = logging.getLogger(__name__)


PROBE_TEMPLATES: dict[str, str] = {
    "row_count":     "SELECT COUNT(*) AS n FROM <asset>",
    "freshness":     "SELECT MAX({col}) AS v FROM <asset>",
    "null_ratio":    "SELECT SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END)*1.0/NULLIF(COUNT(*),0) AS r FROM <asset>",
    "distinct_count":"SELECT COUNT(DISTINCT {col}) AS n FROM <asset>",
    "pk_uniqueness": "SELECT COUNT(*) - COUNT(DISTINCT {col}) AS dup FROM <asset>",
}


def _quote_col(col: str) -> str:
    """简单合法性校验，防止把 column 当 SQL 注入。"""
    if not col or not all(ch.isalnum() or ch == "_" for ch in col):
        raise ValueError(f"非法列名: {col}")
    return col


class ProbeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.assets = AssetRepository(db)
        self.metrics = QualityMetricRepository(db)
        self.exec_svc = ExecuteService(db)

    def run(
        self,
        asset_id: str,
        kind: str,
        *,
        column: str | None = None,
        threshold: float | None = None,
    ) -> QualityMetric:
        asset = self.assets.get_by_id(asset_id)
        if not asset:
            raise LookupError(f"资产不存在: {asset_id}")
        if kind == "schema_drift":
            return self._run_schema_drift(asset)
        if kind not in PROBE_TEMPLATES:
            raise ValueError(f"未知探针类型: {kind}")
        if kind in ("freshness", "null_ratio", "distinct_count", "pk_uniqueness") and not column:
            raise ValueError(f"探针 {kind} 需要 column")

        sql = PROBE_TEMPLATES[kind].format(col=_quote_col(column) if column else "")
        result = self.exec_svc.execute(ExecuteRequest(
            asset_id=asset_id, sql=sql, params={}, purpose=f"probe.{kind}",
            bypass_cache=True,
        ))
        v: Any = result.rows[0][0] if result.rows else None
        return self._record(asset_id, kind, column, v, threshold)

    def latest(self, asset_id: str, kind: str, column: str | None = None) -> QualityMetric | None:
        return self.metrics.latest(asset_id, kind, column)

    def history(self, asset_id: str, *, kind: str | None = None, column: str | None = None,
                limit: int = 200) -> list[QualityMetric]:
        return self.metrics.list_for_asset(asset_id, kind=kind, column_name=column, limit=limit)

    # ── 内部 ─────────────────────────────────────────
    def _run_schema_drift(self, asset: Asset) -> QualityMetric:
        from app.services.data_plane.asset_service import AssetService
        result = AssetService(self.db).sync_schema(asset.id)
        diff = result.get("diff", {})
        severity = "ok"
        if diff.get("removed") or diff.get("type_changed"):
            severity = "error"
        elif diff.get("added"):
            severity = "warning"
        m = QualityMetric(
            asset_id=asset.id,
            kind="schema_drift",
            value_text=str(diff),
            severity=severity,
            measured_at=datetime.utcnow(),
        )
        self.db.add(m)
        self.db.commit()
        self.db.refresh(m)
        return m

    def _record(self, asset_id: str, kind: str, column: str | None,
                value: Any, threshold: float | None) -> QualityMetric:
        # 数值化
        try:
            num = float(value) if value is not None else None
        except Exception:
            num = None
        text = None if num is not None else (str(value) if value is not None else None)
        severity = "ok"
        if threshold is not None and num is not None:
            if kind == "null_ratio" and num > threshold:
                severity = "warning"
            elif kind == "pk_uniqueness" and num > threshold:
                severity = "error"
        m = QualityMetric(
            asset_id=asset_id,
            kind=kind,
            column_name=column,
            value_numeric=num,
            value_text=text,
            threshold=threshold,
            severity=severity,
            measured_at=datetime.utcnow(),
        )
        self.db.add(m)
        self.db.commit()
        self.db.refresh(m)
        return m
