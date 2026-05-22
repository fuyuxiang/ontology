"""AIP 场景执行历史 API"""
from __future__ import annotations

import threading
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.scene import AipSceneExecution
from app.repositories import AipSceneExecutionRepository
from app.services.aip.scene_runner import run_scene_in_thread

router = APIRouter(prefix="/aip/executions", tags=["aip-executions"])


def _exec_brief(e: AipSceneExecution) -> dict:
    return {
        "id": e.id,
        "scene_id": e.scene_id,
        "scene_name": e.scene_name or "",
        "scene_version": e.scene_version or 0,
        "status": e.status,
        "triggered_by": e.triggered_by,
        "started_at": e.started_at.isoformat() if e.started_at else "",
        "finished_at": e.finished_at.isoformat() if e.finished_at else None,
        "duration_ms": e.duration_ms or 0,
        "error_message": e.error_message,
        "node_count": len(e.node_results or {}),
    }


def _exec_full(e: AipSceneExecution) -> dict:
    d = _exec_brief(e)
    d["input_params"] = e.input_params or {}
    d["trigger_payload"] = e.trigger_payload or {}
    d["node_results"] = e.node_results or {}
    d["final_output"] = e.final_output or {}
    d["trace_id"] = e.trace_id
    return d


@router.get("")
def list_executions(
    scene_id: str = Query(default=""),
    status: str = Query(default=""),
    triggered_by: str = Query(default=""),
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
):
    repo = AipSceneExecutionRepository(db)
    items = repo.list_by_scene(
        scene_id=scene_id or None,
        status=status or None,
        triggered_by=triggered_by or None,
        limit=limit,
    )
    return [_exec_brief(e) for e in items]


@router.get("/{eid}")
def get_execution(eid: str, db: Session = Depends(get_db)):
    e = db.get(AipSceneExecution, eid)
    if not e:
        raise HTTPException(404, "执行记录不存在")
    return _exec_full(e)


@router.get("/{eid}/trace")
def get_execution_trace(eid: str, db: Session = Depends(get_db)):
    e = db.get(AipSceneExecution, eid)
    if not e:
        raise HTTPException(404, "执行记录不存在")
    if not e.trace_id:
        return {"trace_id": None, "events": []}
    from app.models.trace import AgentTrace
    t = db.get(AgentTrace, e.trace_id)
    if not t:
        return {"trace_id": e.trace_id, "events": []}
    return {
        "trace_id": t.id,
        "input": t.input_text or "",
        "output": t.output_text or "",
        "latency_ms": t.latency_ms or 0,
        "status": t.status or "ok",
    }


@router.post("/{eid}/replay")
def replay_execution(eid: str, db: Session = Depends(get_db)):
    e = db.get(AipSceneExecution, eid)
    if not e:
        raise HTTPException(404, "执行记录不存在")
    holder: dict[str, str] = {"id": ""}

    def _run():
        try:
            holder["id"] = run_scene_in_thread(
                e.scene_id, "replay",
                {"replay_of": eid}, e.input_params or {},
            )
        except Exception:
            pass

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=0.1)
    return {"ok": True, "scheduled": True, "source_execution_id": eid}


@router.delete("/{eid}")
def delete_execution(eid: str, db: Session = Depends(get_db)):
    e = db.get(AipSceneExecution, eid)
    if not e:
        raise HTTPException(404, "执行记录不存在")
    db.delete(e)
    db.commit()
    return {"ok": True}
