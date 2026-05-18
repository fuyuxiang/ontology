"""
AI 智能本体构建 API — 引导式自动化本体构建端点
"""
import json

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.ai_ontology_builder import AIOntologyBuilder, _sessions

router = APIRouter(prefix="/ai-ontology", tags=["ai-ontology"])


class MessageRequest(BaseModel):
    message: str = ""


class SessionResponse(BaseModel):
    id: str
    phase: str
    scenario: str
    materials_count: int
    clarify_count: int
    has_result: bool


@router.post("/sessions", response_model=SessionResponse)
def create_session(db: Session = Depends(get_db)):
    builder = AIOntologyBuilder(db)
    state = builder.create_session()
    return state.to_dict()


@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: str):
    state = _sessions.get(session_id)
    if not state:
        from fastapi import HTTPException
        raise HTTPException(404, "会话不存在")
    return state.to_dict()


@router.post("/sessions/{session_id}/message")
def send_message(
    session_id: str,
    message: str = Form(""),
    files: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
):
    builder = AIOntologyBuilder(db)
    state = builder.get_session(session_id)
    if not state:
        from fastapi import HTTPException
        raise HTTPException(404, "会话不存在")

    file_data: list[dict] = []
    for f in files:
        if f.filename:
            raw = f.file.read()
            content = raw.decode("utf-8", errors="ignore")
            file_data.append({
                "type": "file",
                "name": f.filename,
                "content": content,
            })

    def event_stream():
        try:
            for event in builder.process_message(session_id, message, file_data):
                data = json.dumps(event, ensure_ascii=False)
                yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            error = json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)
            yield f"data: {error}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/sessions/{session_id}/build")
def trigger_build(session_id: str, db: Session = Depends(get_db)):
    builder = AIOntologyBuilder(db)
    state = builder.get_session(session_id)
    if not state:
        from fastapi import HTTPException
        raise HTTPException(404, "会话不存在")

    def event_stream():
        try:
            for event in builder.trigger_build(session_id):
                data = json.dumps(event, ensure_ascii=False)
                yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            error = json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)
            yield f"data: {error}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/sessions/{session_id}/result")
def get_result(session_id: str):
    state = _sessions.get(session_id)
    if not state:
        from fastapi import HTTPException
        raise HTTPException(404, "会话不存在")
    if not state.build_result:
        from fastapi import HTTPException
        raise HTTPException(400, "尚未完成构建")
    return state.build_result


@router.get("/scenarios")
def list_scenarios():
    from app.services.ai_ontology_builder import TELECOM_SCENARIOS
    return {
        "scenarios": [
            {"name": name, "description": info["description"]}
            for name, info in TELECOM_SCENARIOS.items()
        ]
    }
