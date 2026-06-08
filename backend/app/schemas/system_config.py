from pydantic import BaseModel


class ConfigItem(BaseModel):
    key: str
    value: str | None = None


class ConfigGroup(BaseModel):
    group: str
    items: list[ConfigItem]


class ConfigSaveRequest(BaseModel):
    group: str
    items: list[ConfigItem]


class ConfigResponse(BaseModel):
    groups: dict[str, list[dict]]  # group -> [{key, value, description}]


class TestResult(BaseModel):
    success: bool
    message: str
