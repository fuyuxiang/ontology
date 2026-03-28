"""
模块功能：
- 语义层的数据装载、关联索引与事实计算。
- 该文件位于 `backend/app/services/data_pipeline.py`，负责源数据读取、事实计算、索引构建和记录聚合，是语义服务的数据预处理层。
- 文件中定义的核心类包括：`FactEvaluator`。
- 文件中对外暴露或复用的主要函数包括：`infer_target_type`, `build_entity_uri`, `build_entity_label`, `load_source_rows`, `build_dataset_indexes`, `build_records`。
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable
from urllib.parse import quote

from rdflib import URIRef

from app.config.settings import Settings
from app.etl.csv_loader import read_csv_rows
from app.scenario.config import FactConfig, ScenarioConfig
from app.scenario.mapping import MappingRow


class FactEvaluator:
    """
    功能：
    - 封装事实指标计算与基础类型/日期比较逻辑。
    - 该类定义在 `backend/app/services/data_pipeline.py` 中，用于组织与 `FactEvaluator` 相关的数据或行为。
    """

    def __init__(self, *, reference_date: date, primary_dataset: str) -> None:
        """
        功能：
        - 初始化当前对象并准备后续调用所需的依赖、状态和缓存。

        输入：
        - `reference_date`: 事实计算所基于的参考日期。
        - `primary_dataset`: 场景中定义的主实体数据集键名。

        输出：
        - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
        """
        self.reference_date = reference_date
        self.primary_dataset = primary_dataset

    def evaluate_fact(
        self,
        fact: FactConfig,
        primary_row: dict[str, Any],
        related_rows: dict[str, list[dict[str, Any]]],
    ) -> Any:
        """
        功能：
        - 处理与 `evaluate_fact` 相关的逻辑。

        输入：
        - `fact`: 函数执行所需的 `fact` 参数。
        - `primary_row`: 字典参数 `primary_row`，承载键值形式的输入数据。
        - `related_rows`: 字典参数 `related_rows`，承载键值形式的输入数据。

        输出：
        - 返回值: 返回 `Any` 类型结果，供后续流程继续消费。
        """
        rows = [primary_row] if fact.source_dataset == self.primary_dataset else related_rows.get(fact.source_dataset, [])
        candidates = [row for row in rows if not fact.where or self.row_matches(fact.where, row)]

        if fact.aggregate == "first":
            value = candidates[0].get(fact.field or "") if candidates else fact.default
            return self.apply_cast(value, fact.cast, fact.default)
        if fact.aggregate == "latest":
            if not candidates or not fact.field or not fact.order_by:
                return self.apply_cast(fact.default, fact.cast, fact.default)
            ordered = sorted(candidates, key=lambda row: self.order_key(row.get(fact.order_by)))
            return self.apply_cast(ordered[-1].get(fact.field), fact.cast, fact.default)
        if fact.aggregate == "exists":
            return bool(candidates)
        if fact.aggregate == "count":
            return len(candidates)
        if fact.aggregate == "sum":
            total = sum((self.coerce_scalar(row.get(fact.field or ""), fact.cast or "decimal") or Decimal("0")) for row in candidates)
            return total
        if fact.aggregate == "min_days_since":
            if not candidates or not fact.field:
                return fact.default
            days = [self.days_since(row.get(fact.field)) for row in candidates]
            values = [value for value in days if value is not None]
            return min(values) if values else fact.default
        raise ValueError(f"Unsupported fact aggregate: {fact.aggregate}")

    def row_matches(self, condition: dict[str, Any], row: dict[str, Any]) -> bool:
        """
        功能：
        - 处理与 `row_matches` 相关的逻辑。

        输入：
        - `condition`: 规则或过滤匹配条件。
        - `row`: 单行源数据或中间对象数据。

        输出：
        - 返回值: 返回布尔值，表示条件是否成立或当前操作是否允许。
        """
        if "all" in condition:
            return all(self.row_matches(item, row) for item in condition["all"])
        if "any" in condition:
            return any(self.row_matches(item, row) for item in condition["any"])
        if "not" in condition:
            return not self.row_matches(condition["not"], row)

        field = str(condition["field"])
        operator = str(condition["op"])
        expected = condition.get("value")
        actual = row.get(field)

        if operator == "within_days":
            days = self.days_since(actual)
            return days is not None and 0 <= days <= int(expected)
        if operator == "date_on_or_after":
            actual_date = self.parse_date_value(actual)
            if actual_date is None:
                return False
            expected_date = self.reference_date if expected == "today" else date.fromisoformat(str(expected))
            return actual_date >= expected_date
        if operator == "not_empty":
            return actual not in (None, "")

        return self.compare(actual, operator, expected)

    def compare(self, actual: Any, operator: str, expected: Any) -> bool:
        """
        功能：
        - 处理与 `compare` 相关的逻辑。

        输入：
        - `actual`: 函数执行所需的 `actual` 参数。
        - `operator`: 函数执行所需的 `operator` 参数。
        - `expected`: 函数执行所需的 `expected` 参数。

        输出：
        - 返回值: 返回布尔值，表示条件是否成立或当前操作是否允许。
        """
        if isinstance(actual, bool):
            actual_value = actual
            expected_value = self.coerce_scalar(expected, "bool")
        elif isinstance(actual, Decimal):
            actual_value = actual
            expected_value = self.coerce_scalar(expected, "decimal")
        elif isinstance(actual, int):
            actual_value = actual
            expected_value = self.coerce_scalar(expected, "int")
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

    def days_since(self, value: Any) -> int | None:
        """
        功能：
        - 计算给定日期距离参考日期的天数差。

        输入：
        - `value`: 待解析、转换或比较的原始值。

        输出：
        - 返回值: 返回处理结果；当目标不存在、未命中或无法解析时返回 `None`。
        """
        parsed = self.parse_date_value(value)
        if parsed is None:
            return None
        return (self.reference_date - parsed).days

    def parse_date_value(self, value: Any) -> date | None:
        """
        功能：
        - 把输入值解析为日期对象。

        输入：
        - `value`: 待解析、转换或比较的原始值。

        输出：
        - 返回值: 返回处理结果；当目标不存在、未命中或无法解析时返回 `None`。
        """
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

    def apply_cast(self, value: Any, cast: str | None, default: Any) -> Any:
        """
        功能：
        - 按指定类型转换规则处理输入值。

        输入：
        - `value`: 待解析、转换或比较的原始值。
        - `cast`: 函数执行所需的 `cast` 参数。
        - `default`: 无法解析时使用的默认值。

        输出：
        - 返回值: 返回 `Any` 类型结果，供后续流程继续消费。
        """
        if value in (None, ""):
            return default
        if not cast:
            return value
        converted = self.coerce_scalar(value, cast)
        return default if converted is None else converted

    def coerce_scalar(self, value: Any, value_type: str) -> Any:
        """
        功能：
        - 把标量值规范化为指定数据类型。

        输入：
        - `value`: 待解析、转换或比较的原始值。
        - `value_type`: 函数执行所需的 `value_type` 参数。

        输出：
        - 返回值: 返回 `Any` 类型结果，供后续流程继续消费。
        """
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

    def order_key(self, value: Any) -> Any:
        """
        功能：
        - 生成可用于排序比较的键值。

        输入：
        - `value`: 待解析、转换或比较的原始值。

        输出：
        - 返回值: 返回 `Any` 类型结果，供后续流程继续消费。
        """
        parsed_date = self.parse_date_value(value)
        if parsed_date is not None:
            return parsed_date.toordinal()
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (int, float)):
            return value
        return "" if value is None else str(value)


def infer_target_type(mapping_by_dataset: dict[str, list[MappingRow]], dataset_key: str) -> str:
    """
    功能：
    - 从映射表中推断数据集对应的目标类型。

    输入：
    - `mapping_by_dataset`: 按数据集分组的字段映射配置。
    - `dataset_key`: 需要持久化或查询的 RDF 数据集对象。

    输出：
    - 返回值: 返回字符串结果，供调用方继续展示、拼接或查询。
    """
    rows = mapping_by_dataset.get(dataset_key, [])
    if not rows:
        raise ValueError(f"No mapping rows configured for dataset: {dataset_key}")
    return rows[0].target_type


def build_entity_uri(settings: Settings, scenario: ScenarioConfig, dataset_key: str, row: dict[str, Any], index: int) -> URIRef:
    """
    功能：
    - 为原始行构造稳定的实体 URI。

    输入：
    - `settings`: 运行时配置对象，提供目录路径、命名空间和环境参数。
    - `scenario`: 当前激活的场景配置对象。
    - `dataset_key`: 需要持久化或查询的 RDF 数据集对象。
    - `row`: 单行源数据或中间对象数据。
    - `index`: 函数执行所需的 `index` 参数。

    输出：
    - 返回值: 返回 RDF 资源 URI。
    """
    dataset_config = scenario.datasets[dataset_key]
    parts = []
    for field_name in dataset_config.id_fields:
        value = row.get(field_name)
        if value not in (None, ""):
            parts.append(quote(str(value), safe=""))
    if not parts:
        parts.append(f"row-{index + 1}")
    dataset_segment = dataset_key.replace("_", "-")
    return URIRef(f"{settings.data_ns}{dataset_segment}/{'/'.join(parts)}")


def build_entity_label(scenario: ScenarioConfig, dataset_key: str, row: dict[str, Any]) -> str:
    """
    功能：
    - 为实体生成展示标签，优先模板，再退回单字段或序号。

    输入：
    - `scenario`: 当前激活的场景配置对象。
    - `dataset_key`: 需要持久化或查询的 RDF 数据集对象。
    - `row`: 单行源数据或中间对象数据。

    输出：
    - 返回值: 返回字符串结果，供调用方继续展示、拼接或查询。
    """
    dataset_config = scenario.datasets[dataset_key]
    if dataset_config.label_template:
        values = {key: "" if value is None else str(value) for key, value in row.items()}
        return dataset_config.label_template.format(**values)
    if dataset_config.label_field:
        value = row.get(dataset_config.label_field)
        if value not in (None, ""):
            return str(value)
    return f"{dataset_config.entity_label}-{int(row['_row_index']) + 1}"


def load_source_rows(
    *,
    settings: Settings,
    scenario: ScenarioConfig,
    mapping_by_dataset: dict[str, list[MappingRow]],
    fact_evaluator: FactEvaluator,
) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    """
    功能：
    - 读取各数据集 CSV，并补充实体构图所需的运行时元字段。

    输入：
    - `settings`: 运行时配置对象，提供目录路径、命名空间和环境参数。
    - `scenario`: 当前激活的场景配置对象。
    - `mapping_by_dataset`: 按数据集分组的字段映射配置。
    - `fact_evaluator`: 事实计算器，用于派生字段和条件判断。

    输出：
    - 返回值: 返回元组结果，按既定顺序携带多个返回值。
    """
    rows_by_dataset: dict[str, list[dict[str, Any]]] = {}
    warnings: list[str] = []

    for dataset_key, dataset_config in scenario.datasets.items():
        path = settings.data_dir / dataset_config.file
        if not path.exists():
            warnings.append(f"missing_dataset:{dataset_key}:{dataset_config.file}")
            rows_by_dataset[dataset_key] = []
            continue

        raw_rows = read_csv_rows(path)
        typed_rows: list[dict[str, Any]] = []
        target_type = infer_target_type(mapping_by_dataset, dataset_key)
        for index, raw_row in enumerate(raw_rows):
            row: dict[str, Any] = dict(raw_row)
            for mapping in mapping_by_dataset.get(dataset_key, []):
                if mapping.field_name in row:
                    row[mapping.field_name] = fact_evaluator.coerce_scalar(row[mapping.field_name], mapping.value_type)
            row["_dataset_key"] = dataset_key
            row["_row_index"] = index
            row["_target_type"] = target_type
            row["_entity_uri"] = build_entity_uri(settings, scenario, dataset_key, row, index)
            row["_label"] = build_entity_label(scenario, dataset_key, row)
            row["_node_type"] = dataset_config.node_type
            typed_rows.append(row)
        rows_by_dataset[dataset_key] = typed_rows

    return rows_by_dataset, warnings


def build_dataset_indexes(
    source_rows: dict[str, list[dict[str, Any]]],
    scenario: ScenarioConfig,
) -> dict[str, dict[str, dict[str, list[dict[str, Any]]]]]:
    """
    功能：
    - 按场景配置的 join key 构建多级索引，加速跨表关联。

    输入：
    - `source_rows`: 按数据集分组的原始或清洗后行数据。
    - `scenario`: 当前激活的场景配置对象。

    输出：
    - 返回值: 返回字典结构，包含本次处理产生的结果数据。
    """
    indexes: dict[str, dict[str, dict[str, list[dict[str, Any]]]]] = {}
    for dataset_key, rows in source_rows.items():
        dataset_config = scenario.datasets[dataset_key]
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


def build_records(
    *,
    source_rows: dict[str, list[dict[str, Any]]],
    dataset_indexes: dict[str, dict[str, dict[str, list[dict[str, Any]]]]],
    scenario: ScenarioConfig,
    fact_evaluator: FactEvaluator,
    node_id_for_row: Callable[[str, dict[str, Any]], str],
) -> dict[str, dict[str, Any]]:
    """
    功能：
    - 以主数据集为中心拼装实体记录，供告警与详情视图使用。

    输入：
    - `source_rows`: 按数据集分组的原始或清洗后行数据。
    - `dataset_indexes`: 为跨数据集关联建立的多级索引。
    - `scenario`: 当前激活的场景配置对象。
    - `fact_evaluator`: 事实计算器，用于派生字段和条件判断。
    - `node_id_for_row`: 函数执行所需的 `node_id_for_row` 参数。

    输出：
    - 返回值: 返回字典结构，包含本次处理产生的结果数据。
    """
    primary_dataset = scenario.datasets[scenario.primary_dataset]
    records: dict[str, dict[str, Any]] = {}

    for primary_row in source_rows.get(scenario.primary_dataset, []):
        entity_id = str(primary_row.get(scenario.primary_id_field) or "").strip()
        if not entity_id:
            continue

        related: dict[str, list[dict[str, Any]]] = {}
        for dataset_key, dataset_config in scenario.datasets.items():
            if dataset_key == scenario.primary_dataset:
                continue
            matched: dict[tuple[str, int], dict[str, Any]] = {}
            for canonical_key, primary_field in primary_dataset.join_keys.items():
                if canonical_key not in dataset_config.join_keys:
                    continue
                value = primary_row.get(primary_field)
                if value in (None, ""):
                    continue
                for row in dataset_indexes[dataset_key][canonical_key].get(str(value), []):
                    matched[(dataset_key, int(row["_row_index"]))] = row
            related[dataset_key] = list(matched.values())

        facts = {fact.key: fact_evaluator.evaluate_fact(fact, primary_row, related) for fact in scenario.facts}
        records[entity_id] = {
            "entityId": entity_id,
            "displayName": str(primary_row.get(scenario.primary_label_field) or entity_id),
            "nodeId": node_id_for_row(scenario.primary_dataset, primary_row),
            "primary": primary_row,
            "related": related,
            "metrics": facts,
        }

    return records
