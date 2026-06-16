from datetime import datetime

from pydantic import BaseModel, field_validator

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
    action_type: str
    type_config: dict | None = None
    parameters_json: list[ParameterDef] | None = None
    output_schema: list[OutputFieldDef] | None = None
    status: str = "active"

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
    category: str | None = None
    entity_id: str | None = None
    action_type: str | None = None
    type_config: dict | None = None
    parameters_json: list[ParameterDef] | None = None
    output_schema: list[OutputFieldDef] | None = None
    status: str | None = None


class ActionOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    category: str
    entity_id: str | None = None
    entity_name: str | None = None
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


class ActionExecuteResult(BaseModel):
    success: bool
    message: str
    output: dict | None = None


class ActionTypeInfo(BaseModel):
    type_key: str
    label: str
    description: str
    config_schema: dict
