"""
模块功能：
- 规则推理引擎，负责将业务规则转换为推理结果与告警三元组。
- 该文件位于 `backend/app/rules/engine.py`，实现当前领域的核心引擎逻辑，负责状态推进、规则处理或运行时协调。
- 文件中对外暴露或复用的主要函数包括：`load_ruleset`, `canonical_action`, `infer_record`, `materialize_business_inference`。
"""

from __future__ import annotations

from collections import Counter
from typing import Any
from urllib.parse import quote

from rdflib import Graph, Literal, RDF, RDFS, URIRef, XSD

from app.config.settings import Settings
from app.ontology.namespaces import make_namespaces
from app.rules.decision_table import DecisionTable, load_decision_table, matches_condition
from app.scenario.config import ScenarioConfig


def load_ruleset(settings: Settings) -> DecisionTable:
    """
    功能：
    - 根据当前配置加载风险决策表。

    输入：
    - `settings`: 运行时配置对象，提供目录路径、命名空间和环境参数。

    输出：
    - 返回值: 返回已解析完成的决策表对象。
    """
    return load_decision_table(settings.rules_path)


def canonical_action(risk_level: str, decision_table: DecisionTable) -> str:
    """
    功能：
    - 将风险等级映射为标准推荐动作。

    输入：
    - `risk_level`: 待映射或判断的风险等级。
    - `decision_table`: 已加载的风险决策表对象。

    输出：
    - 返回值: 返回字符串结果，供调用方继续展示、拼接或查询。
    """
    try:
        return decision_table.risk_actions[risk_level]
    except KeyError as exc:  # pragma: no cover
        raise ValueError(f"Missing action mapping for risk level: {risk_level}") from exc


def infer_record(record: dict[str, Any], decision_table: DecisionTable) -> dict[str, Any]:
    """
    功能：
    - 对单个实体记录执行因子识别与最终风险判定。

    输入：
    - `record`: 单个实体或业务对象的聚合记录。
    - `decision_table`: 已加载的风险决策表对象。

    输出：
    - 返回值: 返回字典结构，包含本次处理产生的结果数据。
    """
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
    scenario: ScenarioConfig,
) -> tuple[dict[str, dict[str, Any]], Counter]:
    """
    功能：
    - 把规则推理结果写入推理图，并汇总规则命中次数。

    输入：
    - `deductions_graph`: 推理结果图对象，用于承载规则和 OWL 推理三元组。
    - `records`: 按实体标识组织的聚合记录集合。
    - `settings`: 运行时配置对象，提供目录路径、命名空间和环境参数。
    - `scenario`: 当前激活的场景配置对象。

    输出：
    - 返回值: 返回元组结果，按既定顺序携带多个返回值。
    """
    decision_table = load_ruleset(settings)
    namespaces = make_namespaces(settings)
    doim = namespaces["doim"]
    telecom = namespaces["telecom"]

    inferred: dict[str, dict[str, Any]] = {}
    top_rules: Counter = Counter()
    primary_segment = scenario.primary_node_type.lower()

    for entity_id, record in records.items():
        result = infer_record(record, decision_table)
        inferred[entity_id] = result

        primary_row = record.get("primary") or {}
        entity_resource = primary_row.get("_entity_uri")
        if isinstance(entity_resource, URIRef):
            entity = entity_resource
        else:
            # 回退到稳定 URI，避免主实体缺少预计算资源标识时推理链中断。
            entity = URIRef(f"{settings.data_ns}{primary_segment}/{quote(entity_id, safe='')}")
        deductions_graph.add((entity, telecom.inferredRiskLevel, Literal(result["riskLevel"])))
        deductions_graph.add((entity, telecom.recommendedAction, Literal(result["recommendedAction"])))

        alert_resource = URIRef(f"{settings.data_ns}alert/{quote(entity_id, safe='')}")
        deductions_graph.add((alert_resource, RDF.type, telecom.RiskAlert))
        deductions_graph.add((alert_resource, RDFS.label, Literal(f"{entity_id} 风险告警")))
        deductions_graph.add((alert_resource, telecom.riskLevel, Literal(result["riskLevel"])))
        deductions_graph.add((alert_resource, telecom.recommendedAction, Literal(result["recommendedAction"])))
        deductions_graph.add((entity, telecom.generatedAlert, alert_resource))

        for factor in result["factors"]:
            factor_resource = URIRef(f"{settings.data_ns}factor/{factor.code}")
            deductions_graph.add((factor_resource, RDF.type, telecom.RiskFactor))
            deductions_graph.add((factor_resource, RDFS.label, Literal(factor.label)))
            deductions_graph.add((entity, telecom.hasRiskFactor, factor_resource))
            deductions_graph.add((entity, doim.evidenceFrom, factor_resource))

        for rule_label in result["rules"]:
            rule_code = rule_label.encode("utf-8").hex()
            rule_resource = URIRef(f"{settings.data_ns}rule/{rule_code}")
            deductions_graph.add((rule_resource, RDF.type, telecom.Rule))
            deductions_graph.add((rule_resource, RDFS.label, Literal(rule_label)))
            deductions_graph.add((entity, doim.taggedByRule, rule_resource))
            top_rules[rule_label] += 1

        deductions_graph.add(
            (
                entity,
                telecom.riskScore,
                Literal({"HIGH": 90, "MEDIUM": 65, "LOW": 30}[result["riskLevel"]], datatype=XSD.integer),
            )
        )
    return inferred, top_rules
