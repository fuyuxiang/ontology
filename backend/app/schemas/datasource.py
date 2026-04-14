from pydantic import BaseModel
from datetime import datetime


class DataSourceBase(BaseModel):
    name: str
    type: str
    host: str
    port: int
    database: str = ""
    username: str = ""
    password: str = ""
    params: dict | None = None
    description: str | None = None


class DataSourceCreate(DataSourceBase):
    pass


class DataSourceUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    host: str | None = None
    port: int | None = None
    database: str | None = None
    username: str | None = None
    password: str | None = None
    params: dict | None = None
    description: str | None = None
    status: str | None = None


class DataSourceListItem(BaseModel):
    id: str
    name: str
    type: str
    host: str
    port: int
    database: str
    username: str
    password: str
    status: str
    table_count: int = 0
    enabled: bool = False
    description: str | None = None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class DataSourceDetail(DataSourceBase):
    id: str
    status: str
    table_count: int = 0
    enabled: bool = False
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None
    model_config = {"from_attributes": True}


class TestConnectionResult(BaseModel):
    success: bool
    message: str


class TableListResult(BaseModel):
    tables: list[str]


class TablePreviewResult(BaseModel):
    table: str
    columns: list[str]
    rows: list[list]
