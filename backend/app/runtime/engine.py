"""
模块功能：
- 运营运行时引擎。
- 该文件位于 `backend/app/runtime/engine.py`，实现当前领域的核心引擎逻辑，负责状态推进、规则处理或运行时协调。
- 文件中定义的核心类包括：`RuntimeEngine`。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from rdflib import Graph, Literal, RDF, RDFS, URIRef, XSD

from app.config.settings import Settings
from app.ontology.namespaces import make_namespaces
from app.runtime.models import (
    ActionDefinition,
    ActionRun,
    ActorContext,
    DomainEvent,
    OperationalAlert,
    RetentionCase,
    StateTransition,
    Task,
    serialize_dataclass,
    utcnow_iso,
)
from app.runtime.policies import PolicyEngine


class RuntimeEngine:
    """
    功能：
    - 维护 case/task/action/event 的运营状态。
    - 该类定义在 `backend/app/runtime/engine.py` 中，用于组织与 `RuntimeEngine` 相关的数据或行为。
    - 类中声明的主要字段包括：`ACTION_DEFINITIONS`。
    """

    ACTION_DEFINITIONS: tuple[ActionDefinition, ...] = (
        ActionDefinition(
            id="acknowledge-alert",
            label="确认告警",
            description="确认风险告警并把 case 纳入正式跟进流程。",
            allowed_roles=("ops_manager", "senior_agent", "agent"),
            allowed_states=("OPEN",),
            allowed_risk_levels=("HIGH", "MEDIUM"),
            side_effect="update-alert-state",
            queue_hint="triage",
        ),
        ActionDefinition(
            id="assign-retention-owner",
            label="分派维系负责人",
            description="把 case 分派到高风险或标准维系队列。",
            allowed_roles=("ops_manager",),
            allowed_states=("OPEN", "ACKED", "MONITORING"),
            allowed_risk_levels=("HIGH", "MEDIUM", "LOW"),
            side_effect="assign-case-owner",
            queue_hint="dispatch",
        ),
        ActionDefinition(
            id="start-retention-contact",
            label="开始联系用户",
            description="触发外呼或人工联系，正式进入维系执行阶段。",
            allowed_roles=("ops_manager", "senior_agent", "agent"),
            allowed_states=("OPEN", "ACKED", "ASSIGNED"),
            allowed_risk_levels=("HIGH", "MEDIUM"),
            side_effect="create-contact-attempt",
            queue_hint="outreach",
        ),
        ActionDefinition(
            id="submit-retention-offer",
            label="提交维系方案",
            description="向用户提交优惠、套餐调整或专席方案。",
            allowed_roles=("ops_manager", "senior_agent", "agent"),
            allowed_states=("CONTACTED",),
            allowed_risk_levels=("HIGH", "MEDIUM"),
            side_effect="sync-crm-offer",
            queue_hint="offer",
        ),
        ActionDefinition(
            id="mark-offer-accepted",
            label="标记方案接受",
            description="确认用户接受维系方案并把 case 标记为赢回。",
            allowed_roles=("ops_manager", "senior_agent"),
            allowed_states=("OFFERED",),
            allowed_risk_levels=("HIGH", "MEDIUM"),
            side_effect="mark-retention-win",
            queue_hint="closure",
        ),
        ActionDefinition(
            id="mark-customer-lost",
            label="标记流失",
            description="确认用户未被挽留成功或已经转网。",
            allowed_roles=("ops_manager", "senior_agent"),
            allowed_states=("ASSIGNED", "CONTACTED", "OFFERED"),
            allowed_risk_levels=("HIGH", "MEDIUM"),
            side_effect="mark-port-out-loss",
            queue_hint="closure",
        ),
        ActionDefinition(
            id="resolve-monitoring-case",
            label="结束监控",
            description="将低风险监控 case 标记为已完成监控。",
            allowed_roles=("ops_manager", "senior_agent"),
            allowed_states=("MONITORING",),
            allowed_risk_levels=("LOW",),
            side_effect="resolve-monitoring",
            queue_hint="monitoring",
        ),
        ActionDefinition(
            id="close-case",
            label="关闭 Case",
            description="在赢回、流失或已解决后关闭 case。",
            allowed_roles=("ops_manager",),
            allowed_states=("WON", "LOST", "RESOLVED"),
            allowed_risk_levels=("HIGH", "MEDIUM", "LOW"),
            side_effect="close-case",
            queue_hint="closure",
        ),
    )

    def __init__(self, settings: Settings) -> None:
        """
        功能：
        - 初始化当前对象并准备后续调用所需的依赖、状态和缓存。

        输入：
        - `settings`: 运行时配置对象，提供目录路径、命名空间和环境参数。

        输出：
        - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
        """
        self.settings = settings
        self.policy_engine = PolicyEngine()
        self.action_definitions = {item.id: item for item in self.ACTION_DEFINITIONS}
        self.alerts: dict[str, OperationalAlert] = {}
        self.cases: dict[str, RetentionCase] = {}
        self.tasks: dict[str, Task] = {}
        self.action_runs: dict[str, ActionRun] = {}
        self.events: dict[str, DomainEvent] = {}
        self.transitions: dict[str, StateTransition] = {}
        self._loaded = False

    def bootstrap(
        self,
        records: dict[str, dict[str, Any]],
        inference: dict[str, dict[str, Any]],
    ) -> None:
        """
        功能：
        - 按最新推理结果构建或刷新运营态。

        输入：
        - `records`: 按实体标识组织的聚合记录集合。
        - `inference`: 按实体组织的推理结果集合。

        输出：
        - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
        """
        self._load_state_once()
        active_entities = set(records)

        for entity_id, record in records.items():
            result = inference[entity_id]
            area_id = str(record["primary"].get("area_id") or "").strip() or None
            alert = self._ensure_alert(entity_id, result)
            case = self._ensure_case(entity_id, alert, result, area_id)
            self._refresh_case_priority(case, result)
            self._refresh_case_state(case, alert, result)
            self._ensure_default_work_items(case)

        self._mark_stale_entities(active_entities)
        self._save_state()

    def operational_summary(self) -> dict[str, Any]:
        """
        功能：
        - 返回运营态汇总指标。

        输入：
        - 无。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        case_distribution = self._count_by(self.cases.values(), "state")
        task_distribution = self._count_by(self.tasks.values(), "status")
        alert_distribution = self._count_by(self.alerts.values(), "state")
        return {
            "caseCount": len(self.cases),
            "openCaseCount": sum(1 for item in self.cases.values() if item.state not in {"CLOSED"}),
            "taskCount": len(self.tasks),
            "todoTaskCount": sum(1 for item in self.tasks.values() if item.status == "TODO"),
            "actionRunCount": len(self.action_runs),
            "eventCount": len(self.events),
            "caseDistribution": case_distribution,
            "taskDistribution": task_distribution,
            "alertDistribution": alert_distribution,
            "actionCatalog": [serialize_dataclass(item) for item in self.ACTION_DEFINITIONS],
        }

    def list_cases(self) -> list[dict[str, Any]]:
        """
        功能：
        - 列出所有 case 摘要。

        输入：
        - 无。

        输出：
        - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
        """
        payload = [self._case_payload(case) for case in self.cases.values()]
        payload.sort(key=lambda item: (item["priority"], item["entityId"]))
        return payload

    def get_case(self, case_id: str) -> dict[str, Any] | None:
        """
        功能：
        - 返回单个 case 详情。

        输入：
        - `case_id`: 运营 case 标识。

        输出：
        - 返回值: 返回处理结果；当目标不存在、未命中或无法解析时返回 `None`。
        """
        case = self.cases.get(case_id)
        if case is None:
            return None
        payload = self._case_payload(case)
        payload["timeline"] = self.get_timeline(case.id)
        payload["tasks"] = self.list_tasks(case_id=case.id)
        payload["actionRuns"] = self.list_action_runs(case.id)
        return payload

    def get_case_for_entity(self, entity_id: str) -> dict[str, Any] | None:
        """
        功能：
        - 按实体 ID 获取 case。

        输入：
        - `entity_id`: 业务主实体标识。

        输出：
        - 返回值: 返回处理结果；当目标不存在、未命中或无法解析时返回 `None`。
        """
        case = self.cases.get(self._case_id(entity_id))
        if case is None:
            return None
        return self.get_case(case.id)

    def get_alert_for_entity(self, entity_id: str) -> dict[str, Any] | None:
        """
        功能：
        - 按实体 ID 获取运行时告警。

        输入：
        - `entity_id`: 业务主实体标识。

        输出：
        - 返回值: 返回处理结果；当目标不存在、未命中或无法解析时返回 `None`。
        """
        alert = self.alerts.get(self._alert_id(entity_id))
        if alert is None:
            return None
        return serialize_dataclass(alert)

    def list_tasks(
        self,
        *,
        case_id: str | None = None,
        status: str | None = None,
        assignee_role: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        功能：
        - 列出任务。

        输入：
        - `case_id`: 运营 case 标识。
        - `status`: 筛选或设置时使用的状态值。
        - `assignee_role`: 任务或 case 负责人角色标识。

        输出：
        - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
        """
        payload: list[dict[str, Any]] = []
        for task in self.tasks.values():
            if case_id and task.case_id != case_id:
                continue
            if status and task.status != status:
                continue
            if assignee_role and task.assignee_role != assignee_role:
                continue
            payload.append(serialize_dataclass(task))
        payload.sort(key=lambda item: (item["status"], item["created_at"], item["id"]))
        return payload

    def list_action_runs(self, case_id: str) -> list[dict[str, Any]]:
        """
        功能：
        - 列出某个 case 下的动作执行记录。

        输入：
        - `case_id`: 运营 case 标识。

        输出：
        - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
        """
        payload = [serialize_dataclass(run) for run in self.action_runs.values() if run.case_id == case_id]
        payload.sort(key=lambda item: item["created_at"])
        return payload

    def get_timeline(self, case_id: str) -> list[dict[str, Any]]:
        """
        功能：
        - 构造 case 时间线。

        输入：
        - `case_id`: 运营 case 标识。

        输出：
        - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
        """
        case = self.cases.get(case_id)
        if case is None:
            return []
        items: list[dict[str, Any]] = []
        for event_id in case.event_ids:
            event = self.events.get(event_id)
            if event is None:
                continue
            items.append(
                {
                    "kind": "event",
                    "time": event.created_at,
                    "title": event.title,
                    "eventType": event.event_type,
                    "subjectType": event.subject_type,
                    "subjectId": event.subject_id,
                    "payload": event.payload,
                }
            )
        for transition_id in case.transition_ids:
            transition = self.transitions.get(transition_id)
            if transition is None:
                continue
            items.append(
                {
                    "kind": "transition",
                    "time": transition.created_at,
                    "title": f"{transition.subject_type} 状态变更",
                    "fromState": transition.from_state,
                    "toState": transition.to_state,
                    "reason": transition.reason,
                    "subjectType": transition.subject_type,
                    "subjectId": transition.subject_id,
                }
            )
        items.sort(key=lambda item: (item["time"], item["kind"]))
        return items

    def available_actions(self, entity_id: str) -> list[dict[str, Any]]:
        """
        功能：
        - 返回当前 case 可执行的动作清单。

        输入：
        - `entity_id`: 业务主实体标识。

        输出：
        - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
        """
        case = self.cases.get(self._case_id(entity_id))
        if case is None:
            return []
        actions = []
        for definition in self.ACTION_DEFINITIONS:
            if case.state not in definition.allowed_states:
                continue
            if case.risk_level not in definition.allowed_risk_levels:
                continue
            actions.append(serialize_dataclass(definition))
        return actions

    def execute_action(
        self,
        *,
        action_id: str,
        actor: ActorContext,
        entity_id: str | None = None,
        case_id: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        功能：
        - 执行动作并写入动作记录、事件和状态迁移。

        输入：
        - `action_id`: 待执行动作的标识。
        - `actor`: 函数执行所需的 `actor` 参数。
        - `entity_id`: 业务主实体标识。
        - `case_id`: 运营 case 标识。
        - `parameters`: 字典参数 `parameters`，承载键值形式的输入数据。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        if action_id not in self.action_definitions:
            raise ValueError(f"unknown_action:{action_id}")

        runtime_case = self._resolve_case(case_id=case_id, entity_id=entity_id)
        if runtime_case is None:
            raise ValueError("case_not_found")
        action = self.action_definitions[action_id]
        decision = self.policy_engine.authorize(action, runtime_case, actor)
        if not decision.allowed:
            raise ValueError(f"policy_denied:{decision.reason}")

        payload = parameters or {}
        run = ActionRun(
            id=f"action-run:{uuid4().hex}",
            action_id=action_id,
            case_id=runtime_case.id,
            entity_id=runtime_case.entity_id,
            actor_role=actor.role,
            actor_id=actor.actor_id,
            status="SUCCEEDED",
            policy_reason=decision.reason,
            parameters=dict(payload),
        )
        self.action_runs[run.id] = run
        runtime_case.action_run_ids.append(run.id)

        output = self._apply_action(run, runtime_case, payload)
        run.output = output
        run.updated_at = utcnow_iso()
        self._save_state()

        return {
            "actionRun": serialize_dataclass(run),
            "case": self.get_case(runtime_case.id),
            "alert": self.get_alert_for_entity(runtime_case.entity_id),
            "availableActions": self.available_actions(runtime_case.entity_id),
        }

    def materialize(
        self,
        graph: Graph,
        settings: Settings,
        records: dict[str, dict[str, Any]],
    ) -> None:
        """
        功能：
        - 把运营态对象物化为 RDF。

        输入：
        - `graph`: 需要读取或写入的 RDF 图对象。
        - `settings`: 运行时配置对象，提供目录路径、命名空间和环境参数。
        - `records`: 按实体标识组织的聚合记录集合。

        输出：
        - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
        """
        namespaces = make_namespaces(settings)
        telecom = namespaces["telecom"]

        entity_resources = {
            entity_id: record["primary"].get("_entity_uri")
            for entity_id, record in records.items()
            if record.get("primary", {}).get("_entity_uri") is not None
        }

        for definition in self.ACTION_DEFINITIONS:
            definition_uri = self._runtime_uri(settings, "action-definition", definition.id)
            graph.add((definition_uri, RDF.type, telecom.ActionDefinition))
            graph.add((definition_uri, RDFS.label, Literal(definition.label)))
            graph.add((definition_uri, telecom.actionId, Literal(definition.id)))
            graph.add((definition_uri, telecom.description, Literal(definition.description)))
            graph.add((definition_uri, telecom.sideEffect, Literal(definition.side_effect)))
            graph.add((definition_uri, telecom.queueName, Literal(definition.queue_hint)))
            for role in definition.allowed_roles:
                graph.add((definition_uri, telecom.allowedRole, Literal(role)))

        for alert in self.alerts.values():
            alert_uri = URIRef(f"{settings.data_ns}alert/{quote(alert.entity_id, safe='')}")
            graph.add((alert_uri, telecom.alertState, Literal(alert.state)))
            graph.add((alert_uri, telecom.caseId, Literal(alert.case_id)))
            graph.add((alert_uri, telecom.updatedAt, Literal(alert.updated_at, datatype=XSD.dateTime)))

        for case in self.cases.values():
            case_uri = self._runtime_uri(settings, "case", case.id)
            graph.add((case_uri, RDF.type, telecom.RetentionCase))
            graph.add((case_uri, RDFS.label, Literal(f"{case.entity_id} 维系 Case")))
            graph.add((case_uri, telecom.caseId, Literal(case.id)))
            graph.add((case_uri, telecom.caseState, Literal(case.state)))
            graph.add((case_uri, telecom.riskLevel, Literal(case.risk_level)))
            graph.add((case_uri, telecom.priority, Literal(case.priority)))
            graph.add((case_uri, telecom.queueName, Literal(case.queue_name)))
            graph.add((case_uri, telecom.ownerRole, Literal(case.owner_role)))
            graph.add((case_uri, telecom.createdAt, Literal(case.created_at, datatype=XSD.dateTime)))
            graph.add((case_uri, telecom.updatedAt, Literal(case.updated_at, datatype=XSD.dateTime)))
            if case.area_id:
                graph.add((case_uri, telecom.areaId, Literal(case.area_id)))

            entity_uri = entity_resources.get(case.entity_id)
            if isinstance(entity_uri, URIRef):
                graph.add((entity_uri, telecom.hasRetentionCase, case_uri))

            alert_uri = URIRef(f"{settings.data_ns}alert/{quote(case.entity_id, safe='')}")
            graph.add((case_uri, telecom.forAlert, alert_uri))

            for action in self.available_actions(case.entity_id):
                definition_uri = self._runtime_uri(settings, "action-definition", action["id"])
                graph.add((case_uri, telecom.availableAction, definition_uri))

        for task in self.tasks.values():
            task_uri = self._runtime_uri(settings, "task", task.id)
            graph.add((task_uri, RDF.type, telecom.Task))
            graph.add((task_uri, RDFS.label, Literal(task.title)))
            graph.add((task_uri, telecom.taskState, Literal(task.status)))
            graph.add((task_uri, telecom.assigneeRole, Literal(task.assignee_role)))
            graph.add((task_uri, telecom.queueName, Literal(task.queue_name)))
            graph.add((task_uri, telecom.actionId, Literal(task.action_id)))
            graph.add((task_uri, telecom.createdAt, Literal(task.created_at, datatype=XSD.dateTime)))
            graph.add((task_uri, telecom.updatedAt, Literal(task.updated_at, datatype=XSD.dateTime)))
            case_uri = self._runtime_uri(settings, "case", task.case_id)
            graph.add((case_uri, telecom.hasTask, task_uri))
            graph.add((task_uri, telecom.forCase, case_uri))

        for run in self.action_runs.values():
            run_uri = self._runtime_uri(settings, "action-run", run.id)
            graph.add((run_uri, RDF.type, telecom.ActionRun))
            graph.add((run_uri, RDFS.label, Literal(f"{run.entity_id} 动作执行 {run.action_id}")))
            graph.add((run_uri, telecom.actionId, Literal(run.action_id)))
            graph.add((run_uri, telecom.actionStatus, Literal(run.status)))
            graph.add((run_uri, telecom.actorRole, Literal(run.actor_role)))
            graph.add((run_uri, telecom.createdAt, Literal(run.created_at, datatype=XSD.dateTime)))
            graph.add((run_uri, telecom.updatedAt, Literal(run.updated_at, datatype=XSD.dateTime)))
            case_uri = self._runtime_uri(settings, "case", run.case_id)
            definition_uri = self._runtime_uri(settings, "action-definition", run.action_id)
            graph.add((case_uri, telecom.hasActionRun, run_uri))
            graph.add((run_uri, telecom.forCase, case_uri))
            graph.add((run_uri, telecom.usesActionDefinition, definition_uri))

        for event in self.events.values():
            event_uri = self._runtime_uri(settings, "event", event.id)
            graph.add((event_uri, RDF.type, telecom.DomainEvent))
            graph.add((event_uri, RDFS.label, Literal(event.title)))
            graph.add((event_uri, telecom.eventType, Literal(event.event_type)))
            graph.add((event_uri, telecom.eventTime, Literal(event.created_at, datatype=XSD.dateTime)))
            case_uri = self._runtime_uri(settings, "case", event.case_id)
            graph.add((case_uri, telecom.hasEvent, event_uri))
            graph.add((event_uri, telecom.forCase, case_uri))

        for transition in self.transitions.values():
            transition_uri = self._runtime_uri(settings, "transition", transition.id)
            graph.add((transition_uri, RDF.type, telecom.StateTransition))
            graph.add((transition_uri, telecom.transitionFrom, Literal(transition.from_state)))
            graph.add((transition_uri, telecom.transitionTo, Literal(transition.to_state)))
            graph.add((transition_uri, telecom.eventTime, Literal(transition.created_at, datatype=XSD.dateTime)))
            case_uri = self._runtime_uri(settings, "case", transition.case_id)
            graph.add((case_uri, telecom.hasTransition, transition_uri))
            graph.add((transition_uri, telecom.forCase, case_uri))

    def _ensure_alert(self, entity_id: str, result: dict[str, Any]) -> OperationalAlert:
        """
        功能：
        - 确保alert。

        输入：
        - `entity_id`: 业务主实体标识。
        - `result`: 当前实体对应的推理结果。

        输出：
        - 返回值: 返回 `OperationalAlert` 类型结果，供后续流程继续消费。
        """
        alert_id = self._alert_id(entity_id)
        alert = self.alerts.get(alert_id)
        target_state = "NEW" if result["riskLevel"] in {"HIGH", "MEDIUM"} else "MONITORING"
        if alert is None:
            alert = OperationalAlert(
                id=alert_id,
                entity_id=entity_id,
                case_id=self._case_id(entity_id),
                risk_level=result["riskLevel"],
                state=target_state,
                recommended_action=result["recommendedAction"],
            )
            self.alerts[alert_id] = alert
            self._emit_event(
                event_type="alert-created",
                title="风险告警已创建",
                subject_type="alert",
                subject_id=alert.id,
                entity_id=entity_id,
                case_id=self._case_id(entity_id),
                payload={"riskLevel": result["riskLevel"]},
            )
            return alert

        if alert.risk_level != result["riskLevel"]:
            old_level = alert.risk_level
            alert.risk_level = result["riskLevel"]
            self._emit_event(
                event_type="risk-level-updated",
                title="风险等级已更新",
                subject_type="alert",
                subject_id=alert.id,
                entity_id=entity_id,
                case_id=alert.case_id,
                payload={"from": old_level, "to": result["riskLevel"]},
            )
        alert.recommended_action = result["recommendedAction"]
        alert.updated_at = utcnow_iso()
        return alert

    def _ensure_case(
        self,
        entity_id: str,
        alert: OperationalAlert,
        result: dict[str, Any],
        area_id: str | None,
    ) -> RetentionCase:
        """
        功能：
        - 确保case。

        输入：
        - `entity_id`: 业务主实体标识。
        - `alert`: 单个运行时告警对象或告警载荷。
        - `result`: 当前实体对应的推理结果。
        - `area_id`: 函数执行所需的 `area_id` 参数。

        输出：
        - 返回值: 返回 `RetentionCase` 类型结果，供后续流程继续消费。
        """
        case_id = self._case_id(entity_id)
        runtime_case = self.cases.get(case_id)
        if runtime_case is None:
            runtime_case = RetentionCase(
                id=case_id,
                entity_id=entity_id,
                alert_id=alert.id,
                risk_level=result["riskLevel"],
                state="OPEN" if result["riskLevel"] in {"HIGH", "MEDIUM"} else "MONITORING",
                priority=self._priority_for_risk(result["riskLevel"]),
                queue_name=self._queue_for_risk(result["riskLevel"]),
                owner_role=self._owner_role_for_risk(result["riskLevel"]),
                area_id=area_id,
            )
            self.cases[case_id] = runtime_case
            self._emit_event(
                event_type="case-opened",
                title="维系 Case 已创建",
                subject_type="case",
                subject_id=runtime_case.id,
                entity_id=entity_id,
                case_id=runtime_case.id,
                payload={"riskLevel": result["riskLevel"]},
            )
        else:
            runtime_case.risk_level = result["riskLevel"]
            runtime_case.alert_id = alert.id
            runtime_case.area_id = area_id
            runtime_case.updated_at = utcnow_iso()
        return runtime_case

    def _refresh_case_priority(self, case: RetentionCase, result: dict[str, Any]) -> None:
        """
        功能：
        - 刷新casepriority。

        输入：
        - `case`: 单个运营 case 对象。
        - `result`: 当前实体对应的推理结果。

        输出：
        - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
        """
        case.priority = self._priority_for_risk(result["riskLevel"])
        case.queue_name = self._queue_for_risk(result["riskLevel"])
        case.updated_at = utcnow_iso()

    def _refresh_case_state(
        self,
        case: RetentionCase,
        alert: OperationalAlert,
        result: dict[str, Any],
    ) -> None:
        """
        功能：
        - 刷新case状态。

        输入：
        - `case`: 单个运营 case 对象。
        - `alert`: 单个运行时告警对象或告警载荷。
        - `result`: 当前实体对应的推理结果。

        输出：
        - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
        """
        if result["riskLevel"] in {"HIGH", "MEDIUM"} and case.state == "MONITORING":
            self._transition_case(case, "OPEN", "risk-escalated")
            alert.state = "NEW"
        elif result["riskLevel"] == "LOW" and case.state == "OPEN":
            self._transition_case(case, "MONITORING", "risk-deescalated")
            alert.state = "MONITORING"
        case.updated_at = utcnow_iso()
        alert.updated_at = utcnow_iso()

    def _ensure_default_work_items(self, case: RetentionCase) -> None:
        """
        功能：
        - 确保defaultworkitems。

        输入：
        - `case`: 单个运营 case 对象。

        输出：
        - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
        """
        if case.risk_level not in {"HIGH", "MEDIUM"}:
            return
        if any(self.tasks[task_id].status == "TODO" for task_id in case.task_ids if task_id in self.tasks):
            return
        title = "高风险专席联系用户" if case.risk_level == "HIGH" else "常规维系联系用户"
        task = Task(
            id=f"task:{uuid4().hex}",
            case_id=case.id,
            entity_id=case.entity_id,
            action_id="start-retention-contact",
            title=title,
            status="TODO",
            assignee_role=self._owner_role_for_risk(case.risk_level),
            queue_name=self._queue_for_risk(case.risk_level),
            due_sla_hours=24 if case.risk_level == "HIGH" else 72,
        )
        self.tasks[task.id] = task
        case.task_ids.append(task.id)
        self._emit_event(
            event_type="task-created",
            title="默认维系任务已生成",
            subject_type="task",
            subject_id=task.id,
            entity_id=case.entity_id,
            case_id=case.id,
            payload={"actionId": task.action_id, "assigneeRole": task.assignee_role},
        )

    def _mark_stale_entities(self, active_entities: set[str]) -> None:
        """
        功能：
        - 标记staleentities。

        输入：
        - `active_entities`: 函数执行所需的 `active_entities` 参数。

        输出：
        - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
        """
        for runtime_case in self.cases.values():
            if runtime_case.entity_id in active_entities:
                continue
            if runtime_case.state != "CLOSED":
                self._transition_case(runtime_case, "CLOSED", "entity-removed-from-source")
            alert = self.alerts.get(runtime_case.alert_id)
            if alert is not None:
                alert.state = "CLOSED"
                alert.updated_at = utcnow_iso()

    def _resolve_case(self, *, case_id: str | None, entity_id: str | None) -> RetentionCase | None:
        """
        功能：
        - 解析并返回case。

        输入：
        - `case_id`: 运营 case 标识。
        - `entity_id`: 业务主实体标识。

        输出：
        - 返回值: 返回处理结果；当目标不存在、未命中或无法解析时返回 `None`。
        """
        if case_id:
            return self.cases.get(case_id)
        if entity_id:
            return self.cases.get(self._case_id(entity_id))
        return None

    def _apply_action(
        self,
        run: ActionRun,
        case: RetentionCase,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """
        功能：
        - 应用动作。

        输入：
        - `run`: 单个动作执行记录。
        - `case`: 单个运营 case 对象。
        - `parameters`: 字典参数 `parameters`，承载键值形式的输入数据。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        alert = self.alerts[case.alert_id]
        side_effect = self.action_definitions[run.action_id].side_effect

        if run.action_id == "acknowledge-alert":
            alert.state = "ACKED"
            self._transition_case(case, "ACKED", "action:acknowledge-alert")

        elif run.action_id == "assign-retention-owner":
            owner_role = str(parameters.get("ownerRole") or self._owner_role_for_risk(case.risk_level))
            case.owner_role = owner_role
            case.queue_name = self._queue_for_risk(case.risk_level)
            self._transition_case(case, "ASSIGNED", "action:assign-retention-owner")
            self._emit_event(
                event_type="case-assigned",
                title="维系负责人已分派",
                subject_type="case",
                subject_id=case.id,
                entity_id=case.entity_id,
                case_id=case.id,
                payload={"ownerRole": owner_role},
            )

        elif run.action_id == "start-retention-contact":
            alert.state = "IN_PROGRESS"
            self._transition_case(case, "CONTACTED", "action:start-retention-contact")
            self._complete_tasks(case.id, action_id="start-retention-contact", output={"contactStarted": True})

        elif run.action_id == "submit-retention-offer":
            alert.state = "IN_PROGRESS"
            self._transition_case(case, "OFFERED", "action:submit-retention-offer")
            follow_up = Task(
                id=f"task:{uuid4().hex}",
                case_id=case.id,
                entity_id=case.entity_id,
                action_id="mark-offer-accepted",
                title="回收客户确认结果",
                status="TODO",
                assignee_role=case.owner_role,
                queue_name=case.queue_name,
                due_sla_hours=24,
            )
            self.tasks[follow_up.id] = follow_up
            case.task_ids.append(follow_up.id)
            self._emit_event(
                event_type="offer-submitted",
                title="维系方案已提交",
                subject_type="case",
                subject_id=case.id,
                entity_id=case.entity_id,
                case_id=case.id,
                payload={"offerName": parameters.get("offerName") or "default-offer"},
            )

        elif run.action_id == "mark-offer-accepted":
            alert.state = "RESOLVED"
            self._transition_case(case, "WON", "action:mark-offer-accepted")
            self._complete_tasks(case.id, output={"result": "accepted"})

        elif run.action_id == "mark-customer-lost":
            alert.state = "CLOSED"
            self._transition_case(case, "LOST", "action:mark-customer-lost")
            self._complete_tasks(case.id, output={"result": "lost"})

        elif run.action_id == "resolve-monitoring-case":
            alert.state = "RESOLVED"
            self._transition_case(case, "RESOLVED", "action:resolve-monitoring-case")

        elif run.action_id == "close-case":
            alert.state = "CLOSED"
            self._transition_case(case, "CLOSED", "action:close-case")
            self._cancel_open_tasks(case.id)

        case.updated_at = utcnow_iso()
        alert.updated_at = utcnow_iso()
        self._emit_event(
            event_type="action-executed",
            title=f"动作已执行: {self.action_definitions[run.action_id].label}",
            subject_type="action-run",
            subject_id=run.id,
            entity_id=case.entity_id,
            case_id=case.id,
            payload={
                "actionId": run.action_id,
                "actorRole": run.actor_role,
                "sideEffect": side_effect,
                **parameters,
            },
        )
        return {
            "sideEffect": side_effect,
            "caseState": case.state,
            "alertState": alert.state,
        }

    def _transition_case(self, case: RetentionCase, to_state: str, reason: str) -> None:
        """
        功能：
        - 处理与 `_transition_case` 相关的逻辑。

        输入：
        - `case`: 单个运营 case 对象。
        - `to_state`: 函数执行所需的 `to_state` 参数。
        - `reason`: 函数执行所需的 `reason` 参数。

        输出：
        - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
        """
        if case.state == to_state:
            return
        event = self._emit_event(
            event_type="state-transition",
            title=f"Case 状态变更为 {to_state}",
            subject_type="case",
            subject_id=case.id,
            entity_id=case.entity_id,
            case_id=case.id,
            payload={"from": case.state, "to": to_state, "reason": reason},
        )
        transition = StateTransition(
            id=f"transition:{uuid4().hex}",
            subject_type="case",
            subject_id=case.id,
            from_state=case.state,
            to_state=to_state,
            reason=reason,
            event_id=event.id,
            case_id=case.id,
            entity_id=case.entity_id,
        )
        self.transitions[transition.id] = transition
        case.transition_ids.append(transition.id)
        case.state = to_state
        case.updated_at = utcnow_iso()

    def _emit_event(
        self,
        *,
        event_type: str,
        title: str,
        subject_type: str,
        subject_id: str,
        entity_id: str,
        case_id: str,
        payload: dict[str, Any],
    ) -> DomainEvent:
        """
        功能：
        - 处理与 `_emit_event` 相关的逻辑。

        输入：
        - `event_type`: 函数执行所需的 `event_type` 参数。
        - `title`: 函数执行所需的 `title` 参数。
        - `subject_type`: 函数执行所需的 `subject_type` 参数。
        - `subject_id`: 函数执行所需的 `subject_id` 参数。
        - `entity_id`: 业务主实体标识。
        - `case_id`: 运营 case 标识。
        - `payload`: 请求体或内部处理中使用的载荷数据。

        输出：
        - 返回值: 返回 `DomainEvent` 类型结果，供后续流程继续消费。
        """
        event = DomainEvent(
            id=f"event:{uuid4().hex}",
            event_type=event_type,
            title=title,
            subject_type=subject_type,
            subject_id=subject_id,
            entity_id=entity_id,
            case_id=case_id,
            payload=dict(payload),
        )
        self.events[event.id] = event
        runtime_case = self.cases.get(case_id)
        if runtime_case is not None:
            runtime_case.event_ids.append(event.id)
            runtime_case.updated_at = utcnow_iso()
        return event

    def _complete_tasks(
        self,
        case_id: str,
        *,
        action_id: str | None = None,
        output: dict[str, Any] | None = None,
    ) -> None:
        """
        功能：
        - 完成任务列表。

        输入：
        - `case_id`: 运营 case 标识。
        - `action_id`: 待执行动作的标识。
        - `output`: 字典参数 `output`，承载键值形式的输入数据。

        输出：
        - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
        """
        for task in self.tasks.values():
            if task.case_id != case_id or task.status != "TODO":
                continue
            if action_id and task.action_id != action_id:
                continue
            task.status = "DONE"
            task.updated_at = utcnow_iso()
            task.completed_at = task.updated_at
            task.output = dict(output or {})

    def _cancel_open_tasks(self, case_id: str) -> None:
        """
        功能：
        - 取消open任务列表。

        输入：
        - `case_id`: 运营 case 标识。

        输出：
        - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
        """
        for task in self.tasks.values():
            if task.case_id != case_id or task.status != "TODO":
                continue
            task.status = "CANCELED"
            task.updated_at = utcnow_iso()
            task.completed_at = task.updated_at

    def _case_payload(self, case: RetentionCase) -> dict[str, Any]:
        """
        功能：
        - 处理与 `_case_payload` 相关的逻辑。

        输入：
        - `case`: 单个运营 case 对象。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        alert = self.alerts.get(case.alert_id)
        return {
            **serialize_dataclass(case),
            "entityId": case.entity_id,
            "caseId": case.id,
            "alertState": alert.state if alert else "",
            "availableActions": self.available_actions(case.entity_id),
            "openTaskCount": sum(
                1 for task_id in case.task_ids if task_id in self.tasks and self.tasks[task_id].status == "TODO"
            ),
        }

    def _priority_for_risk(self, risk_level: str) -> str:
        """
        功能：
        - 处理与 `_priority_for_risk` 相关的逻辑。

        输入：
        - `risk_level`: 待映射或判断的风险等级。

        输出：
        - 返回值: 返回字符串结果，供调用方继续展示、拼接或查询。
        """
        return {"HIGH": "P1", "MEDIUM": "P2", "LOW": "P3"}.get(risk_level, "P3")

    def _queue_for_risk(self, risk_level: str) -> str:
        """
        功能：
        - 处理与 `_queue_for_risk` 相关的逻辑。

        输入：
        - `risk_level`: 待映射或判断的风险等级。

        输出：
        - 返回值: 返回字符串结果，供调用方继续展示、拼接或查询。
        """
        return {
            "HIGH": "retention-high-priority",
            "MEDIUM": "retention-standard",
            "LOW": "retention-monitoring",
        }.get(risk_level, "retention-monitoring")

    def _owner_role_for_risk(self, risk_level: str) -> str:
        """
        功能：
        - 处理与 `_owner_role_for_risk` 相关的逻辑。

        输入：
        - `risk_level`: 待映射或判断的风险等级。

        输出：
        - 返回值: 返回字符串结果，供调用方继续展示、拼接或查询。
        """
        return "senior_agent" if risk_level == "HIGH" else "agent"

    def _runtime_uri(self, settings: Settings, segment: str, identifier: str) -> URIRef:
        """
        功能：
        - 处理与 `_runtime_uri` 相关的逻辑。

        输入：
        - `settings`: 运行时配置对象，提供目录路径、命名空间和环境参数。
        - `segment`: URI 或资源分类片段。
        - `identifier`: 用于构造稳定标识的原始值。

        输出：
        - 返回值: 返回 RDF 资源 URI。
        """
        return URIRef(f"{settings.data_ns}runtime/{segment}/{quote(identifier, safe='')}")

    def _alert_id(self, entity_id: str) -> str:
        """
        功能：
        - 处理与 `_alert_id` 相关的逻辑。

        输入：
        - `entity_id`: 业务主实体标识。

        输出：
        - 返回值: 返回字符串结果，供调用方继续展示、拼接或查询。
        """
        return f"alert:{entity_id}"

    def _case_id(self, entity_id: str) -> str:
        """
        功能：
        - 处理与 `_case_id` 相关的逻辑。

        输入：
        - `entity_id`: 业务主实体标识。

        输出：
        - 返回值: 返回字符串结果，供调用方继续展示、拼接或查询。
        """
        return f"case:{entity_id}"

    def _count_by(self, items: Any, field_name: str) -> dict[str, int]:
        """
        功能：
        - 统计by。

        输入：
        - `items`: 需要统计或遍历的对象集合。
        - `field_name`: 需要读取或统计的字段名称。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        counts: dict[str, int] = {}
        for item in items:
            value = str(getattr(item, field_name, "") or "UNKNOWN")
            counts[value] = counts.get(value, 0) + 1
        return counts

    def _load_state_once(self) -> None:
        """
        功能：
        - 加载状态once。

        输入：
        - 无。

        输出：
        - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
        """
        if self._loaded:
            return
        self._loaded = True
        if not self.settings.runtime_persistence_enabled:
            return
        path = self.settings.runtime_state_path
        if not path.exists():
            return
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.alerts = {
            item["id"]: OperationalAlert(**item)
            for item in payload.get("alerts", [])
        }
        self.cases = {
            item["id"]: RetentionCase(**item)
            for item in payload.get("cases", [])
        }
        self.tasks = {
            item["id"]: Task(**item)
            for item in payload.get("tasks", [])
        }
        self.action_runs = {
            item["id"]: ActionRun(**item)
            for item in payload.get("action_runs", [])
        }
        self.events = {
            item["id"]: DomainEvent(**item)
            for item in payload.get("events", [])
        }
        self.transitions = {
            item["id"]: StateTransition(**item)
            for item in payload.get("transitions", [])
        }

    def _save_state(self) -> None:
        """
        功能：
        - 保存状态。

        输入：
        - 无。

        输出：
        - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
        """
        if not self.settings.runtime_persistence_enabled:
            return
        path: Path = self.settings.runtime_state_path
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "alerts": [serialize_dataclass(item) for item in self.alerts.values()],
            "cases": [serialize_dataclass(item) for item in self.cases.values()],
            "tasks": [serialize_dataclass(item) for item in self.tasks.values()],
            "action_runs": [serialize_dataclass(item) for item in self.action_runs.values()],
            "events": [serialize_dataclass(item) for item in self.events.values()],
            "transitions": [serialize_dataclass(item) for item in self.transitions.values()],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
