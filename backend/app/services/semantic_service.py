"""
模块功能：
- 语义服务核心实现，负责数据装载、图谱构建、推理与查询。
- 该文件位于 `backend/app/services/semantic_service.py`，负责数据装载、图谱构建、推理、查询和运营工作台聚合，是后端语义层总入口。
- 文件中定义的核心类包括：`SemanticService`。
"""

from __future__ import annotations

import json
import threading
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from rdflib import BNode, Dataset, Graph, RDF, URIRef

from app.agent_tools import agent_tool_catalog
from app.config.settings import Settings
from app.etl.csv_loader import read_csv_rows
from app.graph.repository import GraphRepository
from app.object_catalog import build_object_model
from app.ontology.namespaces import bind_prefixes, make_namespaces
from app.rules.engine import materialize_business_inference
from app.runtime import ActorContext, RuntimeEngine
from app.scenario.config import (
    AlertDisplayField,
    ScenarioConfig,
    load_scenario_config,
)
from app.scenario.mapping import MappingRow, load_mapping_rows
from app.services.data_pipeline import (
    FactEvaluator,
    build_dataset_indexes,
    build_records,
    load_source_rows,
)
from app.services.graph_materializer import materialize_base_graph
from app.services.graph_views import build_entity_graph, build_overview_graph
from app.validation.shacl import run_shacl_validation

try:
    from owlrl import DeductiveClosure, OWLRL_Semantics
except ImportError:  # pragma: no cover
    DeductiveClosure = None
    OWLRL_Semantics = None


class SemanticService:
    """
    功能：
    - 聚合语义层的主要能力，供 API 与 CLI 复用。
    - 该类定义在 `backend/app/services/semantic_service.py` 中，用于组织与 `SemanticService` 相关的数据或行为。
    """

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
        self.repository = GraphRepository(settings)
        self.runtime = RuntimeEngine(settings)
        self.lock = threading.RLock()
        self.batch_id = datetime.now(tz=UTC).strftime("%Y%m%d%H%M%S")
        self.dataset: Dataset | None = None
        self.base_graph: Graph | None = None
        self.deductions_graph: Graph | None = None
        self.scenario: ScenarioConfig = load_scenario_config(settings.scenario_path)
        self.reference_date = self.scenario.reference_date or datetime.now(tz=UTC).date()
        self.fact_evaluator = FactEvaluator(
            reference_date=self.reference_date,
            primary_dataset=self.scenario.primary_dataset,
        )
        self.mapping_rows: list[MappingRow] = load_mapping_rows(settings.mapping_path)
        self.mapping_by_dataset: dict[str, list[MappingRow]] = defaultdict(list)
        for row in self.mapping_rows:
            self.mapping_by_dataset[row.dataset].append(row)
        self.source_rows: dict[str, list[dict[str, Any]]] = {}
        self.dataset_indexes: dict[str, dict[str, dict[str, list[dict[str, Any]]]]] = {}
        self.records: dict[str, dict[str, Any]] = {}
        self.inference: dict[str, dict[str, Any]] = {}
        self.top_rules: dict[str, int] = {}
        self.operational_metrics: dict[str, Any] = {}
        self.validation: dict[str, object] = {}
        self.persistence: dict[str, object] = {}
        self.data_warnings: list[str] = []
        self.initialize()

    def initialize(self) -> None:
        """
        功能：
        - 重新装载配置、原始数据、本体和推理结果。

        输入：
        - 无。

        输出：
        - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
        """
        with self.lock:
            self.batch_id = datetime.now(tz=UTC).strftime("%Y%m%d%H%M%S")
            self.dataset = Dataset()
            self.base_graph = self.dataset.graph(URIRef(self.settings.base_graph_uri))
            self.deductions_graph = self.dataset.graph(URIRef(self.settings.deductions_graph_uri))
            bind_prefixes(self.base_graph, self.settings)
            bind_prefixes(self.deductions_graph, self.settings)

            # 初始化顺序固定：先装入 schema，再读源数据、构图、校验、推理、持久化。
            self._load_schema(self.base_graph)
            self.source_rows, self.data_warnings = load_source_rows(
                settings=self.settings,
                scenario=self.scenario,
                mapping_by_dataset=self.mapping_by_dataset,
                fact_evaluator=self.fact_evaluator,
            )
            self.dataset_indexes = build_dataset_indexes(self.source_rows, self.scenario)
            self.records = build_records(
                source_rows=self.source_rows,
                dataset_indexes=self.dataset_indexes,
                scenario=self.scenario,
                fact_evaluator=self.fact_evaluator,
                node_id_for_row=self._node_id,
            )
            self._materialize_base_graph()
            self.validation = run_shacl_validation(
                self.base_graph,
                self.settings.ontology_shapes_path,
                self.settings.reports_dir / "validation-report.ttl",
            )
            self.run_inference(persist=False)
            self.persistence = self.repository.persist(self.dataset)

    def _load_schema(self, graph: Graph) -> None:
        """
        功能：
        - 把核心本体和领域本体加载到基础图。

        输入：
        - `graph`: 需要读取或写入的 RDF 图对象。

        输出：
        - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
        """
        for path in (self.settings.ontology_core_path, self.settings.ontology_domain_path):
            graph.parse(path, format="turtle")

    def _materialize_base_graph(self) -> None:
        """
        功能：
        - 把原始行数据和场景关系映射为基础 RDF 图。

        输入：
        - 无。

        输出：
        - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
        """
        graph = self.base_graph
        assert graph is not None
        materialize_base_graph(
            graph=graph,
            settings=self.settings,
            scenario=self.scenario,
            source_rows=self.source_rows,
            dataset_indexes=self.dataset_indexes,
            mapping_by_dataset=self.mapping_by_dataset,
            batch_id=self.batch_id,
        )

    def _apply_owlrl(self) -> int:
        """
        功能：
        - 执行 OWL RL 推理，并把新增三元组写入推理图。

        输入：
        - 无。

        输出：
        - 返回值: 返回整数结果，通常用于计数、排序权重或状态统计。
        """
        if DeductiveClosure is None or OWLRL_Semantics is None:
            return 0
        assert self.base_graph is not None
        assert self.deductions_graph is not None
        if len(self.base_graph) > 20000:
            return 0
        closure_graph = Graph()
        bind_prefixes(closure_graph, self.settings)
        for triple in self.base_graph:
            closure_graph.add(triple)
        DeductiveClosure(OWLRL_Semantics).expand(closure_graph)
        added = 0
        for triple in closure_graph:
            subject, predicate, _ = triple
            if not isinstance(subject, (URIRef, BNode)) or not isinstance(predicate, URIRef):
                continue
            if triple not in self.base_graph and triple not in self.deductions_graph:
                self.deductions_graph.add(triple)
                added += 1
        return added

    def _union_graph(self) -> Graph:
        """
        功能：
        - 合并基础图与推理图，形成统一查询视图。

        输入：
        - 无。

        输出：
        - 返回值: 返回构建完成的 RDF 图对象。
        """
        union = Graph()
        bind_prefixes(union, self.settings)
        assert self.base_graph is not None
        assert self.deductions_graph is not None
        for triple in self.base_graph:
            union.add(triple)
        for triple in self.deductions_graph:
            union.add(triple)
        return union

    def run_inference(self, persist: bool = True) -> dict[str, Any]:
        """
        功能：
        - 重新执行推理流程，并按需持久化结果。

        输入：
        - `persist`: 布尔参数 `persist`，用于控制当前分支或开关行为。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        with self.lock:
            assert self.deductions_graph is not None
            # 每次推理前先清空旧推理结果，避免重复叠加。
            self.deductions_graph.remove((None, None, None))
            owlrl_triples = self._apply_owlrl()
            inferred, top_rules = materialize_business_inference(
                self.deductions_graph,
                self.records,
                self.settings,
                self.scenario,
            )
            self.inference = inferred
            self.top_rules = dict(top_rules)
            self.runtime.bootstrap(self.records, self.inference)
            self.runtime.materialize(self.deductions_graph, self.settings, self.records)
            self.operational_metrics = self.runtime.operational_summary()
            if persist and self.dataset is not None:
                self.persistence = self.repository.persist(self.dataset)
            return {
                "deductionTriples": len(self.deductions_graph),
                "owlrlTriples": owlrl_triples,
                "riskDistribution": self._risk_distribution(),
                "operationalMetrics": self.operational_metrics,
            }

    def get_summary(self) -> dict[str, Any]:
        """
        功能：
        - 返回首页概览所需的汇总数据。

        输入：
        - 无。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        with self.lock:
            union = self._union_graph()
            object_model = self.describe_object_model()
            tool_catalog = self.describe_tool_catalog()
            return {
                "scenarioKey": self.settings.scenario_key,
                "scenario": self.scenario.name,
                "appTitle": self.scenario.app_title,
                "headerTitle": self.scenario.header_title,
                "dashboardSubtitle": self.scenario.dashboard_subtitle,
                "tripleCount": len(union),
                "primaryEntityLabel": self.scenario.primary_entity_label,
                "primaryEntityPluralLabel": self.scenario.primary_entity_plural_label,
                "primaryEntityCount": len(self.records),
                "interactionLabel": "交互记录",
                "interactionCount": sum(len(self.source_rows.get(key, [])) for key in self.scenario.interaction_datasets),
                "relationCount": sum(
                    1 for _ in self.base_graph.subjects(RDF.type, URIRef(f"{self.settings.doim_ns}Relation"))
                ),
                "riskDistribution": self._risk_distribution(),
                "topRules": [
                    {"rule": label, "count": count}
                    for label, count in sorted(self.top_rules.items(), key=lambda item: (-item[1], item[0]))
                ],
                "sampleQuery": self.scenario.sample_query or self.settings.default_query,
                "questionSuggestions": list(self.scenario.question_suggestions),
                "ontologyGraph": self._build_overview_graph(),
                "architecture": list(self.scenario.architecture),
                "validation": self.validation,
                "persistence": self.persistence,
                "sourceCards": self._build_source_cards(),
                "ontologyFiles": [item.__dict__ for item in self.scenario.ontology_files],
                "ruleCards": [item.__dict__ for item in self.scenario.rule_cards],
                "mappingExamples": list(self.scenario.mapping_examples),
                "operationalMetrics": self.operational_metrics,
                "caseDistribution": self.operational_metrics.get("caseDistribution", {}),
                "taskDistribution": self.operational_metrics.get("taskDistribution", {}),
                "alertDistribution": self.operational_metrics.get("alertDistribution", {}),
                "actionCatalog": self.operational_metrics.get("actionCatalog", []),
                "operationsWorkbench": self._build_operations_workbench(),
                "ontologyObjects": object_model,
                "toolCatalog": tool_catalog,
                "agentProfile": {
                    "name": "运营智能问答",
                    "mode": "supervised",
                    "planner": "llm-tool-router",
                    "objectCount": len(object_model),
                    "toolCount": len(tool_catalog),
                },
                "warnings": list(self.data_warnings),
            }

    def get_alerts(self) -> list[dict[str, Any]]:
        """
        功能：
        - 构建告警列表，并按场景配置的排序规则输出。

        输入：
        - 无。

        输出：
        - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
        """
        alerts = [
            self._build_alert_payload(context)
            for entity_id in self.records
            if (context := self._entity_context(entity_id)) is not None
        ]
        alerts.sort(key=self._alert_sort_key)
        return alerts

    def search_subscribers(self, query: str) -> list[dict[str, Any]]:
        """
        功能：
        - 按实体标识、名称和搜索字段检索实体。

        输入：
        - `query`: 调用方传入的查询语句或关键字。

        输出：
        - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
        """
        keyword = (query or "").strip().lower()
        alerts = self.get_alerts()
        if any(term in keyword for term in self.scenario.risk_terms):
            return alerts

        matches = []
        for record in self.records.values():
            haystacks = [record["entityId"], record["displayName"]]
            primary_row = record["primary"]
            haystacks.extend(str(primary_row.get(field) or "") for field in self.scenario.search_fields)
            if not keyword or any(keyword in value.lower() for value in haystacks if value):
                matches.append(record["entityId"])

        by_id = {item["entityId"]: item for item in alerts}
        return [by_id[entity_id] for entity_id in matches if entity_id in by_id]

    def get_subscriber(self, subscriber_id: str) -> dict[str, Any]:
        """
        功能：
        - 返回单个实体的详细信息、证据和局部图谱。

        输入：
        - `subscriber_id`: 函数执行所需的 `subscriber_id` 参数。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        entity_id = subscriber_id.strip()
        context = self._entity_context(entity_id)
        if context is None:
            return {"error": "entity_not_found", "entityId": entity_id}
        return self._build_subscriber_payload(context)

    def run_sparql(self, query_string: str | None) -> dict[str, Any]:
        """
        功能：
        - 执行 SPARQL 查询，兼容纯文本和 JSON body 两种输入格式。

        输入：
        - `query_string`: 需要执行的完整查询字符串。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        query = self._extract_query(query_string) or self.scenario.sample_query or self.settings.default_query
        graph = self._union_graph()
        results = graph.query(query)
        variables = [str(variable) for variable in results.vars]
        rows: list[dict[str, str]] = []
        for row in results:
            item: dict[str, str] = {}
            for variable in variables:
                value = row.get(variable)
                item[variable] = "" if value is None else str(value)
            rows.append(item)
        return {
            "query": query,
            "variables": variables,
            "rowCount": len(rows),
            "rows": rows,
        }

    def describe_object_model(self) -> list[dict[str, Any]]:
        """
        功能：
        - 返回监督 agent 可访问的稳定对象模型定义。

        输入：
        - 无。

        输出：
        - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
        """
        with self.lock:
            return build_object_model(
                primary_entity_label=self.scenario.primary_entity_label,
                primary_node_type=self.scenario.primary_node_type,
            )

    def describe_tool_catalog(self) -> list[dict[str, Any]]:
        """
        功能：
        - 返回监督 agent 依赖的工具目录。

        输入：
        - 无。

        输出：
        - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
        """
        with self.lock:
            return agent_tool_catalog()

    def query_objects(
        self,
        object_type: str,
        *,
        limit: int = 10,
        search: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        功能：
        - 按对象类型检索实例，作为监督 agent 的统一 object query 工具。

        输入：
        - `object_type`: 对象类型名称。
        - `limit`: 函数执行所需的 `limit` 参数。
        - `search`: 对象查询时使用的搜索关键字。
        - `filters`: 对象查询时使用的字段过滤条件。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        with self.lock:
            normalized_limit = max(1, min(int(limit or 10), 50))
            rows = self._object_rows(object_type)
            filtered = [
                row
                for row in rows
                if self._matches_object_filters(row, filters or {})
                and self._matches_object_search(row, search)
            ]
            return {
                "objectType": object_type,
                "total": len(filtered),
                "returned": min(len(filtered), normalized_limit),
                "rows": filtered[:normalized_limit],
            }

    def get_object(self, object_type: str, object_id: str) -> dict[str, Any]:
        """
        功能：
        - 读取单个对象详情。

        输入：
        - `object_type`: 对象类型名称。
        - `object_id`: 对象标识。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        with self.lock:
            key = object_id.strip()
            if not key:
                raise ValueError("object_id_required")

            direct_getters = {
                "User": lambda: self.get_subscriber(key),
                "RetentionCase": lambda: self.get_case(key),
                "Task": lambda: self._get_task_object(key),
                "ActionDefinition": lambda: self._get_action_definition_object(key),
            }
            if object_type in direct_getters:
                return direct_getters[object_type]()

            result = self.query_objects(object_type, limit=1, filters={"objectId": key})
            if result["rows"]:
                return result["rows"][0]
            return {"error": "object_not_found", "objectType": object_type, "objectId": key}

    def load_data_file(self, file_path: Path) -> dict[str, Any]:
        """
        功能：
        - 加载上传文件；CSV 触发全量重建，RDF 文件则直接解析入图。

        输入：
        - `file_path`: 待处理的数据文件路径。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        with self.lock:
            if file_path.suffix.lower() == ".csv":
                self.initialize()
                return {
                    "success": True,
                    "file": file_path.name,
                    "rows": len(read_csv_rows(file_path)),
                }

            assert self.base_graph is not None
            self.base_graph.parse(file_path)
            if self.dataset is not None:
                self.persistence = self.repository.persist(self.dataset)
            return {
                "success": True,
                "file": file_path.name,
                "triples": len(self.base_graph),
            }

    def list_cases(self) -> list[dict[str, Any]]:
        """
        功能：
        - 返回当前所有运营 case。

        输入：
        - 无。

        输出：
        - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
        """
        with self.lock:
            return [self._enrich_case_payload(item) for item in self.runtime.list_cases()]

    def get_case(self, case_id: str) -> dict[str, Any]:
        """
        功能：
        - 返回单个运营 case。

        输入：
        - `case_id`: 运营 case 标识。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        with self.lock:
            payload = self.runtime.get_case(case_id)
            if payload is None:
                return {"error": "case_not_found", "caseId": case_id}
            return self._enrich_case_payload(payload, include_detail=True)

    def list_tasks(self, status: str | None = None, assignee_role: str | None = None) -> list[dict[str, Any]]:
        """
        功能：
        - 返回任务列表。

        输入：
        - `status`: 筛选或设置时使用的状态值。
        - `assignee_role`: 任务或 case 负责人角色标识。

        输出：
        - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
        """
        with self.lock:
            return [
                self._enrich_task_payload(item)
                for item in self.runtime.list_tasks(status=status, assignee_role=assignee_role)
            ]

    def execute_action(
        self,
        *,
        action_id: str,
        actor_role: str,
        actor_id: str,
        actor_area_id: str | None,
        entity_id: str | None,
        case_id: str | None,
        parameters: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """
        功能：
        - 执行运营动作。

        输入：
        - `action_id`: 待执行动作的标识。
        - `actor_role`: 当前执行人的角色标识。
        - `actor_id`: 当前执行人的唯一标识。
        - `actor_area_id`: 当前执行人所属区域标识，可为空。
        - `entity_id`: 业务主实体标识。
        - `case_id`: 运营 case 标识。
        - `parameters`: 字典参数 `parameters`，承载键值形式的输入数据。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        with self.lock:
            result = self.runtime.execute_action(
                action_id=action_id,
                actor=ActorContext(role=actor_role, actor_id=actor_id, area_id=actor_area_id),
                entity_id=entity_id,
                case_id=case_id,
                parameters=parameters,
            )
            assert self.deductions_graph is not None
            self.deductions_graph.remove((None, None, None))
            owlrl_triples = self._apply_owlrl()
            materialize_business_inference(
                self.deductions_graph,
                self.records,
                self.settings,
                self.scenario,
            )
            self.runtime.materialize(self.deductions_graph, self.settings, self.records)
            self.operational_metrics = self.runtime.operational_summary()
            if self.dataset is not None:
                self.persistence = self.repository.persist(self.dataset)
            result["owlrlTriples"] = owlrl_triples
            result["operationalMetrics"] = self.operational_metrics
            result["case"] = self._enrich_case_payload(result["case"], include_detail=True)
            result["workbench"] = self._build_operations_workbench()
            return result

    def _build_operations_workbench(self) -> dict[str, Any]:
        """
        功能：
        - 构建前端运营工作台所需的聚合视图。

        输入：
        - 无。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        cases = [self._enrich_case_payload(item) for item in self.runtime.list_cases()]
        tasks = [self._enrich_task_payload(item) for item in self.runtime.list_tasks()]
        open_cases = [item for item in cases if item.get("state") != "CLOSED"]
        todo_tasks = [item for item in tasks if item.get("status") == "TODO"]

        return {
            "focusCases": open_cases[:6],
            "queueLanes": self._build_workbench_queue_lanes(open_cases, todo_tasks),
            "priorityBands": self._build_workbench_priority_bands(open_cases),
            "recentActions": self._build_workbench_recent_actions(),
        }

    def _entity_context(self, entity_id: str) -> dict[str, Any] | None:
        """
        功能：
        - 聚合实体记录、推理结果与运行时状态，减少详情与告警接口的重复取数。

        输入：
        - `entity_id`: 业务主实体标识。

        输出：
        - 返回值: 返回处理结果；当目标不存在、未命中或无法解析时返回 `None`。
        """
        record = self.records.get(entity_id)
        if record is None:
            return None
        return {
            "entityId": entity_id,
            "record": record,
            "inference": self.inference[entity_id],
            "runtimeCase": self.runtime.get_case_for_entity(entity_id),
            "runtimeAlert": self.runtime.get_alert_for_entity(entity_id),
        }

    def _build_alert_payload(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        功能：
        - 构建alert返回载荷。

        输入：
        - `context`: 错误提示或日志中使用的上下文说明。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        record = context["record"]
        inference = context["inference"]
        runtime_case = context["runtimeCase"] or {}
        runtime_alert = context["runtimeAlert"] or {}
        return {
            "entityId": context["entityId"],
            "nodeId": record["nodeId"],
            "displayName": record["displayName"],
            "riskLevel": inference["riskLevel"],
            "recommendedAction": inference["recommendedAction"],
            "factors": [factor.label for factor in inference["factors"]],
            "summaryFields": self._render_display_fields(record, self.scenario.summary_fields),
            "detailFields": self._render_display_fields(record, self.scenario.detail_fields),
            "highlightFields": self._render_display_fields(record, self.scenario.highlight_fields),
            "metrics": self._serialize_metrics(record["metrics"]),
            "alertState": runtime_alert.get("state") or "",
            "caseId": runtime_case.get("caseId") or "",
            "caseState": runtime_case.get("state") or "",
            "taskCount": len(runtime_case.get("tasks", [])),
            "availableActions": runtime_case.get("availableActions", []),
        }

    def _build_subscriber_payload(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        功能：
        - 构建主实体详情返回载荷。

        输入：
        - `context`: 错误提示或日志中使用的上下文说明。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        record = context["record"]
        inference = context["inference"]
        runtime_case = context["runtimeCase"]
        runtime_alert = context["runtimeAlert"] or {}
        interaction_count = sum(len(record["related"].get(key, [])) for key in self.scenario.interaction_datasets)
        return {
            "entityId": context["entityId"],
            "displayName": record["displayName"],
            "riskLevel": inference["riskLevel"],
            "recommendedAction": inference["recommendedAction"],
            "metrics": self._serialize_metrics(record["metrics"]),
            "factors": [factor.label for factor in inference["factors"]],
            "rules": inference["rules"],
            "summaryFields": self._render_display_fields(record, self.scenario.summary_fields),
            "detailFields": self._render_display_fields(record, self.scenario.detail_fields),
            "relatedData": self._serialize_related_data(record),
            "inference": self._build_inference_summary(record["displayName"], inference, interaction_count),
            "evidence": self._build_evidence(record, inference),
            "graph": self._build_entity_graph(record, inference, runtime_case),
            "alertState": runtime_alert.get("state") or "",
            "case": runtime_case,
            "tasks": (runtime_case or {}).get("tasks", []),
            "timeline": (runtime_case or {}).get("timeline", []),
            "actionRuns": (runtime_case or {}).get("actionRuns", []),
            "availableActions": (runtime_case or {}).get("availableActions", []),
        }

    def _serialize_related_data(self, record: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        """
        功能：
        - 序列化relateddata。

        输入：
        - `record`: 单个实体或业务对象的聚合记录。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        return {
            dataset_key: [self._serialize_row(row) for row in rows]
            for dataset_key, rows in record["related"].items()
            if rows
        }

    def _build_workbench_priority_bands(self, open_cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        功能：
        - 构建workbenchprioritybands。

        输入：
        - `open_cases`: 当前仍处于打开状态的 case 列表。

        输出：
        - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
        """
        priority_meta = {
            "P1": "立即处置",
            "P2": "当班跟进",
            "P3": "持续监控",
        }
        bands = []
        for priority in ("P1", "P2", "P3"):
            band_cases = [item for item in open_cases if item.get("priority") == priority]
            bands.append(
                {
                    "priority": priority,
                    "label": priority_meta[priority],
                    "caseCount": len(band_cases),
                    "openTaskCount": sum(int(item.get("openTaskCount") or 0) for item in band_cases),
                    "actionableCount": sum(1 for item in band_cases if item.get("availableActions")),
                }
            )
        return bands

    def _build_workbench_queue_lanes(
        self,
        open_cases: list[dict[str, Any]],
        todo_tasks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        功能：
        - 构建workbench队列lanes。

        输入：
        - `open_cases`: 当前仍处于打开状态的 case 列表。
        - `todo_tasks`: 列表参数 `todo_tasks`，用于批量传入待处理的数据。

        输出：
        - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
        """
        queue_names = sorted({item.get("queue_name", "") for item in open_cases if item.get("queue_name")})
        lanes = []
        for queue_name in queue_names:
            lane_cases = [item for item in open_cases if item.get("queue_name") == queue_name]
            lane_tasks = [item for item in todo_tasks if item.get("queue_name") == queue_name]
            lanes.append(
                {
                    "queueName": queue_name,
                    "label": queue_name.replace("-", " ").title(),
                    "caseCount": len(lane_cases),
                    "taskCount": len(lane_tasks),
                    "highRiskCount": sum(1 for item in lane_cases if item.get("risk_level") == "HIGH"),
                    "owners": sorted({str(item.get("owner_role") or "") for item in lane_cases if item.get("owner_role")}),
                }
            )
        return lanes

    def _build_workbench_recent_actions(self) -> list[dict[str, Any]]:
        """
        功能：
        - 构建workbenchrecent动作列表。

        输入：
        - 无。

        输出：
        - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
        """
        recent_actions = []
        recent_runs = sorted(self.runtime.action_runs.values(), key=lambda item: item.updated_at, reverse=True)[:6]
        for run in recent_runs:
            display_name = self.records.get(run.entity_id, {}).get("displayName", run.entity_id)
            action = self.runtime.action_definitions.get(run.action_id)
            recent_actions.append(
                {
                    "id": run.id,
                    "caseId": run.case_id,
                    "entityId": run.entity_id,
                    "displayName": display_name,
                    "actionId": run.action_id,
                    "label": action.label if action is not None else run.action_id,
                    "actorRole": run.actor_role,
                    "status": run.status,
                    "time": run.updated_at,
                }
            )
        return recent_actions

    def _object_rows(self, object_type: str) -> list[dict[str, Any]]:
        """
        功能：
        - 处理与 `_object_rows` 相关的逻辑。

        输入：
        - `object_type`: 对象类型名称。

        输出：
        - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
        """
        builders = {
            "User": self._build_user_object_rows,
            "RiskAlert": self._build_alert_object_rows,
            "RetentionCase": self._build_case_object_rows,
            "Task": self._build_task_object_rows,
            "InteractionEvent": self._build_interaction_object_rows,
            "RuleHit": self._build_rule_object_rows,
            "ActionDefinition": self._build_action_object_rows,
        }
        builder = builders.get(object_type)
        if builder is None:
            raise ValueError(f"unsupported_object_type:{object_type}")
        return builder()

    def _build_user_object_rows(self) -> list[dict[str, Any]]:
        """
        功能：
        - 构建user对象行数据。

        输入：
        - 无。

        输出：
        - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
        """
        return [self._build_user_object_row(alert) for alert in self.get_alerts()]

    def _build_alert_object_rows(self) -> list[dict[str, Any]]:
        """
        功能：
        - 构建alert对象行数据。

        输入：
        - 无。

        输出：
        - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
        """
        return [self._build_alert_object_row(alert) for alert in self.get_alerts()]

    def _build_user_object_row(self, alert: dict[str, Any]) -> dict[str, Any]:
        """
        功能：
        - 构建user对象单行数据。

        输入：
        - `alert`: 单个运行时告警对象或告警载荷。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        primary = self.records.get(alert["entityId"], {}).get("primary", {})
        return {
            "objectId": alert["entityId"],
            "objectType": "User",
            "entityId": alert["entityId"],
            "displayName": alert["displayName"],
            "riskLevel": alert["riskLevel"],
            "recommendedAction": alert["recommendedAction"],
            "alertState": alert.get("alertState") or "",
            "caseId": alert.get("caseId") or "",
            "caseState": alert.get("caseState") or "",
            "areaId": str(primary.get("area_id") or ""),
            "summary": self._field_line(alert.get("summaryFields", [])),
        }

    def _build_alert_object_row(self, alert: dict[str, Any]) -> dict[str, Any]:
        """
        功能：
        - 构建alert对象单行数据。

        输入：
        - `alert`: 单个运行时告警对象或告警载荷。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        return {
            "objectId": f"alert:{alert['entityId']}",
            "objectType": "RiskAlert",
            "entityId": alert["entityId"],
            "displayName": alert["displayName"],
            "riskLevel": alert["riskLevel"],
            "recommendedAction": alert["recommendedAction"],
            "alertState": alert.get("alertState") or "",
            "caseId": alert.get("caseId") or "",
            "caseState": alert.get("caseState") or "",
            "summary": self._field_line(alert.get("highlightFields", []))
            or self._field_line(alert.get("summaryFields", [])),
        }

    def _build_case_object_rows(self) -> list[dict[str, Any]]:
        """
        功能：
        - 构建case对象行数据。

        输入：
        - 无。

        输出：
        - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
        """
        return [self._enrich_case_payload(item) for item in self.runtime.list_cases()]

    def _build_task_object_rows(self) -> list[dict[str, Any]]:
        """
        功能：
        - 构建task对象行数据。

        输入：
        - 无。

        输出：
        - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
        """
        return [self._enrich_task_payload(item) for item in self.runtime.list_tasks()]

    def _build_rule_object_rows(self) -> list[dict[str, Any]]:
        """
        功能：
        - 构建规则对象行数据。

        输入：
        - 无。

        输出：
        - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
        """
        return [
            {
                "objectId": label,
                "objectType": "RuleHit",
                "rule": label,
                "count": count,
            }
            for label, count in sorted(self.top_rules.items(), key=lambda item: (-item[1], item[0]))
        ]

    def _build_action_object_rows(self) -> list[dict[str, Any]]:
        """
        功能：
        - 构建动作对象行数据。

        输入：
        - 无。

        输出：
        - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
        """
        return [
            {
                **item.__dict__,
                "objectId": item.id,
                "objectType": "ActionDefinition",
            }
            for item in self.runtime.ACTION_DEFINITIONS
        ]

    def _build_interaction_object_rows(self) -> list[dict[str, Any]]:
        """
        功能：
        - 构建interaction对象行数据。

        输入：
        - 无。

        输出：
        - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
        """
        rows: list[dict[str, Any]] = []
        for dataset_key in self.scenario.interaction_datasets:
            dataset_config = self.scenario.datasets[dataset_key]
            for row in self.source_rows.get(dataset_key, []):
                entity_id = self._primary_entity_id_for_row(dataset_key, row)
                display_name = self.records.get(entity_id, {}).get("displayName", "") if entity_id else ""
                rows.append(
                    {
                        "objectId": str(row.get("_entity_uri") or self._node_id(dataset_key, row)),
                        "objectType": "InteractionEvent",
                        "datasetKey": dataset_key,
                        "entityId": entity_id,
                        "displayName": display_name or str(row.get("_label") or dataset_config.entity_label),
                        "eventTime": self._interaction_time_value(row),
                        "sourceSystem": dataset_config.source_system,
                        "summary": self._row_brief(row),
                    }
                )
        rows.sort(key=lambda item: str(item.get("eventTime") or ""), reverse=True)
        return rows

    def _matches_object_filters(self, row: dict[str, Any], filters: dict[str, Any]) -> bool:
        """
        功能：
        - 处理与 `_matches_object_filters` 相关的逻辑。

        输入：
        - `row`: 单行源数据或中间对象数据。
        - `filters`: 对象查询时使用的字段过滤条件。

        输出：
        - 返回值: 返回布尔值，表示条件是否成立或当前操作是否允许。
        """
        for key, value in filters.items():
            if value in (None, ""):
                continue
            candidate = row.get(key)
            if isinstance(value, (list, tuple, set)):
                normalized = {str(item).lower() for item in value}
                if str(candidate or "").lower() not in normalized:
                    return False
                continue
            if str(candidate or "").lower() != str(value).lower():
                return False
        return True

    def _matches_object_search(self, row: dict[str, Any], search: str | None) -> bool:
        """
        功能：
        - 处理与 `_matches_object_search` 相关的逻辑。

        输入：
        - `row`: 单行源数据或中间对象数据。
        - `search`: 对象查询时使用的搜索关键字。

        输出：
        - 返回值: 返回布尔值，表示条件是否成立或当前操作是否允许。
        """
        keyword = (search or "").strip().lower()
        if not keyword:
            return True
        haystacks = []
        for value in row.values():
            if isinstance(value, (str, int, float, bool)):
                haystacks.append(str(value))
        return any(keyword in item.lower() for item in haystacks)

    def _field_line(self, fields: list[dict[str, Any]]) -> str:
        """
        功能：
        - 处理与 `_field_line` 相关的逻辑。

        输入：
        - `fields`: 用于展示或拼接的字段定义列表。

        输出：
        - 返回值: 返回字符串结果，供调用方继续展示、拼接或查询。
        """
        parts = []
        for field in fields:
            label = str(field.get("label") or "").strip()
            value = field.get("value")
            if not label or value in (None, ""):
                continue
            parts.append(f"{label}: {value}")
        return " | ".join(parts)

    def _interaction_time_value(self, row: dict[str, Any]) -> str:
        """
        功能：
        - 处理与 `_interaction_time_value` 相关的逻辑。

        输入：
        - `row`: 单行源数据或中间对象数据。

        输出：
        - 返回值: 返回字符串结果，供调用方继续展示、拼接或查询。
        """
        for field_name in (
            "query_time",
            "accept_time",
            "maintain_time",
            "start_date",
            "create_time",
            "latest_date",
            "stat_date",
            "event_time",
        ):
            value = row.get(field_name)
            if value not in (None, ""):
                return str(value)
        return ""

    def _row_brief(self, row: dict[str, Any]) -> str:
        """
        功能：
        - 处理与 `_row_brief` 相关的逻辑。

        输入：
        - `row`: 单行源数据或中间对象数据。

        输出：
        - 返回值: 返回字符串结果，供调用方继续展示、拼接或查询。
        """
        preview_fields = []
        for key, value in row.items():
            if key.startswith("_") or value in (None, ""):
                continue
            preview_fields.append(f"{key}={value}")
            if len(preview_fields) >= 3:
                break
        return " | ".join(preview_fields)

    def _primary_entity_id_for_row(self, dataset_key: str, row: dict[str, Any]) -> str:
        """
        功能：
        - 处理与 `_primary_entity_id_for_row` 相关的逻辑。

        输入：
        - `dataset_key`: 需要持久化或查询的 RDF 数据集对象。
        - `row`: 单行源数据或中间对象数据。

        输出：
        - 返回值: 返回字符串结果，供调用方继续展示、拼接或查询。
        """
        primary_dataset = self.scenario.datasets[self.scenario.primary_dataset]
        dataset_config = self.scenario.datasets[dataset_key]
        primary_indexes = self.dataset_indexes.get(self.scenario.primary_dataset, {})
        for canonical_key, dataset_field in dataset_config.join_keys.items():
            if canonical_key not in primary_dataset.join_keys:
                continue
            value = row.get(dataset_field)
            if value in (None, ""):
                continue
            for match in primary_indexes.get(canonical_key, {}).get(str(value), []):
                entity_id = match.get(self.scenario.primary_id_field)
                if entity_id not in (None, ""):
                    return str(entity_id)
        return ""

    def _get_task_object(self, task_id: str) -> dict[str, Any]:
        """
        功能：
        - 获取task对象。

        输入：
        - `task_id`: 任务标识。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        task = next((item for item in self.runtime.list_tasks() if str(item.get("id") or "") == task_id), None)
        if task is None:
            return {"error": "object_not_found", "objectType": "Task", "objectId": task_id}
        return self._enrich_task_payload(task)

    def _get_action_definition_object(self, object_id: str) -> dict[str, Any]:
        """
        功能：
        - 获取动作definition对象。

        输入：
        - `object_id`: 对象标识。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        action = self.runtime.action_definitions.get(object_id)
        if action is None:
            return {"error": "object_not_found", "objectType": "ActionDefinition", "objectId": object_id}
        return {
            **action.__dict__,
            "objectType": "ActionDefinition",
            "objectId": object_id,
        }

    def _enrich_case_payload(self, payload: dict[str, Any], include_detail: bool = False) -> dict[str, Any]:
        """
        功能：
        - 补齐前端工作台所需的 case 展示字段。

        输入：
        - `payload`: 请求体或内部处理中使用的载荷数据。
        - `include_detail`: 布尔参数 `include_detail`，用于控制当前分支或开关行为。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        enriched = dict(payload)
        entity_id = str(enriched.get("entityId") or "")
        record = self.records.get(entity_id)
        inference = self.inference.get(entity_id, {})
        if record is not None:
            enriched["displayName"] = record["displayName"]
            enriched["summaryFields"] = self._render_display_fields(record, self.scenario.summary_fields)
            enriched["detailFields"] = self._render_display_fields(record, self.scenario.detail_fields)
        else:
            enriched.setdefault("displayName", entity_id)
            enriched.setdefault("summaryFields", [])
            enriched.setdefault("detailFields", [])

        enriched["recommendedAction"] = inference.get("recommendedAction", "")
        available_actions = enriched.get("availableActions") or []
        enriched["nextAction"] = available_actions[0] if available_actions else None
        timeline = list(enriched.get("timeline") or [])
        last_item = timeline[-1] if timeline else None
        enriched["lastActivityTitle"] = (last_item or {}).get("title") or "维系 Case 已创建"
        enriched["lastActivityTime"] = (last_item or {}).get("time") or enriched.get("updated_at") or enriched.get("created_at")

        if include_detail:
            enriched["tasks"] = [self._enrich_task_payload(item) for item in enriched.get("tasks", [])]
        return enriched

    def _enrich_task_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        功能：
        - 补齐任务列表展示字段。

        输入：
        - `payload`: 请求体或内部处理中使用的载荷数据。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        enriched = dict(payload)
        entity_id = str(enriched.get("entity_id") or "")
        record = self.records.get(entity_id)
        inference = self.inference.get(entity_id, {})
        runtime_case = self.runtime.cases.get(str(enriched.get("case_id") or ""))
        enriched["displayName"] = record["displayName"] if record is not None else entity_id
        enriched["riskLevel"] = inference.get("riskLevel", "")
        enriched["caseState"] = runtime_case.state if runtime_case is not None else ""
        enriched["priority"] = runtime_case.priority if runtime_case is not None else ""
        enriched["recommendedAction"] = inference.get("recommendedAction", "")
        if record is not None:
            enriched["summaryFields"] = self._render_display_fields(record, self.scenario.summary_fields)
        else:
            enriched["summaryFields"] = []
        return enriched

    def _risk_distribution(self) -> dict[str, int]:
        """
        功能：
        - 统计当前推理结果中的风险等级分布。

        输入：
        - 无。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        distribution = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for item in self.inference.values():
            distribution[item["riskLevel"]] += 1
        return distribution

    def _extract_query(self, payload: str | None) -> str:
        """
        功能：
        - 从请求体中提取查询语句。

        输入：
        - `payload`: 请求体或内部处理中使用的载荷数据。

        输出：
        - 返回值: 返回字符串结果，供调用方继续展示、拼接或查询。
        """
        if payload is None:
            return ""
        text = payload.strip()
        if not text:
            return ""
        if text.startswith("{"):
            try:
                body = json.loads(text)
            except json.JSONDecodeError:
                return text
            return str(body.get("query", "")).strip()
        return text

    def _build_inference_summary(self, name: str, inference: dict[str, Any], interaction_count: int) -> dict[str, Any]:
        """
        功能：
        - 生成详情页顶部的推理摘要卡片。

        输入：
        - `name`: 名称、字段名或标识名。
        - `inference`: 按实体组织的推理结果集合。
        - `interaction_count`: 函数执行所需的 `interaction_count` 参数。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        risk_level = inference["riskLevel"]
        summary = {
            "headline": f"{name} 被推理为 {risk_level} 风险",
            "riskLevel": risk_level,
            "recommendedAction": inference["recommendedAction"],
            "factorCount": len(inference["factors"]),
            "ruleCount": len(inference["rules"]),
            "eventCount": interaction_count,
        }
        if risk_level == "HIGH":
            summary["summary"] = "命中高风险携转预警规则，建议立即触发紧急维系流程。"
        elif risk_level == "MEDIUM":
            summary["summary"] = "命中中风险携转预警规则，建议常规维系并持续复核。"
        else:
            summary["summary"] = "未命中中高风险组合规则，维持低风险持续监控。"
        return summary

    def _build_evidence(self, record: dict[str, Any], inference: dict[str, Any]) -> list[dict[str, Any]]:
        """
        功能：
        - 把高亮字段和命中规则整理成前端可直接展示的证据列表。

        输入：
        - `record`: 单个实体或业务对象的聚合记录。
        - `inference`: 按实体组织的推理结果集合。

        输出：
        - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
        """
        evidence: list[dict[str, Any]] = []
        for field in self.scenario.highlight_fields:
            rendered = self._render_display_field(record, field)
            if rendered["value"] in ("", None):
                continue
            evidence.append(
                {
                    "category": "signal",
                    "title": rendered["label"],
                    "summary": f"{rendered['label']} = {rendered['value']}",
                    "facts": [f"{rendered['label']} = {rendered['value']}"],
                }
            )
        evidence.append(
            {
                "category": "decision",
                "title": f"{inference['riskLevel']} 风险判定",
                "summary": f"命中 {len(inference['rules'])} 条规则，形成最终风险等级。",
                "riskLevel": inference["riskLevel"],
                "facts": [f"命中规则：{label}" for label in inference["rules"]],
            }
        )
        return evidence

    def _build_source_cards(self) -> list[dict[str, Any]]:
        """
        功能：
        - 根据场景配置生成首页数据源卡片。

        输入：
        - 无。

        输出：
        - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
        """
        cards: list[dict[str, Any]] = []
        for card in self.scenario.source_cards:
            if card.count_mode == "primary":
                count = len(self.records)
            else:
                count = len(self.source_rows.get(card.dataset, []))
            cards.append(
                {
                    "key": card.key,
                    "label": card.label,
                    "file": card.file,
                    "count": count,
                    "icon": card.icon,
                    "tone": card.tone,
                }
            )
        return cards

    def _build_overview_graph(self) -> dict[str, Any]:
        """
        功能：
        - 构建首页概览图，只抽样展示每个主实体的一组代表性关联节点。

        输入：
        - 无。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        return build_overview_graph(
            records=self.records,
            source_rows=self.source_rows,
            scenario=self.scenario,
        )

    def _build_entity_graph(
        self,
        record: dict[str, Any],
        inference: dict[str, Any],
        runtime_case: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """
        功能：
        - 构建单个实体的详情图谱。

        输入：
        - `record`: 单个实体或业务对象的聚合记录。
        - `inference`: 按实体组织的推理结果集合。
        - `runtime_case`: 单个动作执行记录。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        return build_entity_graph(
            record=record,
            inference=inference,
            runtime_case=runtime_case,
            scenario=self.scenario,
            node_id_for_row=self._node_id,
            relation_label_for=self._relation_label,
        )

    def _render_display_fields(
        self,
        record: dict[str, Any],
        fields: tuple[AlertDisplayField, ...],
    ) -> list[dict[str, Any]]:
        """
        功能：
        - 批量渲染展示字段。

        输入：
        - `record`: 单个实体或业务对象的聚合记录。
        - `fields`: 用于展示或拼接的字段定义列表。

        输出：
        - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
        """
        return [self._render_display_field(record, field) for field in fields]

    def _render_display_field(self, record: dict[str, Any], field: AlertDisplayField) -> dict[str, Any]:
        """
        功能：
        - 根据字段来源规则提取展示值。

        输入：
        - `record`: 单个实体或业务对象的聚合记录。
        - `field`: 函数执行所需的 `field` 参数。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        value: Any = ""
        if field.fact:
            value = record["metrics"].get(field.fact)
        elif field.source == self.scenario.primary_dataset:
            value = record["primary"].get(field.field or "")
        elif field.source:
            related_rows = record["related"].get(field.source, [])
            if related_rows and field.field:
                value = related_rows[0].get(field.field)
        return {
            "label": field.label,
            "value": self._json_ready_value(value),
        }

    def _alert_sort_key(self, item: dict[str, Any]) -> tuple[Any, ...]:
        """
        功能：
        - 生成告警排序键，先按风险等级，再按场景配置事实值排序。

        输入：
        - `item`: 字典参数 `item`，承载键值形式的输入数据。

        输出：
        - 返回值: 返回元组结果，按既定顺序携带多个返回值。
        """
        key_parts: list[Any] = [-self._risk_weight(item["riskLevel"])]
        metrics = item["metrics"]
        for sort_field in self.scenario.alert_sort:
            raw = metrics.get(sort_field.fact)
            normalized = self._sortable_value(raw)
            key_parts.append(-normalized if sort_field.order == "desc" else normalized)
        key_parts.append(item["entityId"])
        return tuple(key_parts)

    def _risk_weight(self, level: str) -> int:
        """
        功能：
        - 把文本风险等级转换成可排序权重。

        输入：
        - `level`: 函数执行所需的 `level` 参数。

        输出：
        - 返回值: 返回整数结果，通常用于计数、排序权重或状态统计。
        """
        return {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(level, 0)

    def _sortable_value(self, value: Any) -> float:
        """
        功能：
        - 把多种事实值归一为可排序的数字。

        输入：
        - `value`: 待解析、转换或比较的原始值。

        输出：
        - 返回值: 返回浮点结果，通常用于数值计算或排序比较。
        """
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
        if value in ("", None):
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _json_ready_value(self, value: Any) -> Any:
        """
        功能：
        - 把不能直接 JSON 序列化的值转换为前端友好格式。

        输入：
        - `value`: 待解析、转换或比较的原始值。

        输出：
        - 返回值: 返回 `Any` 类型结果，供后续流程继续消费。
        """
        if isinstance(value, Decimal):
            return float(value)
        return value

    def _serialize_metrics(self, metrics: dict[str, Any]) -> dict[str, Any]:
        """
        功能：
        - 序列化事实指标字典。

        输入：
        - `metrics`: 实体聚合后的指标字典。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        return {key: self._json_ready_value(value) for key, value in metrics.items()}

    def _serialize_row(self, row: dict[str, Any]) -> dict[str, Any]:
        """
        功能：
        - 剔除内部辅助字段后输出原始行数据。

        输入：
        - `row`: 单行源数据或中间对象数据。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        payload: dict[str, Any] = {}
        for key, value in row.items():
            if key.startswith("_"):
                continue
            payload[key] = self._json_ready_value(value)
        return payload

    def _node_id(self, dataset_key: str, row: dict[str, Any]) -> str:
        """
        功能：
        - 为前端图谱节点生成稳定标识。

        输入：
        - `dataset_key`: 需要持久化或查询的 RDF 数据集对象。
        - `row`: 单行源数据或中间对象数据。

        输出：
        - 返回值: 返回字符串结果，供调用方继续展示、拼接或查询。
        """
        dataset_config = self.scenario.datasets[dataset_key]
        identifiers = [str(row.get(field)) for field in dataset_config.id_fields if row.get(field) not in (None, "")]
        if not identifiers:
            identifiers = [str(row.get("_row_index"))]
        return f"{dataset_config.node_type.lower()}:{'|'.join(identifiers)}"

    def _relation_label(self, source_dataset: str, target_dataset: str) -> str:
        """
        功能：
        - 根据场景配置查找两个数据集之间的默认关系文案。

        输入：
        - `source_dataset`: 函数执行所需的 `source_dataset` 参数。
        - `target_dataset`: 函数执行所需的 `target_dataset` 参数。

        输出：
        - 返回值: 返回字符串结果，供调用方继续展示、拼接或查询。
        """
        for relation in self.scenario.relations:
            if relation.source_dataset == source_dataset and relation.target_dataset == target_dataset:
                return relation.label
        return "关联"
