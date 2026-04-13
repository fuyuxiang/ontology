from pydantic import BaseModel
from datetime import datetime


class RuleCreate(BaseModel):
    entity_id: str
    name: str
    condition_expr: str
    action_desc: str
    status: str = "active"
    priority: str = "medium"


class RuleUpdate(BaseModel):
    name: str | None = None
    condition_expr: str | None = None
    action_desc: str | None = None
    status: str | None = None
    priority: str | None = None


class RuleExecuteResult(BaseModel):
    success: bool
    affected_count: int
    message: str
