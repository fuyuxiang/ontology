"""Shared definition validation for saving and publishing executable actions."""
from pathlib import Path
from app.models.entity import EntityAttribute, OntologyEntity


def validate_parameter_references(db, parameters, ontology_id):
    for parameter in parameters or []:
        if not isinstance(parameter, dict):
            raise ValueError("参数定义必须为对象")
        attribute_id = parameter.get("attribute_id") or parameter.get("entity_attribute_id")
        entity_id = parameter.get("entity_id")
        entity = db.get(OntologyEntity, entity_id) if entity_id else None
        if entity_id and not entity:
            raise ValueError("参数关联对象不存在")
        if attribute_id:
            attribute = db.get(EntityAttribute, attribute_id)
            if not attribute:
                raise ValueError("参数关联属性不存在")
            if entity_id and attribute.entity_id != entity_id:
                raise ValueError("参数关联属性与对象不一致")
            entity = db.get(OntologyEntity, attribute.entity_id)
        if entity and entity.ontology_id != ontology_id:
            raise ValueError("参数关联对象及属性必须属于当前本体")


def validate_action_config(db, action_type, config, ontology_id, entity_id=None):
    from app.services.action_executors import get_executor
    from app.services.version_component_snapshot import _validate_source_entry
    executor = get_executor(action_type, db=db)
    config = config or {}
    missing = []
    for name, field in executor.get_config_schema().items():
        value = config.get(name)
        if action_type == "custom_script" and name == "script" and (config.get("source_code") or config.get("source_path")):
            continue
        if action_type == "call_function" and name == "function_name":
            value = value or config.get("callable_name") or config.get("function_id")
        if field.get("required") and (value is None or (isinstance(value, str) and not value.strip())):
            missing.append(name)
        expected = field.get("type")
        if value is not None and ((expected == "string" and not isinstance(value, str)) or
                (expected == "object" and not isinstance(value, dict)) or
                (expected == "number" and (isinstance(value, bool) or not isinstance(value, (int, float))))):
            raise ValueError(f"行动配置 {name} 类型必须为 {expected}")
        if value is not None and field.get("enum") and value not in field["enum"]:
            raise ValueError(f"行动配置 {name} 无效")
    if missing:
        raise ValueError("行动配置缺少必填项: " + ", ".join(missing))
    if action_type == "api_call" and not config["url"].startswith(("http://", "https://")):
        raise ValueError("API URL 必须使用 http 或 https")
    if action_type in {"api_call", "notification"} and "timeout_seconds" in config:
        try:
            valid_timeout = .05 <= float(config["timeout_seconds"]) <= 120
        except (ValueError, TypeError):
            valid_timeout = False
        if not valid_timeout:
            raise ValueError("timeout_seconds 必须在 0.05~120 秒范围内")
    if action_type == "sql_exec":
        from app.models.connection import Connection
        connection = db.get(Connection, config["connection_id"])
        if not connection:
            raise ValueError("行动数据源连接不存在")
    if action_type == "modify_attribute":
        from app.services.action_executors.modify_attribute import validate_value_expression
        validate_value_expression(config["value_expression"])
        target = db.get(OntologyEntity, config["target_entity_id"])
        if not target or target.ontology_id != ontology_id or (entity_id and target.id != entity_id):
            raise ValueError("行动修改目标必须属于当前本体及关联对象")
        if not db.query(EntityAttribute).filter_by(entity_id=target.id, name=config["target_attribute"]).first():
            raise ValueError("行动修改目标属性不存在")
    if action_type == "call_function":
        from app.models.function import OntologyFunction
        identifier = config.get("function_name") or config.get("callable_name") or config.get("function_id")
        candidates = db.query(OntologyFunction).filter_by(status="active").filter(
            (OntologyFunction.callable_name == identifier) | (OntologyFunction.id == identifier)).all()
        functions = [function for function in candidates if (function.ontology_id or
            (function.entity.ontology_id if function.entity else None)) == ontology_id]
        if len(functions) != 1:
            raise ValueError("行动调用函数不存在、未激活或不属于当前本体")
    if action_type == "custom_script":
        source = config.get("source_code")
        if source is None and config.get("source_path"):
            try:
                source = Path(config["source_path"]).read_text(encoding="utf-8")
            except OSError as exc:
                raise ValueError("行动工作区源码不可读取") from exc
        if source is not None:
            _validate_source_entry(source, config.get("func_name"), "行动")
        else:
            from textwrap import indent
            from app.services.function_runtime.sandbox import UnifiedSandbox
            validation = UnifiedSandbox().validate("def execute_action(params):\n" + indent(config["script"], "    "))
            if not validation.valid:
                raise ValueError("行动脚本校验失败: " + "; ".join(validation.errors))
