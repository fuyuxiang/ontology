import platform
import shutil
from datetime import datetime

import psutil
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import OntologyEntity, Agent, BusinessRule
from app.models.asset import Asset
from app.models.skill import Skill
from app.repositories.monitor_repo import MonitorRepository
from app.schemas.monitor import (
    ResourceMetrics, ServiceStatus, ResponseHistoryPoint,
    AlertItem, LLMStatsResponse, OntologyStatsResponse,
    AgentActivityResponse, PlatformStatsResponse, DashboardOverview,
)
from app.services.monitor.ws_manager import ws_manager

router = APIRouter(prefix="/monitor", tags=["monitor"])


@router.get("/resources", response_model=ResourceMetrics)
def get_resources():
    mem = psutil.virtual_memory()
    disk = shutil.disk_usage("/")
    disk_pct = round(disk.used / disk.total * 100, 1) if disk.total else 0
    return ResourceMetrics(
        cpu_percent=psutil.cpu_percent(interval=0.1),
        memory_percent=mem.percent,
        memory_used_gb=round(mem.used / (1024**3), 2),
        memory_total_gb=round(mem.total / (1024**3), 2),
        disk_percent=disk_pct,
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


@router.get("/platform-stats", response_model=PlatformStatsResponse)
def get_platform_stats(db: Session = Depends(get_db)):
    total_datasources = db.scalar(
        select(func.count(Asset.id)).where(Asset.status == "active")
    ) or 0
    total_rules = db.scalar(select(func.count(BusinessRule.id))) or 0
    return PlatformStatsResponse(
        total_datasources=total_datasources,
        total_rules=total_rules,
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


# -- WebSocket endpoint --

@router.websocket("/ws")
async def monitor_ws(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            if data == "pong":
                continue
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)
