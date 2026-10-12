from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

ACTION_TYPES = ["api_call", "sql_exec", "modify_attribute", "notification", "call_function", "custom_script"]
CATEGORIES = ["domain", "system"]


class ParameterDef(BaseModel):
    name: str
    type: str
    required: bool = True
    default_value: str | None = None
    description: str | None = None
    entity_attribute_id: str | None = None


class OutputFieldDef(BaseModel):
    name: str
    type: str
    description: str | None = None


class ActionCreate(BaseModel):
    name: str
    description: str | None = None
    category: str
    entity_id: str | None = None
    ontology_id: str | None = None
    action_type: str
    type_config: dict | None = None
    parameters_json: list[ParameterDef] | None = None
    output_schema: list[OutputFieldDef] | None = None
    status: Literal["active", "inactive", "draft"] = "active"

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        if v not in CATEGORIES:
            raise ValueError(f"category must be one of {CATEGORIES}")
        return v

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, v):
        if v not in ACTION_TYPES:
            raise ValueError(f"action_type must be one of {ACTION_TYPES}")
        return v


class ActionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: Literal["domain", "system"] | None = None
    entity_id: str | None = None
    ontology_id: str | None = None
    action_type: Literal["api_call", "sql_exec", "modify_attribute", "notification", "call_function", "custom_script"] | None = None
    type_config: dict | None = None
    parameters_json: list[ParameterDef] | None = None
    output_schema: list[OutputFieldDef] | None = None
    status: Literal["active", "inactive", "draft"] | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_null_required_fields(cls, values):
        if isinstance(values, dict):
            for key in {"name", "category", "action_type", "status"}:
                if key in values and values[key] is None:
                    raise ValueError(f"{key} 不能为空")
        return values


class ActionOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    category: str
    entity_id: str | None = None
    entity_name: str | None = None
    ontology_id: str | None = None
    action_type: str
    type_config: dict | None = None
    parameters_json: list | None = None
    output_schema: list | None = None
    status: str
    impact_count: int | None = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ActionExecuteRequest(BaseModel):
    params: dict = {}
    dry_run: bool = False
    idempotency_key: str | None = None
    version_id: str | None = None


class ActionExecuteResult(BaseModel):
    success: bool
    message: str
    output: dict | None = None
    execution_id: str | None = None
    state: str | None = None


class ActionReconciliation(BaseModel):
    resolution: Literal["succeeded", "failed"]
    evidence: str = Field(min_length=10, max_length=5000)
    receipt_id: str | None = Field(default=None, max_length=200)


class ActionTypeInfo(BaseModel):
    type_key: str
    label: str
    description: str
    config_schema: dict
