from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from pydantic import BaseModel
from datetime import datetime, timedelta
import platform
import psutil

from app.database import get_db
from app.models import OntologyEntity, EntityAction, BusinessRule, AuditLog
from app.models.function import OntologyFunction
from app.models.agent import Agent
from app.models.datasource import DataSource

router = APIRouter(prefix="/monitor", tags=["monitor"])


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
    uptime_hours: float | None = None


class SecurityEvent(BaseModel):
    id: str
    event_type: str
    user_name: str | None = None
    target: str
    timestamp: str
    severity: str


class MonitorOverview(BaseModel):
    resources: ResourceMetrics
    services: list[ServiceStatus]
    security_events: list[SecurityEvent]
    system_info: dict


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
    services = []
    try:
        db.execute(text("SELECT 1"))
        services.append(ServiceStatus(name="数据库", status="healthy", response_ms=1.0))
    except Exception:
        services.append(ServiceStatus(name="数据库", status="unhealthy"))

    services.append(ServiceStatus(name="API 服务", status="healthy"))
    services.append(ServiceStatus(name="规则引擎", status="healthy"))
    services.append(ServiceStatus(name="函数运行时", status="healthy"))
    services.append(ServiceStatus(name="Agent 服务", status="healthy"))
    return services


@router.get("/security-events", response_model=list[SecurityEvent])
def get_security_events(db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=7)
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.timestamp >= since)
        .filter(AuditLog.action.in_(["login", "login_failed", "delete", "update"]))
        .order_by(AuditLog.timestamp.desc())
        .limit(50)
        .all()
    )
    events = []
    for log in logs:
        severity = "low"
        if log.action == "login_failed":
            severity = "high"
        elif log.action == "delete":
            severity = "medium"
        events.append(SecurityEvent(
            id=log.id,
            event_type=log.action,
            user_name=log.user_name,
            target=f"{log.target_type}:{log.target_name}",
            timestamp=log.timestamp.isoformat() if log.timestamp else "",
            severity=severity,
        ))
    return events


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


@router.get("/overview", response_model=MonitorOverview)
def get_overview(db: Session = Depends(get_db)):
    return MonitorOverview(
        resources=get_resources(),
        services=get_services(db),
        security_events=get_security_events(db)[:10],
        system_info=get_system_info(),
    )
