"""
模块功能：
- 场景配置模型与 YAML 解析器。
- 该文件位于 `backend/app/scenario/config.py`，定义场景配置模型并解析 YAML 配置，统一约束场景元数据结构。
- 文件中定义的核心类包括：`DatasetConfig`, `RelationConfig`, `FactConfig`, `AlertDisplayField`, `SortConfig`, `SourceCardConfig`, `OntologyFileConfig`, `RuleCardConfig`, `ScenarioConfig`。
- 文件中对外暴露或复用的主要函数包括：`load_scenario_config`, `_load_dataset_config`, `_load_relation`, `_load_fact`, `_load_display_field`, `_load_sort`, `_load_source_card`, `_load_ontology_file`, `_load_rule_card`, `_parse_date_optional`, `_as_mapping`, `_as_sequence`, `_as_string_list`。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class DatasetConfig:
    """
    功能：
    - 描述一个原始数据集的文件、标识字段和图谱节点映射方式。
    - 该类定义在 `backend/app/scenario/config.py` 中，用于组织与 `DatasetConfig` 相关的数据或行为。
    - 类中声明的主要字段包括：`key`, `file`, `source_system`, `id_fields`, `join_keys`, `label_field`, `label_template`, `node_type`, `entity_label`。
    """

    key: str
    file: str
    source_system: str
    id_fields: tuple[str, ...]
    join_keys: dict[str, str]
    label_field: str | None
    label_template: str | None
    node_type: str
    entity_label: str


@dataclass(frozen=True)
class RelationConfig:
    """
    功能：
    - 描述两个数据集之间的关联关系生成规则。
    - 该类定义在 `backend/app/scenario/config.py` 中，用于组织与 `RelationConfig` 相关的数据或行为。
    - 类中声明的主要字段包括：`source_dataset`, `target_dataset`, `source_join_key`, `target_join_key`, `predicate`, `label`, `source_system`。
    """

    source_dataset: str
    target_dataset: str
    source_join_key: str
    target_join_key: str
    predicate: str
    label: str
    source_system: str


@dataclass(frozen=True)
class FactConfig:
    """
    功能：
    - 描述事实指标的聚合来源与计算方式。
    - 该类定义在 `backend/app/scenario/config.py` 中，用于组织与 `FactConfig` 相关的数据或行为。
    - 类中声明的主要字段包括：`key`, `label`, `source_dataset`, `aggregate`, `field`, `cast`, `order_by`, `default`, `where`。
    """

    key: str
    label: str
    source_dataset: str
    aggregate: str
    field: str | None
    cast: str | None
    order_by: str | None
    default: Any
    where: dict[str, Any] | None


@dataclass(frozen=True)
class AlertDisplayField:
    """
    功能：
    - 描述告警卡片中的一个展示字段。
    - 该类定义在 `backend/app/scenario/config.py` 中，用于组织与 `AlertDisplayField` 相关的数据或行为。
    - 类中声明的主要字段包括：`label`, `source`, `field`, `fact`。
    """

    label: str
    source: str | None
    field: str | None
    fact: str | None


@dataclass(frozen=True)
class SortConfig:
    """
    功能：
    - 描述告警列表的排序规则。
    - 该类定义在 `backend/app/scenario/config.py` 中，用于组织与 `SortConfig` 相关的数据或行为。
    - 类中声明的主要字段包括：`fact`, `order`。
    """

    fact: str
    order: str


@dataclass(frozen=True)
class SourceCardConfig:
    """
    功能：
    - 描述首页数据源卡片。
    - 该类定义在 `backend/app/scenario/config.py` 中，用于组织与 `SourceCardConfig` 相关的数据或行为。
    - 类中声明的主要字段包括：`key`, `dataset`, `label`, `file`, `icon`, `tone`, `count_mode`。
    """

    key: str
    dataset: str
    label: str
    file: str
    icon: str
    tone: str
    count_mode: str


@dataclass(frozen=True)
class OntologyFileConfig:
    """
    功能：
    - 描述前端展示的本体文件说明项。
    - 该类定义在 `backend/app/scenario/config.py` 中，用于组织与 `OntologyFileConfig` 相关的数据或行为。
    - 类中声明的主要字段包括：`name`, `desc`, `tone`。
    """

    name: str
    desc: str
    tone: str


@dataclass(frozen=True)
class RuleCardConfig:
    """
    功能：
    - 描述前端展示的规则卡片说明项。
    - 该类定义在 `backend/app/scenario/config.py` 中，用于组织与 `RuleCardConfig` 相关的数据或行为。
    - 类中声明的主要字段包括：`label`, `desc`, `tone`。
    """

    label: str
    desc: str
    tone: str


@dataclass(frozen=True)
class ScenarioConfig:
    """
    功能：
    - 聚合整个场景运行所需的 UI、数据和规则配置。
    - 该类定义在 `backend/app/scenario/config.py` 中，用于组织与 `ScenarioConfig` 相关的数据或行为。
    - 类中声明的主要字段包括：`key`, `name`, `app_title`, `header_title`, `dashboard_subtitle`, `reference_date`, `primary_dataset`, `primary_entity_label`, `primary_entity_plural_label`, `primary_id_field`, `primary_label_field`, `primary_node_type`, `search_fields`, `risk_terms`, `sample_query`, `question_suggestions`, `interaction_datasets`, `graph_datasets`, `source_cards`, `ontology_files`, `rule_cards`, `architecture`, `mapping_examples`, `datasets`, `relations`, `facts`, `summary_fields`, `detail_fields`, `highlight_fields`, `alert_sort`。
    """

    key: str
    name: str
    app_title: str
    header_title: str
    dashboard_subtitle: str
    reference_date: date | None
    primary_dataset: str
    primary_entity_label: str
    primary_entity_plural_label: str
    primary_id_field: str
    primary_label_field: str
    primary_node_type: str
    search_fields: tuple[str, ...]
    risk_terms: tuple[str, ...]
    sample_query: str
    question_suggestions: tuple[str, ...]
    interaction_datasets: tuple[str, ...]
    graph_datasets: tuple[str, ...]
    source_cards: tuple[SourceCardConfig, ...]
    ontology_files: tuple[OntologyFileConfig, ...]
    rule_cards: tuple[RuleCardConfig, ...]
    architecture: tuple[dict[str, Any], ...]
    mapping_examples: tuple[dict[str, str], ...]
    datasets: dict[str, DatasetConfig]
    relations: tuple[RelationConfig, ...]
    facts: tuple[FactConfig, ...]
    summary_fields: tuple[AlertDisplayField, ...]
    detail_fields: tuple[AlertDisplayField, ...]
    highlight_fields: tuple[AlertDisplayField, ...]
    alert_sort: tuple[SortConfig, ...]


def load_scenario_config(path: Path) -> ScenarioConfig:
    """
    功能：
    - 从 YAML 文件加载完整场景配置。

    输入：
    - `path`: 待读取或写入的路径对象。

    输出：
    - 返回值: 返回解析后的场景配置对象。
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    config = _as_mapping(raw, "scenario config")
    scenario_raw = _as_mapping(config.get("scenario"), "scenario")
    datasets_raw = _as_mapping(config.get("datasets"), "datasets")

    datasets = {
        key: _load_dataset_config(key, value)
        for key, value in datasets_raw.items()
    }

    return ScenarioConfig(
        key=str(scenario_raw["key"]),
        name=str(scenario_raw["name"]),
        app_title=str(scenario_raw.get("app_title") or scenario_raw["name"]),
        header_title=str(scenario_raw.get("header_title") or scenario_raw.get("app_title") or scenario_raw["name"]),
        dashboard_subtitle=str(scenario_raw.get("dashboard_subtitle") or ""),
        reference_date=_parse_date_optional(scenario_raw.get("reference_date")),
        primary_dataset=str(scenario_raw["primary_dataset"]),
        primary_entity_label=str(scenario_raw["primary_entity_label"]),
        primary_entity_plural_label=str(scenario_raw.get("primary_entity_plural_label") or scenario_raw["primary_entity_label"]),
        primary_id_field=str(scenario_raw["primary_id_field"]),
        primary_label_field=str(scenario_raw["primary_label_field"]),
        primary_node_type=str(scenario_raw.get("primary_node_type") or "Entity"),
        search_fields=tuple(_as_string_list(scenario_raw.get("search_fields", []), "search_fields")),
        risk_terms=tuple(_as_string_list(scenario_raw.get("risk_terms", []), "risk_terms")),
        sample_query=str(scenario_raw.get("sample_query") or ""),
        question_suggestions=tuple(
            _as_string_list(scenario_raw.get("question_suggestions", []), "question_suggestions")
        ),
        interaction_datasets=tuple(
            _as_string_list(scenario_raw.get("interaction_datasets", []), "interaction_datasets")
        ),
        graph_datasets=tuple(_as_string_list(scenario_raw.get("graph_datasets", []), "graph_datasets")),
        source_cards=tuple(_load_source_card(item) for item in _as_sequence(scenario_raw.get("source_cards", []), "source_cards")),
        ontology_files=tuple(
            _load_ontology_file(item) for item in _as_sequence(scenario_raw.get("ontology_files", []), "ontology_files")
        ),
        rule_cards=tuple(_load_rule_card(item) for item in _as_sequence(scenario_raw.get("rule_cards", []), "rule_cards")),
        architecture=tuple(_as_mapping(item, "architecture item") for item in _as_sequence(scenario_raw.get("architecture", []), "architecture")),
        mapping_examples=tuple(
            _as_mapping(item, "mapping example") for item in _as_sequence(scenario_raw.get("mapping_examples", []), "mapping_examples")
        ),
        datasets=datasets,
        relations=tuple(_load_relation(item) for item in _as_sequence(config.get("relations", []), "relations")),
        facts=tuple(_load_fact(item) for item in _as_sequence(config.get("facts", []), "facts")),
        summary_fields=tuple(
            _load_display_field(item) for item in _as_sequence(config.get("alert_fields", {}).get("summary", []), "alert_fields.summary")
        ),
        detail_fields=tuple(
            _load_display_field(item) for item in _as_sequence(config.get("alert_fields", {}).get("detail", []), "alert_fields.detail")
        ),
        highlight_fields=tuple(
            _load_display_field(item) for item in _as_sequence(config.get("alert_fields", {}).get("highlights", []), "alert_fields.highlights")
        ),
        alert_sort=tuple(_load_sort(item) for item in _as_sequence(config.get("alert_sort", []), "alert_sort")),
    )


def _load_dataset_config(key: str, raw: Any) -> DatasetConfig:
    """
    功能：
    - 解析单个数据集配置。

    输入：
    - `key`: 函数执行所需的 `key` 参数。
    - `raw`: 尚未校验或转换的原始配置值。

    输出：
    - 返回值: 返回 `DatasetConfig` 类型结果，供后续流程继续消费。
    """
    item = _as_mapping(raw, f"datasets.{key}")
    return DatasetConfig(
        key=key,
        file=str(item["file"]),
        source_system=str(item["source_system"]),
        id_fields=tuple(_as_string_list(item.get("id_fields", []), f"datasets.{key}.id_fields")),
        join_keys={str(name): str(field) for name, field in _as_mapping(item.get("join_keys", {}), f"datasets.{key}.join_keys").items()},
        label_field=str(item["label_field"]) if item.get("label_field") else None,
        label_template=str(item["label_template"]) if item.get("label_template") else None,
        node_type=str(item.get("node_type") or "Entity"),
        entity_label=str(item.get("entity_label") or key),
    )


def _load_relation(raw: Any) -> RelationConfig:
    """
    功能：
    - 解析关系配置。

    输入：
    - `raw`: 尚未校验或转换的原始配置值。

    输出：
    - 返回值: 返回 `RelationConfig` 类型结果，供后续流程继续消费。
    """
    item = _as_mapping(raw, "relation")
    return RelationConfig(
        source_dataset=str(item["source_dataset"]),
        target_dataset=str(item["target_dataset"]),
        source_join_key=str(item["source_join_key"]),
        target_join_key=str(item["target_join_key"]),
        predicate=str(item["predicate"]),
        label=str(item["label"]),
        source_system=str(item["source_system"]),
    )


def _load_fact(raw: Any) -> FactConfig:
    """
    功能：
    - 解析事实指标配置。

    输入：
    - `raw`: 尚未校验或转换的原始配置值。

    输出：
    - 返回值: 返回 `FactConfig` 类型结果，供后续流程继续消费。
    """
    item = _as_mapping(raw, "fact")
    return FactConfig(
        key=str(item["key"]),
        label=str(item["label"]),
        source_dataset=str(item["source_dataset"]),
        aggregate=str(item["aggregate"]),
        field=str(item["field"]) if item.get("field") else None,
        cast=str(item["cast"]) if item.get("cast") else None,
        order_by=str(item["order_by"]) if item.get("order_by") else None,
        default=item.get("default"),
        where=_as_mapping(item["where"], f"fact {item['key']}.where") if item.get("where") else None,
    )


def _load_display_field(raw: Any) -> AlertDisplayField:
    """
    功能：
    - 解析告警展示字段配置。

    输入：
    - `raw`: 尚未校验或转换的原始配置值。

    输出：
    - 返回值: 返回 `AlertDisplayField` 类型结果，供后续流程继续消费。
    """
    item = _as_mapping(raw, "display field")
    return AlertDisplayField(
        label=str(item["label"]),
        source=str(item["source"]) if item.get("source") else None,
        field=str(item["field"]) if item.get("field") else None,
        fact=str(item["fact"]) if item.get("fact") else None,
    )


def _load_sort(raw: Any) -> SortConfig:
    """
    功能：
    - 解析排序配置。

    输入：
    - `raw`: 尚未校验或转换的原始配置值。

    输出：
    - 返回值: 返回 `SortConfig` 类型结果，供后续流程继续消费。
    """
    item = _as_mapping(raw, "sort field")
    return SortConfig(
        fact=str(item["fact"]),
        order=str(item.get("order") or "desc"),
    )


def _load_source_card(raw: Any) -> SourceCardConfig:
    """
    功能：
    - 解析首页数据源卡片配置。

    输入：
    - `raw`: 尚未校验或转换的原始配置值。

    输出：
    - 返回值: 返回 `SourceCardConfig` 类型结果，供后续流程继续消费。
    """
    item = _as_mapping(raw, "source card")
    return SourceCardConfig(
        key=str(item["key"]),
        dataset=str(item["dataset"]),
        label=str(item["label"]),
        file=str(item["file"]),
        icon=str(item["icon"]),
        tone=str(item["tone"]),
        count_mode=str(item.get("count_mode") or "records"),
    )


def _load_ontology_file(raw: Any) -> OntologyFileConfig:
    """
    功能：
    - 解析本体文件展示配置。

    输入：
    - `raw`: 尚未校验或转换的原始配置值。

    输出：
    - 返回值: 返回 `OntologyFileConfig` 类型结果，供后续流程继续消费。
    """
    item = _as_mapping(raw, "ontology file")
    return OntologyFileConfig(
        name=str(item["name"]),
        desc=str(item["desc"]),
        tone=str(item["tone"]),
    )


def _load_rule_card(raw: Any) -> RuleCardConfig:
    """
    功能：
    - 解析规则卡片配置。

    输入：
    - `raw`: 尚未校验或转换的原始配置值。

    输出：
    - 返回值: 返回 `RuleCardConfig` 类型结果，供后续流程继续消费。
    """
    item = _as_mapping(raw, "rule card")
    return RuleCardConfig(
        label=str(item["label"]),
        desc=str(item["desc"]),
        tone=str(item["tone"]),
    )


def _parse_date_optional(value: Any) -> date | None:
    """
    功能：
    - 把可选日期字段解析为 `date` 对象。

    输入：
    - `value`: 待解析、转换或比较的原始值。

    输出：
    - 返回值: 返回处理结果；当目标不存在、未命中或无法解析时返回 `None`。
    """
    if value in (None, ""):
        return None
    return date.fromisoformat(str(value))


def _as_mapping(value: Any, context: str) -> dict[str, Any]:
    """
    功能：
    - 确保 YAML 节点是映射结构。

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
    - 确保 YAML 节点是列表结构。

    输入：
    - `value`: 待解析、转换或比较的原始值。
    - `context`: 错误提示或日志中使用的上下文说明。

    输出：
    - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
    """
    if not isinstance(value, list):
        raise ValueError(f"{context} must be a list")
    return value


def _as_string_list(value: Any, context: str) -> list[str]:
    """
    功能：
    - 把 YAML 列表节点规范化为字符串列表。

    输入：
    - `value`: 待解析、转换或比较的原始值。
    - `context`: 错误提示或日志中使用的上下文说明。

    输出：
    - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
    """
    return [str(item) for item in _as_sequence(value, context)]
