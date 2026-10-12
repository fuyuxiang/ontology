import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import require_user
from app.models.user import User
from app.services.agent_management import require_edit
from app.models.agent import Agent, ModelRegistry
from app.models.eval import EvalCase, EvalResult, EvalRun, EvalSuite

router = APIRouter(prefix="/evals", tags=["evals"], dependencies=[Depends(require_user)])


class SuiteCreate(BaseModel):
    agent_id: str
    name: str = Field(min_length=1, max_length=200)


class SuiteUpdate(BaseModel):
    name: str | None = None


class CaseCreate(BaseModel):
    input_prompt: str = Field(min_length=1, max_length=20000)
    expected_keywords: list | None = None


class CaseUpdate(BaseModel):
    input_prompt: str | None = None
    expected_keywords: list | None = None


@router.get("/suites")
def list_suites(agent_id: str | None = Query(None), db: Session = Depends(get_db)):
    q = db.query(EvalSuite).order_by(EvalSuite.created_at.desc())
    if agent_id:
        q = q.filter(EvalSuite.agent_id == agent_id)
    suites = q.all()
    agent_ids = {s.agent_id for s in suites}
    agents_map = {}
    if agent_ids:
        for a in db.query(Agent).filter(Agent.id.in_(agent_ids)).all():
            agents_map[a.id] = a.name
    return [
        {
            "id": s.id,
            "agent_id": s.agent_id,
            "agent_name": agents_map.get(s.agent_id, ""),
            "name": s.name,
            "case_count": db.query(EvalCase).filter(EvalCase.suite_id == s.id).count(),
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in suites
    ]


@router.post("/suites", status_code=201)
def create_suite(body: SuiteCreate, db: Session = Depends(get_db), user: User = Depends(require_user)):
    require_edit(user)
    a = db.get(Agent, body.agent_id)
    if not a:
        raise HTTPException(404, "Agent not found")
    s = EvalSuite(agent_id=body.agent_id, name=body.name)
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"id": s.id, "agent_id": s.agent_id, "name": s.name, "created_at": s.created_at.isoformat()}


@router.get("/suites/{sid}")
def get_suite(sid: str, db: Session = Depends(get_db)):
    s = db.get(EvalSuite, sid)
    if not s:
        raise HTTPException(404, "Suite not found")
    cases = db.query(EvalCase).filter(EvalCase.suite_id == sid).order_by(EvalCase.created_at).all()
    runs = db.query(EvalRun).filter(EvalRun.suite_id == sid).order_by(EvalRun.started_at.desc()).limit(10).all()
    agent_name = ""
    a = db.get(Agent, s.agent_id)
    if a:
        agent_name = a.name
    return {
        "id": s.id,
        "agent_id": s.agent_id,
        "agent_name": agent_name,
        "name": s.name,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "cases": [
            {"id": c.id, "input_prompt": c.input_prompt, "expected_keywords": c.expected_keywords or [], "created_at": c.created_at.isoformat() if c.created_at else None}
            for c in cases
        ],
        "runs": [
            {"id": r.id, "status": r.status, "metrics": r.metrics, "started_at": r.started_at.isoformat() if r.started_at else None, "finished_at": r.finished_at.isoformat() if r.finished_at else None}
            for r in runs
        ],
    }


@router.put("/suites/{sid}")
def update_suite(sid: str, body: SuiteUpdate, db: Session = Depends(get_db), user: User = Depends(require_user)):
    require_edit(user)
    s = db.get(EvalSuite, sid)
    if not s:
        raise HTTPException(404, "Suite not found")
    if body.name is not None:
        s.name = body.name
    db.commit()
    db.refresh(s)
    return {"id": s.id, "name": s.name}


@router.delete("/suites/{sid}")
def delete_suite(sid: str, db: Session = Depends(get_db), user: User = Depends(require_user)):
    require_edit(user)
    s = db.get(EvalSuite, sid)
    if not s:
        raise HTTPException(404, "Suite not found")
    run_ids = [r.id for r in db.query(EvalRun).filter_by(suite_id=sid).all()]
    case_ids = [c.id for c in db.query(EvalCase).filter_by(suite_id=sid).all()]
    db.query(EvalResult).filter((EvalResult.run_id.in_(run_ids)) | (EvalResult.case_id.in_(case_ids))).delete(synchronize_session=False)
    db.query(EvalRun).filter_by(suite_id=sid).delete()
    db.query(EvalCase).filter_by(suite_id=sid).delete()
    db.delete(s)
    db.commit()
    return {"ok": True}


@router.post("/suites/{sid}/cases", status_code=201)
def create_case(sid: str, body: CaseCreate, db: Session = Depends(get_db), user: User = Depends(require_user)):
    require_edit(user)
    s = db.get(EvalSuite, sid)
    if not s:
        raise HTTPException(404, "Suite not found")
    c = EvalCase(suite_id=sid, input_prompt=body.input_prompt, expected_keywords=body.expected_keywords or [])
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"id": c.id, "input_prompt": c.input_prompt, "expected_keywords": c.expected_keywords or []}


@router.put("/cases/{cid}")
def update_case(cid: str, body: CaseUpdate, db: Session = Depends(get_db), user: User = Depends(require_user)):
    require_edit(user)
    c = db.get(EvalCase, cid)
    if not c:
        raise HTTPException(404, "Case not found")
    if body.input_prompt is not None:
        c.input_prompt = body.input_prompt
    if body.expected_keywords is not None:
        c.expected_keywords = body.expected_keywords
    db.commit()
    db.refresh(c)
    return {"id": c.id, "input_prompt": c.input_prompt, "expected_keywords": c.expected_keywords or []}


@router.delete("/cases/{cid}")
def delete_case(cid: str, db: Session = Depends(get_db), user: User = Depends(require_user)):
    require_edit(user)
    c = db.get(EvalCase, cid)
    if not c:
        raise HTTPException(404, "Case not found")
    db.query(EvalResult).filter_by(case_id=cid).delete()
    db.delete(c)
    db.commit()
    return {"ok": True}


@router.post("/suites/{sid}/run")
def run_suite(sid: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    require_edit(user)
    s = db.get(EvalSuite, sid)
    if not s:
        raise HTTPException(404, "Suite not found")
    cases = db.query(EvalCase).filter(EvalCase.suite_id == sid).all()
    if not cases:
        raise HTTPException(400, "No test cases in suite")

    a = db.get(Agent, s.agent_id)
    if not a:
        raise HTTPException(404, "Agent not found")

    from types import SimpleNamespace
    from app.api.v1.agents import _collect_steps, _writeback_conversation
    from app.services.agent.orchestrator import AgentService
    from app.services.agent_chat import execute_chat
    from app.services.agent_management import config_snapshot
    snapshot = config_snapshot(a)
    # Evaluation is an isolated preview; confirmation belongs to a user conversation.
    snapshot["tools_config"] = {**(snapshot.get("tools_config") or {}), "action_mode": "simulation"}

    run = EvalRun(suite_id=sid, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    results = []
    for case in cases:
        t0 = time.time()
        actual_output, status, error = "", "error", None
        try:
            observed = execute_chat(db, a, snapshot,
                SimpleNamespace(question=case.input_prompt, messages=None, conversation_id=None, stream=False),
                request, user, AgentService, _collect_steps, _writeback_conversation)
            actual_output = observed.get("answer") or ""
            status, error = observed["status"], observed.get("error")
        except Exception as exc:
            error = str(getattr(exc, "detail", exc))
        latency_ms = int((time.time() - t0) * 1000)
        keywords = case.expected_keywords or []
        passed = status == "completed" and bool(actual_output.strip()) and all(
            str(kw).lower() in actual_output.lower() for kw in keywords)
        if status != "completed":
            actual_output = f"[运行失败：{error or status}]\n{actual_output}"

        r = EvalResult(
            run_id=run.id, case_id=case.id, actual_output=actual_output,
            passed=passed, latency_ms=latency_ms, tokens_used=None,
        )
        db.add(r)
        results.append(r)

    total = len(results)
    passed_count = sum(1 for r in results if r.passed)
    avg_latency = int(sum(r.latency_ms or 0 for r in results) / total) if total else 0

    run.status = "done"
    run.finished_at = datetime.utcnow()
    run.metrics = {"total": total, "passed": passed_count, "pass_rate": round(passed_count / total * 100, 1) if total else 0, "avg_latency_ms": avg_latency}
    db.commit()

    return {
        "id": run.id,
        "status": run.status,
        "metrics": run.metrics,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "results": [
            {"id": r.id, "case_id": r.case_id, "actual_output": r.actual_output[:500], "passed": r.passed, "latency_ms": r.latency_ms}
            for r in results
        ],
    }


@router.get("/runs/{rid}")
def get_run(rid: str, db: Session = Depends(get_db)):
    run = db.get(EvalRun, rid)
    if not run:
        raise HTTPException(404, "Run not found")
    results = db.query(EvalResult).filter(EvalResult.run_id == rid).all()
    case_ids = {r.case_id for r in results}
    cases_map = {}
    if case_ids:
        for c in db.query(EvalCase).filter(EvalCase.id.in_(case_ids)).all():
            cases_map[c.id] = c.input_prompt
    return {
        "id": run.id,
        "suite_id": run.suite_id,
        "status": run.status,
        "metrics": run.metrics,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "results": [
            {"id": r.id, "case_id": r.case_id, "input_prompt": cases_map.get(r.case_id, ""), "actual_output": r.actual_output, "passed": r.passed, "latency_ms": r.latency_ms, "tokens_used": r.tokens_used}
            for r in results
        ],
    }
