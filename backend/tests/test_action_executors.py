import pytest
from app.services.action_executors import get_executor, get_all_type_info
from app.services.action_executors.base import ExecutionResult


@pytest.mark.asyncio
async def test_api_call_dry_run():
    executor = get_executor("api_call")
    config = {"url": "https://example.com/api/$id", "method": "POST", "body": {"name": "$name"}}
    result = await executor.execute(config, {"id": "123", "name": "test"}, dry_run=True)
    assert result.success is True
    assert "[Dry Run]" in result.message
    assert result.output["url"] == "https://example.com/api/123"


@pytest.mark.asyncio
async def test_sql_exec_dry_run():
    executor = get_executor("sql_exec")
    config = {"connection_id": "conn_1", "sql": "UPDATE users SET status='$status' WHERE id=$id"}
    result = await executor.execute(config, {"status": "active", "id": "42"}, dry_run=True)
    assert result.success is True
    assert "conn_1" in result.message
    assert "active" in result.output["sql"]


@pytest.mark.asyncio
async def test_modify_attribute_dry_run():
    executor = get_executor("modify_attribute")
    config = {"target_entity_id": "e1", "target_attribute": "price", "value_expression": "new_price"}
    result = await executor.execute(config, {"new_price": "99.9"}, dry_run=True)
    assert result.success is True
    assert "price" in result.message
    assert result.output["value"] == "99.9"


@pytest.mark.asyncio
async def test_notification_dry_run():
    executor = get_executor("notification")
    config = {"channel": "email", "recipient": "$email", "message_template": "Hello $name"}
    result = await executor.execute(config, {"email": "a@b.com", "name": "Alice"}, dry_run=True)
    assert result.success is True
    assert result.output["recipient"] == "a@b.com"
    assert result.output["message"] == "Hello Alice"


@pytest.mark.asyncio
async def test_call_function_dry_run():
    executor = get_executor("call_function")
    config = {"function_id": "fn_1", "param_mapping": {"x": "input_x"}}
    result = await executor.execute(config, {"input_x": "hello"}, dry_run=True)
    assert result.success is True
    assert result.output["function_id"] == "fn_1"
    assert result.output["params"]["x"] == "hello"


@pytest.mark.asyncio
async def test_custom_script_success():
    executor = get_executor("custom_script")
    config = {"script": "result['total'] = params['a'] + params['b']"}
    result = await executor.execute(config, {"a": 1, "b": 2}, dry_run=False)
    assert result.success is True
    assert result.output["total"] == 3


@pytest.mark.asyncio
async def test_custom_script_error():
    executor = get_executor("custom_script")
    config = {"script": "raise ValueError('bad input')"}
    result = await executor.execute(config, {}, dry_run=False)
    assert result.success is False
    assert "bad input" in result.message


def test_get_all_type_info():
    types = get_all_type_info()
    assert len(types) == 6
    type_keys = [t["type_key"] for t in types]
    assert "api_call" in type_keys
    assert "custom_script" in type_keys


def test_get_executor_unknown_type():
    with pytest.raises(ValueError, match="Unknown action type"):
        get_executor("nonexistent")
