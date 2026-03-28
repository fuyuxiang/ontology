"""
模块功能：
- 运行时策略校验。
- 该文件位于 `backend/app/runtime/policies.py`，定义运行时动作授权策略，校验角色、状态和风险级别是否允许执行操作。
- 文件中定义的核心类包括：`PolicyEngine`。
"""

from __future__ import annotations

from app.runtime.models import ActionDefinition, ActorContext, PolicyDecision, RetentionCase


class PolicyEngine:
    """
    功能：
    - 基于角色、区域和状态执行简单策略判定。
    - 该类定义在 `backend/app/runtime/policies.py` 中，用于组织与 `PolicyEngine` 相关的数据或行为。
    """

    def authorize(
        self,
        action: ActionDefinition,
        case: RetentionCase,
        actor: ActorContext,
    ) -> PolicyDecision:
        """
        功能：
        - 判断给定操作者能否在当前 case 上执行动作。

        输入：
        - `action`: 函数执行所需的 `action` 参数。
        - `case`: 单个运营 case 对象。
        - `actor`: 函数执行所需的 `actor` 参数。

        输出：
        - 返回值: 返回 `PolicyDecision` 类型结果，供后续流程继续消费。
        """
        matched_rules: list[str] = []

        if actor.role not in action.allowed_roles:
            return PolicyDecision(
                allowed=False,
                reason=f"role_not_allowed:{actor.role}",
                matched_rules=("allowed_roles",),
            )
        matched_rules.append("allowed_roles")

        if case.state not in action.allowed_states:
            return PolicyDecision(
                allowed=False,
                reason=f"case_state_not_allowed:{case.state}",
                matched_rules=tuple(matched_rules + ["allowed_states"]),
            )
        matched_rules.append("allowed_states")

        if case.risk_level not in action.allowed_risk_levels:
            return PolicyDecision(
                allowed=False,
                reason=f"risk_level_not_allowed:{case.risk_level}",
                matched_rules=tuple(matched_rules + ["allowed_risk_levels"]),
            )
        matched_rules.append("allowed_risk_levels")

        if actor.area_id and case.area_id and actor.area_id != case.area_id and actor.role != "ops_manager":
            return PolicyDecision(
                allowed=False,
                reason=f"cross_area_denied:{actor.area_id}->{case.area_id}",
                matched_rules=tuple(matched_rules + ["area_scope"]),
            )
        matched_rules.append("area_scope")

        return PolicyDecision(
            allowed=True,
            reason="allowed",
            matched_rules=tuple(matched_rules),
        )
