"""Integration test: rule with function_call condition"""
from unittest.mock import MagicMock

from app.services.rule_engine import RuleEvaluator


def test_rule_evaluates_function_call_condition():
    """A rule condition of type function_call should invoke FunctionExecutor"""
    db = MagicMock()

    rule = MagicMock()
    rule.name = "test_rule"
    rule.conditions_json = [
        {
            "type": "function_call",
            "callable_name": "calc_score",
            "params": {"user_id": "$context.user_id"},
            "operator": ">=",
            "value": 0.7,
            "display": "calc_score() >= 0.7",
        }
    ]
    rule.rule_meta_json = {"match_mode": "all"}
    rule.trigger_count = 0
    rule.last_triggered = None

    mock_func = MagicMock()
    mock_func.logic_type = "expression"
    mock_func.logic_body = "0.85"
    mock_func.status = "active"
    mock_func.callable_name = "calc_score"
    mock_func.entity_id = None
    mock_func.name = "calc_score"
    mock_func.input_schema = []
    mock_func.execution_count = 0
    mock_func.last_executed = None

    db.query.return_value.filter.return_value.first.return_value = mock_func

    evaluator = RuleEvaluator(db)
    result = evaluator.evaluate(rule, "user-001")

    assert result.triggered is True
    assert result.confidence == 1.0
    assert result.conditions[0].matched is True
    assert result.conditions[0].actual == 0.85


def test_rule_function_call_not_triggered():
    """Function returns value below threshold — rule should not trigger"""
    db = MagicMock()

    rule = MagicMock()
    rule.name = "low_score_rule"
    rule.conditions_json = [
        {
            "type": "function_call",
            "callable_name": "calc_score",
            "params": {"user_id": "$context.user_id"},
            "operator": ">=",
            "value": 0.7,
            "display": "calc_score() >= 0.7",
        }
    ]
    rule.rule_meta_json = {"match_mode": "all"}
    rule.trigger_count = 0
    rule.last_triggered = None

    mock_func = MagicMock()
    mock_func.logic_type = "expression"
    mock_func.logic_body = "0.3"
    mock_func.status = "active"
    mock_func.callable_name = "calc_score"
    mock_func.entity_id = None
    mock_func.name = "calc_score"
    mock_func.input_schema = []
    mock_func.execution_count = 0
    mock_func.last_executed = None

    db.query.return_value.filter.return_value.first.return_value = mock_func

    evaluator = RuleEvaluator(db)
    result = evaluator.evaluate(rule, "user-001")

    assert result.triggered is False
    assert result.conditions[0].matched is False
    assert result.conditions[0].actual == 0.3
