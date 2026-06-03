import re
from pydantic import BaseModel, field_validator, model_validator
from typing import Literal


PASCAL_CASE_RE = re.compile(r"^[A-Z][a-zA-Z0-9]{1,}$")
SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")
CAMEL_CASE_RE = re.compile(r"^[a-z][a-zA-Z0-9]*$")


class OntologyAttribute(BaseModel):
    name: str
    display_name: str
    type: Literal["string", "number", "boolean", "date", "json", "ref", "computed", "enum"]
    required: bool
    description: str

    @field_validator("name")
    @classmethod
    def name_must_be_snake_case(cls, v: str) -> str:
        if not SNAKE_CASE_RE.match(v) or len(v) > 40:
            raise ValueError(f"name must be snake_case and ≤40 chars, got: {v}")
        return v

    @field_validator("display_name")
    @classmethod
    def display_name_length(cls, v: str) -> str:
        if len(v) > 10:
            raise ValueError(f"display_name must be ≤10 chars, got {len(v)} chars")
        return v


class OntologyEntity(BaseModel):
    name: str
    name_cn: str
    tier: Literal[1, 2, 3]
    description: str
    attributes: list[OntologyAttribute]

    @field_validator("name")
    @classmethod
    def name_must_be_pascal_case(cls, v: str) -> str:
        if not PASCAL_CASE_RE.match(v):
            raise ValueError(f"name must be PascalCase, got: {v}")
        return v

    @field_validator("name_cn")
    @classmethod
    def name_cn_length(cls, v: str) -> str:
        if len(v) > 10:
            raise ValueError(f"name_cn must be ≤10 chars, got {len(v)} chars")
        return v

    @field_validator("attributes")
    @classmethod
    def attributes_not_empty(cls, v: list) -> list:
        if len(v) == 0:
            raise ValueError("attributes must have at least 1 item")
        return v


class OntologyRelation(BaseModel):
    from_entity: str
    to_entity: str
    name: str
    rel_type: Literal["has_one", "has_many", "belongs_to", "many_to_many"]
    cardinality: Literal["1:1", "1:N", "N:1", "N:N"]

    @field_validator("name")
    @classmethod
    def name_must_be_camel_case(cls, v: str) -> str:
        if not CAMEL_CASE_RE.match(v):
            raise ValueError(f"name must be camelCase, got: {v}")
        return v


class OntologyOutput(BaseModel):
    entities: list[OntologyEntity]
    relations: list[OntologyRelation]

    @field_validator("entities")
    @classmethod
    def entities_not_empty(cls, v: list) -> list:
        if len(v) == 0:
            raise ValueError("entities must have at least 1 item")
        return v

    @model_validator(mode="after")
    def relations_reference_valid_entities(self) -> "OntologyOutput":
        entity_names = {e.name for e in self.entities}
        for rel in self.relations:
            if rel.from_entity not in entity_names:
                raise ValueError(f"from_entity '{rel.from_entity}' not found in entities")
            if rel.to_entity not in entity_names:
                raise ValueError(f"to_entity '{rel.to_entity}' not found in entities")
        return self
