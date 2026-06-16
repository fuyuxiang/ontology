"""
AIP 场景平台 — 轻量级定时调度器
- 后台单线程，每分钟检查一次所有 enabled=schedule 的触发器
- 支持 5-field cron（不依赖外部包）
- 触发到时丢到线程池跑场景，避免阻塞调度器
"""
from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from app.database import SessionLocal
from app.models.scene import AipSceneTrigger
from app.repositories import AipSceneTriggerRepository
from app.services.aip.scene_runner import run_scene_in_thread

logger = logging.getLogger(__name__)


# ── Cron 解析 ─────────────────────────────────────────────────

def _parse_field(field: str, lo: int, hi: int) -> set[int]:
    out: set[int] = set()
    for part in field.split(","):
        part = part.strip()
        step = 1
        if "/" in part:
            base, step_s = part.split("/", 1)
            step = int(step_s)
        else:
            base = part
        if base == "*":
            start, end = lo, hi
        elif "-" in base:
            a, b = base.split("-", 1)
            start, end = int(a), int(b)
        else:
            v = int(base)
            out.add(v)
            continue
        for v in range(start, end + 1, step):
            if lo <= v <= hi:
                out.add(v)
    return out


def cron_match(cron_expr: str, now: datetime) -> bool:
    """5-field cron: minute hour day-of-month month day-of-week (0=Sunday)"""
    try:
        m, h, dom, mo, dow = cron_expr.strip().split()
    except ValueError:
        return False
    try:
        return (
            now.minute in _parse_field(m, 0, 59)
            and now.hour in _parse_field(h, 0, 23)
            and now.day in _parse_field(dom, 1, 31)
            and now.month in _parse_field(mo, 1, 12)
            # Python weekday: Mon=0..Sun=6 → cron: 0/7=Sun, 1=Mon..6=Sat
            and ((now.weekday() + 1) % 7) in _parse_field(dow.replace("7", "0"), 0, 6)
        )
    except Exception:
        return False


# ── 调度器单例 ───────────────────────────────────────────────

class SceneScheduler:
    def __init__(self):
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="aip-job-")
        # 防同一分钟内重复触发
        self._last_fired: dict[str, str] = {}

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="aip-scheduler")
        self._thread.start()
        logger.info("[aip-scheduler] 启动")

    def stop(self):
        self._stop.set()
        self._pool.shutdown(wait=False)

    def _loop(self):
        # 启动时先睡到下一分钟边界
        time.sleep(max(0.0, 60 - datetime.utcnow().second))
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception as e:
                logger.warning(f"[aip-scheduler] tick 异常: {e}")
            # 每 30 秒滚动一次（足够支撑分钟级 cron）
            self._stop.wait(30)

    def _tick(self):
        db = SessionLocal()
        try:
            repo = AipSceneTriggerRepository(db)
            triggers = repo.list_enabled(type_="schedule")
            now = datetime.now()
            now_key = now.strftime("%Y%m%d%H%M")
            for trg in triggers:
                if not trg.cron_expr:
                    continue
                if self._last_fired.get(trg.id) == now_key:
                    continue
                if cron_match(trg.cron_expr, now):
                    self._last_fired[trg.id] = now_key
                    repo.mark_fired(trg)
                    db.commit()
                    logger.info(f"[aip-scheduler] 触发场景 {trg.scene_id} (cron={trg.cron_expr})")
                    self._pool.submit(self._safe_run, trg.scene_id)
        finally:
            db.close()

    def _safe_run(self, scene_id: str):
        try:
            run_scene_in_thread(scene_id, "schedule", {}, {})
        except Exception as e:
            logger.warning(f"[aip-scheduler] 场景执行异常 {scene_id}: {e}")


_scheduler = SceneScheduler()


def get_scheduler() -> SceneScheduler:
    return _scheduler


def start_scheduler() -> None:
    _scheduler.start()


def stop_scheduler() -> None:
    _scheduler.stop()


def sync_trigger_job(trigger: AipSceneTrigger) -> None:
    """目前是无状态轮询模式，无需注册。保留接口以便未来切换为 APScheduler。"""
    return None


def remove_trigger_job(trigger: AipSceneTrigger) -> None:
    return None
