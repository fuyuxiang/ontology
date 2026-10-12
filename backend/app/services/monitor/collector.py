import asyncio
import logging
import shutil
import time

import psutil

from app.database import SessionLocal
from app.repositories.monitor_repo import MonitorRepository
from app.services.monitor.event_bus import event_bus
from app.services.monitor.ws_manager import ws_manager
from app.config import settings

logger = logging.getLogger(__name__)

# ── Service definitions ──

SERVICES = [
    {"name": "后端API", "check": "http", "url": f"http://127.0.0.1:{settings.PORT}/api/health"},
    {"name": "数据库", "check": "db"},
    {"name": "图数据库", "check": "neo4j"},
    {"name": "大模型网关", "check": "http", "url": settings.LLM_BASE_URL},
    {"name": "MinIO", "check": "minio"},
    {"name": "Redis", "check": "redis"},
]

_collector_tasks: list[asyncio.Task] = []
_alert_subscribed = False


async def _check_http(url: str, timeout: float = 3.0) -> tuple[str, float | None]:
    import httpx
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            start = time.monotonic()
            resp = await client.get(url)
            elapsed = (time.monotonic() - start) * 1000
            if resp.status_code < 400:
                return "healthy", round(elapsed, 1)
            return "warning", round(elapsed, 1)
    except Exception:
        return "unhealthy", None


async def _check_db() -> tuple[str, float | None]:
    def probe():
        from sqlalchemy import text
        with SessionLocal() as db:
            start = time.monotonic()
            db.execute(text("SELECT 1"))
            return "healthy", round((time.monotonic() - start) * 1000, 1)
    try:
        return await asyncio.to_thread(probe)
    except Exception:
        return "unhealthy", None


async def _check_neo4j() -> tuple[str, float | None]:
    def probe():
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            connection_timeout=3, connection_acquisition_timeout=3,
            max_transaction_retry_time=0)
        try:
            start = time.monotonic()
            with driver.session() as session:
                from neo4j import Query
                session.run(Query("RETURN 1", timeout=3)).consume()
            return "healthy", round((time.monotonic() - start) * 1000, 1)
        finally:
            driver.close()
    try:
        return await asyncio.to_thread(probe)
    except Exception:
        return "unhealthy", None


async def _check_minio() -> tuple[str, float | None]:
    def probe():
        from app.connectors.s3 import S3Connector
        from app.services.data_plane.storage_policy import storage_policy
        with SessionLocal() as db:
            policy = storage_policy(db)
        client = S3Connector()._client(policy, policy)
        try:
            start = time.monotonic()
            client.head_bucket(Bucket=policy["bucket"])
            return "healthy", round((time.monotonic() - start) * 1000, 1)
        finally:
            client.close()
    try:
        return await asyncio.to_thread(probe)
    except Exception:
        return "unhealthy", None


async def _check_redis() -> tuple[str, float | None]:
    def probe():
        import redis
        client = redis.from_url(settings.REDIS_URL, socket_timeout=3, socket_connect_timeout=3)
        try:
            start = time.monotonic()
            client.ping()
            return "healthy", round((time.monotonic() - start) * 1000, 1)
        finally:
            client.close()
    try:
        return await asyncio.to_thread(probe)
    except Exception:
        return "unhealthy", None


async def _check_service(svc: dict) -> tuple[str, str, float | None]:
    name = svc["name"]
    check = svc["check"]
    try:
        if check == "http":
            status, ms = await _check_http(svc["url"])
        elif check == "db":
            status, ms = await _check_db()
        elif check == "neo4j":
            status, ms = await _check_neo4j()
        elif check == "minio":
            status, ms = await _check_minio()
        elif check == "redis":
            status, ms = await _check_redis()
        else:
            raise ValueError(f"Unsupported health check: {check}")
    except Exception:
        status, ms = "unhealthy", None
    return name, status, ms


async def collect_service_metrics():
    while True:
        try:
            cpu = await asyncio.to_thread(psutil.cpu_percent, interval=0.1)
            mem = psutil.virtual_memory()
            disk = shutil.disk_usage("/")
            disk_pct = round(disk.used / disk.total * 100, 1) if disk.total else 0

            db = SessionLocal()
            repo = MonitorRepository(db)
            try:
                for svc in SERVICES:
                    name, status, ms = await _check_service(svc)
                    repo.save_metric(
                        service_name=name, status=status, response_ms=ms,
                        cpu_percent=cpu, memory_percent=mem.percent, disk_percent=disk_pct,
                    )
                logger.debug("Service metrics collected")
            finally:
                db.close()
        except Exception as e:
            logger.error("Metric collection error: %s", e, exc_info=True)

        await asyncio.sleep(30)


async def check_alerts():
    while True:
        try:
            db = SessionLocal()
            repo = MonitorRepository(db)
            try:
                metrics = repo.get_latest_metrics()
                for m in metrics:
                    if m.status == "unhealthy":
                        existing = repo.get_alerts(limit=100, resolved=False)
                        has_active = any(a.service_name == m.service_name and a.level == "critical" for a in existing)
                        if not has_active:
                            alert = repo.create_alert(
                                level="critical",
                                service_name=m.service_name,
                                message=f"{m.service_name} 服务不可达" if m.response_ms is None
                                        else f"{m.service_name} 响应超时 ({m.response_ms:.0f}ms)",
                            )
                            await event_bus.emit("alert", {
                                "id": alert.id, "level": alert.level,
                                "service_name": alert.service_name, "message": alert.message,
                                "created_at": alert.created_at.isoformat(),
                            })
                    elif m.status == "warning":
                        existing = repo.get_alerts(limit=100, resolved=False)
                        has_active = any(a.service_name == m.service_name and a.level == "warning" for a in existing)
                        if not has_active:
                            alert = repo.create_alert(
                                level="warning",
                                service_name=m.service_name,
                                message=f"{m.service_name} 响应较慢 ({m.response_ms:.0f}ms)",
                            )
                            await event_bus.emit("alert", {
                                "id": alert.id, "level": alert.level,
                                "service_name": alert.service_name, "message": alert.message,
                                "created_at": alert.created_at.isoformat(),
                            })
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Alert check error: {e}")

        await asyncio.sleep(30)


async def cleanup_old_data():
    while True:
        await asyncio.sleep(3600)
        try:
            db = SessionLocal()
            repo = MonitorRepository(db)
            try:
                repo.cleanup_old_metrics(days=7)
                repo.cleanup_old_alerts(days=30)
                logger.debug("Old monitor data cleaned up")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


async def start_collector():
    global _alert_subscribed
    if not settings.MONITOR_ENABLED or _collector_tasks:
        return
    _collector_tasks.extend(asyncio.create_task(task()) for task in
                            (collect_service_metrics, check_alerts, cleanup_old_data))
    ws_manager.start_heartbeat()
    logger.info("Monitor collector started")

    async def _on_alert(data: dict):
        await ws_manager.broadcast({"type": "alert", "data": data})

    if not _alert_subscribed:
        event_bus.subscribe("alert", _on_alert)
        _alert_subscribed = True


async def stop_collector():
    tasks, _collector_tasks[:] = list(_collector_tasks), []
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await ws_manager.stop()
