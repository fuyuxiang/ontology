# System Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full-featured system dashboard page with real-time monitoring, WebSocket alerts, LLM call tracking, and historical metrics.

**Architecture:** Independent monitoring service layer (`services/monitor/`) with event bus, WebSocket manager, and periodic collector. Frontend uses ECharts + Ant Design Vue with REST polling + WebSocket for real-time data.

**Tech Stack:** FastAPI, SQLAlchemy, asyncio, WebSocket, Vue 3, ECharts, Ant Design Vue

---

## File Structure

### Backend (Create)

| File | Responsibility |
|------|---------------|
| `backend/app/models/monitor.py` | ORM: ServiceMetric, LLMCallRecord, Alert |
| `backend/app/repositories/monitor_repo.py` | Data access for monitor tables |
| `backend/app/services/monitor/__init__.py` | Package init |
| `backend/app/services/monitor/event_bus.py` | Async event bus |
| `backend/app/services/monitor/ws_manager.py` | WebSocket connection manager |
| `backend/app/services/monitor/collector.py` | Periodic metric collection + alerting |
| `backend/app/schemas/monitor.py` | Pydantic response models |

### Backend (Modify)

| File | Change |
|------|--------|
| `backend/app/models/__init__.py` | Register new models |
| `backend/app/repositories/__init__.py` | Register new repo |
| `backend/app/api/v1/monitor.py` | Expand with 6 new endpoints |
| `backend/app/main.py` | Start collector + mount WebSocket |

### Frontend (Create)

| File | Responsibility |
|------|---------------|
| `frontend/src/composables/useMonitorWS.ts` | WebSocket composable |
| `frontend/src/views/dashboard/components/ServiceHealthCards.vue` | Service health cards |
| `frontend/src/views/dashboard/components/ResourceGauges.vue` | CPU/Memory/Disk gauges |
| `frontend/src/views/dashboard/components/ResponseTimeChart.vue` | Response time line chart |
| `frontend/src/views/dashboard/components/AlertTable.vue` | Alert list table |
| `frontend/src/views/dashboard/components/EventStream.vue` | System event stream |
| `frontend/src/views/dashboard/components/OntologyStats.vue` | Ontology count stats |
| `frontend/src/views/dashboard/components/LLMCallStats.vue` | LLM call volume |
| `frontend/src/views/dashboard/components/AgentActivity.vue` | Agent activity |

### Frontend (Modify)

| File | Change |
|------|--------|
| `frontend/src/api/monitor.ts` | Add new API calls |
| `frontend/src/views/dashboard/SystemDashboardView.vue` | Replace PlaceholderView |

---

## Task 1: Backend Data Models

**Files:**
- Create: `backend/app/models/monitor.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create monitor models**

Create `backend/app/models/monitor.py`:

```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, Index
from app.database import Base


class ServiceMetric(Base):
    __tablename__ = "t_service_metric"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_name = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default="healthy")  # healthy / warning / unhealthy
    response_ms = Column(Float, nullable=True)
    cpu_percent = Column(Float, nullable=True)
    memory_percent = Column(Float, nullable=True)
    disk_percent = Column(Float, nullable=True)
    collected_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_service_metric_collected_at", "collected_at"),
        Index("ix_service_metric_service_name", "service_name"),
    )


class LLMCallRecord(Base):
    __tablename__ = "t_llm_call_record"

    id = Column(Integer, primary_key=True, autoincrement=True)
    caller_module = Column(String(50), nullable=False)  # copilot / agent / builder / rule_engine
    model_name = Column(String(100), nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    latency_ms = Column(Float, nullable=True)
    success = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_llm_call_created_at", "created_at"),
        Index("ix_llm_call_caller_module", "caller_module"),
    )


class Alert(Base):
    __tablename__ = "t_alert"

    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String(20), nullable=False)  # critical / warning / info
    service_name = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_alert_created_at", "created_at"),
        Index("ix_alert_resolved", "resolved"),
    )
```

- [ ] **Step 2: Register models in __init__.py**

Edit `backend/app/models/__init__.py`, add after the last import:

```python
from app.models.monitor import ServiceMetric, LLMCallRecord, Alert
```

And add to `__all__`:

```python
"ServiceMetric", "LLMCallRecord", "Alert",
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/monitor.py backend/app/models/__init__.py
git commit -m "feat(monitor): add ServiceMetric, LLMCallRecord, Alert ORM models"
```

---

## Task 2: Backend Repository

**Files:**
- Create: `backend/app/repositories/monitor_repo.py`
- Modify: `backend/app/repositories/__init__.py`

- [ ] **Step 1: Create monitor repository**

Create `backend/app/repositories/monitor_repo.py`:

```python
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.monitor import ServiceMetric, LLMCallRecord, Alert


class MonitorRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Service Metrics ──

    def save_metric(self, service_name: str, status: str, response_ms: float | None = None,
                    cpu_percent: float | None = None, memory_percent: float | None = None,
                    disk_percent: float | None = None) -> ServiceMetric:
        m = ServiceMetric(
            service_name=service_name, status=status, response_ms=response_ms,
            cpu_percent=cpu_percent, memory_percent=memory_percent, disk_percent=disk_percent,
        )
        self.db.add(m)
        self.db.commit()
        return m

    def get_latest_metrics(self) -> list[ServiceMetric]:
        """Get the latest metric for each service."""
        subq = (
            self.db.query(
                ServiceMetric.service_name,
                func.max(ServiceMetric.id).label("max_id"),
            )
            .group_by(ServiceMetric.service_name)
            .subquery()
        )
        rows = (
            self.db.query(ServiceMetric)
            .join(subq, ServiceMetric.id == subq.c.max_id)
            .all()
        )
        return rows

    def get_metric_history(self, hours: int = 1, service_name: str | None = None) -> list[ServiceMetric]:
        """Get metric history for the last N hours."""
        since = datetime.utcnow() - timedelta(hours=hours)
        q = self.db.query(ServiceMetric).filter(ServiceMetric.collected_at >= since)
        if service_name:
            q = q.filter(ServiceMetric.service_name == service_name)
        return q.order_by(ServiceMetric.collected_at.asc()).all()

    # ── LLM Calls ──

    def save_llm_call(self, caller_module: str, model_name: str | None = None,
                      prompt_tokens: int | None = None, completion_tokens: int | None = None,
                      latency_ms: float | None = None, success: bool = True) -> LLMCallRecord:
        r = LLMCallRecord(
            caller_module=caller_module, model_name=model_name,
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
            latency_ms=latency_ms, success=success,
        )
        self.db.add(r)
        self.db.commit()
        return r

    def get_llm_stats_24h(self) -> dict:
        """Get LLM call statistics for the last 24 hours."""
        since = datetime.utcnow() - timedelta(hours=24)
        rows = (
            self.db.query(
                LLMCallRecord.caller_module,
                func.count(LLMCallRecord.id).label("count"),
                func.sum(LLMCallRecord.prompt_tokens).label("total_prompt_tokens"),
                func.sum(LLMCallRecord.completion_tokens).label("total_completion_tokens"),
                func.avg(LLMCallRecord.latency_ms).label("avg_latency_ms"),
            )
            .filter(LLMCallRecord.created_at >= since)
            .group_by(LLMCallRecord.caller_module)
            .all()
        )
        total = sum(r.count for r in rows)
        by_module = {}
        for r in rows:
            by_module[r.caller_module] = {
                "count": r.count,
                "total_prompt_tokens": int(r.total_prompt_tokens or 0),
                "total_completion_tokens": int(r.total_completion_tokens or 0),
                "avg_latency_ms": round(float(r.avg_latency_ms or 0), 1),
            }
        return {"total_24h": total, "by_module": by_module}

    # ── Alerts ──

    def create_alert(self, level: str, service_name: str, message: str) -> Alert:
        a = Alert(level=level, service_name=service_name, message=message)
        self.db.add(a)
        self.db.commit()
        self.db.refresh(a)
        return a

    def get_alerts(self, limit: int = 20, resolved: bool | None = None,
                   level: str | None = None) -> list[Alert]:
        q = self.db.query(Alert)
        if resolved is not None:
            q = q.filter(Alert.resolved == resolved)
        if level:
            q = q.filter(Alert.level == level)
        return q.order_by(desc(Alert.created_at)).limit(limit).all()

    def resolve_alert(self, alert_id: int) -> Alert | None:
        a = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if a:
            a.resolved = True
            a.resolved_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(a)
        return a

    # ── Cleanup ──

    def cleanup_old_metrics(self, days: int = 7):
        cutoff = datetime.utcnow() - timedelta(days=days)
        self.db.query(ServiceMetric).filter(ServiceMetric.collected_at < cutoff).delete()
        self.db.commit()

    def cleanup_old_alerts(self, days: int = 30):
        cutoff = datetime.utcnow() - timedelta(days=days)
        self.db.query(Alert).filter(Alert.created_at < cutoff).delete()
        self.db.commit()
```

- [ ] **Step 2: Register repository**

Edit `backend/app/repositories/__init__.py`, add import:

```python
from app.repositories.monitor_repo import MonitorRepository
```

Add `"MonitorRepository"` to `__all__`.

- [ ] **Step 3: Commit**

```bash
git add backend/app/repositories/monitor_repo.py backend/app/repositories/__init__.py
git commit -m "feat(monitor): add MonitorRepository with metric/alert/LLM CRUD"
```

---

## Task 3: Backend Event Bus

**Files:**
- Create: `backend/app/services/monitor/__init__.py`
- Create: `backend/app/services/monitor/event_bus.py`

- [ ] **Step 1: Create package init**

Create `backend/app/services/monitor/__init__.py`:

```python
```

- [ ] **Step 2: Create event bus**

Create `backend/app/services/monitor/event_bus.py`:

```python
import asyncio
import logging
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)

EventHandler = Callable[[dict], Awaitable[None]]


class EventBus:
    """Simple async event bus for decoupled module communication."""

    def __init__(self):
        self._subscribers: dict[str, list[EventHandler]] = {}

    def subscribe(self, event_type: str, handler: EventHandler):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    async def emit(self, event_type: str, data: dict[str, Any]):
        handlers = self._subscribers.get(event_type, [])
        for handler in handlers:
            try:
                asyncio.create_task(handler(data))
            except Exception as e:
                logger.error(f"EventBus error dispatching {event_type}: {e}")


# Global singleton
event_bus = EventBus()
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/monitor/
git commit -m "feat(monitor): add async EventBus singleton"
```

---

## Task 4: Backend WebSocket Manager

**Files:**
- Create: `backend/app/services/monitor/ws_manager.py`

- [ ] **Step 1: Create WebSocket manager**

Create `backend/app/services/monitor/ws_manager.py`:

```python
import asyncio
import json
import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class MonitorWSManager:
    """Manages WebSocket connections for the system dashboard."""

    def __init__(self):
        self._connections: list[WebSocket] = []
        self._heartbeat_task: asyncio.Task | None = None

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections.append(ws)
        logger.info(f"Monitor WS connected, total: {len(self._connections)}")

    def disconnect(self, ws: WebSocket):
        if ws in self._connections:
            self._connections.remove(ws)
        logger.info(f"Monitor WS disconnected, total: {len(self._connections)}")

    async def broadcast(self, data: dict):
        dead = []
        for ws in self._connections:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    def start_heartbeat(self, interval: int = 30):
        if self._heartbeat_task is None:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(interval))

    async def _heartbeat_loop(self, interval: int):
        while True:
            await asyncio.sleep(interval)
            await self.broadcast({"type": "ping"})
            # Clean up connections that failed during broadcast
            # (disconnect is called in broadcast on error)


# Global singleton
ws_manager = MonitorWSManager()
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/monitor/ws_manager.py
git commit -m "feat(monitor): add MonitorWSManager with heartbeat"
```

---

## Task 5: Backend Data Collector

**Files:**
- Create: `backend/app/services/monitor/collector.py`

- [ ] **Step 1: Create collector**

Create `backend/app/services/monitor/collector.py`:

```python
import asyncio
import logging
import time

import psutil

from app.database import SessionLocal
from app.repositories.monitor_repo import MonitorRepository
from app.services.monitor.event_bus import event_bus
from app.services.monitor.ws_manager import ws_manager

logger = logging.getLogger(__name__)

# ── Service definitions ──

SERVICES = [
    {"name": "后端API", "check": "http", "url": "http://localhost:8001/api/health"},
    {"name": "数据库", "check": "db"},
    {"name": "规则引擎", "check": "memory"},
    {"name": "函数运行时", "check": "memory"},
    {"name": "Agent 服务", "check": "memory"},
    {"name": "本体引擎", "check": "memory"},
    {"name": "图数据库", "check": "neo4j"},
    {"name": "大模型网关", "check": "http", "url": "https://dashscope.aliyuncs.com"},
    {"name": "MinIO", "check": "minio"},
    {"name": "Redis", "check": "redis"},
]


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
    from sqlalchemy import text
    db = SessionLocal()
    try:
        start = time.monotonic()
        db.execute(text("SELECT 1"))
        elapsed = (time.monotonic() - start) * 1000
        return "healthy", round(elapsed, 1)
    except Exception:
        return "unhealthy", None
    finally:
        db.close()


async def _check_neo4j() -> tuple[str, float | None]:
    try:
        from app.config import settings
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD))
        start = time.monotonic()
        with driver.session() as session:
            session.run("RETURN 1")
        elapsed = (time.monotonic() - start) * 1000
        driver.close()
        return "healthy", round(elapsed, 1)
    except Exception:
        return "unhealthy", None


async def _check_minio() -> tuple[str, float | None]:
    try:
        import boto3
        from app.config import settings
        client = boto3.client(
            "s3",
            endpoint_url=settings.MINIO_ENDPOINT,
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
        )
        start = time.monotonic()
        client.head_bucket(Bucket=settings.MINIO_BUCKET)
        elapsed = (time.monotonic() - start) * 1000
        return "healthy", round(elapsed, 1)
    except Exception:
        return "unhealthy", None


async def _check_redis() -> tuple[str, float | None]:
    try:
        import redis
        from app.config import settings
        r = redis.from_url(settings.REDIS_URL, socket_timeout=3)
        start = time.monotonic()
        r.ping()
        elapsed = (time.monotonic() - start) * 1000
        return "healthy", round(elapsed, 1)
    except Exception:
        return "unhealthy", None


async def _check_service(svc: dict) -> tuple[str, str, float | None]:
    """Returns (service_name, status, response_ms)."""
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
            status, ms = "healthy", None
    except Exception:
        status, ms = "unhealthy", None
    return name, status, ms


def _determine_status(response_ms: float | None) -> str:
    if response_ms is None:
        return "unhealthy"
    if response_ms < 500:
        return "healthy"
    if response_ms < 2000:
        return "warning"
    return "unhealthy"


# ── Collector tasks ──

async def collect_service_metrics():
    """Collect metrics every 30s and persist to DB."""
    while True:
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            db = SessionLocal()
            repo = MonitorRepository(db)
            try:
                for svc in SERVICES:
                    name, status, ms = await _check_service(svc)
                    repo.save_metric(
                        service_name=name, status=status, response_ms=ms,
                        cpu_percent=cpu, memory_percent=mem.percent, disk_percent=disk.percent,
                    )
                logger.debug("Service metrics collected")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Metric collection error: {e}")

        await asyncio.sleep(30)


async def check_alerts():
    """Check latest metrics for alert conditions every 30s."""
    while True:
        try:
            db = SessionLocal()
            repo = MonitorRepository(db)
            try:
                metrics = repo.get_latest_metrics()
                for m in metrics:
                    if m.status == "unhealthy":
                        # Check if an unresolved alert already exists for this service
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
    """Clean up old data every hour."""
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
    """Start all collector tasks. Call from FastAPI lifespan."""
    asyncio.create_task(collect_service_metrics())
    asyncio.create_task(check_alerts())
    asyncio.create_task(cleanup_old_data())
    ws_manager.start_heartbeat()
    logger.info("Monitor collector started")

    # Subscribe to alert events → broadcast via WebSocket
    async def _on_alert(data: dict):
        await ws_manager.broadcast({"type": "alert", "data": data})

    event_bus.subscribe("alert", _on_alert)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/monitor/collector.py
git commit -m "feat(monitor): add periodic metric collector with alerting"
```

---

## Task 6: Backend Schemas

**Files:**
- Create: `backend/app/schemas/monitor.py`

- [ ] **Step 1: Create Pydantic response models**

Create `backend/app/schemas/monitor.py`:

```python
from pydantic import BaseModel


class ResourceMetrics(BaseModel):
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float


class ServiceStatus(BaseModel):
    name: str
    status: str
    response_ms: float | None = None


class ResponseHistoryPoint(BaseModel):
    service_name: str
    response_ms: float | None
    status: str
    collected_at: str


class AlertItem(BaseModel):
    id: int
    level: str
    service_name: str
    message: str
    resolved: bool
    created_at: str
    resolved_at: str | None = None


class AlertResolveRequest(BaseModel):
    pass  # No body needed


class LLMStatsResponse(BaseModel):
    total_24h: int
    by_module: dict[str, dict]


class OntologyStatsResponse(BaseModel):
    total_entities: int
    by_type: dict[str, int]


class AgentActivityResponse(BaseModel):
    total_agents: int
    published_agents: int
    total_skills: int


class DashboardOverview(BaseModel):
    resources: ResourceMetrics
    services: list[ServiceStatus]
    alerts: list[AlertItem]
    llm_stats: LLMStatsResponse
    ontology_stats: OntologyStatsResponse
    agent_activity: AgentActivityResponse
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/monitor.py
git commit -m "feat(monitor): add Pydantic response schemas"
```

---

## Task 7: Backend API Routes Expansion

**Files:**
- Modify: `backend/app/api/v1/monitor.py`

- [ ] **Step 1: Rewrite monitor.py with all endpoints**

Replace `backend/app/api/v1/monitor.py` entirely:

```python
import platform
from datetime import datetime

import psutil
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import OntologyEntity, Agent
from app.models.skill import Skill
from app.repositories.monitor_repo import MonitorRepository
from app.schemas.monitor import (
    ResourceMetrics, ServiceStatus, ResponseHistoryPoint,
    AlertItem, LLMStatsResponse, OntologyStatsResponse,
    AgentActivityResponse, DashboardOverview,
)
from app.services.monitor.ws_manager import ws_manager

router = APIRouter(prefix="/monitor", tags=["monitor"])


@router.get("/resources", response_model=ResourceMetrics)
def get_resources():
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return ResourceMetrics(
        cpu_percent=psutil.cpu_percent(interval=0.1),
        memory_percent=mem.percent,
        memory_used_gb=round(mem.used / (1024**3), 2),
        memory_total_gb=round(mem.total / (1024**3), 2),
        disk_percent=disk.percent,
        disk_used_gb=round(disk.used / (1024**3), 2),
        disk_total_gb=round(disk.total / (1024**3), 2),
    )


@router.get("/services", response_model=list[ServiceStatus])
def get_services(db: Session = Depends(get_db)):
    repo = MonitorRepository(db)
    metrics = repo.get_latest_metrics()
    return [
        ServiceStatus(name=m.service_name, status=m.status, response_ms=m.response_ms)
        for m in metrics
    ]


@router.get("/response-history", response_model=list[ResponseHistoryPoint])
def get_response_history(hours: int = 1, service: str | None = None, db: Session = Depends(get_db)):
    repo = MonitorRepository(db)
    metrics = repo.get_metric_history(hours=hours, service_name=service)
    return [
        ResponseHistoryPoint(
            service_name=m.service_name,
            response_ms=m.response_ms,
            status=m.status,
            collected_at=m.collected_at.isoformat(),
        )
        for m in metrics
    ]


@router.get("/alerts", response_model=list[AlertItem])
def get_alerts(limit: int = 20, resolved: bool | None = None, level: str | None = None,
               db: Session = Depends(get_db)):
    repo = MonitorRepository(db)
    alerts = repo.get_alerts(limit=limit, resolved=resolved, level=level)
    return [
        AlertItem(
            id=a.id, level=a.level, service_name=a.service_name, message=a.message,
            resolved=a.resolved, created_at=a.created_at.isoformat(),
            resolved_at=a.resolved_at.isoformat() if a.resolved_at else None,
        )
        for a in alerts
    ]


@router.post("/alerts/{alert_id}/resolve", response_model=AlertItem)
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    repo = MonitorRepository(db)
    a = repo.resolve_alert(alert_id)
    if not a:
        from fastapi import HTTPException
        raise HTTPException(404, "Alert not found")
    return AlertItem(
        id=a.id, level=a.level, service_name=a.service_name, message=a.message,
        resolved=a.resolved, created_at=a.created_at.isoformat(),
        resolved_at=a.resolved_at.isoformat() if a.resolved_at else None,
    )


@router.get("/llm-stats", response_model=LLMStatsResponse)
def get_llm_stats(db: Session = Depends(get_db)):
    repo = MonitorRepository(db)
    return LLMStatsResponse(**repo.get_llm_stats_24h())


@router.get("/ontology-stats", response_model=OntologyStatsResponse)
def get_ontology_stats(db: Session = Depends(get_db)):
    total = db.query(OntologyEntity).count()
    # Count by entity_type if the field exists, otherwise just total
    by_type = {}
    try:
        from sqlalchemy import func
        rows = (
            db.query(OntologyEntity.entity_type, func.count(OntologyEntity.id))
            .group_by(OntologyEntity.entity_type)
            .all()
        )
        by_type = {r[0] or "unknown": r[1] for r in rows}
    except Exception:
        pass
    return OntologyStatsResponse(total_entities=total, by_type=by_type)


@router.get("/agent-activity", response_model=AgentActivityResponse)
def get_agent_activity(db: Session = Depends(get_db)):
    total_agents = db.query(Agent).count()
    published = db.query(Agent).filter(Agent.status == "published").count()
    total_skills = db.query(Skill).count()
    return AgentActivityResponse(
        total_agents=total_agents, published_agents=published, total_skills=total_skills,
    )


@router.get("/overview", response_model=DashboardOverview)
def get_overview(db: Session = Depends(get_db)):
    repo = MonitorRepository(db)
    return DashboardOverview(
        resources=get_resources(),
        services=[
            ServiceStatus(name=m.service_name, status=m.status, response_ms=m.response_ms)
            for m in repo.get_latest_metrics()
        ],
        alerts=[
            AlertItem(
                id=a.id, level=a.level, service_name=a.service_name, message=a.message,
                resolved=a.resolved, created_at=a.created_at.isoformat(),
                resolved_at=a.resolved_at.isoformat() if a.resolved_at else None,
            )
            for a in repo.get_alerts(limit=10)
        ],
        llm_stats=LLMStatsResponse(**repo.get_llm_stats_24h()),
        ontology_stats=OntologyStatsResponse(
            total_entities=db.query(OntologyEntity).count(), by_type={},
        ),
        agent_activity=AgentActivityResponse(
            total_agents=db.query(Agent).count(),
            published_agents=db.query(Agent).filter(Agent.status == "published").count(),
            total_skills=db.query(Skill).count(),
        ),
    )


@router.get("/system-info")
def get_system_info():
    return {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "python_version": platform.python_version(),
        "hostname": platform.node(),
        "cpu_count": psutil.cpu_count(),
        "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
    }


# ── WebSocket endpoint ──

@router.websocket("/ws")
async def monitor_ws(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            # Keep connection alive, receive pings from client
            data = await ws.receive_text()
            if data == "pong":
                continue  # Client heartbeat response
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/v1/monitor.py
git commit -m "feat(monitor): expand API with response-history, alerts, llm-stats, ontology-stats, ws"
```

---

## Task 8: Backend Main.py Integration

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add collector startup to lifespan**

In `backend/app/main.py`, find the lifespan function. After the line `start_pipeline_worker()` (around line 372), add:

```python
    # 启动监控采集器
    try:
        from app.services.monitor.collector import start_collector
        await start_collector()
        logger.info("监控采集器已启动")
    except Exception as e:
        logger.warning(f"监控采集器启动失败: {e}")
```

- [ ] **Step 2: Add WebSocket route**

The WebSocket endpoint is already defined in the monitor router (at `/ws/monitor/ws`). Since the monitor router is mounted at `prefix="/api/v1"` and the router itself has `prefix="/monitor"`, the WebSocket path will be `/api/v1/monitor/ws`. No additional mounting needed.

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat(monitor): integrate collector startup in lifespan"
```

---

## Task 9: Frontend API Layer Expansion

**Files:**
- Modify: `frontend/src/api/monitor.ts`

- [ ] **Step 1: Expand monitor API client**

Replace `frontend/src/api/monitor.ts`:

```typescript
import { get, post } from './client'

export interface ResourceMetrics {
  cpu_percent: number
  memory_percent: number
  memory_used_gb: number
  memory_total_gb: number
  disk_percent: number
  disk_used_gb: number
  disk_total_gb: number
}

export interface ServiceStatus {
  name: string
  status: string
  response_ms: number | null
}

export interface ResponseHistoryPoint {
  service_name: string
  response_ms: number | null
  status: string
  collected_at: string
}

export interface AlertItem {
  id: number
  level: string
  service_name: string
  message: string
  resolved: boolean
  created_at: string
  resolved_at: string | null
}

export interface LLMStatsResponse {
  total_24h: number
  by_module: Record<string, {
    count: number
    total_prompt_tokens: number
    total_completion_tokens: number
    avg_latency_ms: number
  }>
}

export interface OntologyStatsResponse {
  total_entities: number
  by_type: Record<string, number>
}

export interface AgentActivityResponse {
  total_agents: number
  published_agents: number
  total_skills: number
}

export interface DashboardOverview {
  resources: ResourceMetrics
  services: ServiceStatus[]
  alerts: AlertItem[]
  llm_stats: LLMStatsResponse
  ontology_stats: OntologyStatsResponse
  agent_activity: AgentActivityResponse
}

export const monitorApi = {
  overview() {
    return get<DashboardOverview>('/monitor/overview')
  },
  resources() {
    return get<ResourceMetrics>('/monitor/resources')
  },
  services() {
    return get<ServiceStatus[]>('/monitor/services')
  },
  responseHistory(hours: number = 1, service?: string) {
    const params = new URLSearchParams({ hours: String(hours) })
    if (service) params.set('service', service)
    return get<ResponseHistoryPoint[]>(`/monitor/response-history?${params}`)
  },
  alerts(limit = 20, resolved?: boolean, level?: string) {
    const params = new URLSearchParams({ limit: String(limit) })
    if (resolved !== undefined) params.set('resolved', String(resolved))
    if (level) params.set('level', level)
    return get<AlertItem[]>(`/monitor/alerts?${params}`)
  },
  resolveAlert(id: number) {
    return post<AlertItem>(`/monitor/alerts/${id}/resolve`)
  },
  llmStats() {
    return get<LLMStatsResponse>('/monitor/llm-stats')
  },
  ontologyStats() {
    return get<OntologyStatsResponse>('/monitor/ontology-stats')
  },
  agentActivity() {
    return get<AgentActivityResponse>('/monitor/agent-activity')
  },
  systemInfo() {
    return get<Record<string, any>>('/monitor/system-info')
  },
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/monitor.ts
git commit -m "feat(monitor): expand frontend API with response-history, alerts, llm-stats"
```

---

## Task 10: Frontend WebSocket Composable

**Files:**
- Create: `frontend/src/composables/useMonitorWS.ts`

- [ ] **Step 1: Create WebSocket composable**

Create `frontend/src/composables/useMonitorWS.ts`:

```typescript
import { ref, onMounted, onUnmounted } from 'vue'

export interface WSMessage {
  type: 'alert' | 'event' | 'ping'
  data?: any
}

export function useMonitorWS() {
  const connected = ref(false)
  const lastMessage = ref<WSMessage | null>(null)
  const alerts = ref<any[]>([])

  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null

  function getWsUrl(): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    return `${protocol}//${host}/api/v1/monitor/ws`
  }

  function connect() {
    if (ws?.readyState === WebSocket.OPEN) return

    ws = new WebSocket(getWsUrl())

    ws.onopen = () => {
      connected.value = true
      // Start client heartbeat
      heartbeatTimer = setInterval(() => {
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send('pong')
        }
      }, 30000)
    }

    ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data)
        lastMessage.value = msg

        if (msg.type === 'ping') return // Server heartbeat

        if (msg.type === 'alert' && msg.data) {
          alerts.value.unshift(msg.data)
          if (alerts.value.length > 50) alerts.value.pop()
        }
      } catch {
        // Ignore parse errors
      }
    }

    ws.onclose = () => {
      connected.value = false
      if (heartbeatTimer) clearInterval(heartbeatTimer)
      // Auto-reconnect after 5s
      reconnectTimer = setTimeout(connect, 5000)
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  function disconnect() {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    if (heartbeatTimer) clearInterval(heartbeatTimer)
    ws?.close()
    ws = null
  }

  onMounted(connect)
  onUnmounted(disconnect)

  return { connected, lastMessage, alerts, connect, disconnect }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/composables/useMonitorWS.ts
git commit -m "feat(monitor): add useMonitorWS composable with auto-reconnect"
```

---

## Task 11: Frontend — ServiceHealthCards Component

**Files:**
- Create: `frontend/src/views/dashboard/components/ServiceHealthCards.vue`

- [ ] **Step 1: Create ServiceHealthCards**

Create `frontend/src/views/dashboard/components/ServiceHealthCards.vue`:

```vue
<template>
  <a-card :bordered="false" class="health-card">
    <div class="health-grid">
      <div v-for="svc in services" :key="svc.name" class="health-item"
           :class="{ unhealthy: svc.status === 'unhealthy', warning: svc.status === 'warning' }">
        <span class="status-dot" :class="svc.status"></span>
        <div class="info">
          <span class="name">{{ svc.name }}</span>
          <span class="latency">{{ svc.response_ms != null ? svc.response_ms.toFixed(0) + 'ms' : '不可达' }}</span>
        </div>
      </div>
    </div>
  </a-card>
</template>

<script setup lang="ts">
defineProps<{
  services: Array<{ name: string; status: string; response_ms: number | null }>
}>()
</script>

<style scoped>
.health-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
.health-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 6px;
  background: var(--color-bg-container, #fafafa);
  min-width: 140px;
  transition: background 0.2s;
}
.health-item:hover {
  background: var(--color-bg-elevated, #f0f0f0);
}
.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.status-dot.healthy { background: #12b886; }
.status-dot.warning { background: #f59f00; animation: pulse 1.5s infinite; }
.status-dot.unhealthy { background: #fa5252; animation: pulse 1.5s infinite; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.info {
  display: flex;
  flex-direction: column;
}
.name { font-size: 13px; font-weight: 500; }
.latency { font-size: 11px; color: var(--color-text-secondary, #888); }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/dashboard/components/ServiceHealthCards.vue
git commit -m "feat(monitor): add ServiceHealthCards component"
```

---

## Task 12: Frontend — ResourceGauges Component

**Files:**
- Create: `frontend/src/views/dashboard/components/ResourceGauges.vue`

- [ ] **Step 1: Create ResourceGauges**

Create `frontend/src/views/dashboard/components/ResourceGauges.vue`:

```vue
<template>
  <a-card title="资源使用率" :bordered="false">
    <div class="gauges-row">
      <div v-for="g in gauges" :key="g.label" class="gauge-item">
        <div class="gauge-chart" ref="chartRefs"></div>
        <div class="gauge-label">{{ g.label }}</div>
        <div class="gauge-detail">{{ g.detail }}</div>
      </div>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import * as echarts from 'echarts'
import type { ResourceMetrics } from '../../../api/monitor'

const props = defineProps<{ data: ResourceMetrics | null }>()

const chartRefs = ref<HTMLElement[]>([])
const chartInstances: echarts.ECharts[] = []

const gauges = computed(() => {
  if (!props.data) return []
  return [
    { label: 'CPU', value: props.data.cpu_percent, detail: `${props.data.cpu_percent.toFixed(1)}%` },
    { label: '内存', value: props.data.memory_percent, detail: `${props.data.memory_used_gb}G / ${props.data.memory_total_gb}G` },
    { label: '磁盘', value: props.data.disk_percent, detail: `${props.data.disk_used_gb}G / ${props.data.disk_total_gb}G` },
  ]
})

function getColor(value: number): string {
  if (value < 60) return '#20c997'
  if (value < 85) return '#f59f00'
  return '#fa5252'
}

function initCharts() {
  // Destroy existing
  chartInstances.forEach(c => c.dispose())
  chartInstances.length = 0

  const containers = document.querySelectorAll('.gauge-chart')
  containers.forEach((el, i) => {
    if (!gauges.value[i]) return
    const chart = echarts.init(el as HTMLElement)
    const g = gauges.value[i]
    chart.setOption({
      series: [{
        type: 'gauge',
        startAngle: 210,
        endAngle: -30,
        min: 0,
        max: 100,
        radius: '90%',
        progress: { show: true, width: 12 },
        axisLine: { lineStyle: { width: 12, color: [[1, '#f1f3f5']] } },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        pointer: { show: false },
        title: { show: false },
        detail: {
          valueAnimation: true,
          fontSize: 28,
          fontWeight: 700,
          formatter: '{value}%',
          offsetCenter: [0, '10%'],
          color: getColor(g.value),
        },
        data: [{ value: Math.round(g.value) }],
      }],
    })
    chartInstances.push(chart)
  })
}

watch(() => props.data, () => {
  setTimeout(initCharts, 50)
}, { deep: true })

onMounted(() => {
  setTimeout(initCharts, 100)
})
</script>

<style scoped>
.gauges-row {
  display: flex;
  justify-content: space-around;
  gap: 16px;
}
.gauge-item {
  text-align: center;
  flex: 1;
}
.gauge-chart {
  width: 100%;
  height: 160px;
}
.gauge-label {
  font-size: 14px;
  font-weight: 500;
  margin-top: 4px;
}
.gauge-detail {
  font-size: 12px;
  color: var(--color-text-secondary, #888);
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/dashboard/components/ResourceGauges.vue
git commit -m "feat(monitor): add ResourceGauges component with ECharts"
```

---

## Task 13: Frontend — ResponseTimeChart Component

**Files:**
- Create: `frontend/src/views/dashboard/components/ResponseTimeChart.vue`

- [ ] **Step 1: Create ResponseTimeChart**

Create `frontend/src/views/dashboard/components/ResponseTimeChart.vue`:

```vue
<template>
  <a-card :bordered="false">
    <template #title>
      <div class="chart-header">
        <span>服务响应时间</span>
        <a-radio-group v-model:value="timeRange" size="small" @change="onRangeChange">
          <a-radio-button value="1">近1小时</a-radio-button>
          <a-radio-button value="6">近6小时</a-radio-button>
          <a-radio-button value="24">近24小时</a-radio-button>
        </a-radio-group>
      </div>
    </template>
    <div ref="chartEl" style="height: 260px;"></div>
  </a-card>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { monitorApi, type ResponseHistoryPoint } from '../../../api/monitor'

const chartEl = ref<HTMLElement>()
const timeRange = ref('1')
let chart: echarts.ECharts | null = null

const SERVICE_COLORS: Record<string, string> = {
  '后端API': '#5c7cfa', '数据库': '#20c997', '规则引擎': '#7950f2',
  '函数运行时': '#f59f00', 'Agent 服务': '#339af0', '本体引擎': '#fa5252',
  '图数据库': '#e64980', '大模型网关': '#fab005', 'MinIO': '#40c057', 'Redis': '#fd7e14',
}

async function fetchData() {
  const hours = parseInt(timeRange.value)
  const data = await monitorApi.responseHistory(hours)
  renderChart(data)
}

function renderChart(data: ResponseHistoryPoint[]) {
  if (!chartEl.value) return
  if (!chart) chart = echarts.init(chartEl.value)

  // Group by service
  const byService: Record<string, { times: string[]; values: (number | null)[] }> = {}
  for (const p of data) {
    if (!byService[p.service_name]) byService[p.service_name] = { times: [], values: [] }
    byService[p.service_name].times.push(p.collected_at)
    byService[p.service_name].values.push(p.response_ms)
  }

  const series = Object.entries(byService).map(([name, d]) => ({
    name,
    type: 'line' as const,
    smooth: true,
    data: d.values,
    lineStyle: { width: 2 },
    itemStyle: { color: SERVICE_COLORS[name] || '#999' },
    connectNulls: false,
  }))

  // Use the longest time axis
  const allTimes = [...new Set(data.map(d => d.collected_at))].sort()

  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { top: 0, right: 0, type: 'scroll' },
    grid: { top: 40, right: 20, bottom: 30, left: 50 },
    xAxis: {
      type: 'category',
      data: allTimes.map(t => t.substring(11, 19)),
      axisLabel: { fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      name: 'ms',
      axisLabel: { fontSize: 11 },
      splitLine: { lineStyle: { type: 'dashed' } },
    },
    series,
  }, true)
}

function onRangeChange() {
  fetchData()
}

onMounted(() => {
  nextTick(fetchData)
  window.addEventListener('resize', () => chart?.resize())
})
</script>

<style scoped>
.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/dashboard/components/ResponseTimeChart.vue
git commit -m "feat(monitor): add ResponseTimeChart with ECharts line chart"
```

---

## Task 14: Frontend — AlertTable Component

**Files:**
- Create: `frontend/src/views/dashboard/components/AlertTable.vue`

- [ ] **Step 1: Create AlertTable**

Create `frontend/src/views/dashboard/components/AlertTable.vue`:

```vue
<template>
  <a-card title="最近告警" :bordered="false">
    <template #extra>
      <a-badge :count="unresolvedCount" :offset="[0, 0]">
        <span style="font-size: 12px; color: #888;">未处理</span>
      </a-badge>
    </template>
    <a-table :dataSource="alerts" :columns="columns" :pagination="false"
             size="small" :scroll="{ y: 320 }" row-key="id">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'level'">
          <a-tag :color="levelColor(record.level)">{{ levelLabel(record.level) }}</a-tag>
        </template>
        <template v-if="column.key === 'time'">
          {{ formatTime(record.created_at) }}
        </template>
        <template v-if="column.key === 'action'">
          <a v-if="!record.resolved" @click="$emit('resolve', record.id)" style="color: #5c7cfa;">处理</a>
          <span v-else style="color: #aaa;">已处理</span>
        </template>
      </template>
    </a-table>
  </a-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AlertItem } from '../../../api/monitor'

const props = defineProps<{ alerts: AlertItem[] }>()
defineEmits<{ resolve: [id: number] }>()

const unresolvedCount = computed(() => props.alerts.filter(a => !a.resolved).length)

const columns = [
  { key: 'level', title: '级别', width: 70 },
  { key: 'message', title: '告警内容', ellipsis: true },
  { key: 'service_name', title: '服务', width: 100 },
  { key: 'time', title: '时间', width: 120 },
  { key: 'action', title: '操作', width: 70 },
]

function levelColor(level: string) {
  return { critical: 'red', warning: 'orange', info: 'blue' }[level] || 'default'
}
function levelLabel(level: string) {
  return { critical: '严重', warning: '警告', info: '提示' }[level] || level
}
function formatTime(iso: string) {
  if (!iso) return ''
  return iso.substring(11, 19)
}
</script>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/dashboard/components/AlertTable.vue
git commit -m "feat(monitor): add AlertTable component"
```

---

## Task 15: Frontend — EventStream Component

**Files:**
- Create: `frontend/src/views/dashboard/components/EventStream.vue`

- [ ] **Step 1: Create EventStream**

Create `frontend/src/views/dashboard/components/EventStream.vue`:

```vue
<template>
  <a-card title="系统事件" :bordered="false">
    <template #extra>
      <a-select v-model:value="filter" size="small" style="width: 100px;">
        <a-select-option value="all">全部</a-select-option>
        <a-select-option value="deploy">部署</a-select-option>
        <a-select-option value="config">配置</a-select-option>
        <a-select-option value="user">用户</a-select-option>
      </a-select>
    </template>
    <div class="event-list" ref="listEl">
      <div v-for="(ev, i) in filteredEvents" :key="i" class="event-item">
        <span class="event-time">{{ ev.time }}</span>
        <a-tag :color="tagColor(ev.type)" size="small">{{ ev.type }}</a-tag>
        <span class="event-desc">{{ ev.description }}</span>
      </div>
      <a-empty v-if="filteredEvents.length === 0" description="暂无系统事件" />
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface SystemEvent {
  time: string
  type: string
  description: string
}

const props = defineProps<{ events: SystemEvent[] }>()
const filter = ref('all')
const listEl = ref<HTMLElement>()

const filteredEvents = computed(() => {
  if (filter.value === 'all') return props.events
  return props.events.filter(e => e.type === filter.value)
})

function tagColor(type: string) {
  return { deploy: 'blue', config: 'purple', user: 'green', alert: 'red' }[type] || 'default'
}
</script>

<style scoped>
.event-list {
  height: 320px;
  overflow-y: auto;
}
.event-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px solid var(--color-border-secondary, #f0f0f0);
}
.event-time {
  font-family: monospace;
  font-size: 12px;
  color: var(--color-text-secondary, #888);
  flex-shrink: 0;
}
.event-desc {
  font-size: 13px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/dashboard/components/EventStream.vue
git commit -m "feat(monitor): add EventStream component"
```

---

## Task 16: Frontend — Stats Components

**Files:**
- Create: `frontend/src/views/dashboard/components/OntologyStats.vue`
- Create: `frontend/src/views/dashboard/components/LLMCallStats.vue`
- Create: `frontend/src/views/dashboard/components/AgentActivity.vue`

- [ ] **Step 1: Create OntologyStats**

Create `frontend/src/views/dashboard/components/OntologyStats.vue`:

```vue
<template>
  <a-card :bordered="false" class="stat-card">
    <div class="stat-icon">🧩</div>
    <div class="stat-value">{{ data?.total_entities ?? '-' }}</div>
    <div class="stat-label">本体对象总数</div>
    <div class="stat-sub" v-if="data?.by_type && Object.keys(data.by_type).length">
      {{ Object.keys(data.by_type).length }} 种类型
    </div>
  </a-card>
</template>

<script setup lang="ts">
import type { OntologyStatsResponse } from '../../../api/monitor'
defineProps<{ data: OntologyStatsResponse | null }>()
</script>

<style scoped>
.stat-card { text-align: center; padding: 20px; }
.stat-icon { font-size: 32px; margin-bottom: 8px; }
.stat-value { font-size: 36px; font-weight: 700; }
.stat-label { font-size: 14px; color: var(--color-text-secondary, #888); margin-top: 4px; }
.stat-sub { font-size: 12px; color: var(--color-text-tertiary, #aaa); margin-top: 2px; }
</style>
```

- [ ] **Step 2: Create LLMCallStats**

Create `frontend/src/views/dashboard/components/LLMCallStats.vue`:

```vue
<template>
  <a-card :bordered="false" class="stat-card">
    <div class="stat-icon">🤖</div>
    <div class="stat-value">{{ data?.total_24h ?? '-' }}</div>
    <div class="stat-label">大模型调用量 (24h)</div>
    <div class="stat-sub" v-if="topModule">最多: {{ topModule }}</div>
  </a-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { LLMStatsResponse } from '../../../api/monitor'

const props = defineProps<{ data: LLMStatsResponse | null }>()

const topModule = computed(() => {
  if (!props.data?.by_module) return null
  const entries = Object.entries(props.data.by_module)
  if (!entries.length) return null
  const top = entries.reduce((a, b) => (b[1].count > a[1].count ? b : a))
  return `${top[0]} (${top[1].count}次)`
})
</script>

<style scoped>
.stat-card { text-align: center; padding: 20px; }
.stat-icon { font-size: 32px; margin-bottom: 8px; }
.stat-value { font-size: 36px; font-weight: 700; }
.stat-label { font-size: 14px; color: var(--color-text-secondary, #888); margin-top: 4px; }
.stat-sub { font-size: 12px; color: var(--color-text-tertiary, #aaa); margin-top: 2px; }
</style>
```

- [ ] **Step 3: Create AgentActivity**

Create `frontend/src/views/dashboard/components/AgentActivity.vue`:

```vue
<template>
  <a-card :bordered="false" class="stat-card">
    <div class="stat-icon">🤖</div>
    <div class="stat-value">{{ data?.published_agents ?? '-' }}</div>
    <div class="stat-label">活跃 Agent</div>
    <div class="stat-sub">共 {{ data?.total_agents ?? '-' }} 个 / {{ data?.total_skills ?? '-' }} 个技能</div>
  </a-card>
</template>

<script setup lang="ts">
import type { AgentActivityResponse } from '../../../api/monitor'
defineProps<{ data: AgentActivityResponse | null }>()
</script>

<style scoped>
.stat-card { text-align: center; padding: 20px; }
.stat-icon { font-size: 32px; margin-bottom: 8px; }
.stat-value { font-size: 36px; font-weight: 700; }
.stat-label { font-size: 14px; color: var(--color-text-secondary, #888); margin-top: 4px; }
.stat-sub { font-size: 12px; color: var(--color-text-tertiary, #aaa); margin-top: 2px; }
</style>
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/dashboard/components/OntologyStats.vue frontend/src/views/dashboard/components/LLMCallStats.vue frontend/src/views/dashboard/components/AgentActivity.vue
git commit -m "feat(monitor): add OntologyStats, LLMCallStats, AgentActivity components"
```

---

## Task 17: Frontend — Main Dashboard Assembly

**Files:**
- Modify: `frontend/src/views/dashboard/SystemDashboardView.vue`

- [ ] **Step 1: Rewrite SystemDashboardView**

Replace `frontend/src/views/dashboard/SystemDashboardView.vue`:

```vue
<template>
  <div class="dashboard-container">
    <!-- Header -->
    <div class="dashboard-header">
      <h2>系统看板</h2>
      <div class="header-right">
        <span class="last-update">最后更新: {{ lastUpdate }}</span>
        <a-dropdown>
          <a-button size="small">
            <template #icon><ReloadOutlined /></template>
            {{ autoRefreshLabel }}
          </a-button>
          <template #overlay>
            <a-menu @click="onRefreshChange">
              <a-menu-item key="30">30秒</a-menu-item>
              <a-menu-item key="60">60秒</a-menu-item>
              <a-menu-item key="0">关闭</a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
        <a-button size="small" @click="fetchAll" :loading="loading">
          <template #icon><ReloadOutlined /></template>
        </a-button>
      </div>
    </div>

    <!-- Service Health -->
    <ServiceHealthCards :services="services" />

    <!-- Resource + Response Time -->
    <a-row :gutter="16" style="margin-top: 16px;">
      <a-col :xs="24" :lg="10">
        <ResourceGauges :data="resources" />
      </a-col>
      <a-col :xs="24" :lg="14">
        <ResponseTimeChart />
      </a-col>
    </a-row>

    <!-- Stats Row -->
    <a-row :gutter="16" style="margin-top: 16px;">
      <a-col :xs="24" :sm="8">
        <OntologyStats :data="ontologyStats" />
      </a-col>
      <a-col :xs="24" :sm="8">
        <LLMCallStats :data="llmStats" />
      </a-col>
      <a-col :xs="24" :sm="8">
        <AgentActivity :data="agentActivity" />
      </a-col>
    </a-row>

    <!-- Alerts + Events -->
    <a-row :gutter="16" style="margin-top: 16px;">
      <a-col :xs="24" :lg="12">
        <AlertTable :alerts="alerts" @resolve="onResolveAlert" />
      </a-col>
      <a-col :xs="24" :lg="12">
        <EventStream :events="wsEvents" />
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { ReloadOutlined } from '@ant-design/icons-vue'
import { monitorApi } from '../../api/monitor'
import type { ResourceMetrics, ServiceStatus, AlertItem, LLMStatsResponse, OntologyStatsResponse, AgentActivityResponse } from '../../api/monitor'
import { useMonitorWS } from '../../composables/useMonitorWS'

import ServiceHealthCards from './components/ServiceHealthCards.vue'
import ResourceGauges from './components/ResourceGauges.vue'
import ResponseTimeChart from './components/ResponseTimeChart.vue'
import AlertTable from './components/AlertTable.vue'
import EventStream from './components/EventStream.vue'
import OntologyStats from './components/OntologyStats.vue'
import LLMCallStats from './components/LLMCallStats.vue'
import AgentActivity from './components/AgentActivity.vue'

const loading = ref(false)
const resources = ref<ResourceMetrics | null>(null)
const services = ref<ServiceStatus[]>([])
const alerts = ref<AlertItem[]>([])
const llmStats = ref<LLMStatsResponse | null>(null)
const ontologyStats = ref<OntologyStatsResponse | null>(null)
const agentActivity = ref<AgentActivityResponse | null>(null)
const lastUpdate = ref('--:--:--')
const autoRefreshSec = ref(30)
let refreshTimer: ReturnType<typeof setInterval> | null = null

const { connected, alerts: wsAlerts, lastMessage } = useMonitorWS()

// Merge WS alerts into table
const mergedAlerts = computed(() => {
  const ws = wsAlerts.value.map(a => ({ ...a, resolved: false }))
  const existing = alerts.value
  const ids = new Set(ws.map(a => a.id))
  const merged = [...ws, ...existing.filter(a => !ids.has(a.id))]
  return merged.sort((a, b) => b.created_at.localeCompare(a.created_at)).slice(0, 20)
})

// Events from WS messages
const wsEvents = ref<Array<{ time: string; type: string; description: string }>>([])

const autoRefreshLabel = computed(() => {
  if (autoRefreshSec.value === 0) return '关闭'
  return `${autoRefreshSec.value}s`
})

async function fetchAll() {
  loading.value = true
  try {
    const [res, svc, alt, llm, ont, agent] = await Promise.all([
      monitorApi.resources(),
      monitorApi.services(),
      monitorApi.alerts(20),
      monitorApi.llmStats(),
      monitorApi.ontologyStats(),
      monitorApi.agentActivity(),
    ])
    resources.value = res
    services.value = svc
    alerts.value = alt
    llmStats.value = llm
    ontologyStats.value = ont
    agentActivity.value = agent
    lastUpdate.value = new Date().toLocaleTimeString('zh-CN')
  } catch (e) {
    console.error('Dashboard fetch error:', e)
  } finally {
    loading.value = false
  }
}

function startAutoRefresh() {
  if (refreshTimer) clearInterval(refreshTimer)
  if (autoRefreshSec.value > 0) {
    refreshTimer = setInterval(fetchAll, autoRefreshSec.value * 1000)
  }
}

function onRefreshChange({ key }: { key: string }) {
  autoRefreshSec.value = parseInt(key)
  startAutoRefresh()
}

async function onResolveAlert(id: number) {
  try {
    await monitorApi.resolveAlert(id)
    const idx = alerts.value.findIndex(a => a.id === id)
    if (idx >= 0) alerts.value[idx].resolved = true
  } catch (e) {
    console.error('Resolve alert error:', e)
  }
}

onMounted(() => {
  fetchAll()
  startAutoRefresh()
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.dashboard-container {
  padding: 24px 32px;
}
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.dashboard-header h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.last-update {
  font-size: 13px;
  color: var(--color-text-secondary, #888);
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/dashboard/SystemDashboardView.vue
git commit -m "feat(monitor): assemble SystemDashboardView with all components"
```

---

## Task 18: Verification

- [ ] **Step 1: Start backend and verify endpoints**

```bash
cd backend && uvicorn app.main:app --reload --port 8001
```

Verify:
- `GET /api/health` returns 200
- `GET /api/v1/monitor/resources` returns CPU/memory/disk
- `GET /api/v1/monitor/services` returns service list
- `GET /api/v1/monitor/overview` returns aggregated data

- [ ] **Step 2: Start frontend and verify dashboard**

```bash
cd frontend && npm run dev
```

Navigate to `http://localhost:5177/dashboard` and verify:
- Service health cards show 10 services with status dots
- Resource gauges render with CPU/memory/disk
- Response time chart loads (may be empty initially, data fills after 30s)
- Ontology stats show count
- LLM stats show count (may be 0 initially)
- Agent activity shows counts
- Alert table loads (may be empty)
- Auto-refresh works (check network tab for periodic requests)

- [ ] **Step 3: Commit all and push**

```bash
cd "E:\工作\国信\AI数据集项目\本体\系统代码\ontology"
git add -A
git commit -m "feat: complete system dashboard implementation"
git push origin master
git push github master
```
