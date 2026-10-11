"""API contracts for instruction skills; these contain no executable code."""
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SkillToolRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["function", "action"]
    id: str = Field(min_length=1, max_length=36)


class SkillTestCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    input: str | dict[str, Any]
    expected_keywords: list[str] = Field(default_factory=list, max_length=100)
    expected_tools: list[str] = Field(default_factory=list, max_length=100)


class SkillCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    prompt_template: str = Field(default="", max_length=50000)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    tools: list[SkillToolRef] = Field(default_factory=list, max_length=100)
    test_cases: list[SkillTestCase] = Field(default_factory=list, max_length=50)
    asset_refs: list[str] = Field(default_factory=list, max_length=100)
    ontology_id: str | None = None
    ontology_version_id: str | None = None
    entity_ids: list[str] = Field(default_factory=list, max_length=100)
    applicable_tasks: str = ""
    excluded_tasks: str = ""
    owner_team: str = Field(default="", max_length=100)
    visibility: Literal["private", "workspace"] = "private"
    tags: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("name")
    @classmethod
    def non_blank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("技能名称不能为空")
        return value.strip()


class SkillUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    prompt_template: str | None = Field(default=None, max_length=50000)
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    tools: list[SkillToolRef] | None = Field(default=None, max_length=100)
    test_cases: list[SkillTestCase] | None = Field(default=None, max_length=50)
    asset_refs: list[str] | None = Field(default=None, max_length=100)
    ontology_id: str | None = None
    ontology_version_id: str | None = None
    entity_ids: list[str] | None = Field(default=None, max_length=100)
    applicable_tasks: str | None = None
    excluded_tasks: str | None = None
    owner_team: str | None = Field(default=None, max_length=100)
    visibility: Literal["private", "workspace"] | None = None
    tags: list[str] | None = Field(default=None, max_length=50)

    @field_validator("name")
    @classmethod
    def non_blank_name(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("技能名称不能为空")
        return value.strip() if value else value


class SkillPublishRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str = Field(default="", max_length=2000)


class SkillTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    test_case_ids: list[str] | None = Field(default=None, max_length=50)
