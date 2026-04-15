import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.copilot import chat_stream, chat_sync
from app.services.agent_service import AgentService

router = APIRouter(prefix="/copilot", tags=["copilot"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    entity_id: str | None = None
    stream: bool = True


@router.post("/chat")
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    msgs = [{"role": m.role, "content": m.content} for m in req.messages]

    if req.stream:
        def event_stream():
            try:
                for chunk in chat_stream(msgs, db, req.entity_id):
                    data = json.dumps({"content": chunk}, ensure_ascii=False)
                    yield f"data: {data}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                error = json.dumps({"error": str(e)}, ensure_ascii=False)
                yield f"data: {error}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    else:
        result = chat_sync(msgs, db, req.entity_id)
        return {"content": result}


class AgentChatRequest(BaseModel):
    question: str
    entity_id: str | None = None


@router.post("/agent-chat")
def agent_chat(req: AgentChatRequest, db: Session = Depends(get_db)):
    agent = AgentService(db)

    def event_stream():
        try:
            for event in agent.ask(req.question, req.entity_id):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'answer', 'content': f'服务异常: {e}', 'suggestions': []}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
