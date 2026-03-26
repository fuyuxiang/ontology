"""运营运行时数据模型。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def utcnow_iso() -> str:
    """返回标准 UTC 时间戳，作为运行时对象默认时间。"""
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat()


def serialize_dataclass(instance: Any) -> dict[str, Any]:
    """把 dataclass 递归转换成 JSON 友好字典。"""
    return asdict(instance)


@dataclass(frozen=True)
class ActorContext:
    """动作执行时的操作者上下文。"""

    role: str
    actor_id: str
    area_id: str | None = None


@dataclass(frozen=True)
class ActionDefinition:
    """动作类型定义。"""

    id: str
    label: str
    description: str
    allowed_roles: tuple[str, ...]
    allowed_states: tuple[str, ...]
    allowed_risk_levels: tuple[str, ...]
    side_effect: str
    queue_hint: str


@dataclass
class OperationalAlert:
    """围绕风险判定生成的运营告警。"""

    id: str
    entity_id: str
    case_id: str
    risk_level: str
    state: str
    recommended_action: str
    created_at: str = field(default_factory=utcnow_iso)
    updated_at: str = field(default_factory=utcnow_iso)


@dataclass
class RetentionCase:
    """围绕主实体展开的运营处置 case。"""

    id: str
    entity_id: str
    alert_id: str
    risk_level: str
    state: str
    priority: str
    queue_name: str
    owner_role: str
    area_id: str | None = None
    created_at: str = field(default_factory=utcnow_iso)
    updated_at: str = field(default_factory=utcnow_iso)
    task_ids: list[str] = field(default_factory=list)
    action_run_ids: list[str] = field(default_factory=list)
    event_ids: list[str] = field(default_factory=list)
    transition_ids: list[str] = field(default_factory=list)


@dataclass
class Task:
    """运营待办任务。"""

    id: str
    case_id: str
    entity_id: str
    action_id: str
    title: str
    status: str
    assignee_role: str
    queue_name: str
    due_sla_hours: int
    created_at: str = field(default_factory=utcnow_iso)
    updated_at: str = field(default_factory=utcnow_iso)
    completed_at: str | None = None
    output: dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionRun:
    """动作执行实例。"""

    id: str
    action_id: str
    case_id: str
    entity_id: str
    actor_role: str
    actor_id: str
    status: str
    policy_reason: str
    created_at: str = field(default_factory=utcnow_iso)
    updated_at: str = field(default_factory=utcnow_iso)
    parameters: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)


@dataclass
class DomainEvent:
    """系统内部记录的业务事件。"""

    id: str
    event_type: str
    title: str
    subject_type: str
    subject_id: str
    entity_id: str
    case_id: str
    created_at: str = field(default_factory=utcnow_iso)
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class StateTransition:
    """对象状态迁移记录。"""

    id: str
    subject_type: str
    subject_id: str
    from_state: str
    to_state: str
    reason: str
    event_id: str
    case_id: str
    entity_id: str
    created_at: str = field(default_factory=utcnow_iso)


@dataclass(frozen=True)
class PolicyDecision:
    """动作授权校验结果。"""

    allowed: bool
    reason: str
    matched_rules: tuple[str, ...]
