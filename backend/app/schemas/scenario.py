from datetime import datetime

from pydantic import BaseModel


class ScenarioBase(BaseModel):
    code: str
    name: str
    color: str | None = None
    description: str | None = None
    sort_order: int = 0


class ScenarioCreate(ScenarioBase):
    pass


class ScenarioUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    description: str | None = None
    sort_order: int | None = None


class ScenarioOut(ScenarioBase):
    id: str
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}
