from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from rdflib import Graph, Literal, RDF, RDFS, URIRef, XSD

from app.config.settings import Settings
from app.ontology.namespaces import make_namespaces


@dataclass(frozen=True)
class RiskFactorDef:
    code: str
    label: str
    rule_label: str


FACTOR_DEFS = {
    "complaint_spike": RiskFactorDef("complaint_spike", "投诉激增", "投诉激增规则"),
    "data_drop": RiskFactorDef("data_drop", "流量下滑", "流量下滑规则"),
    "competitor_contact": RiskFactorDef("competitor_contact", "竞对接触", "竞对接触规则"),
    "contract_expiring": RiskFactorDef("contract_expiring", "合约即将到期", "合约到期规则"),
    "porting_intent": RiskFactorDef("porting_intent", "携转意图明确", "携转意图规则"),
    "payment_pressure": RiskFactorDef("payment_pressure", "支付压力", "支付压力规则"),
    "retention_reject": RiskFactorDef("retention_reject", "挽留拒绝", "挽留拒绝规则"),
}

DECISION_RULES = {
    "HIGH": "高风险组合规则",
    "MEDIUM": "中风险组合规则",
    "LOW": "低风险默认规则",
}


def canonical_action(risk_level: str) -> str:
    if risk_level == "HIGH":
        return "48小时内外呼挽留+定向权益补贴"
    if risk_level == "MEDIUM":
        return "短信/APP 定向优惠+人工复核"
    return "常规关怀与权益提醒"


def infer_record(record: dict[str, Any]) -> dict[str, Any]:
    metrics = record["metrics"]
    factors: list[RiskFactorDef] = []
    rule_labels: list[str] = []

    if metrics["complaintCount30d"] > 2:
        factors.append(FACTOR_DEFS["complaint_spike"])
        rule_labels.append(FACTOR_DEFS["complaint_spike"].rule_label)
    if metrics["dataUsageDropPct"] > 30:
        factors.append(FACTOR_DEFS["data_drop"])
        rule_labels.append(FACTOR_DEFS["data_drop"].rule_label)
    if metrics["competitorContactCount30d"] > 0:
        factors.append(FACTOR_DEFS["competitor_contact"])
        rule_labels.append(FACTOR_DEFS["competitor_contact"].rule_label)
    if metrics["contractRemainingDays"] < 45:
        factors.append(FACTOR_DEFS["contract_expiring"])
        rule_labels.append(FACTOR_DEFS["contract_expiring"].rule_label)
    if metrics["portingCodeRequestCount30d"] > 0:
        factors.append(FACTOR_DEFS["porting_intent"])
        rule_labels.append(FACTOR_DEFS["porting_intent"].rule_label)
    if metrics["overdueDays"] > 7:
        factors.append(FACTOR_DEFS["payment_pressure"])
        rule_labels.append(FACTOR_DEFS["payment_pressure"].rule_label)
    if metrics["retentionOfferRejected"] > 0:
        factors.append(FACTOR_DEFS["retention_reject"])
        rule_labels.append(FACTOR_DEFS["retention_reject"].rule_label)

    porting = metrics["portingCodeRequestCount30d"]
    competitor = metrics["competitorContactCount30d"]
    complaint = metrics["complaintCount30d"]
    data_drop = metrics["dataUsageDropPct"]
    contract_days = metrics["contractRemainingDays"]
    overdue_days = metrics["overdueDays"]
    retention_rejected = metrics["retentionOfferRejected"]

    if porting > 0 and (competitor > 0 or complaint > 2 or contract_days < 45):
        risk_level = "HIGH"
    elif (
        (complaint > 2 and data_drop > 30)
        or (data_drop > 30 and contract_days < 45)
        or (complaint > 2 and competitor > 0)
        or (competitor > 0 and retention_rejected > 0)
        or (overdue_days > 7 and contract_days < 45)
    ):
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    rule_labels.append(DECISION_RULES[risk_level])
    return {
        "riskLevel": risk_level,
        "recommendedAction": canonical_action(risk_level),
        "factors": list({factor.label: factor for factor in factors}.values()),
        "rules": list(dict.fromkeys(rule_labels)),
    }


def materialize_business_inference(
    deductions_graph: Graph,
    records: dict[str, dict[str, Any]],
    settings: Settings,
) -> tuple[dict[str, dict[str, Any]], Counter]:
    namespaces = make_namespaces(settings)
    doim = namespaces["doim"]
    telecom = namespaces["telecom"]
    data = namespaces["data"]

    inferred: dict[str, dict[str, Any]] = {}
    top_rules: Counter = Counter()

    for subscriber_id, record in records.items():
        result = infer_record(record)
        inferred[subscriber_id] = result

        subscriber = URIRef(f"{settings.data_ns}subscriber/{subscriber_id}")
        deductions_graph.add((subscriber, telecom.inferredRiskLevel, Literal(result["riskLevel"])))
        deductions_graph.add((subscriber, telecom.recommendedAction, Literal(result["recommendedAction"])))

        alert_resource = URIRef(f"{settings.data_ns}alert/{subscriber_id}")
        deductions_graph.add((alert_resource, RDF.type, telecom.RiskAlert))
        deductions_graph.add((alert_resource, RDFS.label, Literal(f"{subscriber_id} 风险告警")))
        deductions_graph.add((alert_resource, telecom.riskLevel, Literal(result["riskLevel"])))
        deductions_graph.add((alert_resource, telecom.recommendedAction, Literal(result["recommendedAction"])))
        deductions_graph.add((subscriber, telecom.generatedAlert, alert_resource))

        for factor in result["factors"]:
            factor_resource = URIRef(f"{settings.data_ns}factor/{factor.code}")
            deductions_graph.add((factor_resource, RDF.type, telecom.RiskFactor))
            deductions_graph.add((factor_resource, RDFS.label, Literal(factor.label)))
            deductions_graph.add((subscriber, telecom.hasRiskFactor, factor_resource))
            deductions_graph.add((subscriber, doim.evidenceFrom, factor_resource))

        for rule_label in result["rules"]:
            rule_code = rule_label.encode("utf-8").hex()
            rule_resource = URIRef(f"{settings.data_ns}rule/{rule_code}")
            deductions_graph.add((rule_resource, RDF.type, telecom.Rule))
            deductions_graph.add((rule_resource, RDFS.label, Literal(rule_label)))
            deductions_graph.add((subscriber, doim.taggedByRule, rule_resource))
            top_rules[rule_label] += 1

        deductions_graph.add(
            (
                subscriber,
                telecom.riskScore,
                Literal({"HIGH": 90, "MEDIUM": 65, "LOW": 30}[result["riskLevel"]], datatype=XSD.integer),
            )
        )
    return inferred, top_rules

