from __future__ import annotations

import json
import threading
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from rdflib import BNode, Dataset, Graph, Literal, RDF, RDFS, URIRef, XSD

from app.config.settings import Settings
from app.etl.csv_loader import read_csv_rows
from app.graph.repository import GraphRepository
from app.ontology.namespaces import bind_prefixes, make_namespaces
from app.rules.engine import canonical_action, materialize_business_inference
from app.validation.shacl import run_shacl_validation

try:
    from owlrl import DeductiveClosure, OWLRL_Semantics
except ImportError:  # pragma: no cover
    DeductiveClosure = None
    OWLRL_Semantics = None


class SemanticService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.repository = GraphRepository(settings)
        self.lock = threading.RLock()
        self.batch_id = datetime.now(tz=UTC).strftime("%Y%m%d%H%M%S")
        self.dataset: Dataset | None = None
        self.base_graph: Graph | None = None
        self.deductions_graph: Graph | None = None
        self.records: dict[str, dict[str, Any]] = {}
        self.inference: dict[str, dict[str, Any]] = {}
        self.top_rules: dict[str, int] = {}
        self.validation: dict[str, object] = {}
        self.persistence: dict[str, object] = {}
        self.initialize()

    def initialize(self) -> None:
        with self.lock:
            self.batch_id = datetime.now(tz=UTC).strftime("%Y%m%d%H%M%S")
            self.dataset = Dataset()
            self.base_graph = self.dataset.graph(URIRef(self.settings.base_graph_uri))
            self.deductions_graph = self.dataset.graph(URIRef(self.settings.deductions_graph_uri))
            bind_prefixes(self.base_graph, self.settings)
            bind_prefixes(self.deductions_graph, self.settings)

            self._load_schema(self.base_graph)
            self.records = self._load_records()
            self._materialize_base_graph()
            self.validation = run_shacl_validation(
                self.base_graph,
                self.settings.ontology_dir / "telecom-shapes.ttl",
                self.settings.reports_dir / "validation-report.ttl",
            )
            self.run_inference(persist=False)
            self.persistence = self.repository.persist(self.dataset)

    def _load_schema(self, graph: Graph) -> None:
        for name in ("doim-core.ttl", "telecom-porting.ttl"):
            graph.parse(self.settings.ontology_dir / name, format="turtle")

    def _load_records(self) -> dict[str, dict[str, Any]]:
        subscribers = read_csv_rows(self.settings.data_dir / "subscribers.csv")
        usage_rows = {
            row["subscriber_id"]: row
            for row in read_csv_rows(self.settings.data_dir / "usage_signals.csv")
        }
        commercial_rows = {
            row["subscriber_id"]: row
            for row in read_csv_rows(self.settings.data_dir / "commercial_signals.csv")
        }
        event_rows = defaultdict(list)
        for row in read_csv_rows(self.settings.data_dir / "interaction_events.csv"):
            event_rows[row["subscriber_id"]].append(
                {
                    "eventId": row["event_id"],
                    "eventType": row["event_type"],
                    "channel": row["channel"],
                    "daysAgo": int(row["days_ago"]),
                    "severity": row["severity"],
                    "detail": row["detail"],
                }
            )

        records: dict[str, dict[str, Any]] = {}
        for row in subscribers:
            subscriber_id = row["subscriber_id"]
            usage = usage_rows[subscriber_id]
            commercial = commercial_rows[subscriber_id]
            records[subscriber_id] = {
                "subscriberId": subscriber_id,
                "name": row["customer_name"],
                "msisdn": row["msisdn"],
                "segment": row["segment"],
                "city": row["city"],
                "planName": row["plan_name"],
                "metrics": {
                    "tenureMonths": int(row["tenure_months"]),
                    "monthlyFee": Decimal(row["monthly_fee"]),
                    "vipFlag": int(row["vip_flag"]),
                    "dataUsageDropPct": int(usage["data_usage_drop_pct"]),
                    "voiceUsageDropPct": int(usage["voice_usage_drop_pct"]),
                    "complaintCount30d": int(usage["complaint_count_30d"]),
                    "networkIssueCount30d": int(usage["network_issue_count_30d"]),
                    "npsScore": int(usage["nps_score"]),
                    "serviceTicketCount30d": int(usage["service_ticket_count_30d"]),
                    "contractRemainingDays": int(commercial["contract_remaining_days"]),
                    "overdueDays": int(commercial["overdue_days"]),
                    "competitorContactCount30d": int(commercial["competitor_contact_count_30d"]),
                    "portingCodeRequestCount30d": int(commercial["porting_code_request_count_30d"]),
                    "retentionOfferRejected": int(commercial["retention_offer_rejected"]),
                    "paymentRiskLevel": commercial["payment_risk_level"],
                },
                "events": sorted(event_rows.get(subscriber_id, []), key=lambda item: item["daysAgo"]),
            }
        return records

    def _materialize_base_graph(self) -> None:
        graph = self.base_graph
        assert graph is not None
        namespaces = make_namespaces(self.settings)
        doim = namespaces["doim"]
        telecom = namespaces["telecom"]

        for record in self.records.values():
            subscriber = URIRef(f"{self.settings.data_ns}subscriber/{record['subscriberId']}")
            number = URIRef(f"{self.settings.data_ns}number/{record['msisdn']}")

            self._tag_entity(graph, subscriber, "CRM")
            graph.add((subscriber, RDF.type, telecom.Subscriber))
            graph.add((subscriber, telecom.subscriberId, Literal(record["subscriberId"])))
            graph.add((subscriber, RDFS.label, Literal(record["name"])))
            graph.add((subscriber, telecom.city, Literal(record["city"])))
            graph.add((subscriber, telecom.segmentName, Literal(record["segment"])))
            graph.add((subscriber, telecom.planName, Literal(record["planName"])))

            metrics = record["metrics"]
            self._add_int(graph, subscriber, telecom.tenureMonths, metrics["tenureMonths"])
            graph.add((subscriber, telecom.monthlyFee, Literal(metrics["monthlyFee"], datatype=XSD.decimal)))
            self._add_int(graph, subscriber, telecom.vipFlag, metrics["vipFlag"])
            self._add_int(graph, subscriber, telecom.dataUsageDropPct, metrics["dataUsageDropPct"])
            self._add_int(graph, subscriber, telecom.voiceUsageDropPct, metrics["voiceUsageDropPct"])
            self._add_int(graph, subscriber, telecom.complaintCount30d, metrics["complaintCount30d"])
            self._add_int(graph, subscriber, telecom.networkIssueCount30d, metrics["networkIssueCount30d"])
            self._add_int(graph, subscriber, telecom.npsScore, metrics["npsScore"])
            self._add_int(graph, subscriber, telecom.serviceTicketCount30d, metrics["serviceTicketCount30d"])
            self._add_int(graph, subscriber, telecom.contractRemainingDays, metrics["contractRemainingDays"])
            self._add_int(graph, subscriber, telecom.overdueDays, metrics["overdueDays"])
            self._add_int(graph, subscriber, telecom.competitorContactCount30d, metrics["competitorContactCount30d"])
            self._add_int(graph, subscriber, telecom.portingCodeRequestCount30d, metrics["portingCodeRequestCount30d"])
            self._add_int(graph, subscriber, telecom.retentionOfferRejected, metrics["retentionOfferRejected"])
            graph.add((subscriber, telecom.paymentRiskLevel, Literal(metrics["paymentRiskLevel"])))

            self._tag_entity(graph, number, "CRM")
            graph.add((number, RDF.type, telecom.MobileNumber))
            graph.add((number, RDFS.label, Literal(record["msisdn"])))
            graph.add((number, doim.identifierValue, Literal(record["msisdn"])))

            self._add_relation(subscriber, doim.hasIdentifier, number, f"{record['subscriberId']}-identifier", "关联标识符", "CRM")
            self._add_relation(subscriber, telecom.ownsNumber, number, f"{record['subscriberId']}-number", "拥有号码", "CRM")

            usage_snapshot = URIRef(f"{self.settings.data_ns}usage/{record['subscriberId']}")
            self._tag_entity(graph, usage_snapshot, "NETWORK")
            graph.add((usage_snapshot, RDF.type, telecom.UsageSnapshot))
            graph.add((usage_snapshot, RDFS.label, Literal(f"{record['subscriberId']} 使用快照")))
            self._add_int(graph, usage_snapshot, telecom.dataUsageDropPct, metrics["dataUsageDropPct"])
            self._add_int(graph, usage_snapshot, telecom.voiceUsageDropPct, metrics["voiceUsageDropPct"])
            self._add_int(graph, usage_snapshot, telecom.complaintCount30d, metrics["complaintCount30d"])
            self._add_int(graph, usage_snapshot, telecom.networkIssueCount30d, metrics["networkIssueCount30d"])
            self._add_int(graph, usage_snapshot, telecom.npsScore, metrics["npsScore"])
            self._add_int(graph, usage_snapshot, telecom.serviceTicketCount30d, metrics["serviceTicketCount30d"])
            self._add_relation(subscriber, telecom.hasUsageSnapshot, usage_snapshot, f"{record['subscriberId']}-usage", "关联使用快照", "NETWORK")

            commercial_snapshot = URIRef(f"{self.settings.data_ns}commercial/{record['subscriberId']}")
            self._tag_entity(graph, commercial_snapshot, "BILLING")
            graph.add((commercial_snapshot, RDF.type, telecom.CommercialSnapshot))
            graph.add((commercial_snapshot, RDFS.label, Literal(f"{record['subscriberId']} 商业快照")))
            self._add_int(graph, commercial_snapshot, telecom.contractRemainingDays, metrics["contractRemainingDays"])
            self._add_int(graph, commercial_snapshot, telecom.overdueDays, metrics["overdueDays"])
            self._add_int(graph, commercial_snapshot, telecom.competitorContactCount30d, metrics["competitorContactCount30d"])
            self._add_int(graph, commercial_snapshot, telecom.portingCodeRequestCount30d, metrics["portingCodeRequestCount30d"])
            self._add_int(graph, commercial_snapshot, telecom.retentionOfferRejected, metrics["retentionOfferRejected"])
            graph.add((commercial_snapshot, telecom.paymentRiskLevel, Literal(metrics["paymentRiskLevel"])))
            self._add_relation(
                subscriber,
                telecom.hasCommercialSnapshot,
                commercial_snapshot,
                f"{record['subscriberId']}-commercial",
                "关联商业快照",
                "BILLING",
            )

            for event in record["events"]:
                event_resource = URIRef(f"{self.settings.data_ns}event/{event['eventId']}")
                self._tag_entity(graph, event_resource, "OMNI_CHANNEL")
                graph.add((event_resource, RDF.type, telecom.ChannelInteraction))
                graph.add((event_resource, RDFS.label, Literal(event["eventType"])))
                graph.add((event_resource, telecom.eventId, Literal(event["eventId"])))
                graph.add((event_resource, telecom.eventType, Literal(event["eventType"])))
                graph.add((event_resource, telecom.channelName, Literal(event["channel"])))
                self._add_int(graph, event_resource, telecom.eventDaysAgo, event["daysAgo"])
                graph.add((event_resource, telecom.eventSeverity, Literal(event["severity"])))
                graph.add((event_resource, telecom.eventDetail, Literal(event["detail"])))
                self._add_relation(
                    subscriber,
                    telecom.hasInteraction,
                    event_resource,
                    f"{record['subscriberId']}-event-{event['eventId']}",
                    "发生交互事件",
                    "OMNI_CHANNEL",
                )

    def _add_int(self, graph: Graph, subject: URIRef, predicate: URIRef, value: int) -> None:
        graph.add((subject, predicate, Literal(value, datatype=XSD.integer)))

    def _tag_entity(self, graph: Graph, resource: URIRef, source_system: str) -> None:
        namespaces = make_namespaces(self.settings)
        doim = namespaces["doim"]
        graph.add((resource, doim.sourceSystem, Literal(source_system)))
        graph.add((resource, doim.loadBatch, Literal(self.batch_id)))

    def _add_relation(
        self,
        source: URIRef,
        predicate: URIRef,
        target: URIRef,
        relation_id: str,
        label: str,
        source_system: str,
    ) -> None:
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

    def _apply_owlrl(self) -> int:
        if DeductiveClosure is None or OWLRL_Semantics is None:
            return 0
        assert self.base_graph is not None
        assert self.deductions_graph is not None
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
        with self.lock:
            assert self.deductions_graph is not None
            self.deductions_graph.remove((None, None, None))
            owlrl_triples = self._apply_owlrl()
            inferred, top_rules = materialize_business_inference(self.deductions_graph, self.records, self.settings)
            self.inference = inferred
            self.top_rules = dict(top_rules)
            if persist and self.dataset is not None:
                self.persistence = self.repository.persist(self.dataset)
            return {
                "deductionTriples": len(self.deductions_graph),
                "owlrlTriples": owlrl_triples,
                "riskDistribution": self._risk_distribution(),
            }

    def get_summary(self) -> dict[str, Any]:
        with self.lock:
            union = self._union_graph()
            return {
                "scenario": "运营商携号转网预警",
                "tripleCount": len(union),
                "subscriberCount": len(self.records),
                "interactionCount": sum(len(record["events"]) for record in self.records.values()),
                "relationCount": sum(
                    1
                    for _ in self.base_graph.subjects(RDF.type, URIRef(f"{self.settings.doim_ns}Relation"))
                ),
                "riskDistribution": self._risk_distribution(),
                "topRules": [
                    {"rule": label, "count": count}
                    for label, count in sorted(self.top_rules.items(), key=lambda item: (-item[1], item[0]))
                ],
                "sampleQuery": self.settings.default_query,
                "ontologyGraph": self._build_overview_graph(),
                "architecture": [
                    {
                        "title": "数据接入层",
                        "subtitle": "CSV/多源信号",
                        "items": ["CRM 客户主数据", "NETWORK 使用信号", "BILLING 商业信号", "OMNI_CHANNEL 交互事件"],
                    },
                    {
                        "title": "语义层",
                        "subtitle": "DOIM + 领域本体",
                        "items": ["Entity / Identifier / Relation", "Subscriber / Snapshot / Event", "RiskFactor / Rule / Alert"],
                    },
                    {
                        "title": "存储与推理",
                        "subtitle": "RDFLib + pyoxigraph + pySHACL",
                        "items": ["三元组构建", "命名图持久化", "OWL-RL + 业务规则推理"],
                    },
                    {
                        "title": "应用层",
                        "subtitle": "FastAPI + React",
                        "items": ["告警列表", "客户画像", "知识关系图", "规则命中解释"],
                    },
                ],
                "validation": self.validation,
                "persistence": self.persistence,
            }

    def get_alerts(self) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []
        for record in self.records.values():
            subscriber_id = record["subscriberId"]
            inference = self.inference[subscriber_id]
            metrics = record["metrics"]
            alerts.append(
                {
                    "subscriberId": subscriber_id,
                    "name": record["name"],
                    "city": record["city"],
                    "segment": record["segment"],
                    "planName": record["planName"],
                    "msisdn": record["msisdn"],
                    "riskLevel": inference["riskLevel"],
                    "recommendedAction": inference["recommendedAction"],
                    "factors": [factor.label for factor in inference["factors"]],
                    "metrics": {
                        "dataUsageDropPct": metrics["dataUsageDropPct"],
                        "complaintCount30d": metrics["complaintCount30d"],
                        "competitorContactCount30d": metrics["competitorContactCount30d"],
                        "portingCodeRequestCount30d": metrics["portingCodeRequestCount30d"],
                        "contractRemainingDays": metrics["contractRemainingDays"],
                        "vipFlag": metrics["vipFlag"],
                    },
                    "complaint": metrics["complaintCount30d"],
                    "competitor": metrics["competitorContactCount30d"],
                    "porting": metrics["portingCodeRequestCount30d"],
                    "plan": record["planName"],
                }
            )
        alerts.sort(
            key=lambda item: (
                -self._risk_weight(item["riskLevel"]),
                -item["metrics"]["portingCodeRequestCount30d"],
                -item["metrics"]["competitorContactCount30d"],
                -item["metrics"]["complaintCount30d"],
                item["subscriberId"],
            )
        )
        return alerts

    def search_subscribers(self, query: str) -> list[dict[str, Any]]:
        keyword = (query or "").strip().lower()
        alerts = self.get_alerts()
        risk_terms = {"风险", "risk", "携转", "携号转网", "转网", "流失", "告警"}
        if any(term in keyword for term in risk_terms):
            matches = alerts
        else:
            matches = []
            for item in alerts:
                haystacks = [item["subscriberId"], item["name"], item["msisdn"]]
                if not keyword or any(keyword in str(value).lower() for value in haystacks):
                    matches.append(item)
        return [
            {
                "subscriberId": item["subscriberId"],
                "name": item["name"],
                "msisdn": item["msisdn"],
                "city": item["city"],
                "segment": item["segment"],
                "planName": item["planName"],
                "riskLevel": item["riskLevel"],
                "recommendedAction": item["recommendedAction"],
                "factors": item["factors"],
            }
            for item in matches
        ]

    def get_subscriber(self, subscriber_id: str) -> dict[str, Any]:
        subscriber_id = subscriber_id.strip()
        if subscriber_id not in self.records:
            return {"error": "subscriber_not_found", "subscriberId": subscriber_id}
        record = self.records[subscriber_id]
        inference = self.inference[subscriber_id]
        metrics = record["metrics"]
        return {
            "subscriberId": subscriber_id,
            "name": record["name"],
            "city": record["city"],
            "segment": record["segment"],
            "planName": record["planName"],
            "msisdn": record["msisdn"],
            "riskLevel": inference["riskLevel"],
            "recommendedAction": inference["recommendedAction"],
            "metrics": {
                key: (float(value) if isinstance(value, Decimal) else value)
                for key, value in metrics.items()
            },
            "factors": [factor.label for factor in inference["factors"]],
            "rules": inference["rules"],
            "events": record["events"],
            "inference": self._build_inference_summary(record["name"], inference, len(record["events"])),
            "evidence": self._build_evidence(record, inference),
            "graph": self._build_subscriber_graph(record, inference),
        }

    def run_sparql(self, query_string: str | None) -> dict[str, Any]:
        query = self._extract_query(query_string) or self.settings.default_query
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
        with self.lock:
            assert self.base_graph is not None
            self.base_graph.parse(file_path)
            if self.dataset is not None:
                self.persistence = self.repository.persist(self.dataset)
            return {
                "success": True,
                "file": file_path.name,
                "triples": len(self.base_graph),
            }

    def _risk_distribution(self) -> dict[str, int]:
        distribution = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for item in self.inference.values():
            distribution[item["riskLevel"]] += 1
        return distribution

    def _risk_weight(self, level: str) -> int:
        return {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(level, 0)

    def _extract_query(self, payload: str | None) -> str:
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

    def _build_inference_summary(self, name: str, inference: dict[str, Any], event_count: int) -> dict[str, Any]:
        risk_level = inference["riskLevel"]
        summary = {
            "headline": f"{name} 被推理为 {risk_level} 风险",
            "riskLevel": risk_level,
            "recommendedAction": inference["recommendedAction"],
            "factorCount": len(inference["factors"]),
            "ruleCount": len(inference["rules"]),
            "eventCount": event_count,
        }
        if risk_level == "HIGH":
            summary["summary"] = "命中高风险组合规则，建议立即进入人工挽留流程。"
        elif risk_level == "MEDIUM":
            summary["summary"] = "命中中风险组合规则，建议触发优惠触达并人工复核。"
        else:
            summary["summary"] = "未命中中高风险组合规则，维持常规关怀策略。"
        return summary

    def _build_evidence(self, record: dict[str, Any], inference: dict[str, Any]) -> list[dict[str, Any]]:
        metrics = record["metrics"]
        events = record["events"]
        evidence: list[dict[str, Any]] = []
        if metrics["complaintCount30d"] > 2:
            evidence.append(
                self._evidence_item(
                    "signal",
                    "投诉激增规则",
                    "投诉次数超过阈值，命中“投诉激增”风险因子。",
                    [
                        f"近30天投诉次数 = {metrics['complaintCount30d']}，阈值 > 2",
                        *self._related_event_facts(events, {"complaint"}),
                    ],
                    "投诉激增",
                )
            )
        if metrics["dataUsageDropPct"] > 30:
            evidence.append(
                self._evidence_item(
                    "signal",
                    "流量下滑规则",
                    "使用量明显下滑，命中“流量下滑”风险因子。",
                    [
                        f"近30天流量下降比例 = {metrics['dataUsageDropPct']}%，阈值 > 30%",
                        f"语音下降比例 = {metrics['voiceUsageDropPct']}%",
                    ],
                    "流量下滑",
                )
            )
        if metrics["competitorContactCount30d"] > 0:
            evidence.append(
                self._evidence_item(
                    "signal",
                    "竞对接触规则",
                    "出现竞对接触行为，命中“竞对接触”风险因子。",
                    [
                        f"近30天竞对接触次数 = {metrics['competitorContactCount30d']}，阈值 > 0",
                        *self._related_event_facts(events, {"competitor_visit"}),
                    ],
                    "竞对接触",
                )
            )
        if metrics["portingCodeRequestCount30d"] > 0:
            evidence.append(
                self._evidence_item(
                    "signal",
                    "携转意图规则",
                    "出现携转码申请行为，命中“携转意图明确”风险因子。",
                    [
                        f"近30天携转授权码申请次数 = {metrics['portingCodeRequestCount30d']}，阈值 > 0",
                        *self._related_event_facts(events, {"porting_code_request"}),
                    ],
                    "携转意图明确",
                )
            )
        evidence.append(
            {
                "category": "decision",
                "title": f"{inference['riskLevel']} 风险判定",
                "summary": f"根据命中规则数 {len(inference['rules'])} 与风险因子数 {len(inference['factors'])} 生成最终风险等级。",
                "riskLevel": inference["riskLevel"],
                "facts": [f"命中规则：{label}" for label in inference["rules"]],
            }
        )
        return evidence

    def _evidence_item(
        self,
        category: str,
        title: str,
        summary: str,
        facts: list[str],
        factor: str,
    ) -> dict[str, Any]:
        return {
            "category": category,
            "title": title,
            "summary": summary,
            "factor": factor,
            "facts": facts,
        }

    def _related_event_facts(self, events: list[dict[str, Any]], event_types: set[str]) -> list[str]:
        facts: list[str] = []
        for event in events:
            if event["eventType"] in event_types:
                facts.append(f"{event['daysAgo']} 天前 · {event['channel']} · {event['detail']}")
        return facts[:2]

    def _build_overview_graph(self) -> dict[str, Any]:
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        subscriber_items = list(self.records.values())[:20]
        event_count = 0
        cols = 5
        for index, record in enumerate(subscriber_items):
            row = index // cols
            col = index % cols
            x = 0.12 + col * 0.16
            y = 0.16 + row * 0.18
            subscriber_node_id = f"subscriber:{record['subscriberId']}"
            nodes.append({"id": subscriber_node_id, "label": record["name"], "type": "Subscriber", "x": x, "y": y})
            for event in record["events"][:2]:
                event_count += 1
                event_node_id = f"event:{event['eventId']}"
                nodes.append(
                    {
                        "id": event_node_id,
                        "label": event["eventType"],
                        "type": "Interaction",
                        "x": min(x + 0.06, 0.95),
                        "y": min(y + 0.08 + event_count * 0.002, 0.92),
                    }
                )
                edges.append({"source": subscriber_node_id, "target": event_node_id, "label": "发生交互"})
            result_node_id = f"result:{record['subscriberId']}"
            nodes.append(
                {
                    "id": result_node_id,
                    "label": self.inference[record["subscriberId"]]["riskLevel"],
                    "type": "Result",
                    "x": min(x + 0.1, 0.96),
                    "y": max(y - 0.06, 0.08),
                }
            )
            edges.append({"source": subscriber_node_id, "target": result_node_id, "label": "推理输出"})
        return {
            "nodes": nodes,
            "edges": edges,
            "totalSubscribers": len(self.records),
            "totalInteractions": sum(len(item["events"]) for item in self.records.values()),
        }

    def _build_subscriber_graph(self, record: dict[str, Any], inference: dict[str, Any]) -> dict[str, Any]:
        subscriber_id = record["subscriberId"]
        subscriber_node = {"id": f"subscriber:{subscriber_id}", "label": record["name"], "type": "Subscriber"}
        nodes = [subscriber_node]
        edges = []

        result_node = {"id": f"result:{subscriber_id}", "label": f"{inference['riskLevel']} 风险", "type": "Result"}
        action_node = {"id": f"action:{subscriber_id}", "label": inference["recommendedAction"], "type": "Action"}
        nodes.extend([result_node, action_node])
        edges.append({"source": subscriber_node["id"], "target": result_node["id"], "label": "推理输出"})
        edges.append({"source": result_node["id"], "target": action_node["id"], "label": "推荐动作"})

        number_node = {"id": f"number:{record['msisdn']}", "label": record["msisdn"], "type": "Entity"}
        nodes.append(number_node)
        edges.append({"source": subscriber_node["id"], "target": number_node["id"], "label": "拥有号码"})

        for factor in inference["factors"]:
            node = {"id": f"factor:{factor.code}", "label": factor.label, "type": "Inference"}
            nodes.append(node)
            edges.append({"source": subscriber_node["id"], "target": node["id"], "label": "命中风险因子"})
            edges.append({"source": node["id"], "target": result_node["id"], "label": "支撑结论"})

        for rule_label in inference["rules"]:
            node_id = rule_label.encode("utf-8").hex()
            node = {"id": f"rule:{node_id}", "label": rule_label, "type": "Inference"}
            nodes.append(node)
            edges.append({"source": subscriber_node["id"], "target": node["id"], "label": "命中规则"})
            edges.append({"source": node["id"], "target": result_node["id"], "label": "触发推理"})

        for event in record["events"][:5]:
            node = {"id": f"event:{event['eventId']}", "label": event["eventType"], "type": "Interaction"}
            nodes.append(node)
            edges.append({"source": subscriber_node["id"], "target": node["id"], "label": "发生交互"})

        return {"nodes": nodes, "edges": edges}
