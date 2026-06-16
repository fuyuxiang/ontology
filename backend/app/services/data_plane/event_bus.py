"""进程内事件总线 — 数据集成 / 建模 / AI 召回三模块跨域事件。

设计：
- 单例进程内 pub/sub，subscribe(event, handler, async_=False)
- emit 默认同步派发；handler 独立 try/except，失败不影响主路径
- async_=True 的 handler 在 FastAPI BackgroundTasks 里跑（非阻塞）
- 同时 fan-out 到 SSE sink（被 /events/sse 端点消费），让前端实时收到事件

事件命名约定：
- asset.*           （asset.created / asset.schema.changed / asset.deprecated / asset.profile.completed）
- binding.*         （binding.created / binding.updated / binding.deleted）
- execution.*       （execution.completed / execution.blocked）
- connection.*      （connection.test.failed / connection.updated.password）

事件 payload 必含字段：event_id (uuid), ts (epoch_ms)；其余按事件类型自由。
"""
from __future__ import annotations

import logging
import queue
import threading
import time
import uuid
from collections import defaultdict
from collections.abc import Callable

logger = logging.getLogger(__name__)

EventHandler = Callable[[dict], None]


class EventBus:
    def __init__(self) -> None:
        self._sync_handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._async_handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._sse_sinks: list[queue.Queue] = []
        self._lock = threading.Lock()

    # ── 订阅 ──────────────────────────────────────────────
    def subscribe(self, event: str, handler: EventHandler, *, async_: bool = False) -> None:
        target = self._async_handlers if async_ else self._sync_handlers
        with self._lock:
            target[event].append(handler)

    def subscribe_sse(self, sink: queue.Queue) -> None:
        with self._lock:
            self._sse_sinks.append(sink)

    def unsubscribe_sse(self, sink: queue.Queue) -> None:
        with self._lock:
            if sink in self._sse_sinks:
                self._sse_sinks.remove(sink)

    # ── 派发 ──────────────────────────────────────────────
    def emit(self, event: str, payload: dict | None = None) -> None:
        envelope = {
            "event": event,
            "event_id": uuid.uuid4().hex,
            "ts": int(time.time() * 1000),
            **(payload or {}),
        }

        # 同步 handler（关键路径：lineage / asset_usage 等必须落库）
        for h in list(self._sync_handlers.get(event, [])) + self._wildcard_handlers(event, self._sync_handlers):
            try:
                h(envelope)
            except Exception:
                logger.exception("sync event handler failed: event=%s", event)

        # 异步 handler（通知 / 缓存失效 / 监控统计）
        for h in list(self._async_handlers.get(event, [])) + self._wildcard_handlers(event, self._async_handlers):
            t = threading.Thread(target=self._safe_call, args=(h, envelope), daemon=True)
            t.start()

        # SSE 扇出
        with self._lock:
            sinks = list(self._sse_sinks)
        for s in sinks:
            try:
                s.put_nowait(envelope)
            except queue.Full:
                # 单连接消费过慢 — 丢一条事件，不阻塞 emit
                logger.warning("SSE sink full, dropping event=%s", event)

    @staticmethod
    def _safe_call(handler: EventHandler, envelope: dict) -> None:
        try:
            handler(envelope)
        except Exception:
            logger.exception("async event handler failed: event=%s", envelope.get("event"))

    @staticmethod
    def _wildcard_handlers(event: str, table: dict[str, list[EventHandler]]) -> list[EventHandler]:
        """支持 'asset.*' 这类通配订阅。"""
        if "." not in event:
            return []
        prefix = event.split(".", 1)[0] + ".*"
        return list(table.get(prefix, []))


# ── 单例工厂 ──────────────────────────────────────────────
_bus_singleton: EventBus | None = None


def get_event_bus() -> EventBus:
    global _bus_singleton
    if _bus_singleton is None:
        _bus_singleton = EventBus()
    return _bus_singleton
