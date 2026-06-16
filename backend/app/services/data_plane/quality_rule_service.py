"""QualityRuleService — 规则评估 + 健康度聚合。

每条规则评估一次 = 一次探针 + 写一条 HealthStatus。
资产级聚合状态 = 该资产所有 enabled rule 当前 HealthStatus 取最差。
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.quality_rule import (
    RULE_KINDS,
    STATUS_RANK,
    HealthStatus,
    QualityRule,
)
from app.repositories.asset_repo import AssetRepository
from app.services.data_plane.probe_service import ProbeService

logger = logging.getLogger(__name__)


# 规则种类 → 模板默认参数（前端建规则时回填）
RULE_DEFAULTS: dict[str, dict] = {
    "freshness":      {"max_age_seconds": 86400},
    "row_count_min":  {"min": 1},
    "row_count_max":  {"max": 10_000_000},
    "null_ratio_max": {"max": 0.05},
    "pk_uniqueness":  {},
    "schema_stable":  {},
}


class QualityRuleService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.assets = AssetRepository(db)
        self.probe = ProbeService(db)

    # ── CRUD ────────────────────────────────────────────
    def list_rules(self, asset_id: str | None = None) -> list[QualityRule]:
        q = self.db.query(QualityRule)
        if asset_id:
            q = q.filter(QualityRule.asset_id == asset_id)
        return q.order_by(QualityRule.created_at.asc()).all()

    def get_rule(self, rule_id: str) -> QualityRule | None:
        return self.db.get(QualityRule, rule_id)

    def create_rule(self, *, asset_id: str, name: str, kind: str,
                    column_name: str | None = None, params: dict | None = None,
                    severity: str = "warning", description: str | None = None,
                    user_id: str | None = None) -> QualityRule:
        if kind not in RULE_KINDS:
            raise ValueError(f"未知规则类型: {kind}")
        if not self.assets.get_by_id(asset_id):
            raise LookupError(f"资产不存在: {asset_id}")
        if kind in ("null_ratio_max", "pk_uniqueness", "freshness") and not column_name:
            raise ValueError(f"规则 {kind} 必须指定 column_name")
        if severity not in ("warning", "failure"):
            raise ValueError("severity 取值: warning | failure")
        rule = QualityRule(
            asset_id=asset_id, name=name, kind=kind,
            column_name=column_name,
            params={**RULE_DEFAULTS.get(kind, {}), **(params or {})},
            severity=severity, enabled=True, description=description,
            created_by=user_id,
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def update_rule(self, rule_id: str, *, name: str | None = None,
                    params: dict | None = None, severity: str | None = None,
                    enabled: bool | None = None, description: str | None = None) -> QualityRule:
        rule = self._must_get(rule_id)
        if name is not None:
            rule.name = name
        if params is not None:
            rule.params = {**(rule.params or {}), **params}
        if severity is not None:
            if severity not in ("warning", "failure"):
                raise ValueError("severity 取值: warning | failure")
            rule.severity = severity
        if enabled is not None:
            rule.enabled = enabled
        if description is not None:
            rule.description = description
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def delete_rule(self, rule_id: str) -> None:
        rule = self._must_get(rule_id)
        self.db.delete(rule)
        self.db.commit()

    # ── 评估 ────────────────────────────────────────────
    def evaluate(self, rule_id: str) -> HealthStatus:
        rule = self._must_get(rule_id)
        return self._evaluate_rule(rule)

    def evaluate_asset(self, asset_id: str) -> list[HealthStatus]:
        rules = [r for r in self.list_rules(asset_id) if r.enabled]
        return [self._evaluate_rule(r) for r in rules]

    def evaluate_all(self) -> int:
        rules = self.db.query(QualityRule).filter(QualityRule.enabled.is_(True)).all()
        for r in rules:
            try:
                self._evaluate_rule(r)
            except Exception:
                logger.exception("evaluate_rule failed: rule_id=%s", r.id)
        return len(rules)

    # ── 健康度查询 ──────────────────────────────────────
    def latest_status(self, rule_id: str) -> HealthStatus | None:
        return (
            self.db.query(HealthStatus)
            .filter(HealthStatus.rule_id == rule_id)
            .order_by(desc(HealthStatus.ran_at))
            .first()
        )

    def history(self, rule_id: str, limit: int = 100) -> list[HealthStatus]:
        return (
            self.db.query(HealthStatus)
            .filter(HealthStatus.rule_id == rule_id)
            .order_by(desc(HealthStatus.ran_at))
            .limit(limit)
            .all()
        )

    def asset_aggregate_status(self, asset_id: str) -> dict:
        """聚合：取所有 enabled rule 最新状态里最严重的那一个。"""
        rules = [r for r in self.list_rules(asset_id) if r.enabled]
        if not rules:
            return {"status": "unknown", "rule_count": 0, "by_status": {}}
        statuses: list[str] = []
        by_status: dict[str, int] = {"healthy": 0, "warning": 0, "failure": 0, "unknown": 0}
        for r in rules:
            st = self.latest_status(r.id)
            s = st.status if st else "unknown"
            statuses.append(s)
            by_status[s] = by_status.get(s, 0) + 1
        # 取最严重那一个；优先级：failure > warning > unknown > healthy
        worst = max(statuses, key=lambda s: STATUS_RANK[s])
        return {"status": worst, "rule_count": len(rules), "by_status": by_status}

    # ── 内部 ────────────────────────────────────────────
    def _must_get(self, rule_id: str) -> QualityRule:
        r = self.db.get(QualityRule, rule_id)
        if not r:
            raise LookupError(f"规则不存在: {rule_id}")
        return r

    def _evaluate_rule(self, rule: QualityRule) -> HealthStatus:
        try:
            status, value, msg = self._run(rule)
        except Exception as e:
            logger.warning("rule %s 评估异常: %s", rule.id, e)
            status, value, msg = "unknown", None, f"评估失败: {e}"
        s = HealthStatus(
            rule_id=rule.id, asset_id=rule.asset_id,
            status=status, value_numeric=value, message=msg,
            ran_at=datetime.utcnow(),
        )
        self.db.add(s)
        self.db.commit()
        self.db.refresh(s)
        return s

    def _run(self, rule: QualityRule) -> tuple[str, float | None, str]:
        """跑一次规则评估，返回 (status, value, message)。"""
        params = rule.params or {}
        bad = rule.severity  # 触发阈值时是 warning 还是 failure
        if rule.kind == "row_count_min":
            m = self.probe.run(rule.asset_id, "row_count")
            v = m.value_numeric
            threshold = float(params.get("min", 1))
            if v is None:
                return "unknown", None, "无法取行数"
            if v < threshold:
                return bad, v, f"行数 {int(v)} < 最小阈值 {int(threshold)}"
            return "healthy", v, f"行数 {int(v)} ≥ {int(threshold)}"
        if rule.kind == "row_count_max":
            m = self.probe.run(rule.asset_id, "row_count")
            v = m.value_numeric
            threshold = float(params.get("max", 10_000_000))
            if v is None:
                return "unknown", None, "无法取行数"
            if v > threshold:
                return bad, v, f"行数 {int(v)} > 最大阈值 {int(threshold)}"
            return "healthy", v, f"行数 {int(v)} ≤ {int(threshold)}"
        if rule.kind == "null_ratio_max":
            m = self.probe.run(rule.asset_id, "null_ratio", column=rule.column_name)
            v = m.value_numeric
            threshold = float(params.get("max", 0.05))
            if v is None:
                return "unknown", None, "无法取空值率"
            if v > threshold:
                return bad, v, f"{rule.column_name} 空值率 {v:.2%} > {threshold:.2%}"
            return "healthy", v, f"{rule.column_name} 空值率 {v:.2%} ≤ {threshold:.2%}"
        if rule.kind == "pk_uniqueness":
            m = self.probe.run(rule.asset_id, "pk_uniqueness", column=rule.column_name)
            v = m.value_numeric
            if v is None:
                return "unknown", None, "无法取主键重复数"
            if v > 0:
                return bad, v, f"{rule.column_name} 重复 {int(v)} 行"
            return "healthy", v, f"{rule.column_name} 主键唯一"
        if rule.kind == "schema_stable":
            m = self.probe.run(rule.asset_id, "schema_drift")
            sev = m.severity  # ok / warning / error
            if sev == "ok":
                return "healthy", 0.0, "schema 稳定"
            if sev == "error":
                return "failure", 1.0, "schema 出现破坏性变更"
            return "warning", 0.5, "schema 有新增列"
        if rule.kind == "freshness":
            asset = self.assets.get_by_id(rule.asset_id)
            if not asset:
                return "unknown", None, "资产不存在"
            max_age = float(params.get("max_age_seconds", 86400))
            mu = (asset.profile or {}).get("max_updated_at") if asset.profile else None
            if not mu:
                return "unknown", None, "无 profile.max_updated_at（请先 profile）"
            try:
                ts = datetime.fromisoformat(mu) if isinstance(mu, str) else mu
                age = (datetime.utcnow() - ts).total_seconds()
            except Exception:
                return "unknown", None, "max_updated_at 无法解析"
            if age > max_age:
                return bad, age, f"陈旧 {int(age)}s（阈值 {int(max_age)}s）"
            return "healthy", age, f"新鲜（{int(age)}s 内）"
        return "unknown", None, f"未实现的规则类型: {rule.kind}"
