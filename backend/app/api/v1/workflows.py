"""
智能编排中心 API — 工作流场景 CRUD + SSE 执行引擎
"""
import json
import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Any

from app.database import get_db, Base, engine
from app.models.workflow import Workflow, WorkflowExecution, gen_uuid

router = APIRouter(prefix="/workflows", tags=["workflows"])

# 确保表存在
Base.metadata.create_all(bind=engine)


# ── Pydantic 模型 ─────────────────────────────────────────

class WorkflowCreate(BaseModel):
    name: str
    description: str = ""
    namespace: str = ""
    group_name: str = "未分组"

class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    namespace: str | None = None
    group_name: str | None = None
    nodes_json: list | None = None
    edges_json: list | None = None
    trigger_config: dict | None = None
    status: str | None = None

class WorkflowBrief(BaseModel):
    id: str
    name: str
    description: str
    namespace: str
    group_name: str
    status: str
    node_count: int
    created_at: str
    updated_at: str

class ExecuteRequest(BaseModel):
    input_params: dict[str, Any] = {}


# ── 工具函数 ──────────────────────────────────────────────

def _brief(w: Workflow) -> dict:
    return {
        "id": w.id,
        "name": w.name,
        "description": w.description or "",
        "namespace": w.namespace or "",
        "group_name": w.group_name or "未分组",
        "status": w.status,
        "node_count": len(w.nodes_json or []),
        "created_at": w.created_at.isoformat() if w.created_at else "",
        "updated_at": w.updated_at.isoformat() if w.updated_at else "",
    }


def _full(w: Workflow) -> dict:
    d = _brief(w)
    d["nodes_json"] = w.nodes_json or []
    d["edges_json"] = w.edges_json or []
    d["trigger_config"] = w.trigger_config or {}
    return d


# ── CRUD ─────────────────────────────────────────────────

@router.get("")
def list_workflows(
    status: str = Query(default=""),
    group: str = Query(default=""),
    db: Session = Depends(get_db),
):
    q = db.query(Workflow)
    if status:
        q = q.filter(Workflow.status == status)
    if group:
        q = q.filter(Workflow.group_name == group)
    return [_brief(w) for w in q.order_by(Workflow.updated_at.desc()).all()]


@router.post("")
def create_workflow(body: WorkflowCreate, db: Session = Depends(get_db)):
    w = Workflow(
        id=gen_uuid(),
        name=body.name,
        description=body.description,
        namespace=body.namespace,
        group_name=body.group_name,
        nodes_json=[],
        edges_json=[],
        trigger_config={},
        status="draft",
    )
    db.add(w)
    db.commit()
    db.refresh(w)
    return _full(w)


@router.get("/{wid}")
def get_workflow(wid: str, db: Session = Depends(get_db)):
    w = db.get(Workflow, wid)
    if not w:
        raise HTTPException(404, "工作流不存在")
    return _full(w)


@router.put("/{wid}")
def update_workflow(wid: str, body: WorkflowUpdate, db: Session = Depends(get_db)):
    w = db.get(Workflow, wid)
    if not w:
        raise HTTPException(404, "工作流不存在")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(w, field, val)
    w.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(w)
    return _full(w)


@router.delete("/{wid}")
def delete_workflow(wid: str, db: Session = Depends(get_db)):
    w = db.get(Workflow, wid)
    if not w:
        raise HTTPException(404, "工作流不存在")
    db.delete(w)
    db.commit()
    return {"ok": True}


@router.post("/{wid}/publish")
def publish_workflow(wid: str, db: Session = Depends(get_db)):
    w = db.get(Workflow, wid)
    if not w:
        raise HTTPException(404, "工作流不存在")
    w.status = "published"
    w.updated_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "status": "published"}


# ── 执行历史 ──────────────────────────────────────────────

@router.get("/{wid}/executions")
def list_executions(wid: str, db: Session = Depends(get_db)):
    execs = db.query(WorkflowExecution).filter(
        WorkflowExecution.workflow_id == wid
    ).order_by(WorkflowExecution.started_at.desc()).limit(50).all()
    return [{
        "id": e.id,
        "status": e.status,
        "triggered_by": e.triggered_by,
        "started_at": e.started_at.isoformat() if e.started_at else "",
        "finished_at": e.finished_at.isoformat() if e.finished_at else None,
        "error_message": e.error_message,
        "node_count": len(e.node_results or {}),
    } for e in execs]


@router.get("/{wid}/executions/{eid}")
def get_execution(wid: str, eid: str, db: Session = Depends(get_db)):
    e = db.get(WorkflowExecution, eid)
    if not e or e.workflow_id != wid:
        raise HTTPException(404, "执行记录不存在")
    return {
        "id": e.id,
        "workflow_id": e.workflow_id,
        "workflow_name": e.workflow_name,
        "status": e.status,
        "input_params": e.input_params,
        "node_results": e.node_results,
        "triggered_by": e.triggered_by,
        "started_at": e.started_at.isoformat() if e.started_at else "",
        "finished_at": e.finished_at.isoformat() if e.finished_at else None,
        "error_message": e.error_message,
    }


# ── SSE 执行引擎 ──────────────────────────────────────────

NODE_SIMULATORS = {
    "ontology-query":  ("本体查询",   1.2, "查询到 {n} 条本体实例"),
    "datasource":      ("数据源连接", 0.8, "从数据源读取 {n} 条记录"),
    "rule-engine":     ("规则引擎",   1.5, "评估 {n} 条规则，命中 {m} 条"),
    "llm-inference":   ("大模型推理", 2.5, "推理完成，置信度 {conf}%"),
    "ml-model":        ("预测模型",   1.8, "预测完成，高风险 {n} 人"),
    "write-back":      ("结果写回",   0.6, "写回 {n} 条实例"),
    "notification":    ("通知触达",   0.4, "发送通知 {n} 条"),
    "human-approval":  ("人工审批",   0.3, "审批节点已触发，等待审批"),
    "condition":       ("条件判断",   0.2, "条件评估完成，走 {branch} 分支"),
    "loop":            ("遍历列表",   0.5, "遍历 {n} 个元素"),
    "merge":           ("合并分支",   0.2, "分支合并完成"),
}


async def _run_workflow_sse(workflow: Workflow, execution_id: str, db_factory):
    """SSE 生成器：按拓扑顺序逐节点执行并推送事件"""
    import random, time

    nodes = workflow.nodes_json or []
    edges = workflow.edges_json or []
    node_results = {}

    def sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    yield sse("workflow_start", {
        "execution_id": execution_id,
        "workflow_name": workflow.name,
        "total_nodes": len(nodes),
    })

    # 拓扑排序
    in_degree = {n["id"]: 0 for n in nodes}
    children = {n["id"]: [] for n in nodes}
    for e in edges:
        if e["source"] in children and e["target"] in in_degree:
            children[e["source"]].append(e["target"])
            in_degree[e["target"]] += 1

    queue = [n for n in nodes if in_degree[n["id"]] == 0]
    executed = set()

    while queue:
        node = queue.pop(0)
        nid = node["id"]
        ntype = node.get("type", "ontology-query")
        label, delay, msg_tpl = NODE_SIMULATORS.get(ntype, ("未知节点", 0.5, "执行完成"))

        yield sse("node_start", {"node_id": nid, "label": label, "type": ntype})
        await asyncio.sleep(delay)

        # 模拟执行结果
        n = random.randint(10, 200)
        m = random.randint(1, max(1, n // 3))
        conf = random.randint(72, 96)
        branch = random.choice(["true", "false"])
        msg = msg_tpl.format(n=n, m=m, conf=conf, branch=branch)

        result = {
            "status": "success",
            "message": msg,
            "output_count": n,
            "duration_ms": int(delay * 1000 + random.randint(-100, 200)),
        }
        node_results[nid] = result
        executed.add(nid)

        yield sse("node_result", {"node_id": nid, "label": label, "result": result})

        for child_id in children.get(nid, []):
            in_degree[child_id] -= 1
            if in_degree[child_id] == 0:
                child_node = next((n for n in nodes if n["id"] == child_id), None)
                if child_node:
                    queue.append(child_node)

    # 更新执行记录
    db = db_factory()
    try:
        exc = db.get(WorkflowExecution, execution_id)
        if exc:
            exc.status = "completed"
            exc.node_results = node_results
            exc.finished_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()

    yield sse("workflow_done", {
        "execution_id": execution_id,
        "status": "completed",
        "node_count": len(executed),
    })


@router.post("/{wid}/execute")
async def execute_workflow(
    wid: str,
    body: ExecuteRequest = ExecuteRequest(),
    db: Session = Depends(get_db),
):
    w = db.get(Workflow, wid)
    if not w:
        raise HTTPException(404, "工作流不存在")
    if not w.nodes_json:
        raise HTTPException(400, "画布为空，请先添加节点")

    eid = gen_uuid()
    exc = WorkflowExecution(
        id=eid,
        workflow_id=wid,
        workflow_name=w.name,
        status="running",
        input_params=body.input_params,
        node_results={},
        triggered_by="manual",
    )
    db.add(exc)
    db.commit()

    from app.database import SessionLocal

    return StreamingResponse(
        _run_workflow_sse(w, eid, SessionLocal),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
