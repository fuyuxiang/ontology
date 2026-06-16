"""
AIP 场景平台 — 本体实例事件总线
- 业务代码在本体实例 CRUD 后调用 publish(entity_name, action, payload)
- 此处查所有 enabled=event 的触发器，匹配命中则丢入线程池执行
"""
from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from app.database import SessionLocal
from app.repositories import AipSceneTriggerRepository
from app.services.aip.scene_runner import run_scene_in_thread

logger = logging.getLogger(__name__)

_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="aip-event-")
_lock = threading.Lock()


def publish(entity_name: str, action: str, payload: dict | None = None) -> None:
    """业务侧调用：在本体实例 created/updated/deleted 后通知 AIP。"""
    if not entity_name or not action:
        return
    payload = payload or {}
    _pool.submit(_dispatch_safe, entity_name, action, payload)


def _dispatch_safe(entity_name: str, action: str, payload: dict) -> None:
    try:
        _dispatch(entity_name, action, payload)
    except Exception as e:
        logger.warning(f"[aip-event] dispatch 异常: {e}")


def _dispatch(entity_name: str, action: str, payload: dict) -> None:
    db = SessionLocal()
    try:
        repo = AipSceneTriggerRepository(db)
        triggers = repo.list_enabled(type_="event")
        for trg in triggers:
            if (trg.event_entity or "") != entity_name:
                continue
            if (trg.event_action or "") and (trg.event_action != action):
                continue
            with _lock:
                repo.mark_fired(trg)
                db.commit()
            logger.info(f"[aip-event] {entity_name}.{action} → 场景 {trg.scene_id}")
            _pool.submit(
                _run_safe, trg.scene_id,
                {"entity": entity_name, "action": action, "payload": payload},
            )
    finally:
        db.close()


def _run_safe(scene_id: str, trigger_payload: dict) -> None:
    try:
        run_scene_in_thread(scene_id, "event", trigger_payload, trigger_payload.get("payload") or {})
    except Exception as e:
        logger.warning(f"[aip-event] 场景执行异常 {scene_id}: {e}")
