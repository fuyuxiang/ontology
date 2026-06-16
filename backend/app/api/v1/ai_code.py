import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.ai_code import (
    AiCodeGenerateRequest,
    AiCodeValidateRequest,
    AiCodeValidateResponse,
    ConversationMessageOut,
    ConversationOut,
    ViolationOut,
)
from app.services.ai_code_service import AiCodeService
from app.services.code_validator import validate_code

router = APIRouter(prefix="/ai-code", tags=["ai-code"])


@router.post("/generate")
def generate_code(req: AiCodeGenerateRequest, db: Session = Depends(get_db)):
    service = AiCodeService(db)

    def event_stream():
        try:
            full_code = ""
            for token in service.generate_stream(
                target_type=req.target_type,
                target_id=req.target_id,
                message=req.message,
                extra_entity_ids=req.extra_entity_ids,
            ):
                full_code += token
                data = json.dumps({"event": "chunk", "content": token}, ensure_ascii=False)
                yield f"data: {data}\n\n"

            conv = service.get_conversation(req.target_type, req.target_id)
            done_data = json.dumps({
                "event": "done",
                "full_code": full_code,
                "conversation_id": conv.id if conv else None,
            }, ensure_ascii=False)
            yield f"data: {done_data}\n\n"
        except Exception as e:
            error_data = json.dumps({"event": "error", "message": str(e)}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/conversations/{target_type}/{target_id}", response_model=ConversationOut | None)
def get_conversation(target_type: str, target_id: str, db: Session = Depends(get_db)):
    service = AiCodeService(db)
    conv = service.get_conversation(target_type, target_id)
    if not conv:
        return None
    return ConversationOut(
        id=conv.id,
        target_type=conv.target_type,
        target_id=conv.target_id,
        messages=[ConversationMessageOut(**m) for m in (conv.messages or [])],
        context_entity_ids=conv.context_entity_ids or [],
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


@router.post("/validate", response_model=AiCodeValidateResponse)
def validate_code_endpoint(req: AiCodeValidateRequest):
    result = validate_code(req.code)
    return AiCodeValidateResponse(
        safe=result.safe,
        violations=[ViolationOut(line=v.line, reason=v.reason) for v in result.violations],
    )
