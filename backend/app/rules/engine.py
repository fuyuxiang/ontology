from __future__ import annotations

from collections import Counter
from typing import Any

from rdflib import Graph, Literal, RDF, RDFS, URIRef, XSD

from app.config.settings import Settings
from app.ontology.namespaces import make_namespaces
from app.rules.decision_table import DecisionTable, load_decision_table, matches_condition


def load_ruleset(settings: Settings) -> DecisionTable:
    return load_decision_table(settings.rules_path)


def canonical_action(risk_level: str, decision_table: DecisionTable) -> str:
    try:
        return decision_table.risk_actions[risk_level]
    except KeyError as exc:  # pragma: no cover
        raise ValueError(f"Missing action mapping for risk level: {risk_level}") from exc


def infer_record(record: dict[str, Any], decision_table: DecisionTable) -> dict[str, Any]:
    metrics = record["metrics"]
    factors = []
    rule_labels: list[str] = []

    for rule in decision_table.factor_rules:
        if matches_condition(rule.when, metrics):
            factors.append(rule.factor)
            rule_labels.append(rule.rule_label)

    matched_decision = None
    for rule in decision_table.decision_rules:
        if matches_condition(rule.when, metrics):
            matched_decision = rule
            rule_labels.append(rule.rule_label)
            break

    if matched_decision is None:  # pragma: no cover
        raise ValueError("No decision rule matched the current record")

    risk_level = matched_decision.risk_level
    return {
        "riskLevel": risk_level,
        "recommendedAction": canonical_action(risk_level, decision_table),
        "factors": list({factor.label: factor for factor in factors}.values()),
        "rules": list(dict.fromkeys(rule_labels)),
    }


def materialize_business_inference(
    deductions_graph: Graph,
    records: dict[str, dict[str, Any]],
    settings: Settings,
) -> tuple[dict[str, dict[str, Any]], Counter]:
    decision_table = load_ruleset(settings)
    namespaces = make_namespaces(settings)
    doim = namespaces["doim"]
    telecom = namespaces["telecom"]

    inferred: dict[str, dict[str, Any]] = {}
    top_rules: Counter = Counter()

    for subscriber_id, record in records.items():
        result = infer_record(record, decision_table)
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
