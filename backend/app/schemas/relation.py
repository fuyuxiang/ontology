from pydantic import BaseModel


class RelationCreate(BaseModel):
    from_entity_id: str
    to_entity_id: str
    name: str
    rel_type: str = "has_many"
    cardinality: str = "1:N"
    description: str | None = None


class RelationOut(BaseModel):
    id: str
    from_entity_id: str
    from_entity_name: str
    to_entity_id: str
    to_entity_name: str
    name: str
    rel_type: str
    cardinality: str
    description: str | None
