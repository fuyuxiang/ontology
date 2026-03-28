"""
模块功能：
- 构建面向本体工作台的资源化模型。
- 该文件位于 `backend/app/services/ontology_workspace.py`，负责把场景配置、运行时动作与对象目录组织成 object types、link types、action types、interfaces、rules 等资源集合。
"""

from __future__ import annotations

from typing import Any

from app.scenario.config import DatasetConfig, RelationConfig, RuleCardConfig, ScenarioConfig


def build_ontology_workspace(
    *,
    scenario: ScenarioConfig,
    source_rows: dict[str, list[dict[str, Any]]],
    object_model: list[dict[str, Any]],
    action_catalog: list[dict[str, Any]],
    top_rules: list[dict[str, Any]],
    governance_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    功能：
    - 构建供前端本体工作台消费的资源化本体模型。

    输入：
    - `scenario`: 当前场景配置。
    - `source_rows`: 已加载的数据集原始行。
    - `object_model`: 稳定对象目录。
    - `action_catalog`: 运行时动作目录。
    - `top_rules`: 规则命中统计。

    输出：
    - 返回值: 返回字典结构，包含 object types、link types、action types、interfaces、rules 等资源。
    """
    dataset_object_types = _build_dataset_object_types(scenario, source_rows)
    operational_object_types = _build_operational_object_types(
        object_model,
        action_catalog,
        existing_keys={item["key"] for item in dataset_object_types},
    )
    object_types = dataset_object_types + operational_object_types
    shared_properties = _build_shared_properties(object_types)
    object_type_groups = _build_object_type_groups(object_types)
    _attach_shared_properties_and_groups(object_types, shared_properties, object_type_groups)
    interfaces = _build_interfaces(object_types)
    _attach_interfaces(object_types, interfaces)
    link_types = _build_link_types(scenario, dataset_object_types, operational_object_types)
    action_types = _build_action_types(action_catalog)
    rules = _build_rules(scenario.rule_cards, top_rules, action_types)
    _attach_links_and_actions(object_types, link_types, action_types, rules)
    _attach_shared_properties_to_interfaces(interfaces, shared_properties)
    governance = governance_state or {}
    _apply_governance_overrides(
        governance.get("overrides", {}),
        object_types=object_types,
        shared_properties=shared_properties,
        object_type_groups=object_type_groups,
        link_types=link_types,
        action_types=action_types,
        interfaces=interfaces,
        rules=rules,
    )

    return {
        "scenario": {
            "key": scenario.key,
            "name": scenario.name,
            "title": scenario.app_title,
            "subtitle": "以对象类型、链接类型、接口契约和动作类型组织统一语义层。",
        },
        "philosophy": [
            {
                "title": "对象优先",
                "description": "先定义稳定对象类型，再让数据、规则、动作和应用围绕对象复用。",
            },
            {
                "title": "链接显式化",
                "description": "把关系建模为可治理的 link types，而不是散落在代码里的隐式 join。",
            },
            {
                "title": "接口即契约",
                "description": "用 interfaces 抽象跨对象共性，让多个对象类型共享能力边界和展示方式。",
            },
            {
                "title": "动作附着在本体上",
                "description": "action types 不是按钮集合，而是受角色、状态和风险约束的语义化变更。",
            },
            {
                "title": "规则进入运营闭环",
                "description": "规则不只输出分数，还要把信号转成告警、Case、任务和动作建议。",
            },
        ],
        "metrics": {
            "objectTypeCount": len(object_types),
            "sharedPropertyCount": len(shared_properties),
            "objectTypeGroupCount": len(object_type_groups),
            "linkTypeCount": len(link_types),
            "actionTypeCount": len(action_types),
            "interfaceCount": len(interfaces),
            "ruleCount": len(rules),
        },
        "capabilities": [
            {
                "name": "Ontology Manager",
                "summary": "统一查看对象、链接、动作、接口和规则，不再只停留在流程化演示页面。",
            },
            {
                "name": "Operational Semantics",
                "summary": "风险推理、工作流状态和动作执行共享同一套本体资源，而不是分离在多套模型里。",
            },
            {
                "name": "Governed Actions",
                "summary": "动作类型带角色、状态、风险范围等治理约束，可直接呈现为可执行能力。",
            },
            {
                "name": "Reusable Contracts",
                "summary": "接口把跨对象的风险感知、工作流、动作承载能力显式抽象出来。",
            },
        ],
        "objectTypes": object_types,
        "sharedProperties": shared_properties,
        "objectTypeGroups": object_type_groups,
        "linkTypes": link_types,
        "actionTypes": action_types,
        "interfaces": interfaces,
        "rules": rules,
        "governance": {
            "draftId": governance.get("draftId"),
            "status": governance.get("status", "clean"),
            "lastPublishedAt": governance.get("lastPublishedAt"),
            "changeCount": len(governance.get("changes", [])),
            "changes": list(governance.get("changes", [])),
        },
    }


def _build_dataset_object_types(
    scenario: ScenarioConfig,
    source_rows: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    object_types: list[dict[str, Any]] = []

    for dataset_key, dataset in scenario.datasets.items():
        object_key = _dataset_object_key(dataset_key, dataset, scenario)
        rows = source_rows.get(dataset_key, [])
        sample = rows[0] if rows else {}
        sample_fields = [key for key in sample.keys() if not key.startswith("_")]
        ordered_fields = list(dict.fromkeys([*dataset.id_fields, *sample_fields]))
        properties = [
            {
                "name": field,
                "label": field,
                "required": field in dataset.id_fields,
                "typeClasses": _infer_property_type_classes(
                    field=field,
                    dataset=dataset,
                    scenario=scenario,
                ),
            }
            for field in ordered_fields[:16]
        ]

        object_types.append(
            {
                "id": f"object-type:{object_key}",
                "key": object_key,
                "name": dataset.entity_label,
                "category": "domain",
                "sourceSystem": dataset.source_system,
                "datasetKey": dataset_key,
                "ontologyType": dataset.node_type,
                "description": _dataset_description(dataset_key, dataset, scenario),
                "identityFields": list(dataset.id_fields),
                "titleField": dataset.label_field or dataset.id_fields[0],
                "properties": properties,
                "capabilityTags": _dataset_capabilities(dataset_key, dataset, scenario),
                "implements": [],
                "sharedPropertyIds": [],
                "groupIds": [],
                "incomingLinkTypeIds": [],
                "outgoingLinkTypeIds": [],
                "actionTypeIds": [],
            }
        )

    return object_types


def _build_operational_object_types(
    object_model: list[dict[str, Any]],
    action_catalog: list[dict[str, Any]],
    existing_keys: set[str],
) -> list[dict[str, Any]]:
    object_types: list[dict[str, Any]] = []
    action_type_ids = [f"action-type:{item['id']}" for item in action_catalog]

    for item in object_model:
        if item["key"] in existing_keys:
            continue
        properties = [
            {
                "name": field,
                "label": field,
                "required": field == item["identityField"],
                "typeClasses": _infer_operational_property_classes(field),
            }
            for field in [item["identityField"], *item.get("attributes", [])]
        ]
        unique_properties = list({prop["name"]: prop for prop in properties}.values())
        object_types.append(
            {
                "id": f"object-type:{item['key']}",
                "key": item["key"],
                "name": item["label"],
                "category": "operational",
                "sourceSystem": _operational_source(item["key"]),
                "datasetKey": None,
                "ontologyType": item["ontologyType"],
                "description": item["description"],
                "identityFields": [item["identityField"]],
                "titleField": item["identityField"],
                "properties": unique_properties,
                "capabilityTags": _operational_capabilities(item["key"]),
                "implements": [],
                "sharedPropertyIds": [],
                "groupIds": [],
                "incomingLinkTypeIds": [],
                "outgoingLinkTypeIds": [],
                "actionTypeIds": action_type_ids if item["key"] in {"RetentionCase", "Task", "RiskAlert"} else [],
            }
        )

    return object_types


def _build_interfaces(object_types: list[dict[str, Any]]) -> list[dict[str, Any]]:
    object_ids = {item["id"] for item in object_types}

    def members(keys: set[str]) -> list[str]:
        return sorted(item["id"] for item in object_types if item["key"] in keys and item["id"] in object_ids)

    return [
        {
            "id": "interface:core-entity",
            "name": "CoreEntity",
            "description": "所有对象类型共享的基础契约，要求具备稳定身份、标题字段和可链接语义。",
            "purpose": "统一对象寻址、展示标题和跨应用引用方式。",
            "requiredProperties": ["identifier", "title"],
            "sharedPropertyIds": [],
            "capabilities": ["searchable", "referencable", "governed"],
            "implementedBy": sorted(object_ids),
        },
        {
            "id": "interface:risk-signal",
            "name": "RiskSignalCarrier",
            "description": "承载风险识别输入或输出的对象契约。",
            "purpose": "把用户、交互、规则和告警纳入同一套风险语义链条。",
            "requiredProperties": ["identifier", "risk-signal"],
            "sharedPropertyIds": [],
            "capabilities": ["rule-input", "explainable", "traceable"],
            "implementedBy": members(
                {
                    "User",
                    "PortingQuery",
                    "VoiceUsage",
                    "CustomerService",
                    "RetentionAction",
                    "RiskAlert",
                    "RuleHit",
                    "InteractionEvent",
                }
            ),
        },
        {
            "id": "interface:workflow-subject",
            "name": "WorkflowSubject",
            "description": "具备生命周期、责任归属和状态迁移的运营对象契约。",
            "purpose": "确保告警、Case 与任务在工作台中具备一致的流程语义。",
            "requiredProperties": ["identifier", "status"],
            "sharedPropertyIds": [],
            "capabilities": ["stateful", "assignable", "auditable"],
            "implementedBy": members({"RiskAlert", "RetentionCase", "Task"}),
        },
        {
            "id": "interface:action-surface",
            "name": "ActionSurface",
            "description": "可承载动作类型、展示执行约束并被运营应用直接消费的对象契约。",
            "purpose": "把本体从只读模型提升为可操作的业务表面。",
            "requiredProperties": ["identifier", "action-binding"],
            "sharedPropertyIds": [],
            "capabilities": ["actionable", "policy-checked", "runtime-bound"],
            "implementedBy": members({"RiskAlert", "RetentionCase", "Task", "ActionDefinition"}),
        },
    ]


def _build_shared_properties(object_types: list[dict[str, Any]]) -> list[dict[str, Any]]:
    registry: dict[str, dict[str, Any]] = {}
    name_aliases = {
        "identifier": {"entityId", "caseId", "id", "objectId", "user_id"},
        "title": {"displayName", "device_number"},
        "status": {"state", "status", "alertState", "caseState"},
        "risk-signal": {"riskLevel", "risk_level"},
        "time": {"created_at", "updated_at", "completed_at", "start_date", "query_time"},
        "ownership": {"areaId", "area_id", "owner_role", "assignee_role", "actor_role"},
        "action-binding": {"action_id", "recommendedAction", "availableActions"},
    }

    for object_type in object_types:
        for prop in object_type["properties"]:
            canonical = _shared_property_name(prop["name"], prop["typeClasses"], name_aliases)
            if not canonical:
                continue
            entry = registry.setdefault(
                canonical,
                {
                    "id": f"shared-property:{canonical}",
                    "name": canonical,
                    "description": _shared_property_description(canonical),
                    "typeClasses": [canonical],
                    "implementedBy": [],
                    "fields": [],
                },
            )
            entry["implementedBy"].append(object_type["id"])
            entry["fields"].append(
                {
                    "objectTypeId": object_type["id"],
                    "propertyName": prop["name"],
                    "label": prop["label"],
                    "required": prop["required"],
                }
            )
            entry["typeClasses"] = sorted(set(entry["typeClasses"] + list(prop["typeClasses"])))

    return sorted(registry.values(), key=lambda item: (len(item["implementedBy"]) * -1, item["name"]))


def _build_object_type_groups(object_types: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups = [
        {
            "id": "object-group:customer-360",
            "name": "Customer 360",
            "description": "围绕主客户对象组织基础身份、商业上下文和关系锚点。",
            "objectTypeIds": [
                item["id"]
                for item in object_types
                if item["key"] in {"User", "ContractInfo", "OmDatum", "ChargeInfo", "ArrearInfo"}
            ],
            "interfaceIds": ["interface:core-entity"],
            "capabilities": ["anchor-model", "customer-context"],
        },
        {
            "id": "object-group:signal-network",
            "name": "Signal Network",
            "description": "承载交互、行为与规则信号的对象群组。",
            "objectTypeIds": [
                item["id"]
                for item in object_types
                if item["key"] in {"PortingQuery", "VoiceUsage", "CustomerService", "RetentionAction", "InteractionEvent", "RuleHit", "RiskAlert"}
            ],
            "interfaceIds": ["interface:risk-signal"],
            "capabilities": ["signal-source", "explainable"],
        },
        {
            "id": "object-group:operations-loop",
            "name": "Operations Loop",
            "description": "将告警、Case、任务和动作组织成可执行运营闭环。",
            "objectTypeIds": [
                item["id"]
                for item in object_types
                if item["key"] in {"RiskAlert", "RetentionCase", "Task", "ActionDefinition"}
            ],
            "interfaceIds": ["interface:workflow-subject", "interface:action-surface"],
            "capabilities": ["workflow", "actionable", "auditable"],
        },
    ]
    return [item for item in groups if item["objectTypeIds"]]


def _attach_shared_properties_and_groups(
    object_types: list[dict[str, Any]],
    shared_properties: list[dict[str, Any]],
    object_type_groups: list[dict[str, Any]],
) -> None:
    object_index = {item["id"]: item for item in object_types}
    for shared_property in shared_properties:
        for object_id in shared_property["implementedBy"]:
            object_index[object_id]["sharedPropertyIds"].append(shared_property["id"])

    for group in object_type_groups:
        for object_id in group["objectTypeIds"]:
            if object_id in object_index:
                object_index[object_id]["groupIds"].append(group["id"])


def _attach_interfaces(object_types: list[dict[str, Any]], interfaces: list[dict[str, Any]]) -> None:
    memberships: dict[str, list[str]] = {item["id"]: [] for item in object_types}
    for interface in interfaces:
        for object_id in interface["implementedBy"]:
            memberships.setdefault(object_id, []).append(interface["id"])
    for item in object_types:
        item["implements"] = memberships.get(item["id"], [])


def _attach_shared_properties_to_interfaces(
    interfaces: list[dict[str, Any]],
    shared_properties: list[dict[str, Any]],
) -> None:
    shared_index = {item["name"]: item["id"] for item in shared_properties}
    for interface in interfaces:
        interface["sharedPropertyIds"] = [
            shared_index[name]
            for name in interface["requiredProperties"]
            if name in shared_index
        ]


def _apply_governance_overrides(
    overrides: dict[str, dict[str, dict[str, Any]]],
    *,
    object_types: list[dict[str, Any]],
    shared_properties: list[dict[str, Any]],
    object_type_groups: list[dict[str, Any]],
    link_types: list[dict[str, Any]],
    action_types: list[dict[str, Any]],
    interfaces: list[dict[str, Any]],
    rules: list[dict[str, Any]],
) -> None:
    collections = {
        "objectTypes": object_types,
        "sharedProperties": shared_properties,
        "objectTypeGroups": object_type_groups,
        "linkTypes": link_types,
        "actionTypes": action_types,
        "interfaces": interfaces,
        "rules": rules,
    }
    for resource_type, by_id in overrides.items():
        items = collections.get(resource_type)
        if not items:
            continue
        index = {item["id"]: item for item in items}
        for resource_id, patch in by_id.items():
            target = index.get(resource_id)
            if target is None:
                continue
            for field, value in patch.items():
                if field in target:
                    target[field] = value


def _build_link_types(
    scenario: ScenarioConfig,
    dataset_object_types: list[dict[str, Any]],
    operational_object_types: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    object_id_by_dataset = {
        item["datasetKey"]: item["id"]
        for item in dataset_object_types
        if item["datasetKey"]
    }
    object_id_by_key = {item["key"]: item["id"] for item in [*dataset_object_types, *operational_object_types]}

    link_types = [
        _relation_link_payload(relation, object_id_by_dataset)
        for relation in scenario.relations
        if relation.source_dataset in object_id_by_dataset and relation.target_dataset in object_id_by_dataset
    ]

    derived_links = [
        {
            "id": "link-type:rule-hit-supports-alert",
            "name": "支撑风险告警",
            "description": "规则命中对象会被汇聚为风险告警对象，形成面向运营的统一风险表面。",
            "sourceObjectTypeId": object_id_by_key.get("RuleHit"),
            "targetObjectTypeId": object_id_by_key.get("RiskAlert"),
            "predicate": "supportsAlert",
            "cardinality": "many-to-one",
            "typeClasses": ["derived-link", "risk-link"],
        },
        {
            "id": "link-type:alert-opens-case",
            "name": "转化为运营 Case",
            "description": "风险告警进入处置流程后转化为运营 Case。",
            "sourceObjectTypeId": object_id_by_key.get("RiskAlert"),
            "targetObjectTypeId": object_id_by_key.get("RetentionCase"),
            "predicate": "opensCase",
            "cardinality": "one-to-one",
            "typeClasses": ["derived-link", "workflow-link"],
        },
        {
            "id": "link-type:case-spawns-task",
            "name": "拆解为任务",
            "description": "运营 Case 会进一步拆解为可执行任务。",
            "sourceObjectTypeId": object_id_by_key.get("RetentionCase"),
            "targetObjectTypeId": object_id_by_key.get("Task"),
            "predicate": "spawnsTask",
            "cardinality": "one-to-many",
            "typeClasses": ["derived-link", "workflow-link"],
        },
        {
            "id": "link-type:case-binds-action",
            "name": "绑定动作类型",
            "description": "Case 和任务通过动作类型暴露可执行变更能力。",
            "sourceObjectTypeId": object_id_by_key.get("RetentionCase"),
            "targetObjectTypeId": object_id_by_key.get("ActionDefinition"),
            "predicate": "bindsActionType",
            "cardinality": "many-to-many",
            "typeClasses": ["derived-link", "action-link"],
        },
    ]

    return [
        item
        for item in [*link_types, *derived_links]
        if item["sourceObjectTypeId"] and item["targetObjectTypeId"]
    ]


def _build_action_types(action_catalog: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": f"action-type:{item['id']}",
            "name": item["label"],
            "description": item["description"],
            "queueHint": item["queue_hint"],
            "sideEffect": item["side_effect"],
            "allowedRoles": list(item["allowed_roles"]),
            "allowedStates": list(item["allowed_states"]),
            "allowedRiskLevels": list(item["allowed_risk_levels"]),
            "implements": ["interface:action-surface"],
            "boundObjectTypeIds": [
                "object-type:RiskAlert",
                "object-type:RetentionCase",
                "object-type:Task",
            ],
        }
        for item in action_catalog
    ]


def _build_rules(
    rule_cards: tuple[RuleCardConfig, ...],
    top_rules: list[dict[str, Any]],
    action_types: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    action_ids = [item["id"] for item in action_types[:3]]
    top_rule_counts = {item["rule"]: int(item["count"]) for item in top_rules}

    return [
        {
            "id": f"rule:{card.label}",
            "name": card.label,
            "description": card.desc,
            "riskLevel": _tone_to_risk_level(card.tone),
            "signalProperties": _signal_properties_for_tone(card.tone),
            "targetObjectTypeIds": ["object-type:RiskAlert", "object-type:RetentionCase"],
            "actionTypeIds": action_ids,
            "hitCount": top_rule_counts.get(card.label, 0),
        }
        for card in rule_cards
    ]


def _attach_links_and_actions(
    object_types: list[dict[str, Any]],
    link_types: list[dict[str, Any]],
    action_types: list[dict[str, Any]],
    rules: list[dict[str, Any]],
) -> None:
    index = {item["id"]: item for item in object_types}
    for link in link_types:
        index[link["sourceObjectTypeId"]]["outgoingLinkTypeIds"].append(link["id"])
        index[link["targetObjectTypeId"]]["incomingLinkTypeIds"].append(link["id"])

    action_ids = [item["id"] for item in action_types]
    for key in ("object-type:RiskAlert", "object-type:RetentionCase", "object-type:Task"):
        if key in index:
            index[key]["actionTypeIds"] = action_ids

    rule_related = {target_id for item in rules for target_id in item["targetObjectTypeIds"]}
    for object_id in rule_related:
        if object_id in index:
            index[object_id]["capabilityTags"] = sorted(set(index[object_id]["capabilityTags"] + ["rule-target"]))


def _relation_link_payload(
    relation: RelationConfig,
    object_id_by_dataset: dict[str, str],
) -> dict[str, Any]:
    return {
        "id": f"link-type:{relation.source_dataset}:{relation.target_dataset}:{relation.label}",
        "name": relation.label,
        "description": f"{relation.source_dataset} 通过 {relation.label} 连接到 {relation.target_dataset}，关系谓词为 {relation.predicate}。",
        "sourceObjectTypeId": object_id_by_dataset[relation.source_dataset],
        "targetObjectTypeId": object_id_by_dataset[relation.target_dataset],
        "predicate": relation.predicate,
        "cardinality": _guess_cardinality(relation),
        "typeClasses": ["link-type", "semantic-link"],
    }


def _dataset_object_key(dataset_key: str, dataset: DatasetConfig, scenario: ScenarioConfig) -> str:
    if dataset_key == scenario.primary_dataset:
        return scenario.primary_node_type
    return "".join(part.capitalize() for part in dataset_key.split("_"))


def _dataset_description(dataset_key: str, dataset: DatasetConfig, scenario: ScenarioConfig) -> str:
    if dataset_key == scenario.primary_dataset:
        return f"主业务对象类型，承载 {scenario.primary_entity_label} 的身份、标签和跨域关联锚点。"
    if dataset_key in scenario.interaction_datasets:
        return f"来自 {dataset.source_system} 的交互/行为对象类型，为风险规则提供时序信号。"
    return f"来自 {dataset.source_system} 的领域对象类型，用于补充 {scenario.primary_entity_label} 的业务上下文。"


def _dataset_capabilities(dataset_key: str, dataset: DatasetConfig, scenario: ScenarioConfig) -> list[str]:
    capabilities = ["typed-object", "referencable"]
    if dataset_key == scenario.primary_dataset:
        capabilities.extend(["anchor-object", "searchable", "action-surface"])
    if dataset_key in scenario.interaction_datasets:
        capabilities.extend(["signal-source", "timeline-ready"])
    if dataset.label_field:
        capabilities.append("display-labeled")
    if dataset.join_keys:
        capabilities.append("linkable")
    return sorted(set(capabilities))


def _infer_property_type_classes(
    *,
    field: str,
    dataset: DatasetConfig,
    scenario: ScenarioConfig,
) -> list[str]:
    field_lower = field.lower()
    classes: list[str] = []
    if field in dataset.id_fields:
        classes.append("identifier")
    if field == dataset.label_field:
        classes.append("title")
    if field in dataset.join_keys:
        classes.append("join-key")
    if field in scenario.search_fields:
        classes.append("search-index")
    if "time" in field_lower or "date" in field_lower:
        classes.append("timestamp")
    if "risk" in field_lower:
        classes.append("risk-signal")
    if "state" in field_lower or "status" in field_lower:
        classes.append("status")
    if "amount" in field_lower or "fee" in field_lower or "charge" in field_lower:
        classes.append("metric")
    return classes or ["attribute"]


def _infer_operational_property_classes(field: str) -> list[str]:
    field_lower = field.lower()
    classes: list[str] = []
    if field_lower in {"id", "case_id", "entity_id", "objectid"}:
        classes.append("identifier")
    if "risk" in field_lower:
        classes.append("risk-signal")
    if "state" in field_lower or "status" in field_lower:
        classes.append("status")
    if "role" in field_lower or "owner" in field_lower:
        classes.append("governance")
    if "time" in field_lower or "at" in field_lower:
        classes.append("timestamp")
    return classes or ["attribute"]


def _operational_source(object_key: str) -> str:
    if object_key in {"RiskAlert", "RuleHit"}:
        return "Inference"
    if object_key in {"RetentionCase", "Task", "ActionDefinition"}:
        return "Runtime"
    return "Application"


def _operational_capabilities(object_key: str) -> list[str]:
    mapping = {
        "User": ["anchor-object", "searchable", "risk-evaluable"],
        "RiskAlert": ["workflow-entry", "risk-output", "action-surface"],
        "RetentionCase": ["workflow-subject", "action-surface", "auditable"],
        "Task": ["workflow-subject", "assignable", "auditable"],
        "InteractionEvent": ["signal-source", "timeline-ready", "queryable"],
        "RuleHit": ["derived-object", "explainable", "risk-output"],
        "ActionDefinition": ["governed-action", "policy-bound", "runtime-bound"],
    }
    return mapping.get(object_key, ["typed-object"])


def _guess_cardinality(relation: RelationConfig) -> str:
    if relation.source_dataset == relation.target_dataset:
        return "many-to-many"
    if relation.source_dataset == "user_info":
        return "one-to-many"
    return "many-to-one"


def _tone_to_risk_level(tone: str) -> str:
    if tone == "high":
        return "HIGH"
    if tone == "medium":
        return "MEDIUM"
    return "LOW"


def _signal_properties_for_tone(tone: str) -> list[str]:
    if tone == "high":
        return ["近7天是否查询携转资格", "近30天投诉次数", "近7天竞对通话次数", "最近维系是否成功"]
    if tone == "medium":
        return ["近30天是否查询携转资格", "近30天投诉次数", "近30天竞对通话次数", "是否存在有效合约"]
    return ["近60天投诉次数", "是否存在欠费", "是否存在融合绑定", "最近查询距今天数"]


def _shared_property_name(
    property_name: str,
    type_classes: list[str],
    aliases: dict[str, set[str]],
) -> str | None:
    for shared_name, candidates in aliases.items():
        if property_name in candidates:
            return shared_name
    if "identifier" in type_classes:
        return "identifier"
    if "title" in type_classes:
        return "title"
    if "status" in type_classes:
        return "status"
    if "risk-signal" in type_classes:
        return "risk-signal"
    if "timestamp" in type_classes:
        return "time"
    return None


def _shared_property_description(shared_name: str) -> str:
    descriptions = {
        "identifier": "跨对象共享的稳定标识属性，用于引用、去重和跨应用寻址。",
        "title": "跨对象共享的展示标题属性，用于列表、详情页和对象引用渲染。",
        "status": "跨对象共享的生命周期或状态属性，用于工作流治理和过滤。",
        "risk-signal": "跨对象共享的风险语义属性，用于规则评估、解释和优先级判断。",
        "time": "跨对象共享的时间属性，用于时间线、窗口计算和时序分析。",
        "ownership": "跨对象共享的归属/责任属性，用于队列治理和组织协同。",
        "action-binding": "跨对象共享的动作绑定属性，用于把对象和可执行动作语义联结起来。",
    }
    return descriptions.get(shared_name, "多个对象类型共享的语义属性。")
