from pydantic import BaseModel
from datetime import datetime


class RuleCreate(BaseModel):
    entity_id: str
    name: str
    condition_expr: str
    action_desc: str
    status: str = "active"
    priority: str = "medium"
    conditions_json: list | None = None
    rule_meta_json: dict | None = None


class RuleUpdate(BaseModel):
    name: str | None = None
    condition_expr: str | None = None
    action_desc: str | None = None
    status: str | None = None
    priority: str | None = None
    conditions_json: list | None = None
    rule_meta_json: dict | None = None


class RuleExecuteResult(BaseModel):
    success: bool
    affected_count: int
    message: str


class RuleEvaluateRequest(BaseModel):
    user_id: str


class ConditionResult(BaseModel):
    field: str
    display: str
    operator: str
    expected: str | int | float | bool | None = None
    actual: str | int | float | bool | None = None
    matched: bool


class RuleEvaluateResult(BaseModel):
    rule_id: str
    rule_name: str
    triggered: bool
    matched_count: int
    total_count: int
    confidence: float
    conditions: list[ConditionResult]
    risk_level: str | None = None
