import secrets
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.agent import Agent, ModelRegistry
from app.models.scene import AipScene

router = APIRouter(prefix="/agents", tags=["agents"])
open_router = APIRouter(prefix="/open/agents", tags=["open-api"])


class AgentCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    tags: Optional[list] = None
    model_id: Optional[str] = None
    system_prompt: Optional[str] = ""
    kb_ids: Optional[list] = None
    entity_ids: Optional[list] = None
    tools_config: Optional[dict] = None
    nodes_json: Optional[list] = None
    edges_json: Optional[list] = None


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list] = None
    model_id: Optional[str] = None
    system_prompt: Optional[str] = None
    kb_ids: Optional[list] = None
    entity_ids: Optional[list] = None
    tools_config: Optional[dict] = None
    nodes_json: Optional[list] = None
    edges_json: Optional[list] = None
    status: Optional[str] = None


class ChatRequest(BaseModel):
    messages: Optional[list] = None
    question: Optional[str] = None
    stream: Optional[bool] = True


def _agent_out(a: Agent, db: Session, referenced_scenes: Optional[list] = None) -> dict:
    model_name = None
    if a.model_id:
        m = db.get(ModelRegistry, a.model_id)
        model_name = m.name if m else None
    result = {
        "id": a.id,
        "name": a.name,
        "description": a.description,
        "tags": a.tags or [],
        "model_id": a.model_id,
        "model_name": model_name,
        "system_prompt": a.system_prompt,
        "kb_ids": a.kb_ids or [],
        "entity_ids": a.entity_ids or [],
        "tools_config": a.tools_config or {},
        "status": a.status,
        "api_key": a.api_key if a.status == "published" else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }
    if referenced_scenes is not None:
        result["referenced_scenes"] = referenced_scenes
    return result


@router.get("")
def list_agents(db: Session = Depends(get_db)):
    # Build agent_id -> referenced scenes mapping
    scenes = db.query(AipScene).all()
    agent_scene_map: dict[str, list[dict]] = {}
    for scene in scenes:
        seen_agents: set[str] = set()
        for node in (scene.nodes_json or []):
            agent_id = (node.get("data") or {}).get("agent_id")
            if agent_id and agent_id not in seen_agents:
                seen_agents.add(agent_id)
                agent_scene_map.setdefault(agent_id, []).append(
                    {"id": scene.id, "name": scene.name}
                )
    return [
        _agent_out(a, db, referenced_scenes=agent_scene_map.get(a.id, []))
        for a in db.query(Agent).all()
    ]


@router.post("", status_code=201)
def create_agent(body: AgentCreate, db: Session = Depends(get_db)):
    a = Agent(**body.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)
    return _agent_out(a, db)


@router.get("/{aid}")
def get_agent(aid: str, db: Session = Depends(get_db)):
    a = db.get(Agent, aid)
    if not a:
        raise HTTPException(404, "Agent not found")
    return _agent_out(a, db)


@router.put("/{aid}")
def update_agent(aid: str, body: AgentUpdate, db: Session = Depends(get_db)):
    a = db.get(Agent, aid)
    if not a:
        raise HTTPException(404, "Agent not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(a, k, v)
    db.commit()
    db.refresh(a)
    return _agent_out(a, db)


@router.delete("/{aid}")
def delete_agent(aid: str, db: Session = Depends(get_db)):
    a = db.get(Agent, aid)
    if not a:
        raise HTTPException(404, "Agent not found")
    db.delete(a)
    db.commit()
    return {"ok": True}


@router.post("/{aid}/publish")
def publish_agent(aid: str, db: Session = Depends(get_db)):
    a = db.get(Agent, aid)
    if not a:
        raise HTTPException(404, "Agent not found")
    if not a.api_key:
        a.api_key = secrets.token_urlsafe(32)
    a.status = "published"
    db.commit()
    db.refresh(a)
    return _agent_out(a, db)


@router.get("/{aid}/api-info")
def get_api_info(aid: str, db: Session = Depends(get_db)):
    a = db.get(Agent, aid)
    if not a:
        raise HTTPException(404, "Agent not found")
    if a.status != "published":
        raise HTTPException(400, "Agent not published")
    endpoint = f"/api/v1/agents/{aid}/chat"
    curl = (
        f'curl -X POST "{endpoint}" \\\n'
        f'  -H "Content-Type: application/json" \\\n'
        f'  -H "X-Agent-Key: {a.api_key}" \\\n'
        f'  -d \'{{"messages": [{{"role": "user", "content": "你好"}}]}}\''
    )
    return {"endpoint": endpoint, "api_key": a.api_key, "curl": curl}


@router.post("/{aid}/chat")
async def chat_with_agent(aid: str, body: ChatRequest, db: Session = Depends(get_db)):
    a = db.get(Agent, aid)
    if not a:
        raise HTTPException(404, "Agent not found")

    import json as _json
    import time as _time
    from app.services.agent.orchestrator import AgentService
    from app.services.agent.graph_engine import GraphEngine
    from app.models.trace import AgentTrace

    # Extract question from messages or direct field
    question = body.question or ""
    if not question and body.messages:
        for m in reversed(body.messages):
            if m.get("role") == "user" and m.get("content"):
                question = m["content"]
                break

    if not question:
        raise HTTPException(400, "No question provided")

    # Build model config from agent settings
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
    agent_id_for_trace = aid
    question_for_trace = question

    if has_canvas:
        engine = GraphEngine(
            db,
            nodes_json=a.nodes_json,
            edges_json=a.edges_json or [],
            system_prompt=a.system_prompt or "",
            model_name=model_name,
            model_config=model_config or None,
        )

        def event_stream():
            t0 = _time.time()
            chunks = []
            status = "ok"
            try:
                for event in engine.run(question_for_trace):
                    if event.get("type") == "answer" and event.get("content"):
                        chunks.append(event["content"])
                    yield f"data: {_json.dumps(event, ensure_ascii=False)}\n\n"
            except Exception as e:
                status = "error"
                yield f"data: {_json.dumps({'type': 'answer', 'content': f'服务异常: {e}', 'suggestions': []}, ensure_ascii=False)}\n\n"
            finally:
                yield "data: [DONE]\n\n"
                try:
                    trace = AgentTrace(
                        agent_id=agent_id_for_trace,
                        input_text=question_for_trace,
                        output_text="".join(chunks),
                        latency_ms=int((_time.time() - t0) * 1000),
                        status=status,
                    )
                    db.add(trace)
                    db.commit()
                except Exception:
                    pass
    else:
        entity_id = (a.entity_ids or [None])[0] if a.entity_ids else None
        agent_svc = AgentService(
            db,
            system_prompt_prefix=a.system_prompt or None,
            model_name=model_name,
            model_config=model_config or None,
        )

        def event_stream():
            t0 = _time.time()
            chunks = []
            status = "ok"
            try:
                for event in agent_svc.ask(question_for_trace, entity_id):
                    if event.get("type") == "answer" and event.get("content"):
                        chunks.append(event["content"])
                    yield f"data: {_json.dumps(event, ensure_ascii=False)}\n\n"
            except Exception as e:
                status = "error"
                yield f"data: {_json.dumps({'type': 'answer', 'content': f'服务异常: {e}', 'suggestions': []}, ensure_ascii=False)}\n\n"
            finally:
                yield "data: [DONE]\n\n"
                try:
                    trace = AgentTrace(
                        agent_id=agent_id_for_trace,
                        input_text=question_for_trace,
                        output_text="".join(chunks),
                        latency_ms=int((_time.time() - t0) * 1000),
                        status=status,
                    )
                    db.add(trace)
                    db.commit()
                except Exception:
                    pass

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ── 公开 API（外部调用，X-Agent-Key 鉴权）──────────────────────────────────

@open_router.post("/{aid}/chat")
async def open_chat(
    aid: str,
    body: ChatRequest,
    x_agent_key: Optional[str] = Header(None, alias="X-Agent-Key"),
    db: Session = Depends(get_db),
):
    a = db.get(Agent, aid)
    if not a:
        raise HTTPException(404, "Agent not found")
    if a.status != "published":
        raise HTTPException(403, "Agent not published")
    if not a.api_key or a.api_key != x_agent_key:
        raise HTTPException(401, "Invalid or missing X-Agent-Key")

    # Reuse internal chat logic
    return await chat_with_agent(aid, body, db)


@open_router.get("/{aid}/info")
def open_agent_info(
    aid: str,
    x_agent_key: Optional[str] = Header(None, alias="X-Agent-Key"),
    db: Session = Depends(get_db),
):
    a = db.get(Agent, aid)
    if not a:
        raise HTTPException(404, "Agent not found")
    if a.status != "published":
        raise HTTPException(403, "Agent not published")
    if not a.api_key or a.api_key != x_agent_key:
        raise HTTPException(401, "Invalid or missing X-Agent-Key")
    return {
        "id": a.id,
        "name": a.name,
        "description": a.description,
        "tags": a.tags or [],
    }


@router.post("/{agent_id}/acknowledge-stale")
def acknowledge_stale(agent_id: str, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(404, "Agent 不存在")
    if not agent.ontology_stale:
        return {"message": "该 Agent 没有过期标记"}

    from app.models.version import OntologyVersion
    active_version = db.query(OntologyVersion).filter(OntologyVersion.is_active == True).first()
    agent.ontology_stale = False
    agent.ontology_stale_detail = None
    agent.ontology_version_id = active_version.id if active_version else None
    db.commit()
    return {"message": "已确认，过期标记已清除"}
