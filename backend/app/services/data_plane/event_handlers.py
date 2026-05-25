"""跨模块事件订阅 — 把 EventBus 与 Lineage / 治理动作连起来。

通过显式 `register_event_handlers()` 在应用启动时调用一次，避免循环 import。

订阅清单：
- binding.created  → LineageService.upsert_binding
- binding.deleted  → LineageService.deprecate_binding
- execution.completed → LineageService.upsert_execution（按 purpose 白名单）
- asset.schema.changed → 把受影响的 ObjectBinding 标"needs_review"
"""
from __future__ import annotations

import logging

from app.database import SessionLocal
from app.repositories.object_binding_repo import ObjectBindingRepository
from app.services.data_plane.event_bus import get_event_bus
from app.services.data_plane.lineage_service import LineageService

logger = logging.getLogger(__name__)

_registered = False


def register_event_handlers() -> None:
    global _registered
    if _registered:
        return
    _registered = True
    bus = get_event_bus()

    bus.subscribe("binding.created", _on_binding_created)
    bus.subscribe("binding.updated", _on_binding_updated)
    bus.subscribe("binding.deleted", _on_binding_deleted)
    bus.subscribe("execution.completed", _on_execution_completed, async_=True)
    bus.subscribe("asset.schema.changed", _on_schema_changed)


# ── handlers ──────────────────────────────────────────────────

def _with_db(fn):
    db = SessionLocal()
    try:
        return fn(db)
    finally:
        db.close()


def _on_binding_created(env: dict) -> None:
    asset_id = env.get("asset_id")
    object_type_id = env.get("object_type_id")
    if not (asset_id and object_type_id):
        return

    def _do(db):
        LineageService(db).upsert_binding(asset_id, object_type_id)
    _with_db(_do)


def _on_binding_updated(env: dict) -> None:
    asset_id = env.get("asset_id")
    object_type_id = env.get("object_type_id")
    if not (asset_id and object_type_id):
        return

    def _do(db):
        LineageService(db).upsert_binding(asset_id, object_type_id)
    _with_db(_do)


def _on_binding_deleted(env: dict) -> None:
    asset_id = env.get("asset_id")
    object_type_id = env.get("object_type_id")
    if not (asset_id and object_type_id):
        return

    def _do(db):
        LineageService(db).deprecate_binding(asset_id, object_type_id)
    _with_db(_do)


def _on_execution_completed(env: dict) -> None:
    asset_id = env.get("asset_id")
    purpose = env.get("purpose")
    if not (asset_id and purpose):
        return

    def _do(db):
        LineageService(db).upsert_execution(asset_id, purpose)
    try:
        _with_db(_do)
    except Exception:
        logger.exception("on_execution_completed failed")


def _on_schema_changed(env: dict) -> None:
    """把绑定到这个 Asset 的 binding 标 needs_review。"""
    asset_id = env.get("asset_id")
    diff = env.get("diff") or {}
    if not asset_id:
        return
    severity_breaks_binding = bool(diff.get("removed") or diff.get("type_changed"))
    if not severity_breaks_binding:
        return

    def _do(db):
        repo = ObjectBindingRepository(db)
        for b in repo.list(asset_id=asset_id, status="active"):
            b.status = "needs_review"
            b.review_reason = f"asset schema changed: {diff}"
        db.commit()
    try:
        _with_db(_do)
    except Exception:
        logger.exception("on_schema_changed failed")
