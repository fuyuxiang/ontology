"""AIP 场景平台 — Webhook 触发入口
- POST /api/v1/aip/webhooks/{path}
- 可选 X-AIP-Signature: HMAC-SHA256(secret, body)
- 命中后异步丢线程池跑场景；当场返回 ok
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import threading

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories import AipSceneTriggerRepository
from app.services.aip.scene_runner import run_scene_in_thread

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/aip/webhooks", tags=["aip-webhooks"])


def _verify_signature(secret: str, body: bytes, signature: str | None) -> bool:
    if not secret:
        return True  # 未配置 secret 视为不校验
    if not signature:
        return False
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.lower().replace("sha256=", ""))


@router.post("/{path}")
async def fire_webhook(
    path: str,
    request: Request,
    db: Session = Depends(get_db),
    x_signature: str | None = Header(default=None, alias="X-AIP-Signature"),
):
    repo = AipSceneTriggerRepository(db)
    trg = repo.get_by_webhook_path(path)
    if not trg:
        raise HTTPException(404, "Webhook 不存在")
    if not trg.enabled:
        raise HTTPException(403, "Webhook 已停用")
    if trg.type != "webhook":
        raise HTTPException(400, "触发器类型不匹配")

    body = await request.body()
    if not _verify_signature(trg.webhook_secret or "", body, x_signature):
        raise HTTPException(401, "签名无效")

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    repo.mark_fired(trg)
    db.commit()

    scene_id = trg.scene_id

    def _run():
        try:
            run_scene_in_thread(scene_id, "webhook", payload, payload if isinstance(payload, dict) else {"raw": payload})
        except Exception as e:
            logger.warning(f"[aip-webhook] 场景执行异常: {e}")

    threading.Thread(target=_run, daemon=True).start()
    return {"ok": True, "scene_id": scene_id, "queued": True}
