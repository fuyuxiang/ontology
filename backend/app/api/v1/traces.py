from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.trace import AgentTrace
from app.models.agent import Agent

router = APIRouter(prefix="/traces", tags=["traces"])


@router.get("")
def list_traces(
    agent_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(AgentTrace).order_by(AgentTrace.created_at.desc())
    if agent_id:
        q = q.filter(AgentTrace.agent_id == agent_id)
    if status:
        q = q.filter(AgentTrace.status == status)
    if date_from:
        q = q.filter(AgentTrace.created_at >= date_from)
    if date_to:
        q = q.filter(AgentTrace.created_at <= date_to)

    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()

    agent_ids = {t.agent_id for t in items}
    agents_map = {}
    if agent_ids:
        for a in db.query(Agent).filter(Agent.id.in_(agent_ids)).all():
            agents_map[a.id] = a.name

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": t.id,
                "agent_id": t.agent_id,
                "agent_name": agents_map.get(t.agent_id, ""),
                "input_text": t.input_text[:200] if t.input_text else "",
                "output_text": t.output_text[:200] if t.output_text else "",
                "latency_ms": t.latency_ms,
                "tokens_used": t.tokens_used,
                "status": t.status,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in items
        ],
    }


@router.get("/{tid}")
def get_trace(tid: str, db: Session = Depends(get_db)):
    from fastapi import HTTPException
    t = db.get(AgentTrace, tid)
    if not t:
        raise HTTPException(404, "Trace not found")
    agent_name = ""
    if t.agent_id:
        a = db.get(Agent, t.agent_id)
        if a:
            agent_name = a.name
    return {
        "id": t.id,
        "agent_id": t.agent_id,
        "agent_name": agent_name,
        "input_text": t.input_text,
        "output_text": t.output_text,
        "latency_ms": t.latency_ms,
        "tokens_used": t.tokens_used,
        "status": t.status,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }
