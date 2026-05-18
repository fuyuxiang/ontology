from pydantic import BaseModel
from datetime import datetime


class ActionCreate(BaseModel):
    entity_id: str
    name: str
    type: str = "manual"
    status: str = "active"
    parameters_json: list | None = None
    preconditions_json: list | None = None
    effects_json: list | None = None
    action_meta_json: dict | None = None


class ActionUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    status: str | None = None
    parameters_json: list | None = None
    preconditions_json: list | None = None
    effects_json: list | None = None
    action_meta_json: dict | None = None


class ActionOut(BaseModel):
    id: str
    entity_id: str
    entity_name: str = ""
    name: str
    type: str
    status: str
    impact_count: int | None = None
    parameters_json: list | None = None
    preconditions_json: list | None = None
    effects_json: list | None = None
    action_meta_json: dict | None = None
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


class ActionExecuteRequest(BaseModel):
    params: dict = {}
    dry_run: bool = False


class ActionExecuteResult(BaseModel):
    success: bool
    message: str
    effects: list[dict] = []
