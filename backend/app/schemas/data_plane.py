"""Data Plane —— Connection / Asset / Execute / Probe / Lineage / Binding 共享 Pydantic schema。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, ConfigDict


# ── Connection ──────────────────────────────────────────────────

class ConnectionCreate(BaseModel):
    name: str
    category: Literal["database", "object_storage", "file_transfer", "message_queue", "api"] | None = None
    type: str
    host: str = ""
    port: int = 0
    database: str = ""
    username: str = ""
    password: str = ""
    params: dict | None = None
    credential: dict | None = None
    writable: bool = False
    pool_size: int = 4
    rate_limit_qps: int = 20
    description: str | None = None


class ConnectionUpdate(BaseModel):
    name: str | None = None
    host: str | None = None
    port: int | None = None
    database: str | None = None
    username: str | None = None
    password: str | None = None
    params: dict | None = None
    credential: dict | None = None
    writable: bool | None = None
    pool_size: int | None = None
    rate_limit_qps: int | None = None
    description: str | None = None
    enabled: bool | None = None


class ConnectionDetail(BaseModel):
    id: str
    name: str
    category: str
    type: str
    host: str
    port: int
    database: str
    params: dict | None
    writable: bool
    pool_size: int
    rate_limit_qps: int
    description: str | None
    status: str
    enabled: bool
    last_test_at: datetime | None
    last_test_ok: bool
    last_test_message: str | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TestResult(BaseModel):
    success: bool
    message: str
    latency_ms: int | None = None


# ── Asset ────────────────────────────────────────────────────────

class AssetCreate(BaseModel):
    name: str
    alias: str | None = None
    kind: Literal["table", "sql_view", "document"]
    connection_id: str | None = None
    locator: dict
    description: str | None = None
    domain: str | None = None
    tags: list[str] = Field(default_factory=list)
    owner: str | None = None
    sensitivity_tags: dict = Field(default_factory=dict)
    refresh_policy: Literal["on_demand", "hourly", "daily"] = "on_demand"
    cache_ttl_seconds: int = 0


class AssetUpdate(BaseModel):
    name: str | None = None
    alias: str | None = None
    description: str | None = None
    domain: str | None = None
    tags: list[str] | None = None
    owner: str | None = None
    sensitivity_tags: dict | None = None
    refresh_policy: Literal["on_demand", "hourly", "daily"] | None = None
    cache_ttl_seconds: int | None = None


class AssetDetail(BaseModel):
    id: str
    name: str
    alias: str | None
    description: str | None
    kind: str
    connection_id: str | None
    locator: dict
    schema_snapshot: list | None
    schema_synced_at: datetime | None
    primary_key: list | None
    profile: dict | None
    document_source_type: str | None
    parsed_summary: str | None
    embedding_index_ref: str | None
    refresh_policy: str
    cache_ttl_seconds: int
    sensitivity_tags: dict | None
    domain: str | None
    tags: list | None
    owner: str | None
    status: str
    legacy_datasource_id: str | None
    legacy_business_document_id: str | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AssetUsageOut(BaseModel):
    bindings: list[dict]
    builder_sessions: list[dict]
    rules: list[dict]
    actions: list[dict]


class AssetWithUsageOut(BaseModel):
    asset: AssetDetail
    usage: AssetUsageOut
    ref_count: int


class PreviewOut(BaseModel):
    columns: list[str] | None = None
    rows: list[list] | None = None
    rows_returned: int | None = None
    # document
    file_path: str | None = None
    file_type: str | None = None
    summary: str | None = None
    files: list[str] | None = None
    directory_path: str | None = None
    endpoint: str | None = None
    bucket: str | None = None
    prefix: str | None = None
    api_url: str | None = None
    host: str | None = None
    topic: str | None = None
    note: str | None = None
    error: str | None = None


class SchemaSyncOut(BaseModel):
    diff: dict
    schema_snapshot: list


# ── Document 接入特化 schema ─────────────────────────────────────

class OssDocCreate(BaseModel):
    name: str
    endpoint: str
    bucket: str
    access_key: str
    secret_key: str
    prefix: str = ""
    description: str | None = None
    domain: str | None = None
    tags: list[str] = Field(default_factory=list)


class DirectoryDocCreate(BaseModel):
    name: str
    directory_path: str
    file_extensions: list[str] = Field(default_factory=list)
    description: str | None = None
    domain: str | None = None
    tags: list[str] = Field(default_factory=list)


class ApiDocCreate(BaseModel):
    name: str
    api_url: str
    api_method: str = "GET"
    api_headers: dict | None = None
    api_body: str | None = None
    poll_interval: int = 60
    description: str | None = None
    domain: str | None = None
    tags: list[str] = Field(default_factory=list)


class MqDocCreate(BaseModel):
    name: str
    host: str
    port: int = 9092
    topic: str
    group: str = "ontology-consumer"
    username: str = ""
    password: str = ""
    poll_interval: int = 60
    description: str | None = None
    domain: str | None = None
    tags: list[str] = Field(default_factory=list)


# ── Execute ──────────────────────────────────────────────────────

class ExecuteRequestModel(BaseModel):
    asset_id: str
    sql: str
    params: dict = Field(default_factory=dict)
    purpose: str
    timeout_ms: int = 5000
    bypass_cache: bool = False


class ExecuteResultModel(BaseModel):
    columns: list[str]
    rows: list[list]
    rows_returned: int
    duration_ms: int
    cache_hit: bool


class ExecuteBlockedModel(BaseModel):
    blocked: bool = True
    reason: str
    detail: str | None = None


class DryRunOut(BaseModel):
    compiled_sql: str
    referenced_tables: list[str]
    placeholders: list[str]
    is_select: bool
    is_dml: bool


# ── Probe ────────────────────────────────────────────────────────

class ProbeRequest(BaseModel):
    asset_id: str
    column: str | None = None
    threshold: float | None = None


class QualityMetricOut(BaseModel):
    id: str
    asset_id: str
    kind: str
    column_name: str | None
    value_numeric: float | None
    value_text: str | None
    threshold: float | None
    severity: str
    measured_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ── ObjectBinding ───────────────────────────────────────────────

class FieldMapping(BaseModel):
    attribute_id: str
    source_column: str
    transform: str | None = None


class BindingCreate(BaseModel):
    object_type_id: str
    asset_id: str
    role: Literal["primary", "enrichment", "document_evidence"] = "primary"
    field_mappings: list[FieldMapping] = Field(default_factory=list)
    id_column: str | None = None
    filter_expr: str | None = None


class BindingUpdate(BaseModel):
    field_mappings: list[FieldMapping] | None = None
    id_column: str | None = None
    filter_expr: str | None = None
    status: str | None = None
    review_reason: str | None = None


class BindingDetail(BaseModel):
    id: str
    object_type_id: str
    asset_id: str
    role: str
    field_mappings: list
    id_column: str | None
    filter_expr: str | None
    status: str
    review_reason: str | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ── Lineage ──────────────────────────────────────────────────────

class LineageNode(BaseModel):
    kind: str
    id: str
    label: str | None = None
    sub_label: str | None = None
    extra: dict | None = None


class LineageEdgeOut(BaseModel):
    source: LineageNode
    target: LineageNode
    relation: str
    via_module: str | None = None
    via_purpose: str | None = None
    weight: int = 1


class LineageGraph(BaseModel):
    nodes: list[LineageNode]
    edges: list[LineageEdgeOut]


# ── ExecutionLog (审计) ─────────────────────────────────────────

class ExecutionLogOut(BaseModel):
    id: str
    asset_id: str | None
    connection_id: str | None
    purpose: str
    sql_hash: str
    sql_preview: str
    params_redacted: dict | None
    rows_returned: int
    duration_ms: int
    cache_hit: bool
    blocked: bool
    block_reason: str | None
    user_id: str | None
    started_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ExecutionStatsOut(BaseModel):
    total: int
    cache_hit_rate: float
    blocked_rate: float
    avg_duration_ms: float
