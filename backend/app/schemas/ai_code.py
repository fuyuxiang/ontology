from pydantic import BaseModel
from datetime import datetime


class AiCodeGenerateRequest(BaseModel):
    target_type: str  # "function" | "action"
    target_id: str
    message: str
    extra_entity_ids: list[str] = []


class AiCodeValidateRequest(BaseModel):
    code: str


class ViolationOut(BaseModel):
    line: int
    reason: str


class AiCodeValidateResponse(BaseModel):
    safe: bool
    violations: list[ViolationOut] = []


class ConversationMessageOut(BaseModel):
    role: str
    content: str
    timestamp: str


class ConversationOut(BaseModel):
    id: str
    target_type: str
    target_id: str
    messages: list[ConversationMessageOut]
    context_entity_ids: list[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}
