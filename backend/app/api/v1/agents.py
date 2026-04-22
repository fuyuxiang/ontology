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
    messages: list
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

    from app.services.copilot import build_ontology_context, get_llm_client
    from app.config import settings

    # Build ontology context from linked entities
    entity_ids = a.entity_ids or []
    ontology_ctx = ""
    if entity_ids:
        ontology_ctx = build_ontology_context(db, entity_ids[0] if entity_ids else None)

    system_parts = []
    if a.system_prompt:
        system_parts.append(a.system_prompt)
    if ontology_ctx:
        system_parts.append(ontology_ctx)
    system_content = "\n\n".join(system_parts) or "你是一个智能助手。"

    messages = [{"role": "system", "content": system_content}] + list(body.messages)

    # Determine model config
    model_cfg = {}
    model_name = settings.LLM_MODEL
    api_key = settings.LLM_API_KEY
    api_base = settings.LLM_API_BASE

    if a.model_id:
        m = db.get(ModelRegistry, a.model_id)
        if m:
            model_name = m.model_name
            if m.api_key:
                api_key = m.api_key
            if m.api_base:
                api_base = m.api_base
            model_cfg = m.config_json or {}

    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=api_base)

    def generate():
        try:
            stream = client.chat.completions.create(
                model=model_name,
                messages=messages,
                stream=True,
                temperature=model_cfg.get("temperature", 0.7),
                max_tokens=model_cfg.get("max_tokens", 2048),
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    yield f"data: {delta}\n\n"
        except Exception as e:
            yield f"data: [ERROR] {e}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


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
