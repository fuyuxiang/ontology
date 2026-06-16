from datetime import datetime

from pydantic import BaseModel


class RuleCreate(BaseModel):
    entity_id: str
    name: str
    description: str = ""
    condition_expr: str = ""
    action_desc: str = ""
    status: str = "active"
    priority: str = "medium"
    conditions_json: list | None = None
    rule_meta_json: dict | None = None
    tags: list[str] | None = None
    input_params: list[dict] | None = None
    output_schema: dict | None = None
    action_id: str | None = None


class RuleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    condition_expr: str | None = None
    action_desc: str | None = None
    status: str | None = None
    priority: str | None = None
    conditions_json: list | None = None
    rule_meta_json: dict | None = None
    tags: list[str] | None = None
    input_params: list[dict] | None = None
    output_schema: dict | None = None
    action_id: str | None = None


class RuleOut(BaseModel):
    id: str
    name: str
    description: str = ""
    entity_id: str
    entity_name: str = ""
    condition_expr: str = ""
    action_desc: str = ""
    status: str
    priority: str
    trigger_count: int = 0
    last_triggered: datetime | None = None
    conditions_json: list | None = None
    rule_meta_json: dict | None = None
    tags: list[str] | None = None
    input_params: list[dict] | None = None
    output_schema: dict | None = None
    action_id: str | None = None
    ref_count: int = 0
    model_config = {"from_attributes": True}


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
