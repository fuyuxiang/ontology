"""运行时策略校验。"""

from __future__ import annotations

from app.runtime.models import ActionDefinition, ActorContext, PolicyDecision, RetentionCase


class PolicyEngine:
    """基于角色、区域和状态执行简单策略判定。"""

    def authorize(
        self,
        action: ActionDefinition,
        case: RetentionCase,
        actor: ActorContext,
    ) -> PolicyDecision:
        """判断给定操作者能否在当前 case 上执行动作。"""
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
