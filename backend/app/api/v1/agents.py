import secrets
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.agent import Agent, ModelRegistry

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


def _agent_out(a: Agent, db: Session) -> dict:
    model_name = None
    if a.model_id:
        m = db.get(ModelRegistry, a.model_id)
        model_name = m.name if m else None
    return {
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
        "nodes_json": a.nodes_json or [],
        "edges_json": a.edges_json or [],
        "status": a.status,
        "api_key": a.api_key if a.status == "published" else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


@router.get("")
def list_agents(db: Session = Depends(get_db)):
    return [_agent_out(a, db) for a in db.query(Agent).all()]


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
    from app.services.agent.orchestrator import AgentService

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

    entity_id = (a.entity_ids or [None])[0] if a.entity_ids else None

    agent_svc = AgentService(
        db,
        system_prompt_prefix=a.system_prompt or None,
        model_name=model_name,
        model_config=model_config or None,
    )

    def event_stream():
        try:
            for event in agent_svc.ask(question, entity_id):
                yield f"data: {_json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {_json.dumps({'type': 'answer', 'content': f'服务异常: {e}', 'suggestions': []}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

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
