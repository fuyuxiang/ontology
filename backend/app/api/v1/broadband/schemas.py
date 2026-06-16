"""
宽带装机退单稽核 — 请求/响应模型
"""
from typing import Any

from pydantic import BaseModel


# ── 响应模型 ──────────────────────────────────────────────

class OverviewResp(BaseModel):
    total: int = 0
    pending: int = 0
    analyzing: int = 0
    pending_todo: int = 0
    completed: int = 0
    error_count: int = 0
    accuracy_rate: float = 0.0
    avg_confidence: float = 0.0
    today_new: int = 0


class PaginatedList(BaseModel):
    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int


class StatsResp(BaseModel):
    cause_distribution: list[dict[str, Any]]
    subcategory_distribution: list[dict[str, Any]]
    trend_daily: list[dict[str, Any]]
    engineer_ranking: list[dict[str, Any]]
    channel_stats: list[dict[str, Any]]
    address_hotspots: list[dict[str, Any]]
    audit_status_distribution: list[dict[str, Any]]


class AuditActionReq(BaseModel):
    action: str  # archive / override / flag_anomaly
    override_label: str | None = None
    reason: str | None = None


class ApproveReq(BaseModel):
    approved_by: str = "admin"


class RejectReq(BaseModel):
    rejected_by: str = "admin"
    reason: str = ""


class FeedbackReq(BaseModel):
    feedback_type: str = ""
    feedback_value: str = ""
    feedback_text: str = ""


class BatchApproveReq(BaseModel):
    action_ids: list[str]
    approved_by: str = "admin"


class VoiceAuditReq(BaseModel):
    calls: list[dict]  # [{call_id, call_type, asr_text, engineer_name?}]
