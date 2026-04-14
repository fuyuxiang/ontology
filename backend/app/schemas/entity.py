from pydantic import BaseModel
from datetime import datetime


class AttributeBase(BaseModel):
    name: str
    type: str
    description: str = ""
    required: bool = False
    example: str | None = None
    constraints_json: dict | None = None


class AttributeOut(AttributeBase):
    id: str
    model_config = {"from_attributes": True}


class EntityBase(BaseModel):
    name: str
    name_cn: str
    tier: int
    status: str = "active"
    description: str | None = None
    schema_json: dict | None = None


class EntityCreate(EntityBase):
    attributes: list[AttributeBase] = []


class EntityUpdate(BaseModel):
    name: str | None = None
    name_cn: str | None = None
    tier: int | None = None
    status: str | None = None
    description: str | None = None
    schema_json: dict | None = None


class FromDatasourceRequest(BaseModel):
    datasource_id: str
    table_name: str
    name_cn: str
    tier: int = 3
    namespace: str = ""


class EntityListItem(BaseModel):
    id: str
    name: str
    name_cn: str
    tier: int
    status: str
    attr_count: int = 0
    relation_count: int = 0
    rule_count: int = 0
    datasource_name: str | None = None
    model_config = {"from_attributes": True}


class RelationOut(BaseModel):
    id: str
    name: str
    rel_type: str
    from_entity_id: str
    from_entity_name: str = ""
    to_entity_id: str
    to_entity_name: str = ""
    to_entity_tier: int = 1
    cardinality: str
    acyclic: bool = False
    description: str | None = None
    model_config = {"from_attributes": True}


class ActionOut(BaseModel):
    id: str
    name: str
    type: str
    status: str
    impact_count: int | None = None
    model_config = {"from_attributes": True}


class RuleOut(BaseModel):
    id: str
    name: str
    entity_id: str
    entity_name: str = ""
    condition_expr: str
    action_desc: str
    status: str
    priority: str
    trigger_count: int
    last_triggered: datetime | None = None
    model_config = {"from_attributes": True}


class EntityDetail(EntityBase):
    id: str
    attributes: list[AttributeOut] = []
    relations: list[RelationOut] = []
    rules: list[RuleOut] = []
    actions: list[ActionOut] = []
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None
    model_config = {"from_attributes": True}


class GraphNode(BaseModel):
    id: str
    name: str
    name_cn: str
    tier: int
    status: str
    relation_count: int = 0


class GraphEdge(BaseModel):
    from_id: str
    from_name: str
    to_id: str
    to_name: str
    label: str
    cardinality: str


class GraphData(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
