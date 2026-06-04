from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime


ACTION_TYPES = ["api_call", "sql_exec", "modify_attribute", "notification", "call_function", "custom_script"]
CATEGORIES = ["domain", "system"]


class ParameterDef(BaseModel):
    name: str
    type: str
    required: bool = True
    default_value: Optional[str] = None
    description: Optional[str] = None
    entity_attribute_id: Optional[str] = None


class OutputFieldDef(BaseModel):
    name: str
    type: str
    description: Optional[str] = None


class ActionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str
    entity_id: Optional[str] = None
    action_type: str
    type_config: Optional[dict] = None
    parameters_json: Optional[list[ParameterDef]] = None
    output_schema: Optional[list[OutputFieldDef]] = None
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
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    entity_id: Optional[str] = None
    action_type: Optional[str] = None
    type_config: Optional[dict] = None
    parameters_json: Optional[list[ParameterDef]] = None
    output_schema: Optional[list[OutputFieldDef]] = None
    status: Optional[str] = None


class ActionOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    category: str
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    action_type: str
    type_config: Optional[dict] = None
    parameters_json: Optional[list] = None
    output_schema: Optional[list] = None
    status: str
    impact_count: Optional[int] = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ActionExecuteRequest(BaseModel):
    params: dict = {}
    dry_run: bool = False


class ActionExecuteResult(BaseModel):
    success: bool
    message: str
    output: Optional[dict] = None


class ActionTypeInfo(BaseModel):
    type_key: str
    label: str
    description: str
    config_schema: dict
