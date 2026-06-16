"""/events/sse — 跨模块事件流。

前端订阅 SSE，接 EventBus 派发的实时事件用于 store invalidate / toast 通知。
"""
from __future__ import annotations

import json
import logging
import queue
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from app.services.data_plane.event_bus import get_event_bus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["data-plane:events"])


@router.get("/sse")
async def stream_events(request: Request, topics: str | None = None):
    bus = get_event_bus()
    sink: queue.Queue = queue.Queue(maxsize=512)
    bus.subscribe_sse(sink)

    wanted = set(t.strip() for t in (topics or "").split(",") if t.strip())

    async def gen() -> AsyncIterator[dict]:
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    env = sink.get(timeout=1.0)
                except queue.Empty:
                    # 心跳，保持连接
                    yield {"event": "ping", "data": "{}"}
                    continue
                event = env.get("event", "")
                if wanted and not _topic_match(event, wanted):
                    continue
                yield {
                    "event": event,
                    "data": json.dumps(env, ensure_ascii=False, default=str),
                }
        finally:
            bus.unsubscribe_sse(sink)

    return EventSourceResponse(gen())


def _topic_match(event: str, wanted: set[str]) -> bool:
    if event in wanted:
        return True
    for w in wanted:
        if w.endswith(".*") and event.startswith(w[:-1]):
            return True
    return False
