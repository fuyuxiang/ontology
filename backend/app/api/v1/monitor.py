import asyncio
import logging
import platform
import shutil
from datetime import datetime

import psutil
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.core.security import decode_token_payload
from app.models.user import User
from app.models import Agent, OntologyEntity
from app.models.asset import Asset
from app.models.quality_rule import QualityRule
from app.models.skill import Skill
from app.repositories.monitor_repo import MonitorRepository
from app.schemas.monitor import (
    AgentActivityResponse,
    AlertItem,
    DashboardOverview,
    LLMStatsResponse,
    OntologyStatsResponse,
    PlatformStatsResponse,
    ResourceMetrics,
    ResponseHistoryPoint,
    ServiceStatus,
)
from app.services.monitor.ws_manager import ws_manager

router = APIRouter(prefix="/monitor", tags=["monitor"])

logger = logging.getLogger(__name__)

# 本体分层语义标签,与前端 OntologyNode 保持一致(1 核心 / 2 领域 / 3 场景)
_TIER_LABELS = {1: "核心", 2: "领域", 3: "场景"}


def _to_alert_item(a) -> AlertItem:
    """ORM Alert → AlertItem schema 的统一映射。"""
    return AlertItem(
        id=a.id, level=a.level, service_name=a.service_name, message=a.message,
        resolved=a.resolved, created_at=a.created_at.isoformat(),
        resolved_at=a.resolved_at.isoformat() if a.resolved_at else None,
    )


def _to_service_status(m) -> ServiceStatus:
    """ORM 指标 → ServiceStatus schema 的统一映射。"""
    return ServiceStatus(name=m.service_name, status=m.status, response_ms=m.response_ms)


def _resource_metrics() -> ResourceMetrics:
    """采集当前主机资源指标。"""
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


def _ontology_stats(db: Session) -> OntologyStatsResponse:
    """本体实体统计(总数 + 按分层分组),供单项端点与概览复用。"""
    total = db.query(OntologyEntity).count()
    by_type = {}
    try:
        rows = (
            db.query(OntologyEntity.tier, func.count(OntologyEntity.id))
            .group_by(OntologyEntity.tier)
            .all()
        )
        by_type = {_TIER_LABELS.get(r[0], f"T{r[0]}"): r[1] for r in rows}
    except Exception:
        logger.warning("本体分层统计失败,by_type 回退为空", exc_info=True)
    return OntologyStatsResponse(total_entities=total, by_type=by_type)


def _agent_activity(db: Session) -> AgentActivityResponse:
    """智能体活跃度统计,供单项端点与概览复用。"""
    return AgentActivityResponse(
        total_agents=db.query(Agent).count(),
        published_agents=db.query(Agent).filter(Agent.status == "published").count(),
        total_skills=db.query(Skill).count(),
    )


@router.get("/resources", response_model=ResourceMetrics)
def get_resources():
    return _resource_metrics()


@router.get("/services", response_model=list[ServiceStatus])
def get_services(db: Session = Depends(get_db)):
    repo = MonitorRepository(db)
    return [_to_service_status(m) for m in repo.get_latest_metrics()]


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
    return [_to_alert_item(a) for a in alerts]


@router.post("/alerts/{alert_id}/resolve", response_model=AlertItem)
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    repo = MonitorRepository(db)
    a = repo.resolve_alert(alert_id)
    if not a:
        raise HTTPException(404, "Alert not found")
    return _to_alert_item(a)


@router.get("/llm-stats", response_model=LLMStatsResponse)
def get_llm_stats(db: Session = Depends(get_db)):
    repo = MonitorRepository(db)
    return LLMStatsResponse(**repo.get_llm_stats_24h())


@router.get("/ontology-stats", response_model=OntologyStatsResponse)
def get_ontology_stats(db: Session = Depends(get_db)):
    return _ontology_stats(db)


@router.get("/agent-activity", response_model=AgentActivityResponse)
def get_agent_activity(db: Session = Depends(get_db)):
    return _agent_activity(db)


@router.get("/platform-stats", response_model=PlatformStatsResponse)
def get_platform_stats(db: Session = Depends(get_db)):
    total_datasources = db.scalar(
        select(func.count(Asset.id)).where(Asset.status == "active")
    ) or 0
    return PlatformStatsResponse(
        total_datasources=total_datasources,
        total_rules=db.scalar(select(func.count(QualityRule.id))) or 0,
    )


@router.get("/overview", response_model=DashboardOverview)
def get_overview(db: Session = Depends(get_db)):
    repo = MonitorRepository(db)
    return DashboardOverview(
        resources=_resource_metrics(),
        services=[_to_service_status(m) for m in repo.get_latest_metrics()],
        alerts=[_to_alert_item(a) for a in repo.get_alerts(limit=10)],
        llm_stats=LLMStatsResponse(**repo.get_llm_stats_24h()),
        ontology_stats=_ontology_stats(db),
        agent_activity=_agent_activity(db),
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
async def monitor_ws(ws: WebSocket, db: Session = Depends(get_db)):
    offered = ws.headers.get("sec-websocket-protocol", "").split(",")
    token = next((value.strip()[4:] for value in offered if value.strip().startswith("jwt.")), None)
    header = ws.headers.get("Authorization", "")
    token = token or (header[7:] if header.startswith("Bearer ") else ws.query_params.get("token"))
    await ws_manager.connect(ws)
    try:
        while True:
            payload = decode_token_payload(token, "access") if token else None
            db.rollback()
            user = db.get(User, payload["sub"], populate_existing=True) if payload else None
            if not user or not user.is_active or payload.get("tv", 0) != user.token_version:
                await ws.close(code=1008, reason="登录会话已失效")
                break
            try:
                data = await asyncio.wait_for(ws.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                continue
            if data == "pong":
                continue
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(ws)
