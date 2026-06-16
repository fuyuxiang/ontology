"""Test workflow executor for component nodes"""
from unittest.mock import MagicMock, patch

from app.services.workflow_executor_components import (
    _eval_expression,
    _resolve_params,
    execute_component_node,
)


def test_resolve_params_variable():
    mapping = {"score": {"source": "variable", "var_name": "input_score"}}
    context = {"vars": {"input_score": 85}}
    result = _resolve_params(mapping, context)
    assert result == {"score": 85}


def test_resolve_params_node():
    mapping = {"amount": {"source": "node", "node_id": "node1", "field": "output.total"}}
    context = {"nodes": {"node1": {"output": {"total": 100}}}}
    result = _resolve_params(mapping, context)
    assert result == {"amount": 100}


def test_resolve_params_expression():
    mapping = {"discount": {"source": "expression", "expr": '{{vars["price"] * 0.8}}'}}
    context = {"vars": {"price": 100}}
    result = _resolve_params(mapping, context)
    assert result == {"discount": 80.0}


def test_eval_expression_plain_string():
    assert _eval_expression("hello", {}) == "hello"


def test_execute_function_node():
    db = MagicMock()
    mock_vf = MagicMock()
    mock_vf.logic_type = "expression"
    mock_vf.logic_body = 'params["score"] * 0.8'
    mock_vf.input_schema = [{"name": "score", "type": "number"}]
    mock_vf.name = "calc"
    mock_vf.callable_name = "calc"
    mock_vf.entity_id = None
    mock_vf.execution_count = 0
    mock_vf.last_executed = None
    db.query.return_value.filter.return_value.first.return_value = mock_vf

    node_data = {"ref_type": "function", "ref_id": "vf1",
                 "param_mapping": {"score": {"source": "variable", "var_name": "s"}}}
    context = {"vars": {"s": 100}}

    result = execute_component_node(db, node_data, context)
    assert result["success"] is True
    assert result["value"] == 80.0


def test_execute_rule_node_triggered():
    db = MagicMock()
    mock_vr = MagicMock()
    mock_vr.conditions_json = [{"field": "score", "operator": "<", "value": 60}]
    db.query.return_value.filter.return_value.first.return_value = mock_vr

    node_data = {"ref_type": "rule", "ref_id": "vr1",
                 "param_mapping": {"score": {"source": "variable", "var_name": "credit"}}}
    context = {"vars": {"credit": 45}}

    result = execute_component_node(db, node_data, context)
    assert result["triggered"] is True


def test_execute_rule_node_not_triggered():
    db = MagicMock()
    mock_vr = MagicMock()
    mock_vr.conditions_json = [{"field": "score", "operator": "<", "value": 60}]
    db.query.return_value.filter.return_value.first.return_value = mock_vr

    node_data = {"ref_type": "rule", "ref_id": "vr1",
                 "param_mapping": {"score": {"source": "variable", "var_name": "credit"}}}
    context = {"vars": {"credit": 75}}

    result = execute_component_node(db, node_data, context)
    assert result["triggered"] is False


def test_execute_not_found():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    node_data = {"ref_type": "function", "ref_id": "missing", "param_mapping": {}}
    result = execute_component_node(db, node_data, {})
    assert result["success"] is False
    assert "not found" in result["error"]
