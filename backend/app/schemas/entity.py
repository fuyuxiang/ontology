from datetime import datetime

from pydantic import BaseModel, Field


class AttributeBase(BaseModel):
    name: str
    type: str
    description: str = ""
    required: bool = False
    example: str | None = None
    constraints_json: dict | None = None
    source_table: str | None = None
    source_field: str | None = None
    data_status: str = "未确认来源"


class AttributeOut(AttributeBase):
    id: str
    model_config = {"from_attributes": True}


class AttributeMappingUpdate(BaseModel):
    attribute_id: str
    source_table: str | None = None
    source_field: str | None = None
    data_status: str = "未确认来源"


class EntityBase(BaseModel):
    name: str
    name_cn: str
    tier: int
    status: str = "active"
    description: str | None = None
    config_json: dict | None = None
    scenario_codes: list[str] | None = None


class EntityCreate(EntityBase):
    ontology_id: str
    attributes: list[AttributeBase] = []


class EntityUpdate(BaseModel):
    name: str | None = None
    name_cn: str | None = None
    tier: int | None = None
    status: str | None = None
    description: str | None = None
    config_json: dict | None = None
    scenario_codes: list[str] | None = None


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
    function_count: int = 0
    action_count: int = 0
    rule_count: int = 0
    datasource_name: str | None = None
    scenario_codes: list[str] | None = None
    is_shared: bool = False
    model_config = {"from_attributes": True}


class RelationOut(BaseModel):
    id: str
    name: str
    rel_type: str
    from_entity_id: str
    from_entity_name: str = ""
    from_entity_tier: int = 1
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
    type: str = Field(validation_alias="action_type")
    status: str
    impact_count: int | None = None
    parameters_json: list | None = None
    preconditions_json: list | None = None
    effects_json: list | None = None
    action_meta_json: dict | None = None
    created_at: datetime | None = None
    model_config = {"from_attributes": True, "populate_by_name": True}


class FunctionBriefOut(BaseModel):
    id: str
    name: str
    description: str = ""
    return_type: str
    logic_type: str
    status: str
    execution_count: int = 0
    model_config = {"from_attributes": True}


class EntityDetail(EntityBase):
    id: str
    attributes: list[AttributeOut] = []
    relations: list[RelationOut] = []
    actions: list[ActionOut] = []
    functions: list[FunctionBriefOut] = []
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None
    model_config = {"from_attributes": True}


class FileImportResult(BaseModel):
    entities_created: int = 0
    entities_skipped: int = 0
    attributes_created: int = 0
    relations_created: int = 0
    rules_created: int = 0
    actions_created: int = 0
    errors: list[str] = []


# ── 本体文件预览（只解析不落库）──
class PreviewProperty(BaseModel):
    name: str
    display_name: str
    type: str
    raw_type: str
    required: bool = False
    description: str = ""
    source_table: str | None = None
    source_field: str | None = None


class PreviewObject(BaseModel):
    name: str
    display_name: str
    tier: int = 3
    namespace: str | None = None
    primary_key: str | None = None
    description: str = ""
    properties: list[PreviewProperty] = []


class PreviewRelation(BaseModel):
    name: str
    display_name: str
    source: str
    target: str
    cardinality: str
    description: str = ""


class PreviewAction(BaseModel):
    name: str
    display_name: str
    trigger: str = "automatic"
    target_object: str | None = None
    description: str = ""


class PreviewDataSource(BaseModel):
    source_id: str
    physical_table: str = ""
    display_name: str = ""


class PreviewSummary(BaseModel):
    object_count: int = 0
    relation_count: int = 0
    property_count: int = 0
    action_count: int = 0


class OntologyPreviewResult(BaseModel):
    objects: list[PreviewObject] = []
    relations: list[PreviewRelation] = []
    actions: list[PreviewAction] = []
    data_sources: list[PreviewDataSource] = []
    summary: PreviewSummary = PreviewSummary()


class GraphNode(BaseModel):
    id: str
    name: str
    name_cn: str
    tier: int
    status: str
    relation_count: int = 0
    action_count: int = 0
    rule_count: int = 0
    function_count: int = 0


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
