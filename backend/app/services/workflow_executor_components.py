"""Execute function-call / rule-evaluate / action-execute nodes in workflow context."""
import logging
import re
from typing import Any

from sqlalchemy.orm import Session

from app.models.version_components import (
    OntologyVersionFunction, OntologyVersionRule, OntologyVersionAction,
)
from app.services.function_executor import FunctionExecutor

logger = logging.getLogger(__name__)


def _resolve_params(param_mapping: dict, context: dict) -> dict:
    """Resolve param_mapping against execution context.

    Each param has a source type:
    - "variable": get from context["vars"][var_name]
    - "node": get from context["nodes"][node_id] following field path
    - "expression": evaluate {{...}} template expression
    """
    resolved = {}
    for param_name, mapping in param_mapping.items():
        source = mapping.get("source")
        if source == "variable":
            resolved[param_name] = context.get("vars", {}).get(mapping.get("var_name"))
        elif source == "node":
            node_output = context.get("nodes", {}).get(mapping.get("node_id"), {})
            field_path = (mapping.get("field") or "").split(".")
            val = node_output
            for part in field_path:
                if isinstance(val, dict):
                    val = val.get(part)
                else:
                    val = None
                    break
            resolved[param_name] = val
        elif source == "expression":
            resolved[param_name] = _eval_expression(mapping.get("expr", ""), context)
        else:
            resolved[param_name] = None
    return resolved


def _eval_expression(expr: str, context: dict) -> Any:
    """Evaluate a simple template expression like {{vars.amount * 0.8}}."""
    match = re.match(r'^\{\{(.+)\}\}$', expr.strip())
    if not match:
        return expr
    inner = match.group(1).strip()
    ns = {"nodes": context.get("nodes", {}), "vars": context.get("vars", {})}
    try:
        return eval(inner, {"__builtins__": {}}, ns)
    except Exception:
        return None


def execute_component_node(db: Session, node_data: dict, context: dict) -> dict:
    """Execute a component node and return result dict."""
    ref_type = node_data.get("ref_type")
    ref_id = node_data.get("ref_id")
    param_mapping = node_data.get("param_mapping", {})

    resolved_params = _resolve_params(param_mapping, context)

    if ref_type == "function":
        vf = db.query(OntologyVersionFunction).filter(
            OntologyVersionFunction.id == ref_id
        ).first()
        if not vf:
            return {"success": False, "error": f"Version function {ref_id} not found"}
        executor = FunctionExecutor(db)
        result = executor.execute(vf, resolved_params)
        return {"success": result.success, "value": result.value,
                "error": result.error, "execution_ms": result.execution_ms}

    elif ref_type == "rule":
        vr = db.query(OntologyVersionRule).filter(
            OntologyVersionRule.id == ref_id
        ).first()
        if not vr:
            return {"triggered": False, "error": f"Version rule {ref_id} not found"}
        triggered = _evaluate_rule_conditions(vr, resolved_params)
        return {"triggered": triggered, "confidence": 1.0 if triggered else 0.0,
                "conditions": []}

    elif ref_type == "action":
        va = db.query(OntologyVersionAction).filter(
            OntologyVersionAction.id == ref_id
        ).first()
        if not va:
            return {"success": False, "error": f"Version action {ref_id} not found"}
        try:
            from app.services.action_executors import run_executor_sync
            result = run_executor_sync(va.action_type, va.type_config or {}, resolved_params)
            return {"success": result.success, "message": result.message,
                    "output": result.output}
        except Exception as e:
            logger.warning(f"Action execution failed for {ref_id}: {e}")
            return {"success": False, "error": str(e)}

    return {"success": False, "error": f"Unknown ref_type: {ref_type}"}


def _evaluate_rule_conditions(vr, params: dict) -> bool:
    """Simple rule condition evaluator for versioned rules."""
    conditions = vr.conditions_json or []
    if not conditions:
        return False

    for cond in conditions:
        field = cond.get("field", "")
        operator = cond.get("operator", "==")
        expected = cond.get("value")
        actual = params.get(field)

        if actual is None:
            return False

        try:
            if operator == "==":
                if actual != expected:
                    return False
            elif operator == "!=":
                if actual == expected:
                    return False
            elif operator == "<":
                if not (actual < expected):
                    return False
            elif operator == "<=":
                if not (actual <= expected):
                    return False
            elif operator == ">":
                if not (actual > expected):
                    return False
            elif operator == ">=":
                if not (actual >= expected):
                    return False
            elif operator == "in":
                if actual not in expected:
                    return False
        except (TypeError, ValueError):
            return False

    return True
