"""
模块功能：
- 风险决策表模型与加载逻辑。
- 该文件位于 `backend/app/rules/decision_table.py`，负责解析决策表配置并提供规则匹配能力，供推理引擎调用。
- 文件中定义的核心类包括：`RiskFactorDef`, `FactorRule`, `DecisionRule`, `DecisionTable`。
- 文件中对外暴露或复用的主要函数包括：`_as_mapping`, `_as_sequence`, `load_decision_table`, `_load_factor_rules`, `_load_decision_rules`, `matches_condition`。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


@dataclass(frozen=True)
class RiskFactorDef:
    """
    功能：
    - 单个风险因子的静态定义。
    - 该类定义在 `backend/app/rules/decision_table.py` 中，用于组织与 `RiskFactorDef` 相关的数据或行为。
    - 类中声明的主要字段包括：`code`, `label`, `rule_label`。
    """

    code: str
    label: str
    rule_label: str


@dataclass(frozen=True)
class FactorRule:
    """
    功能：
    - 命中后会附着风险因子的规则。
    - 该类定义在 `backend/app/rules/decision_table.py` 中，用于组织与 `FactorRule` 相关的数据或行为。
    - 类中声明的主要字段包括：`id`, `rule_label`, `factor`, `when`。
    """

    id: str
    rule_label: str
    factor: RiskFactorDef
    when: dict[str, Any]


@dataclass(frozen=True)
class DecisionRule:
    """
    功能：
    - 用于产出最终风险等级的决策规则。
    - 该类定义在 `backend/app/rules/decision_table.py` 中，用于组织与 `DecisionRule` 相关的数据或行为。
    - 类中声明的主要字段包括：`id`, `rule_label`, `priority`, `when`, `risk_level`。
    """

    id: str
    rule_label: str
    priority: int
    when: dict[str, Any]
    risk_level: str


@dataclass(frozen=True)
class DecisionTable:
    """
    功能：
    - 完整的风险规则表，包含动作映射、因子规则和决策规则。
    - 该类定义在 `backend/app/rules/decision_table.py` 中，用于组织与 `DecisionTable` 相关的数据或行为。
    - 类中声明的主要字段包括：`risk_actions`, `factor_rules`, `decision_rules`。
    """

    risk_actions: dict[str, str]
    factor_rules: tuple[FactorRule, ...]
    decision_rules: tuple[DecisionRule, ...]


OPS = {
    ">": lambda actual, expected: actual > expected,
    ">=": lambda actual, expected: actual >= expected,
    "<": lambda actual, expected: actual < expected,
    "<=": lambda actual, expected: actual <= expected,
    "==": lambda actual, expected: actual == expected,
    "!=": lambda actual, expected: actual != expected,
    "in": lambda actual, expected: actual in expected,
    "not in": lambda actual, expected: actual not in expected,
}


def _as_mapping(value: Any, context: str) -> dict[str, Any]:
    """
    功能：
    - 断言对象为映射类型，失败时带上明确上下文。

    输入：
    - `value`: 待解析、转换或比较的原始值。
    - `context`: 错误提示或日志中使用的上下文说明。

    输出：
    - 返回值: 返回字典结构，包含本次处理产生的结果数据。
    """
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be a mapping")
    return value


def _as_sequence(value: Any, context: str) -> list[Any]:
    """
    功能：
    - 断言对象为列表类型，失败时带上明确上下文。

    输入：
    - `value`: 待解析、转换或比较的原始值。
    - `context`: 错误提示或日志中使用的上下文说明。

    输出：
    - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
    """
    if not isinstance(value, list):
        raise ValueError(f"{context} must be a list")
    return value


def load_decision_table(path: Path) -> DecisionTable:
    """
    功能：
    - 从 YAML 文件加载风险决策表。

    输入：
    - `path`: 待读取或写入的路径对象。

    输出：
    - 返回值: 返回已解析完成的决策表对象。
    """
    if yaml is None:  # pragma: no cover
        raise RuntimeError("PyYAML is required to load decision tables")
    if not path.exists():
        raise FileNotFoundError(f"Decision table not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    config = _as_mapping(raw, "decision table")

    risk_actions = _as_mapping(config.get("risk_actions"), "risk_actions")
    factor_rules = tuple(_load_factor_rules(config.get("factor_rules", [])))
    decision_rules = tuple(_load_decision_rules(config.get("decision_rules", [])))
    if not decision_rules:
        raise ValueError("decision_rules must contain at least one rule")
    return DecisionTable(
        risk_actions={str(key): str(value) for key, value in risk_actions.items()},
        factor_rules=factor_rules,
        decision_rules=decision_rules,
    )


def _load_factor_rules(raw_rules: Any) -> list[FactorRule]:
    """
    功能：
    - 解析风险因子规则列表。

    输入：
    - `raw_rules`: 尚未转换成对象的规则配置集合。

    输出：
    - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
    """
    factor_rules: list[FactorRule] = []
    for index, raw_rule in enumerate(_as_sequence(raw_rules, "factor_rules"), start=1):
        rule = _as_mapping(raw_rule, f"factor_rules[{index}]")
        factor = _as_mapping(rule.get("factor"), f"factor_rules[{index}].factor")
        factor_rules.append(
            FactorRule(
                id=str(rule["id"]),
                rule_label=str(rule["rule_label"]),
                factor=RiskFactorDef(
                    code=str(factor["code"]),
                    label=str(factor["label"]),
                    rule_label=str(rule["rule_label"]),
                ),
                when=_as_mapping(rule.get("when"), f"factor_rules[{index}].when"),
            )
        )
    return factor_rules


def _load_decision_rules(raw_rules: Any) -> list[DecisionRule]:
    """
    功能：
    - 解析决策规则，并按优先级从高到低排序。

    输入：
    - `raw_rules`: 尚未转换成对象的规则配置集合。

    输出：
    - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
    """
    decision_rules: list[DecisionRule] = []
    for index, raw_rule in enumerate(_as_sequence(raw_rules, "decision_rules"), start=1):
        rule = _as_mapping(raw_rule, f"decision_rules[{index}]")
        then = _as_mapping(rule.get("then"), f"decision_rules[{index}].then")
        decision_rules.append(
            DecisionRule(
                id=str(rule["id"]),
                rule_label=str(rule["rule_label"]),
                priority=int(rule.get("priority", 0)),
                when=_as_mapping(rule.get("when"), f"decision_rules[{index}].when"),
                risk_level=str(then["risk_level"]),
            )
        )
    return sorted(decision_rules, key=lambda item: (-item.priority, item.id))


def matches_condition(condition: dict[str, Any], facts: dict[str, Any]) -> bool:
    """
    功能：
    - 递归匹配 all/any/not 组合条件和基础比较条件。

    输入：
    - `condition`: 规则或过滤匹配条件。
    - `facts`: 参与规则匹配的事实字典。

    输出：
    - 返回值: 返回布尔值，表示条件是否成立或当前操作是否允许。
    """
    if "all" in condition:
        children = _as_sequence(condition["all"], "all")
        return all(matches_condition(_as_mapping(child, "all child"), facts) for child in children)
    if "any" in condition:
        children = _as_sequence(condition["any"], "any")
        return any(matches_condition(_as_mapping(child, "any child"), facts) for child in children)
    if "not" in condition:
        return not matches_condition(_as_mapping(condition["not"], "not"), facts)

    field = str(condition["field"])
    operator = str(condition["op"])
    if operator not in OPS:
        raise ValueError(f"Unsupported operator: {operator}")
    if field not in facts:
        raise KeyError(f"Unknown fact field: {field}")
    return OPS[operator](facts[field], condition.get("value"))
