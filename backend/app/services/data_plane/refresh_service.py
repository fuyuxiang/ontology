"""Periodic source refresh using persisted schedules, real connectors and bounded reads.

The worker never executes business Actions, publishes versions, or commits MQ offsets.
Failures preserve the previous summary and persist an explicit failed refresh state.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timezone

from app.models.asset import Asset
from app.services.data_plane.asset_service import AssetService
from app.services.data_plane.event_bus import emit_after_commit

logger = logging.getLogger(__name__)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class DataPlaneRefresher:
    def __init__(self, db_factory, *, tick_seconds: float = 5) -> None:
        self.db_factory = db_factory
        self.tick_seconds = tick_seconds
        self._task = None
        self._stop = None

    @staticmethod
    def interval(asset: Asset) -> int | None:
        if asset.kind == "document" and asset.document_source_type in {"api", "mq"}:
            raw = (asset.locator or {}).get("poll_interval", 60)
            if isinstance(raw, bool) or not isinstance(raw, int) or raw < 10:
                raise ValueError("poll_interval 必须为至少 10 秒的整数")
            return raw
        return {"hourly": 3600, "daily": 86400}.get(asset.refresh_policy)

    @classmethod
    def due(cls, asset: Asset, now: datetime) -> bool:
        interval = cls.interval(asset)
        if interval is None:
            return False
        previous = ((asset.profile or {}).get("source_refresh") or {}).get("at")
        try:
            last = datetime.fromisoformat(previous.replace("Z", "+00:00")) if previous else asset.created_at
        except (ValueError, TypeError):
            last = None
        return last is None or (_utc(now) - _utc(last)).total_seconds() >= interval

    def refresh_due(self, *, now: datetime | None = None) -> dict:
        now = _utc(now or datetime.now(timezone.utc))
        completed, failed, skipped = [], [], []
        with self.db_factory() as db:
            ids = []
            for asset in db.query(Asset).filter(Asset.status == "active").all():
                try:
                    if self.due(asset, now):
                        ids.append(asset.id)
                except ValueError:
                    # Persist invalid legacy schedules instead of silently disabling them.
                    # Bound retries of an invalid schedule as well; otherwise one old
                    # row produces a DB write/event every polling tick indefinitely.
                    previous = ((asset.profile or {}).get("source_refresh") or {}).get("at")
                    try:
                        last = datetime.fromisoformat(previous.replace("Z", "+00:00")) if previous else None
                    except (ValueError, TypeError):
                        last = None
                    if last is None or (now - _utc(last)).total_seconds() >= 60:
                        ids.append(asset.id)
        for asset_id in ids:
            with self.db_factory() as db:
                asset = db.get(Asset, asset_id)
                if not asset or asset.status != "active":
                    skipped.append(asset_id)
                    continue
                prior = dict((asset.profile or {}).get("source_refresh") or {})
                before_digest = prior.get("content_sha256")
                try:
                    self.interval(asset)
                    service = AssetService(db)
                    if asset.kind == "document":
                        service.preview(asset.id, limit=200)
                    else:
                        service.sync_schema(asset.id)
                        service.profile(asset.id)
                        from app.services.data_plane.quality_rule_service import QualityRuleService
                        QualityRuleService(db).evaluate_asset(asset.id)
                    after = dict((asset.profile or {}).get("source_refresh") or {})
                    digest = after.get("content_sha256")
                    if not digest:
                        import json
                        profile = asset.profile or {}
                        payload = json.dumps({"schema": asset.schema_snapshot,
                            "row_count": profile.get("row_count"), "null_ratio": profile.get("null_ratio")}, sort_keys=True, default=str)
                        digest = hashlib.sha256(payload.encode()).hexdigest()
                    asset.profile = {**(asset.profile or {}), "source_refresh": {
                        "status": "ok", "at": now.isoformat(), "last_success": now.isoformat(),
                        "error": None, "content_sha256": digest}}
                    emit_after_commit(db, "asset.refreshed", {"asset_id": asset.id})
                    if before_digest and before_digest != digest:
                        emit_after_commit(db, "asset.content.changed", {"asset_id": asset.id})
                    db.commit()
                    completed.append(asset_id)
                except Exception as exc:
                    db.rollback()
                    asset = db.get(Asset, asset_id)
                    if not asset:
                        skipped.append(asset_id)
                        continue
                    # Connector exceptions may include endpoint query credentials. Only
                    # safe validation messages and exception types enter persistent UI state.
                    detail = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
                    asset.profile = {**(asset.profile or {}), "source_refresh": {
                        **prior, "status": "error", "at": now.isoformat(), "error": detail}}
                    emit_after_commit(db, "asset.refresh.failed", {"asset_id": asset.id, "error": detail})
                    db.commit()
                    failed.append(asset_id)
        return {"completed": completed, "failed": failed, "skipped": skipped}

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop = asyncio.Event()
        self._task = asyncio.create_task(self._run(), name="data-plane-source-refresh")

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                await asyncio.to_thread(self.refresh_due)
            except Exception:
                logger.exception("Data Plane refresh cycle failed")
            if self._stop.is_set():
                break
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.tick_seconds)
            except asyncio.TimeoutError:
                pass

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stop.set()
        # Let an in-flight bounded source read finish before closing its DB session.
        await self._task
        self._task = None


_refresher: DataPlaneRefresher | None = None


async def start_refresher(*, db_factory=None) -> bool:
    from app.config import settings
    if not getattr(settings, "DATA_PLANE_REFRESH_ENABLED", True):
        return False
    if db_factory is None:
        from app.database import SessionLocal
        db_factory = SessionLocal
    global _refresher
    if _refresher is None:
        _refresher = DataPlaneRefresher(db_factory)
    await _refresher.start()
    return True


async def stop_refresher() -> None:
    global _refresher
    if _refresher is not None:
        await _refresher.stop()
        _refresher = None
