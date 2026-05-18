import time
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.agent import Agent, ModelRegistry, gen_uuid
from app.models.eval import EvalSuite, EvalCase, EvalRun, EvalResult

router = APIRouter(prefix="/evals", tags=["evals"])


class SuiteCreate(BaseModel):
    agent_id: str
    name: str


class SuiteUpdate(BaseModel):
    name: Optional[str] = None


class CaseCreate(BaseModel):
    input_prompt: str
    expected_keywords: Optional[list] = None


class CaseUpdate(BaseModel):
    input_prompt: Optional[str] = None
    expected_keywords: Optional[list] = None


@router.get("/suites")
def list_suites(agent_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
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
def create_suite(body: SuiteCreate, db: Session = Depends(get_db)):
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
def update_suite(sid: str, body: SuiteUpdate, db: Session = Depends(get_db)):
    s = db.get(EvalSuite, sid)
    if not s:
        raise HTTPException(404, "Suite not found")
    if body.name is not None:
        s.name = body.name
    db.commit()
    db.refresh(s)
    return {"id": s.id, "name": s.name}


@router.delete("/suites/{sid}")
def delete_suite(sid: str, db: Session = Depends(get_db)):
    s = db.get(EvalSuite, sid)
    if not s:
        raise HTTPException(404, "Suite not found")
    db.delete(s)
    db.commit()
    return {"ok": True}


@router.post("/suites/{sid}/cases", status_code=201)
def create_case(sid: str, body: CaseCreate, db: Session = Depends(get_db)):
    s = db.get(EvalSuite, sid)
    if not s:
        raise HTTPException(404, "Suite not found")
    c = EvalCase(suite_id=sid, input_prompt=body.input_prompt, expected_keywords=body.expected_keywords or [])
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"id": c.id, "input_prompt": c.input_prompt, "expected_keywords": c.expected_keywords or []}


@router.put("/cases/{cid}")
def update_case(cid: str, body: CaseUpdate, db: Session = Depends(get_db)):
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
def delete_case(cid: str, db: Session = Depends(get_db)):
    c = db.get(EvalCase, cid)
    if not c:
        raise HTTPException(404, "Case not found")
    db.delete(c)
    db.commit()
    return {"ok": True}


@router.post("/suites/{sid}/run")
def run_suite(sid: str, db: Session = Depends(get_db)):
    s = db.get(EvalSuite, sid)
    if not s:
        raise HTTPException(404, "Suite not found")
    cases = db.query(EvalCase).filter(EvalCase.suite_id == sid).all()
    if not cases:
        raise HTTPException(400, "No test cases in suite")

    a = db.get(Agent, s.agent_id)
    if not a:
        raise HTTPException(404, "Agent not found")

    from app.services.agent.orchestrator import AgentService
    from app.services.agent.graph_engine import GraphEngine

    model_name = None
    model_config: dict = {}
    if a.model_id:
        m = db.get(ModelRegistry, a.model_id)
        if m:
            model_name = m.model_name
            if m.api_key:
                model_config["api_key"] = m.api_key
            if m.api_base:
                model_config["api_base"] = m.api_base
            if m.config_json:
                model_config.update(m.config_json)
    if a.tools_config:
        for k in ("temperature", "max_tokens"):
            if k in a.tools_config:
                model_config.setdefault(k, a.tools_config[k])

    has_canvas = bool(a.nodes_json and len(a.nodes_json) > 0)

    run = EvalRun(suite_id=sid, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    results = []
    for case in cases:
        t0 = time.time()
        output_chunks = []
        status = "ok"
        try:
            if has_canvas:
                engine = GraphEngine(
                    db, nodes_json=a.nodes_json, edges_json=a.edges_json or [],
                    system_prompt=a.system_prompt or "", model_name=model_name,
                    model_config=model_config or None,
                )
                for event in engine.run(case.input_prompt):
                    if event.get("type") == "answer" and event.get("content"):
                        output_chunks.append(event["content"])
            else:
                entity_id = (a.entity_ids or [None])[0] if a.entity_ids else None
                agent_svc = AgentService(
                    db, system_prompt_prefix=a.system_prompt or None,
                    model_name=model_name, model_config=model_config or None,
                )
                for event in agent_svc.ask(case.input_prompt, entity_id):
                    if event.get("type") == "answer" and event.get("content"):
                        output_chunks.append(event["content"])
        except Exception:
            status = "error"

        latency_ms = int((time.time() - t0) * 1000)
        actual_output = "".join(output_chunks)
        keywords = case.expected_keywords or []
        passed = all(kw.lower() in actual_output.lower() for kw in keywords) if keywords else (status == "ok")

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
