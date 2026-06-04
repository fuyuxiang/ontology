"""
规则引擎 — 将本体规则和动作从描述性文本变为可调用函数

两个核心组件：
- FieldResolver: 将 "EntityName.property" 解析为真实数据查询
- RuleEvaluator: 评估规则条件，返回结构化判断结果
"""
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models import OntologyEntity
from app.models.rule import BusinessRule
from app.services.data_plane.entity_data_service import EntityDataService

logger = logging.getLogger(__name__)


# ── 结果数据类 ──────────────────────────────────────────

@dataclass
class ConditionResult:
    field: str
    display: str
    operator: str
    expected: Any
    actual: Any = None
    matched: bool = False
    error: str | None = None


@dataclass
class RuleResult:
    rule_name: str
    triggered: bool
    matched_count: int
    total_count: int
    confidence: float
    conditions: list[ConditionResult] = field(default_factory=list)
    risk_level: str | None = None
    rule_id: str | None = None


# ── FieldResolver ───────────────────────────────────────

class FieldResolver:
    """将 "EntityName.property" 解析为真实数据查询并返回值"""

    def __init__(self, db: Session):
        self.db = db
        self._entity_cache: dict[str, OntologyEntity] = {}
        self._asset_cache: dict[str, Any] = {}
        self._data_svc = EntityDataService(db)

    def resolve(self, field_ref: str, user_id: str) -> Any:
        """
        解析字段引用并查询真实值。
        field_ref: "EntityName.property" 如 "SubscriberContract.is_contract_active"
        user_id: 用于关联查询的用户标识
        """
        if "." not in field_ref:
            return None

        entity_name, prop_name = field_ref.split(".", 1)
        entity = self._get_entity(entity_name)
        if not entity:
            return None

        resolved = self._get_entity_asset(entity)
        if not resolved:
            return None
        asset, _ = resolved

        attr = next((a for a in entity.attributes if a.name == prop_name), None)
        if attr and attr.type == "computed" and attr.constraints_json:
            expr = attr.constraints_json.get("expression", "")
            return self._resolve_computed(asset, entity, expr, user_id)

        table_name = self._data_svc.get_table_name(asset)
        if not table_name:
            return None

        pk_field = self._get_join_field(entity)
        column = self._find_column(entity, prop_name)
        if not column:
            column = prop_name

        sql = f"SELECT {column} FROM {table_name} WHERE {pk_field} = :uid LIMIT 1"
        result = self._data_svc.execute_sql_on_entity(
            entity.id, sql, params={"uid": user_id}, purpose="rule_engine.resolve",
        )
        if result.get("error") or not result.get("rows"):
            return None
        return result["rows"][0][0]

    def resolve_count(self, field_ref: str, user_id: str, since_days: int | None = None) -> int:
        """解析计数类字段，如 complaint_count"""
        entity_name, prop_name = field_ref.split(".", 1) if "." in field_ref else (field_ref, "")
        entity = self._get_entity(entity_name)
        if not entity:
            return 0

        resolved = self._get_entity_asset(entity)
        if not resolved:
            return 0
        asset, _ = resolved
        table_name = self._data_svc.get_table_name(asset)
        if not table_name:
            return 0

        pk_field = self._get_join_field(entity)
        sql = f"SELECT COUNT(*) FROM {table_name} WHERE {pk_field} = :uid"
        if since_days:
            sql += f" AND created_at >= NOW() - INTERVAL {since_days} DAY"

        result = self._data_svc.execute_sql_on_entity(
            entity.id, sql, params={"uid": user_id}, purpose="rule_engine.resolve_count",
        )
        if result.get("error") or not result.get("rows"):
            return 0
        return int(result["rows"][0][0] or 0)

    def _get_entity(self, name: str) -> OntologyEntity | None:
        if name not in self._entity_cache:
            entity = self.db.query(OntologyEntity).filter(OntologyEntity.name == name).first()
            if entity:
                self._entity_cache[name] = entity
        return self._entity_cache.get(name)

    def _get_entity_asset(self, entity: OntologyEntity):
        if entity.id not in self._asset_cache:
            resolved = self._data_svc.resolve_entity_asset(entity.id)
            if resolved:
                self._asset_cache[entity.id] = resolved
        return self._asset_cache.get(entity.id)

    def _get_join_field(self, entity: OntologyEntity) -> str:
        pk = (entity.config_json or {}).get("primary_key", "")
        return pk if pk else "user_id"

    def _find_column(self, entity: OntologyEntity, prop_name: str) -> str | None:
        """尝试从属性列表中找到对应的数据库列名"""
        attr = next((a for a in entity.attributes if a.name == prop_name), None)
        return attr.name if attr else None

    def _resolve_computed(self, asset, entity: OntologyEntity,
                          expression: str, user_id: str) -> Any:
        """解析计算属性表达式"""
        table_name = self._data_svc.get_table_name(asset)
        pk_field = self._get_join_field(entity)
        sql = f"SELECT CASE WHEN {expression} THEN 1 ELSE 0 END FROM {table_name} WHERE {pk_field} = :uid LIMIT 1"
        result = self._data_svc.execute_sql_on_entity(
            entity.id, sql, params={"uid": user_id}, purpose="rule_engine.computed",
        )
        if result.get("error") or not result.get("rows"):
            return None
        return bool(result["rows"][0][0])

# ── PLACEHOLDER_RULE_EVALUATOR ──


# ── 操作符比较 ──────────────────────────────────────────

def _compare(actual: Any, operator: str, expected: Any) -> bool:
    """通用操作符比较"""
    # NULL 比较
    if expected is None:
        if operator == "==":
            return actual is None
        elif operator == "!=":
            return actual is not None
    if actual is None:
        return False
    try:
        if operator == "==":
            return _normalize(actual) == _normalize(expected)
        elif operator == "!=":
            return _normalize(actual) != _normalize(expected)
        elif operator == ">=":
            return float(actual) >= float(expected)
        elif operator == ">":
            return float(actual) > float(expected)
        elif operator == "<=":
            return float(actual) <= float(expected)
        elif operator == "<":
            return float(actual) < float(expected)
        elif operator.lower() == "in":
            return actual in expected
        elif operator.lower() == "not_in":
            return actual not in expected
    except (ValueError, TypeError):
        pass
    return False


def _normalize(val: Any) -> Any:
    """归一化比较值"""
    if isinstance(val, str):
        low = val.lower()
        if low in ("true", "1", "yes"):
            return True
        if low in ("false", "0", "no"):
            return False
    if isinstance(val, (int, float)):
        if val == 0:
            return False
        if val == 1:
            return True
    return val


def _parse_time_offset(value: str) -> datetime | None:
    """解析 'NOW()-7d' / 'NOW()-30d' 等时间偏移表达式"""
    m = re.match(r"NOW\(\)\s*-\s*(\d+)d", str(value))
    if m:
        days = int(m.group(1))
        return datetime.utcnow() - timedelta(days=days)
    return None


# ── RuleEvaluator ───────────────────────────────────────

class RuleEvaluator:
    """评估单条规则的所有条件"""

    def __init__(self, db: Session):
        self.db = db
        self.resolver = FieldResolver(db)

    def evaluate(self, rule: BusinessRule, user_id: str) -> RuleResult:
        """对指定用户评估一条规则"""
        conditions = rule.conditions_json or []
        meta = rule.rule_meta_json or {}
        match_mode = meta.get("match_mode", "all")
        risk_level = meta.get("risk_level")
        rule_id = meta.get("rule_id")

        if not conditions:
            return RuleResult(
                rule_name=rule.name, triggered=False,
                matched_count=0, total_count=0, confidence=0.0,
                risk_level=risk_level, rule_id=rule_id,
            )

        results: list[ConditionResult] = []
        for cond in conditions:
            cr = self._evaluate_condition(cond, user_id)
            results.append(cr)

        matched = sum(1 for r in results if r.matched)
        total = len(results)
        triggered = self._check_match_mode(match_mode, matched, total)
        confidence = matched / total if total > 0 else 0.0

        # 更新触发计数
        if triggered:
            rule.trigger_count = (rule.trigger_count or 0) + 1
            rule.last_triggered = datetime.utcnow()

        return RuleResult(
            rule_name=rule.name, triggered=triggered,
            matched_count=matched, total_count=total,
            confidence=round(confidence, 4),
            conditions=results, risk_level=risk_level, rule_id=rule_id,
        )

    def evaluate_all(self, user_id: str) -> dict:
        """评估所有活跃的结构化规则，互斥分层：命中高风险则不算中/低"""
        rules = self.db.query(BusinessRule).filter(
            BusinessRule.status == "active",
            BusinessRule.conditions_json.isnot(None),
        ).all()

        # 按风险等级排序：高 → 中 → 低，优先评估高风险
        risk_order = {"high": 3, "medium": 2, "low": 1}
        rules.sort(
            key=lambda r: risk_order.get((r.rule_meta_json or {}).get("risk_level", ""), 0),
            reverse=True,
        )

        results = []
        final_risk = None

        for rule in rules:
            meta = rule.rule_meta_json or {}
            rule_risk = meta.get("risk_level")

            # 互斥逻辑：已命中更高等级则跳过当前等级
            if final_risk and rule_risk:
                if risk_order.get(rule_risk, 0) < risk_order.get(final_risk, 0):
                    # 仍然评估但标记为跳过
                    r = self.evaluate(rule, user_id)
                    r.triggered = False  # 强制不触发（被更高等级覆盖）
                    results.append(r)
                    continue

            r = self.evaluate(rule, user_id)
            results.append(r)
            if r.triggered and rule_risk:
                if final_risk is None or risk_order.get(rule_risk, 0) > risk_order.get(final_risk, 0):
                    final_risk = rule_risk

        self.db.commit()

        return {
            "user_id": user_id,
            "overall_risk": final_risk or "none",
            "evaluated_count": len(results),
            "triggered_count": sum(1 for r in results if r.triggered),
            "results": [self._result_to_dict(r) for r in results],
        }

    def _evaluate_condition(self, cond: dict, user_id: str) -> ConditionResult:
        """评估单个条件"""
        if cond.get("type") == "function_call":
            return self._evaluate_function_condition(cond, user_id)

        field_ref = cond.get("field", "")
        operator = cond.get("operator", "==")
        expected = cond.get("value")
        display = cond.get("display", field_ref)

        try:
            # 处理时间偏移类条件
            time_threshold = _parse_time_offset(str(expected)) if isinstance(expected, str) else None

            if time_threshold and operator == ">=":
                actual = self.resolver.resolve(field_ref, user_id)
                if actual and isinstance(actual, str):
                    try:
                        actual_dt = datetime.fromisoformat(actual.replace("Z", "+00:00"))
                        matched = actual_dt >= time_threshold
                        return ConditionResult(
                            field=field_ref, display=display, operator=operator,
                            expected=str(expected), actual=str(actual), matched=matched,
                        )
                    except ValueError:
                        pass
                matched = actual is not None
                return ConditionResult(
                    field=field_ref, display=display, operator=operator,
                    expected=str(expected), actual=str(actual) if actual else None,
                    matched=matched,
                )

            # 计数类条件（field 以 _count 结尾）
            if "_count" in field_ref.split(".")[-1]:
                actual = self.resolver.resolve_count(field_ref, user_id)
            else:
                actual = self.resolver.resolve(field_ref, user_id)

            matched = _compare(actual, operator, expected)
            return ConditionResult(
                field=field_ref, display=display, operator=operator,
                expected=expected, actual=actual, matched=matched,
            )
        except Exception as e:
            logger.warning(f"条件评估失败 {field_ref}: {e}")
            return ConditionResult(
                field=field_ref, display=display, operator=operator,
                expected=expected, matched=False, error=str(e),
            )

    def _evaluate_function_condition(self, cond: dict, user_id: str) -> ConditionResult:
        """评估函数调用类型条件"""
        callable_name = cond.get("callable_name", "")
        params = dict(cond.get("params", {}))
        operator = cond.get("operator", "==")
        expected = cond.get("value")
        display = cond.get("display", f"{callable_name}()")

        for k, v in params.items():
            if v == "$context.user_id":
                params[k] = user_id

        try:
            from app.services.function_executor import FunctionExecutor
            executor = FunctionExecutor(self.db)
            result = executor.execute_by_callable_name(callable_name, params)

            if not result.success:
                return ConditionResult(
                    field=callable_name, display=display, operator=operator,
                    expected=expected, matched=False, error=result.error,
                )

            actual = result.value
            matched = _compare(actual, operator, expected)
            return ConditionResult(
                field=callable_name, display=display, operator=operator,
                expected=expected, actual=actual, matched=matched,
            )
        except Exception as e:
            logger.warning(f"Function condition evaluation failed {callable_name}: {e}")
            return ConditionResult(
                field=callable_name, display=display, operator=operator,
                expected=expected, matched=False, error=str(e),
            )

    @staticmethod
    def _check_match_mode(mode: str, matched: int, total: int) -> bool:
        if mode == "all":
            return matched == total
        m = re.match(r"at_least_(\d+)", mode)
        if m:
            return matched >= int(m.group(1))
        return matched == total

    @staticmethod
    def _result_to_dict(r: RuleResult) -> dict:
        return {
            "rule_id": r.rule_id,
            "rule_name": r.rule_name,
            "triggered": r.triggered,
            "matched_count": r.matched_count,
            "total_count": r.total_count,
            "confidence": r.confidence,
            "risk_level": r.risk_level,
            "conditions": [
                {
                    "field": c.field, "display": c.display,
                    "operator": c.operator, "expected": c.expected,
                    "actual": c.actual, "matched": c.matched,
                    "error": c.error,
                }
                for c in r.conditions
            ],
        }

# ── PLACEHOLDER_ACTION_EXECUTOR ──


# ── RuleScreener（规则驱动批量筛选）─────────────────────

class RuleScreener:
    """
    根据规则条件批量筛选用户。
    核心思路：解析规则的 conditions_json，将每个条件转为 SQL 子查询，
    通过 user_id JOIN 找出满足 match_mode 的所有用户。
    """

    def __init__(self, db: Session):
        self.db = db
        self.resolver = FieldResolver(db)
        self._data_svc = EntityDataService(db)

    def screen(self, rule: BusinessRule, limit: int = 50) -> dict:
        """根据规则筛选命中的用户列表"""
        conditions = rule.conditions_json or []
        meta = rule.rule_meta_json or {}
        match_mode = meta.get("match_mode", "all")
        risk_level = meta.get("risk_level")

        if not conditions:
            return {"error": "规则没有结构化条件", "users": []}

        # 1. 分析条件涉及的实体和数据源
        condition_sqls = []
        for cond in conditions:
            sub = self._condition_to_subquery(cond)
            if sub:
                condition_sqls.append(sub)

        if not condition_sqls:
            return {"error": "无法将规则条件转为查询", "users": []}

        # 2. 找到主实体（用户表）作为驱动表
        main_entity, main_asset = self._find_main_entity()
        if not main_entity or not main_asset:
            return {"error": "未找到主用户实体或数据源", "users": []}

        main_table = self._data_svc.get_table_name(main_asset)
        main_pk = self._resolver_pk(main_entity)

        # 3. 根据 match_mode 构建最终 SQL
        if match_mode == "all":
            # 所有条件都满足：用 AND 连接 EXISTS 子查询
            where_parts = [f"({sq})" for sq in condition_sqls]
            final_where = " AND ".join(where_parts)
        else:
            # at_least_N：用 CASE WHEN 计数
            m = re.match(r"at_least_(\d+)", match_mode)
            threshold = int(m.group(1)) if m else len(condition_sqls)
            case_parts = [f"CASE WHEN ({sq}) THEN 1 ELSE 0 END" for sq in condition_sqls]
            sum_expr = " + ".join(case_parts)
            final_where = f"({sum_expr}) >= {threshold}"

        # 4. 构建完整查询
        sql = (
            f"SELECT u.{main_pk}, u.device_number, u.area_id, u.user_status, u.innet_months "
            f"FROM {main_table} u "
            f"WHERE {final_where} "
            f"LIMIT {min(limit, 200)}"
        )

        result = self._data_svc.execute_sql_on_entity(
            main_entity.id, sql, params={}, purpose="rule_engine.screen",
        )
        if result.get("error"):
            return {
                "error": result["error"],
                "sql_generated": sql,
                "users": [],
            }

        # 5. 格式化结果
        users = []
        columns = result.get("columns", [])
        for row in result.get("rows", []):
            user = dict(zip(columns, row))
            users.append(user)

        return {
            "rule_name": rule.name,
            "rule_id": meta.get("rule_id"),
            "risk_level": risk_level,
            "match_mode": match_mode,
            "conditions_count": len(conditions),
            "sql_conditions_resolved": len(condition_sqls),
            "matched_users": len(users),
            "users": users,
        }

    def screen_by_name(self, rule_name: str, limit: int = 50) -> dict:
        """按规则名称筛选"""
        rule = self.db.query(BusinessRule).filter(
            BusinessRule.name == rule_name,
            BusinessRule.status == "active",
        ).first()
        if not rule:
            return {"error": f"规则 '{rule_name}' 不存在或未激活", "users": []}
        if not rule.conditions_json:
            return {"error": f"规则 '{rule_name}' 没有结构化条件", "users": []}
        return self.screen(rule, limit)

    def _find_main_entity(self):
        """找到主用户实体（CbssSubscriber 或类似的核心用户表）"""
        candidates = self.db.query(OntologyEntity).filter(
            OntologyEntity.status == "active"
        ).all()
        for e in candidates:
            if "subscriber" in e.name.lower() or "user" in e.name.lower():
                resolved = self.resolver._get_entity_asset(e)
                if resolved:
                    asset, _ = resolved
                    if self._data_svc.get_table_name(asset):
                        return e, asset
        for e in candidates:
            if e.tier == 3:
                resolved = self.resolver._get_entity_asset(e)
                if resolved:
                    asset, _ = resolved
                    if self._data_svc.get_table_name(asset):
                        return e, asset
        return None, None

    def _resolver_pk(self, entity: OntologyEntity) -> str:
        return (entity.config_json or {}).get("primary_key", "user_id")

    def _condition_to_subquery(self, cond: dict) -> str | None:
        """将单个条件转为 SQL 表达式（以 u.user_id 为关联键）"""
        field_ref = cond.get("field", "")
        operator = cond.get("operator", "==")
        expected = cond.get("value")

        if "." not in field_ref:
            return None

        entity_name, prop_name = field_ref.split(".", 1)
        entity = self.resolver._get_entity(entity_name)
        if not entity:
            return None

        resolved = self.resolver._get_entity_asset(entity)
        if not resolved:
            return None
        asset, _ = resolved
        table = self._data_svc.get_table_name(asset)
        if not table:
            return None
        pk = self._resolver_pk(entity)

        # 检查是否为 computed_property
        attr = next((a for a in entity.attributes if a.name == prop_name), None)
        if attr and attr.type == "computed" and attr.constraints_json:
            expr = attr.constraints_json.get("expression", "")
            # 将本体简写时间语法转为 MySQL 语法
            expr = self._fix_time_syntax(expr)
            # 根据 operator 和 expected 决定是否取反
            if operator == "==" and expected is False:
                return f"EXISTS (SELECT 1 FROM {table} t WHERE t.{self._join_key(pk)} = u.user_id AND NOT ({expr}))"
            elif operator == "==" and expected is True:
                return f"EXISTS (SELECT 1 FROM {table} t WHERE t.{self._join_key(pk)} = u.user_id AND ({expr}))"
            elif operator == "!=" and expected is False:
                return f"EXISTS (SELECT 1 FROM {table} t WHERE t.{self._join_key(pk)} = u.user_id AND ({expr}))"
            else:
                return f"EXISTS (SELECT 1 FROM {table} t WHERE t.{self._join_key(pk)} = u.user_id AND ({expr}))"

        # 计数类条件
        if "_count" in prop_name:
            sql_op = self._op_to_sql(operator)
            if expected == 0 and operator == "==":
                # complaint_count == 0 → 不存在记录
                return f"NOT EXISTS (SELECT 1 FROM {table} t WHERE t.{self._join_key(pk)} = u.user_id)"
            return (
                f"(SELECT COUNT(*) FROM {table} t WHERE t.{self._join_key(pk)} = u.user_id) "
                f"{sql_op} {self._format_value(expected)}"
            )

        # 时间偏移条件
        if isinstance(expected, str) and "NOW()" in expected:
            time_expr = self._time_offset_to_sql(expected)
            if time_expr:
                sql_op = self._op_to_sql(operator)
                return f"EXISTS (SELECT 1 FROM {table} t WHERE t.{self._join_key(pk)} = u.user_id AND t.{prop_name} {sql_op} {time_expr})"

        # NULL 条件
        if expected is None:
            if operator == "==":
                return f"EXISTS (SELECT 1 FROM {table} t WHERE t.{self._join_key(pk)} = u.user_id AND t.{prop_name} IS NULL)"
            elif operator == "!=":
                return f"EXISTS (SELECT 1 FROM {table} t WHERE t.{self._join_key(pk)} = u.user_id AND t.{prop_name} IS NOT NULL)"

        # 普通条件
        sql_op = self._op_to_sql(operator)
        val = self._format_value(expected)
        return f"EXISTS (SELECT 1 FROM {table} t WHERE t.{self._join_key(pk)} = u.user_id AND t.{prop_name} {sql_op} {val})"

    @staticmethod
    def _join_key(pk: str) -> str:
        """确定 JOIN 键：如果主键不是 user_id 类的，用 device_number 关联"""
        if pk in ("user_id", "subs_id"):
            return pk
        # 对于 sheet_id、device_number 等非 user_id 主键的表，用 device_number 关联
        return "device_number"

    @staticmethod
    def _fix_time_syntax(expr: str) -> str:
        """将本体简写时间语法转为 MySQL 语法"""
        import re as _re
        # NOW() + 30d → DATE_ADD(NOW(), INTERVAL 30 DAY)
        expr = _re.sub(r'NOW\(\)\s*\+\s*(\d+)d', r'DATE_ADD(NOW(), INTERVAL \1 DAY)', expr)
        # NOW() - 30d → DATE_SUB(NOW(), INTERVAL 30 DAY)
        expr = _re.sub(r'NOW\(\)\s*-\s*(\d+)d', r'DATE_SUB(NOW(), INTERVAL \1 DAY)', expr)
        return expr

    @staticmethod
    def _op_to_sql(op: str) -> str:
        return {"==": "=", "!=": "!=", ">=": ">=", ">": ">", "<=": "<=", "<": "<"}.get(op, "=")

    @staticmethod
    def _format_value(val: Any) -> str:
        if isinstance(val, bool):
            return "1" if val else "0"
        if isinstance(val, (int, float)):
            return str(val)
        if isinstance(val, str):
            return f"'{val}'"
        return f"'{val}'"

    @staticmethod
    def _time_offset_to_sql(value: str) -> str | None:
        m = re.match(r"NOW\(\)\s*-\s*(\d+)d", value)
        if m:
            days = int(m.group(1))
            return f"DATE_SUB(NOW(), INTERVAL {days} DAY)"
        return None

