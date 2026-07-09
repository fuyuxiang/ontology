from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.mcp_call_log import McpCallLog
from app.services.mcp_tools.registry import get_tools_list

router = APIRouter(prefix="/mcp", tags=["mcp-stats"])


@router.get("/stats/overview")
def get_overview(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)

    total_today = db.query(func.count(McpCallLog.id)).filter(McpCallLog.called_at >= today_start).scalar() or 0
    total_yesterday = db.query(func.count(McpCallLog.id)).filter(
        McpCallLog.called_at >= yesterday_start, McpCallLog.called_at < today_start
    ).scalar() or 0

    avg_ms = db.query(func.avg(McpCallLog.duration_ms)).filter(McpCallLog.called_at >= today_start).scalar() or 0
    error_count = db.query(func.count(McpCallLog.id)).filter(
        McpCallLog.called_at >= today_start, McpCallLog.is_error == True
    ).scalar() or 0
    error_rate = round(error_count / total_today, 4) if total_today > 0 else 0

    return {
        "total_calls_today": total_today,
        "total_calls_yesterday": total_yesterday,
        "avg_response_ms": round(avg_ms, 1),
        "error_rate": error_rate,
        "active_connections": 0,
    }


@router.get("/stats/trend")
def get_trend(range: str = Query("24h"), db: Session = Depends(get_db)):
    now = datetime.utcnow()
    if range == "7d":
        start = now - timedelta(days=7)
        trunc = func.strftime("%Y-%m-%d", McpCallLog.called_at)
    elif range == "1h":
        start = now - timedelta(hours=1)
        trunc = func.strftime("%Y-%m-%d %H:%M", McpCallLog.called_at)
    else:
        start = now - timedelta(hours=24)
        trunc = func.strftime("%Y-%m-%d %H:00", McpCallLog.called_at)

    rows = (
        db.query(trunc.label("bucket"), func.count(McpCallLog.id).label("count"))
        .filter(McpCallLog.called_at >= start)
        .group_by("bucket")
        .order_by("bucket")
        .all()
    )
    return {"range": range, "data": [{"time": r.bucket, "count": r.count} for r in rows]}


@router.get("/stats/tools")
def get_tool_stats(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    start = now - timedelta(days=7)

    rows = (
        db.query(
            McpCallLog.tool_name,
            func.count(McpCallLog.id).label("call_count"),
            func.avg(McpCallLog.duration_ms).label("avg_ms"),
            func.sum(func.cast(McpCallLog.is_error, type_=None)).label("error_count"),
            func.max(McpCallLog.called_at).label("last_called"),
        )
        .filter(McpCallLog.called_at >= start)
        .group_by(McpCallLog.tool_name)
        .all()
    )
    total = sum(r.call_count for r in rows) or 1
    return [
        {
            "tool_name": r.tool_name,
            "call_count": r.call_count,
            "avg_ms": round(r.avg_ms or 0, 1),
            "error_count": int(r.error_count or 0),
            "last_called": r.last_called.isoformat() if r.last_called else None,
            "percentage": round(r.call_count / total * 100, 1),
        }
        for r in rows
    ]


@router.get("/tools")
def get_tools():
    return {"tools": get_tools_list()}
