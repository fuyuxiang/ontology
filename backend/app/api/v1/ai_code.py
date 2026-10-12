import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import require_user
from app.models.user import User
from app.schemas.ai_code import (
    AiCodeGenerateRequest,
    AiCodeValidateRequest,
    AiCodeValidateResponse,
    ConversationMessageOut,
    ConversationOut,
    ViolationOut,
)
from app.services.ai_code_service import AiCodeService

router = APIRouter(prefix="/ai-code", tags=["ai-code"])


@router.post("/generate")
def generate_code(req: AiCodeGenerateRequest, db: Session = Depends(get_db), user: User = Depends(require_user)):
    service = AiCodeService(db, user.id)

    def event_stream():
        try:
            full_code = ""
            for token in service.generate_stream(
                target_type=req.target_type,
                target_id=req.target_id,
                message=req.message,
                extra_entity_ids=req.extra_entity_ids,
                execution_mode=req.execution_mode,
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
def get_conversation(target_type: str, target_id: str, db: Session = Depends(get_db), user: User = Depends(require_user)):
    service = AiCodeService(db, user.id)
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
    from app.services.code_validator import ValidationResult, Violation
    from app.services.function_runtime.sandbox import UnifiedSandbox
    def execution_validation(code):
        checked = UnifiedSandbox().validate(code)
        return ValidationResult(checked.valid, [Violation(1, reason) for reason in checked.errors])
    if req.execution_mode == "sql":
        from app.services.data_plane.sql_introspect import introspect
        from app.services.code_validator import ValidationResult, Violation
        checked = introspect(req.code)
        result = ValidationResult(checked.ok and checked.is_select, [] if checked.ok and checked.is_select else [Violation(1, checked.reason or "仅允许单条只读SELECT")])
    elif req.execution_mode == "expression":
        import ast
        from app.services.code_validator import ValidationResult, Violation
        try:
            ast.parse(req.code, mode="eval")
            result = execution_validation(req.code)
        except SyntaxError as exc:
            result = ValidationResult(False, [Violation(exc.lineno or 1, "表达式必须是单个可求值表达式")])
    else:
        result = execution_validation(req.code)
    return AiCodeValidateResponse(
        safe=result.safe,
        violations=[ViolationOut(line=v.line, reason=v.reason) for v in result.violations],
    )
