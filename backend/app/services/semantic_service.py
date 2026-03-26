"""语义服务核心实现，负责数据装载、图谱构建、推理与查询。"""

from __future__ import annotations

import json
import math
import threading
from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import quote

from rdflib import BNode, Dataset, Graph, Literal, RDF, RDFS, URIRef, XSD

from app.config.settings import Settings
from app.etl.csv_loader import read_csv_rows
from app.graph.repository import GraphRepository
from app.ontology.namespaces import bind_prefixes, make_namespaces
from app.rules.engine import materialize_business_inference
from app.runtime import ActorContext, RuntimeEngine
from app.scenario.config import (
    AlertDisplayField,
    FactConfig,
    RelationConfig,
    ScenarioConfig,
    SortConfig,
    load_scenario_config,
)
from app.scenario.mapping import MappingRow, load_mapping_rows
from app.validation.shacl import run_shacl_validation

try:
    from owlrl import DeductiveClosure, OWLRL_Semantics
except ImportError:  # pragma: no cover
    DeductiveClosure = None
    OWLRL_Semantics = None


class SemanticService:
    """聚合语义层的主要能力，供 API 与 CLI 复用。"""

    def __init__(self, settings: Settings) -> None:
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
        """重新装载配置、原始数据、本体和推理结果。"""
        with self.lock:
            self.batch_id = datetime.now(tz=UTC).strftime("%Y%m%d%H%M%S")
            self.dataset = Dataset()
            self.base_graph = self.dataset.graph(URIRef(self.settings.base_graph_uri))
            self.deductions_graph = self.dataset.graph(URIRef(self.settings.deductions_graph_uri))
            bind_prefixes(self.base_graph, self.settings)
            bind_prefixes(self.deductions_graph, self.settings)

            # 初始化顺序固定：先装入 schema，再读源数据、构图、校验、推理、持久化。
            self._load_schema(self.base_graph)
            self.source_rows = self._load_source_rows()
            self.dataset_indexes = self._build_dataset_indexes()
            self.records = self._build_records()
            self._materialize_base_graph()
            self.validation = run_shacl_validation(
                self.base_graph,
                self.settings.ontology_shapes_path,
                self.settings.reports_dir / "validation-report.ttl",
            )
            self.run_inference(persist=False)
            self.persistence = self.repository.persist(self.dataset)

    def _load_schema(self, graph: Graph) -> None:
        """把核心本体和领域本体加载到基础图。"""
        for path in (self.settings.ontology_core_path, self.settings.ontology_domain_path):
            graph.parse(path, format="turtle")

    def _load_source_rows(self) -> dict[str, list[dict[str, Any]]]:
        """读取各数据集 CSV，并补充实体构图所需的运行时元字段。"""
        rows_by_dataset: dict[str, list[dict[str, Any]]] = {}
        self.data_warnings = []

        for dataset_key, dataset_config in self.scenario.datasets.items():
            path = self.settings.data_dir / dataset_config.file
            if not path.exists():
                self.data_warnings.append(f"missing_dataset:{dataset_key}:{dataset_config.file}")
                rows_by_dataset[dataset_key] = []
                continue

            raw_rows = read_csv_rows(path)
            typed_rows: list[dict[str, Any]] = []
            target_type = self._target_type_for_dataset(dataset_key)
            for index, raw_row in enumerate(raw_rows):
                row: dict[str, Any] = dict(raw_row)
                for mapping in self.mapping_by_dataset.get(dataset_key, []):
                    if mapping.field_name in row:
                        row[mapping.field_name] = self._coerce_scalar(row[mapping.field_name], mapping.value_type)
                row["_dataset_key"] = dataset_key
                row["_row_index"] = index
                row["_target_type"] = target_type
                # 以下下划线字段仅在服务内部使用，不直接暴露给前端。
                row["_entity_uri"] = self._entity_uri(dataset_key, row, index)
                row["_label"] = self._entity_label(dataset_key, row)
                row["_node_type"] = dataset_config.node_type
                typed_rows.append(row)
            rows_by_dataset[dataset_key] = typed_rows
        return rows_by_dataset

    def _build_dataset_indexes(self) -> dict[str, dict[str, dict[str, list[dict[str, Any]]]]]:
        """按场景配置的 join key 构建多级索引，加速跨表关联。"""
        indexes: dict[str, dict[str, dict[str, list[dict[str, Any]]]]] = {}
        for dataset_key, rows in self.source_rows.items():
            dataset_config = self.scenario.datasets[dataset_key]
            join_indexes: dict[str, dict[str, list[dict[str, Any]]]] = {
                canonical_key: defaultdict(list) for canonical_key in dataset_config.join_keys
            }
            for row in rows:
                for canonical_key, field_name in dataset_config.join_keys.items():
                    value = row.get(field_name)
                    if value in (None, ""):
                        continue
                    join_indexes[canonical_key][str(value)].append(row)
            indexes[dataset_key] = join_indexes
        return indexes

    def _build_records(self) -> dict[str, dict[str, Any]]:
        """以主数据集为中心拼装实体记录，供告警与详情视图使用。"""
        primary_dataset = self.scenario.datasets[self.scenario.primary_dataset]
        records: dict[str, dict[str, Any]] = {}

        for primary_row in self.source_rows.get(self.scenario.primary_dataset, []):
            entity_id = str(primary_row.get(self.scenario.primary_id_field) or "").strip()
            if not entity_id:
                continue

            related: dict[str, list[dict[str, Any]]] = {}
            for dataset_key, dataset_config in self.scenario.datasets.items():
                if dataset_key == self.scenario.primary_dataset:
                    continue
                # 使用数据集键 + 行号去重，避免同一关联记录因多个 join key 重复命中。
                matched: dict[tuple[str, int], dict[str, Any]] = {}
                for canonical_key, primary_field in primary_dataset.join_keys.items():
                    if canonical_key not in dataset_config.join_keys:
                        continue
                    value = primary_row.get(primary_field)
                    if value in (None, ""):
                        continue
                    for row in self.dataset_indexes[dataset_key][canonical_key].get(str(value), []):
                        matched[(dataset_key, int(row["_row_index"]))] = row
                related[dataset_key] = list(matched.values())

            facts = {fact.key: self._evaluate_fact(fact, primary_row, related) for fact in self.scenario.facts}
            records[entity_id] = {
                "entityId": entity_id,
                "displayName": str(primary_row.get(self.scenario.primary_label_field) or entity_id),
                "nodeId": self._node_id(self.scenario.primary_dataset, primary_row),
                "primary": primary_row,
                "related": related,
                "metrics": facts,
            }
        return records

    def _materialize_base_graph(self) -> None:
        """把原始行数据和场景关系映射为基础 RDF 图。"""
        graph = self.base_graph
        assert graph is not None

        for dataset_key, rows in self.source_rows.items():
            target_type = self._target_type_for_dataset(dataset_key)
            target_class = self._resolve_curie(target_type)
            for row in rows:
                resource = row["_entity_uri"]
                self._tag_entity(graph, resource, self.scenario.datasets[dataset_key].source_system)
                graph.add((resource, RDF.type, target_class))

                label = row.get("_label")
                if label:
                    graph.add((resource, RDFS.label, Literal(str(label))))

                for mapping in self.mapping_by_dataset.get(dataset_key, []):
                    value = row.get(mapping.field_name)
                    if value in (None, ""):
                        continue
                    predicate = self._resolve_curie(mapping.mapped_predicate)
                    graph.add((resource, predicate, self._literal_for_value(value, mapping.value_type)))

        for relation in self.scenario.relations:
            source_rows = self.source_rows.get(relation.source_dataset, [])
            target_index = self.dataset_indexes.get(relation.target_dataset, {}).get(relation.target_join_key, {})
            source_dataset_config = self.scenario.datasets[relation.source_dataset]
            source_field = source_dataset_config.join_keys[relation.source_join_key]

            for source_row in source_rows:
                join_value = source_row.get(source_field)
                if join_value in (None, ""):
                    continue
                for target_row in target_index.get(str(join_value), []):
                    self._add_relation(
                        source_row["_entity_uri"],
                        self._resolve_curie(relation.predicate),
                        target_row["_entity_uri"],
                        self._relation_id(relation.source_dataset, source_row, relation.target_dataset, target_row),
                        relation.label,
                        relation.source_system,
                    )

    def _add_relation(
        self,
        source: URIRef,
        predicate: URIRef,
        target: URIRef,
        relation_id: str,
        label: str,
        source_system: str,
    ) -> None:
        """同时写入实体间关系边和关系对象节点，便于查询与溯源。"""
        graph = self.base_graph
        assert graph is not None
        namespaces = make_namespaces(self.settings)
        doim = namespaces["doim"]
        relation = URIRef(f"{self.settings.data_ns}relation/{relation_id}")
        self._tag_entity(graph, relation, source_system)
        graph.add((source, predicate, target))
        graph.add((source, doim.relatedTo, target))
        graph.add((relation, RDF.type, doim.Relation))
        graph.add((relation, RDFS.label, Literal(label)))
        graph.add((relation, doim.fromEntity, source))
        graph.add((relation, doim.toEntity, target))
        graph.add((relation, doim.predicateUri, Literal(str(predicate))))

    def _tag_entity(self, graph: Graph, resource: URIRef, source_system: str) -> None:
        """为实体补充来源系统和导入批次标记。"""
        namespaces = make_namespaces(self.settings)
        doim = namespaces["doim"]
        graph.add((resource, doim.sourceSystem, Literal(source_system)))
        graph.add((resource, doim.loadBatch, Literal(self.batch_id)))

    def _apply_owlrl(self) -> int:
        """执行 OWL RL 推理，并把新增三元组写入推理图。"""
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
        """合并基础图与推理图，形成统一查询视图。"""
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
        """重新执行推理流程，并按需持久化结果。"""
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
        """返回首页概览所需的汇总数据。"""
        with self.lock:
            union = self._union_graph()
            return {
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
                "warnings": list(self.data_warnings),
            }

    def get_alerts(self) -> list[dict[str, Any]]:
        """构建告警列表，并按场景配置的排序规则输出。"""
        alerts: list[dict[str, Any]] = []
        for record in self.records.values():
            inference = self.inference[record["entityId"]]
            runtime_case = self.runtime.get_case_for_entity(record["entityId"])
            runtime_alert = self.runtime.get_alert_for_entity(record["entityId"])
            alerts.append(
                {
                    "entityId": record["entityId"],
                    "nodeId": record["nodeId"],
                    "displayName": record["displayName"],
                    "riskLevel": inference["riskLevel"],
                    "recommendedAction": inference["recommendedAction"],
                    "factors": [factor.label for factor in inference["factors"]],
                    "summaryFields": self._render_display_fields(record, self.scenario.summary_fields),
                    "detailFields": self._render_display_fields(record, self.scenario.detail_fields),
                    "highlightFields": self._render_display_fields(record, self.scenario.highlight_fields),
                    "metrics": self._serialize_metrics(record["metrics"]),
                    "alertState": (runtime_alert or {}).get("state") or "",
                    "caseId": (runtime_case or {}).get("caseId") or "",
                    "caseState": (runtime_case or {}).get("state") or "",
                    "taskCount": len((runtime_case or {}).get("tasks", [])),
                    "availableActions": (runtime_case or {}).get("availableActions", []),
                }
            )

        alerts.sort(key=self._alert_sort_key)
        return alerts

    def search_subscribers(self, query: str) -> list[dict[str, Any]]:
        """按实体标识、名称和搜索字段检索实体。"""
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
        """返回单个实体的详细信息、证据和局部图谱。"""
        entity_id = subscriber_id.strip()
        if entity_id not in self.records:
            return {"error": "entity_not_found", "entityId": entity_id}

        record = self.records[entity_id]
        inference = self.inference[entity_id]
        runtime_case = self.runtime.get_case_for_entity(entity_id)
        runtime_alert = self.runtime.get_alert_for_entity(entity_id)
        related_payload = {
            dataset_key: [self._serialize_row(row) for row in rows]
            for dataset_key, rows in record["related"].items()
            if rows
        }
        interaction_count = sum(len(record["related"].get(key, [])) for key in self.scenario.interaction_datasets)
        return {
            "entityId": entity_id,
            "displayName": record["displayName"],
            "riskLevel": inference["riskLevel"],
            "recommendedAction": inference["recommendedAction"],
            "metrics": self._serialize_metrics(record["metrics"]),
            "factors": [factor.label for factor in inference["factors"]],
            "rules": inference["rules"],
            "summaryFields": self._render_display_fields(record, self.scenario.summary_fields),
            "detailFields": self._render_display_fields(record, self.scenario.detail_fields),
            "relatedData": related_payload,
            "inference": self._build_inference_summary(record["displayName"], inference, interaction_count),
            "evidence": self._build_evidence(record, inference),
            "graph": self._build_entity_graph(record, inference, runtime_case),
            "alertState": (runtime_alert or {}).get("state") or "",
            "case": runtime_case,
            "tasks": (runtime_case or {}).get("tasks", []),
            "timeline": (runtime_case or {}).get("timeline", []),
            "actionRuns": (runtime_case or {}).get("actionRuns", []),
            "availableActions": (runtime_case or {}).get("availableActions", []),
        }

    def run_sparql(self, query_string: str | None) -> dict[str, Any]:
        """执行 SPARQL 查询，兼容纯文本和 JSON body 两种输入格式。"""
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

    def load_data_file(self, file_path: Path) -> dict[str, Any]:
        """加载上传文件；CSV 触发全量重建，RDF 文件则直接解析入图。"""
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
        """返回当前所有运营 case。"""
        with self.lock:
            return [self._enrich_case_payload(item) for item in self.runtime.list_cases()]

    def get_case(self, case_id: str) -> dict[str, Any]:
        """返回单个运营 case。"""
        with self.lock:
            payload = self.runtime.get_case(case_id)
            if payload is None:
                return {"error": "case_not_found", "caseId": case_id}
            return self._enrich_case_payload(payload, include_detail=True)

    def list_tasks(self, status: str | None = None, assignee_role: str | None = None) -> list[dict[str, Any]]:
        """返回任务列表。"""
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
        """执行运营动作。"""
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
        """构建前端运营工作台所需的聚合视图。"""
        cases = [self._enrich_case_payload(item) for item in self.runtime.list_cases()]
        tasks = [self._enrich_task_payload(item) for item in self.runtime.list_tasks()]
        open_cases = [item for item in cases if item.get("state") != "CLOSED"]
        todo_tasks = [item for item in tasks if item.get("status") == "TODO"]

        priority_meta = {
            "P1": "立即处置",
            "P2": "当班跟进",
            "P3": "持续监控",
        }
        priority_bands = []
        for priority in ("P1", "P2", "P3"):
            band_cases = [item for item in open_cases if item.get("priority") == priority]
            priority_bands.append(
                {
                    "priority": priority,
                    "label": priority_meta[priority],
                    "caseCount": len(band_cases),
                    "openTaskCount": sum(int(item.get("openTaskCount") or 0) for item in band_cases),
                    "actionableCount": sum(1 for item in band_cases if item.get("availableActions")),
                }
            )

        queue_names = sorted({item.get("queue_name", "") for item in open_cases if item.get("queue_name")})
        queue_lanes = []
        for queue_name in queue_names:
            lane_cases = [item for item in open_cases if item.get("queue_name") == queue_name]
            lane_tasks = [item for item in todo_tasks if item.get("queue_name") == queue_name]
            queue_lanes.append(
                {
                    "queueName": queue_name,
                    "label": queue_name.replace("-", " ").title(),
                    "caseCount": len(lane_cases),
                    "taskCount": len(lane_tasks),
                    "highRiskCount": sum(1 for item in lane_cases if item.get("risk_level") == "HIGH"),
                    "owners": sorted({str(item.get("owner_role") or "") for item in lane_cases if item.get("owner_role")}),
                }
            )

        recent_actions = []
        for run in sorted(self.runtime.action_runs.values(), key=lambda item: item.updated_at, reverse=True)[:6]:
            display_name = self.records.get(run.entity_id, {}).get("displayName", run.entity_id)
            recent_actions.append(
                {
                    "id": run.id,
                    "caseId": run.case_id,
                    "entityId": run.entity_id,
                    "displayName": display_name,
                    "actionId": run.action_id,
                    "label": self.runtime.action_definitions.get(run.action_id).label
                    if run.action_id in self.runtime.action_definitions
                    else run.action_id,
                    "actorRole": run.actor_role,
                    "status": run.status,
                    "time": run.updated_at,
                }
            )

        return {
            "focusCases": open_cases[:6],
            "queueLanes": queue_lanes,
            "priorityBands": priority_bands,
            "recentActions": recent_actions,
        }

    def _enrich_case_payload(self, payload: dict[str, Any], include_detail: bool = False) -> dict[str, Any]:
        """补齐前端工作台所需的 case 展示字段。"""
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
        """补齐任务列表展示字段。"""
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
        """统计当前推理结果中的风险等级分布。"""
        distribution = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for item in self.inference.values():
            distribution[item["riskLevel"]] += 1
        return distribution

    def _extract_query(self, payload: str | None) -> str:
        """从请求体中提取查询语句。"""
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
        """生成详情页顶部的推理摘要卡片。"""
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
        """把高亮字段和命中规则整理成前端可直接展示的证据列表。"""
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
        """根据场景配置生成首页数据源卡片。"""
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

    def _overview_cluster_offsets(self) -> dict[str, tuple[float, float]]:
        """定义概览图中各关联节点相对主实体的布局偏移。"""
        return {
            "porting_query": (0.0, -78.0),
            "contract_info": (80.0, -34.0),
            "charge_info": (88.0, 42.0),
            "arrear_info": (0.0, 94.0),
            "customer_service": (-88.0, 42.0),
            "retention_action": (-80.0, -34.0),
            "voice_usage": (-96.0, 0.0),
        }

    def _add_overview_node(
        self,
        nodes_by_id: dict[str, dict[str, Any]],
        position_accumulators: dict[str, dict[str, float]],
        node_id: str,
        label: str,
        node_type: str,
        x: float,
        y: float,
    ) -> None:
        """向概览图累加节点及其平均坐标。"""
        nodes_by_id.setdefault(
            node_id,
            {
                "id": node_id,
                "label": label,
                "type": node_type,
            },
        )
        accumulator = position_accumulators.setdefault(node_id, {"x": 0.0, "y": 0.0, "count": 0.0})
        accumulator["x"] += x
        accumulator["y"] += y
        accumulator["count"] += 1.0

    def _overview_related_node_id(self, dataset_key: str, row: dict[str, Any]) -> str:
        """为概览图中的关联节点生成稳定 ID。"""
        label = str(row.get("_label") or self.scenario.datasets[dataset_key].entity_label)
        return f"overview:{self.scenario.datasets[dataset_key].node_type.lower()}:{quote(label, safe='')}"

    def _rows_match_relation(
        self,
        relation: RelationConfig,
        source_row: dict[str, Any],
        target_row: dict[str, Any],
    ) -> bool:
        """判断两条原始记录是否满足某条场景关系配置。"""
        source_field = self.scenario.datasets[relation.source_dataset].join_keys[relation.source_join_key]
        target_field = self.scenario.datasets[relation.target_dataset].join_keys[relation.target_join_key]
        source_value = source_row.get(source_field)
        target_value = target_row.get(target_field)
        if source_value in (None, "") or target_value in (None, ""):
            return False
        return str(source_value) == str(target_value)

    def _build_overview_graph(self) -> dict[str, Any]:
        """构建首页概览图，只抽样展示每个主实体的一组代表性关联节点。"""
        nodes_by_id: dict[str, dict[str, Any]] = {}
        position_accumulators: dict[str, dict[str, float]] = {}
        edges_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
        primary_items = list(self.records.values())
        if not primary_items:
            return {
                "nodes": [],
                "edges": [],
                "totalPrimaryEntities": 0,
                "totalInteractions": 0,
                "displayedPrimaryEntities": 0,
            }

        cols = max(4, math.ceil(math.sqrt(len(primary_items))))
        cluster_width = 260.0
        cluster_height = 220.0
        margin_x = 160.0
        margin_y = 150.0
        cluster_offsets = self._overview_cluster_offsets()

        for index, record in enumerate(primary_items):
            row = index // cols
            col = index % cols
            center_x = margin_x + col * cluster_width
            center_y = margin_y + row * cluster_height
            sampled_rows: dict[str, dict[str, Any]] = {
                self.scenario.primary_dataset: record["primary"],
            }
            sampled_node_ids: dict[str, str] = {}
            primary_node_id = record["nodeId"]
            sampled_node_ids[self.scenario.primary_dataset] = primary_node_id
            self._add_overview_node(
                nodes_by_id,
                position_accumulators,
                primary_node_id,
                record["displayName"],
                self.scenario.primary_node_type,
                center_x,
                center_y,
            )

            for dataset_key in self.scenario.graph_datasets:
                related_rows = record["related"].get(dataset_key, [])
                if not related_rows:
                    continue
                related = related_rows[0]
                sampled_rows[dataset_key] = related
                related_node_id = self._overview_related_node_id(dataset_key, related)
                sampled_node_ids[dataset_key] = related_node_id
                offset_x, offset_y = cluster_offsets.get(dataset_key, (0.0, 0.0))
                self._add_overview_node(
                    nodes_by_id,
                    position_accumulators,
                    related_node_id,
                    str(related.get("_label") or self.scenario.datasets[dataset_key].entity_label),
                    self.scenario.datasets[dataset_key].node_type,
                    center_x + offset_x,
                    center_y + offset_y,
                )

            for relation in self.scenario.relations:
                source_row = sampled_rows.get(relation.source_dataset)
                target_row = sampled_rows.get(relation.target_dataset)
                if source_row is None or target_row is None:
                    continue
                if not self._rows_match_relation(relation, source_row, target_row):
                    continue
                source_id = sampled_node_ids.get(relation.source_dataset)
                target_id = sampled_node_ids.get(relation.target_dataset)
                if source_id is None or target_id is None:
                    continue
                edges_by_key[(source_id, target_id, relation.label)] = {
                    "source": source_id,
                    "target": target_id,
                    "label": relation.label,
                }

        nodes = []
        for node_id, node in nodes_by_id.items():
            accumulator = position_accumulators[node_id]
            count = max(accumulator["count"], 1.0)
            nodes.append(
                {
                    **node,
                    "x": accumulator["x"] / count,
                    "y": accumulator["y"] / count,
                }
            )

        return {
            "nodes": nodes,
            "edges": list(edges_by_key.values()),
            "totalPrimaryEntities": len(self.records),
            "totalInteractions": sum(len(self.source_rows.get(key, [])) for key in self.scenario.interaction_datasets),
            "displayedPrimaryEntities": len(primary_items),
        }

    def _build_entity_graph(
        self,
        record: dict[str, Any],
        inference: dict[str, Any],
        runtime_case: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """构建单个实体的详情图谱。"""
        primary_node = {
            "id": record["nodeId"],
            "label": record["displayName"],
            "type": self.scenario.primary_node_type,
        }
        nodes = [primary_node]
        edges = []

        result_node = {
            "id": f"risk:{record['entityId']}",
            "label": f"{inference['riskLevel']} 风险",
            "type": "RiskResult",
        }
        action_node = {
            "id": f"action:{record['entityId']}",
            "label": inference["recommendedAction"],
            "type": "Action",
        }
        nodes.extend([result_node, action_node])
        edges.append({"source": primary_node["id"], "target": result_node["id"], "label": "推理输出"})
        edges.append({"source": result_node["id"], "target": action_node["id"], "label": "推荐动作"})

        for dataset_key in self.scenario.graph_datasets:
            for row in record["related"].get(dataset_key, [])[:2]:
                node_id = self._node_id(dataset_key, row)
                nodes.append(
                    {
                        "id": node_id,
                        "label": str(row.get("_label") or self.scenario.datasets[dataset_key].entity_label),
                        "type": self.scenario.datasets[dataset_key].node_type,
                    }
                )
                edges.append({"source": primary_node["id"], "target": node_id, "label": self._relation_label(self.scenario.primary_dataset, dataset_key)})

        for factor in inference["factors"]:
            node_id = f"factor:{factor.code}"
            nodes.append({"id": node_id, "label": factor.label, "type": "Inference"})
            edges.append({"source": primary_node["id"], "target": node_id, "label": "命中风险因子"})
            edges.append({"source": node_id, "target": result_node["id"], "label": "支撑结论"})

        for rule_label in inference["rules"]:
            node_id = f"rule:{rule_label.encode('utf-8').hex()}"
            nodes.append({"id": node_id, "label": rule_label, "type": "Inference"})
            edges.append({"source": primary_node["id"], "target": node_id, "label": "命中规则"})
            edges.append({"source": node_id, "target": result_node["id"], "label": "触发推理"})

        if runtime_case:
            case_node_id = f"case:{record['entityId']}"
            nodes.append(
                {
                    "id": case_node_id,
                    "label": f"{runtime_case['state']} Case",
                    "type": "Case",
                }
            )
            edges.append({"source": primary_node["id"], "target": case_node_id, "label": "运营处置"})

            for task in runtime_case.get("tasks", [])[:3]:
                task_node_id = f"task:{task['id']}"
                nodes.append(
                    {
                        "id": task_node_id,
                        "label": f"{task['title']} [{task['status']}]",
                        "type": "Task",
                    }
                )
                edges.append({"source": case_node_id, "target": task_node_id, "label": "任务"})

            for action in runtime_case.get("availableActions", [])[:3]:
                action_def_node_id = f"action-definition:{action['id']}"
                nodes.append(
                    {
                        "id": action_def_node_id,
                        "label": action["label"],
                        "type": "ActionDefinition",
                    }
                )
                edges.append({"source": case_node_id, "target": action_def_node_id, "label": "可执行动作"})

            for timeline_item in runtime_case.get("timeline", [])[:4]:
                event_node_id = f"timeline:{record['entityId']}:{quote(str(timeline_item['time']), safe='')}"
                nodes.append(
                    {
                        "id": event_node_id,
                        "label": timeline_item["title"],
                        "type": "Event",
                    }
                )
                edges.append({"source": case_node_id, "target": event_node_id, "label": "时间线"})

        return {"nodes": nodes, "edges": edges}

    def _render_display_fields(
        self,
        record: dict[str, Any],
        fields: tuple[AlertDisplayField, ...],
    ) -> list[dict[str, Any]]:
        """批量渲染展示字段。"""
        return [self._render_display_field(record, field) for field in fields]

    def _render_display_field(self, record: dict[str, Any], field: AlertDisplayField) -> dict[str, Any]:
        """根据字段来源规则提取展示值。"""
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
        """生成告警排序键，先按风险等级，再按场景配置事实值排序。"""
        key_parts: list[Any] = [-self._risk_weight(item["riskLevel"])]
        metrics = item["metrics"]
        for sort_field in self.scenario.alert_sort:
            raw = metrics.get(sort_field.fact)
            normalized = self._sortable_value(raw)
            key_parts.append(-normalized if sort_field.order == "desc" else normalized)
        key_parts.append(item["entityId"])
        return tuple(key_parts)

    def _risk_weight(self, level: str) -> int:
        """把文本风险等级转换成可排序权重。"""
        return {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(level, 0)

    def _sortable_value(self, value: Any) -> float:
        """把多种事实值归一为可排序的数字。"""
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

    def _evaluate_fact(
        self,
        fact: FactConfig,
        primary_row: dict[str, Any],
        related_rows: dict[str, list[dict[str, Any]]],
    ) -> Any:
        """根据聚合类型计算单个事实指标。"""
        rows = [primary_row] if fact.source_dataset == self.scenario.primary_dataset else related_rows.get(fact.source_dataset, [])
        candidates = [row for row in rows if not fact.where or self._row_matches(fact.where, row)]

        if fact.aggregate == "first":
            value = candidates[0].get(fact.field or "") if candidates else fact.default
            return self._apply_cast(value, fact.cast, fact.default)
        if fact.aggregate == "latest":
            if not candidates or not fact.field or not fact.order_by:
                return self._apply_cast(fact.default, fact.cast, fact.default)
            ordered = sorted(candidates, key=lambda row: self._order_key(row.get(fact.order_by)))
            return self._apply_cast(ordered[-1].get(fact.field), fact.cast, fact.default)
        if fact.aggregate == "exists":
            return bool(candidates)
        if fact.aggregate == "count":
            return len(candidates)
        if fact.aggregate == "sum":
            total = sum((self._coerce_scalar(row.get(fact.field or ""), fact.cast or "decimal") or Decimal("0")) for row in candidates)
            return total
        if fact.aggregate == "min_days_since":
            if not candidates or not fact.field:
                return fact.default
            days = [
                self._days_since(row.get(fact.field))
                for row in candidates
            ]
            values = [value for value in days if value is not None]
            return min(values) if values else fact.default
        raise ValueError(f"Unsupported fact aggregate: {fact.aggregate}")

    def _row_matches(self, condition: dict[str, Any], row: dict[str, Any]) -> bool:
        """评估单行数据是否满足 where 条件。"""
        if "all" in condition:
            return all(self._row_matches(item, row) for item in condition["all"])
        if "any" in condition:
            return any(self._row_matches(item, row) for item in condition["any"])
        if "not" in condition:
            return not self._row_matches(condition["not"], row)

        field = str(condition["field"])
        operator = str(condition["op"])
        expected = condition.get("value")
        actual = row.get(field)

        if operator == "within_days":
            days = self._days_since(actual)
            return days is not None and 0 <= days <= int(expected)
        if operator == "date_on_or_after":
            actual_date = self._parse_date_value(actual)
            if actual_date is None:
                return False
            expected_date = self.reference_date if expected == "today" else date.fromisoformat(str(expected))
            return actual_date >= expected_date
        if operator == "not_empty":
            return actual not in (None, "")

        return self._compare(actual, operator, expected)

    def _compare(self, actual: Any, operator: str, expected: Any) -> bool:
        """在基础 Python 类型上执行统一比较。"""
        if isinstance(actual, bool):
            actual_value = actual
            expected_value = self._coerce_scalar(expected, "bool")
        elif isinstance(actual, Decimal):
            actual_value = actual
            expected_value = self._coerce_scalar(expected, "decimal")
        elif isinstance(actual, int):
            actual_value = actual
            expected_value = self._coerce_scalar(expected, "int")
        else:
            actual_value = "" if actual is None else actual
            expected_value = expected

        if operator == ">":
            return actual_value > expected_value
        if operator == ">=":
            return actual_value >= expected_value
        if operator == "<":
            return actual_value < expected_value
        if operator == "<=":
            return actual_value <= expected_value
        if operator == "==":
            return actual_value == expected_value
        if operator == "!=":
            return actual_value != expected_value
        if operator == "in":
            return actual_value in expected_value
        if operator == "not in":
            return actual_value not in expected_value
        raise ValueError(f"Unsupported row operator: {operator}")

    def _days_since(self, value: Any) -> int | None:
        """计算给定日期距参考日的天数差。"""
        parsed = self._parse_date_value(value)
        if parsed is None:
            return None
        return (self.reference_date - parsed).days

    def _parse_date_value(self, value: Any) -> date | None:
        """尽量把输入解析为日期对象，兼容 ISO 日期和时间戳字符串。"""
        if value in (None, ""):
            return None
        text = str(value).strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        except ValueError:
            pass
        try:
            return date.fromisoformat(text)
        except ValueError:
            return None

    def _apply_cast(self, value: Any, cast: str | None, default: Any) -> Any:
        """按事实定义的 cast 规则转换值，并处理空值默认值。"""
        if value in (None, ""):
            return default
        if not cast:
            return value
        converted = self._coerce_scalar(value, cast)
        return default if converted is None else converted

    def _coerce_scalar(self, value: Any, value_type: str) -> Any:
        """把字符串或原始值转换为规则/映射要求的标量类型。"""
        if value in (None, ""):
            return None
        if isinstance(value, (int, float, Decimal, bool)) and value_type.lower() not in {"string", "str"}:
            if value_type.lower() in {"bool", "boolean"}:
                return bool(value)
            return value

        text = str(value).strip()
        lowered = value_type.lower()
        if lowered in {"int", "integer"}:
            return int(text)
        if lowered == "decimal":
            return Decimal(text)
        if lowered in {"float", "double"}:
            return float(text)
        if lowered in {"bool", "boolean"}:
            return text.lower() in {"1", "true", "yes", "y"}
        return text

    def _json_ready_value(self, value: Any) -> Any:
        """把不能直接 JSON 序列化的值转换为前端友好格式。"""
        if isinstance(value, Decimal):
            return float(value)
        return value

    def _serialize_metrics(self, metrics: dict[str, Any]) -> dict[str, Any]:
        """序列化事实指标字典。"""
        return {key: self._json_ready_value(value) for key, value in metrics.items()}

    def _serialize_row(self, row: dict[str, Any]) -> dict[str, Any]:
        """剔除内部辅助字段后输出原始行数据。"""
        payload: dict[str, Any] = {}
        for key, value in row.items():
            if key.startswith("_"):
                continue
            payload[key] = self._json_ready_value(value)
        return payload

    def _order_key(self, value: Any) -> Any:
        """为 latest 聚合生成统一排序键。"""
        parsed_date = self._parse_date_value(value)
        if parsed_date is not None:
            return parsed_date.toordinal()
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (int, float)):
            return value
        return "" if value is None else str(value)

    def _target_type_for_dataset(self, dataset_key: str) -> str:
        """从映射表中推断某个数据集对应的目标类型。"""
        rows = self.mapping_by_dataset.get(dataset_key, [])
        if not rows:
            raise ValueError(f"No mapping rows configured for dataset: {dataset_key}")
        return rows[0].target_type

    def _entity_uri(self, dataset_key: str, row: dict[str, Any], index: int) -> URIRef:
        """为原始行构造稳定的实体 URI。"""
        dataset_config = self.scenario.datasets[dataset_key]
        parts = []
        for field_name in dataset_config.id_fields:
            value = row.get(field_name)
            if value not in (None, ""):
                parts.append(quote(str(value), safe=""))
        if not parts:
            parts.append(f"row-{index + 1}")
        dataset_segment = dataset_key.replace("_", "-")
        return URIRef(f"{self.settings.data_ns}{dataset_segment}/{'/'.join(parts)}")

    def _entity_label(self, dataset_key: str, row: dict[str, Any]) -> str:
        """为实体生成展示标签，优先模板，再退回单字段或序号。"""
        dataset_config = self.scenario.datasets[dataset_key]
        if dataset_config.label_template:
            values = {key: "" if value is None else str(value) for key, value in row.items()}
            return dataset_config.label_template.format(**values)
        if dataset_config.label_field:
            value = row.get(dataset_config.label_field)
            if value not in (None, ""):
                return str(value)
        return f"{dataset_config.entity_label}-{int(row['_row_index']) + 1}"

    def _resolve_curie(self, curie: str) -> URIRef:
        """把 CURIE 形式的谓词或类型解析为完整 URI。"""
        namespace, local = curie.split(":", 1)
        if namespace == "rdf":
            return URIRef(str(RDF[local]))
        if namespace == "rdfs":
            return URIRef(str(RDFS[local]))
        return URIRef(str(make_namespaces(self.settings)[namespace][local]))

    def _literal_for_value(self, value: Any, value_type: str) -> Literal:
        """按映射值类型构造 RDF Literal。"""
        lowered = value_type.lower()
        if lowered in {"int", "integer"}:
            return Literal(int(value), datatype=XSD.integer)
        if lowered == "decimal":
            return Literal(Decimal(str(value)), datatype=XSD.decimal)
        if lowered in {"bool", "boolean"}:
            return Literal(bool(value), datatype=XSD.boolean)
        return Literal(value)

    def _relation_id(
        self,
        source_dataset: str,
        source_row: dict[str, Any],
        target_dataset: str,
        target_row: dict[str, Any],
    ) -> str:
        """为关系节点构造稳定 ID。"""
        source_bits = [source_dataset, str(source_row["_row_index"])]
        target_bits = [target_dataset, str(target_row["_row_index"])]
        return "-".join(source_bits + target_bits)

    def _node_id(self, dataset_key: str, row: dict[str, Any]) -> str:
        """为前端图谱节点生成稳定标识。"""
        dataset_config = self.scenario.datasets[dataset_key]
        identifiers = [str(row.get(field)) for field in dataset_config.id_fields if row.get(field) not in (None, "")]
        if not identifiers:
            identifiers = [str(row.get("_row_index"))]
        return f"{dataset_config.node_type.lower()}:{'|'.join(identifiers)}"

    def _relation_label(self, source_dataset: str, target_dataset: str) -> str:
        """根据场景配置查找两个数据集之间的默认关系文案。"""
        for relation in self.scenario.relations:
            if relation.source_dataset == source_dataset and relation.target_dataset == target_dataset:
                return relation.label
        return "关联"
