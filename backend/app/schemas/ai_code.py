from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class AiCodeGenerateRequest(BaseModel):
    target_type: Literal["function", "action"]
    target_id: str
    message: str
    extra_entity_ids: list[str] = []
    execution_mode: Literal["expression", "sql", "python", "custom_script"] | None = None


class AiCodeValidateRequest(BaseModel):
    code: str
    execution_mode: Literal["expression", "sql", "python", "custom_script"] = "python"


class ViolationOut(BaseModel):
    line: int
    reason: str


class AiCodeValidateResponse(BaseModel):
    safe: bool
    violations: list[ViolationOut] = []


class ConversationMessageOut(BaseModel):
    execution_mode: str | None = None
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
