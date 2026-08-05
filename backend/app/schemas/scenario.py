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
    # 本体下各类组件数量，由列表接口聚合填充
    entity_count: int = 0
    relation_count: int = 0
    logic_count: int = 0
    action_count: int = 0
    model_config = {"from_attributes": True}
