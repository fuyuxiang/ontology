"""
模块功能：
- 运营运行时数据模型。
- 该文件位于 `backend/app/runtime/models.py`，定义运行时使用的数据模型与序列化辅助函数，统一数据结构表达。
- 文件中定义的核心类包括：`ActorContext`, `ActionDefinition`, `OperationalAlert`, `RetentionCase`, `Task`, `ActionRun`, `DomainEvent`, `StateTransition`, `PolicyDecision`。
- 文件中对外暴露或复用的主要函数包括：`utcnow_iso`, `serialize_dataclass`。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def utcnow_iso() -> str:
    """
    功能：
    - 返回标准 UTC 时间戳，作为运行时对象默认时间。

    输入：
    - 无。

    输出：
    - 返回值: 返回字符串结果，供调用方继续展示、拼接或查询。
    """
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat()


def serialize_dataclass(instance: Any) -> dict[str, Any]:
    """
    功能：
    - 把 dataclass 递归转换成 JSON 友好字典。

    输入：
    - `instance`: 待序列化或处理的实例对象。

    输出：
    - 返回值: 返回字典结构，包含本次处理产生的结果数据。
    """
    return asdict(instance)


@dataclass(frozen=True)
class ActorContext:
    """
    功能：
    - 动作执行时的操作者上下文。
    - 该类定义在 `backend/app/runtime/models.py` 中，用于组织与 `ActorContext` 相关的数据或行为。
    - 类中声明的主要字段包括：`role`, `actor_id`, `area_id`。
    """

    role: str
    actor_id: str
    area_id: str | None = None


@dataclass(frozen=True)
class ActionDefinition:
    """
    功能：
    - 动作类型定义。
    - 该类定义在 `backend/app/runtime/models.py` 中，用于组织与 `ActionDefinition` 相关的数据或行为。
    - 类中声明的主要字段包括：`id`, `label`, `description`, `allowed_roles`, `allowed_states`, `allowed_risk_levels`, `side_effect`, `queue_hint`。
    """

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
    """
    功能：
    - 围绕风险判定生成的运营告警。
    - 该类定义在 `backend/app/runtime/models.py` 中，用于组织与 `OperationalAlert` 相关的数据或行为。
    - 类中声明的主要字段包括：`id`, `entity_id`, `case_id`, `risk_level`, `state`, `recommended_action`, `created_at`, `updated_at`。
    """

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
    """
    功能：
    - 围绕主实体展开的运营处置 case。
    - 该类定义在 `backend/app/runtime/models.py` 中，用于组织与 `RetentionCase` 相关的数据或行为。
    - 类中声明的主要字段包括：`id`, `entity_id`, `alert_id`, `risk_level`, `state`, `priority`, `queue_name`, `owner_role`, `area_id`, `created_at`, `updated_at`, `task_ids`, `action_run_ids`, `event_ids`, `transition_ids`。
    """

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
    """
    功能：
    - 运营待办任务。
    - 该类定义在 `backend/app/runtime/models.py` 中，用于组织与 `Task` 相关的数据或行为。
    - 类中声明的主要字段包括：`id`, `case_id`, `entity_id`, `action_id`, `title`, `status`, `assignee_role`, `queue_name`, `due_sla_hours`, `created_at`, `updated_at`, `completed_at`, `output`。
    """

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
    """
    功能：
    - 动作执行实例。
    - 该类定义在 `backend/app/runtime/models.py` 中，用于组织与 `ActionRun` 相关的数据或行为。
    - 类中声明的主要字段包括：`id`, `action_id`, `case_id`, `entity_id`, `actor_role`, `actor_id`, `status`, `policy_reason`, `created_at`, `updated_at`, `parameters`, `output`。
    """

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
    """
    功能：
    - 系统内部记录的业务事件。
    - 该类定义在 `backend/app/runtime/models.py` 中，用于组织与 `DomainEvent` 相关的数据或行为。
    - 类中声明的主要字段包括：`id`, `event_type`, `title`, `subject_type`, `subject_id`, `entity_id`, `case_id`, `created_at`, `payload`。
    """

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
    """
    功能：
    - 对象状态迁移记录。
    - 该类定义在 `backend/app/runtime/models.py` 中，用于组织与 `StateTransition` 相关的数据或行为。
    - 类中声明的主要字段包括：`id`, `subject_type`, `subject_id`, `from_state`, `to_state`, `reason`, `event_id`, `case_id`, `entity_id`, `created_at`。
    """

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
    """
    功能：
    - 动作授权校验结果。
    - 该类定义在 `backend/app/runtime/models.py` 中，用于组织与 `PolicyDecision` 相关的数据或行为。
    - 类中声明的主要字段包括：`allowed`, `reason`, `matched_rules`。
    """

    allowed: bool
    reason: str
    matched_rules: tuple[str, ...]
