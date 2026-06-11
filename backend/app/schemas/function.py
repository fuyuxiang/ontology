from pydantic import BaseModel
from datetime import datetime
from typing import Any


class FunctionInputParam(BaseModel):
    """Schema for a single input parameter in a function's input_schema list.

    Expected JSON shape stored in OntologyFunction.input_schema:
    {
        "name": "amount",          # required – parameter identifier
        "type": "number",          # required – string | number | boolean | date | json
        "required": false,         # optional, default false
        "description": "...",      # optional human-readable hint
        "entity_id": "...",        # optional – links param to an ontology entity
        "attribute_id": "..."      # optional – links param to a specific entity attribute
                                   #  enables type-safety and semantic validation at publish time
    }
    """
    name: str
    type: str = "string"
    required: bool = False
    description: str = ""
    entity_id: str | None = None      # ontology entity this param maps to
    attribute_id: str | None = None   # specific attribute within that entity


class FunctionCreate(BaseModel):
    entity_id: str | None = None
    name: str
    callable_name: str = ""
    description: str = ""
    return_type: str = "string"
    input_schema: list | None = None
    logic_type: str = "expression"
    logic_body: str = ""
    is_derived_property: bool = False
    status: str = "active"
    tags: list[str] | None = None


class FunctionUpdate(BaseModel):
    name: str | None = None
    callable_name: str | None = None
    entity_id: str | None = None
    description: str | None = None
    return_type: str | None = None
    input_schema: list | None = None
    logic_type: str | None = None
    logic_body: str | None = None
    is_derived_property: bool | None = None
    status: str | None = None
    tags: list[str] | None = None


class FunctionOut(BaseModel):
    id: str
    entity_id: str | None = None
    entity_name: str = ""
    name: str
    callable_name: str = ""
    description: str = ""
    return_type: str
    input_schema: list | None = None
    logic_type: str
    logic_body: str = ""
    is_derived_property: bool = False
    status: str
    execution_count: int = 0
    last_executed: datetime | None = None
    tags: list[str] | None = None
    ref_count: int = 0
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
