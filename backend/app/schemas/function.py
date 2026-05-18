from pydantic import BaseModel
from datetime import datetime


class FunctionCreate(BaseModel):
    entity_id: str | None = None
    name: str
    description: str = ""
    return_type: str = "string"
    input_schema: list | None = None
    logic_type: str = "expression"
    logic_body: str = ""
    is_derived_property: bool = False
    status: str = "active"


class FunctionUpdate(BaseModel):
    name: str | None = None
    entity_id: str | None = None
    description: str | None = None
    return_type: str | None = None
    input_schema: list | None = None
    logic_type: str | None = None
    logic_body: str | None = None
    is_derived_property: bool | None = None
    status: str | None = None


class FunctionOut(BaseModel):
    id: str
    entity_id: str | None = None
    entity_name: str = ""
    name: str
    description: str = ""
    return_type: str
    input_schema: list | None = None
    logic_type: str
    logic_body: str = ""
    is_derived_property: bool = False
    status: str
    execution_count: int = 0
    last_executed: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}


class FunctionTestRequest(BaseModel):
    params: dict = {}


class FunctionTestResult(BaseModel):
    success: bool
    result: str | int | float | bool | None = None
    error: str | None = None
    execution_ms: float = 0
