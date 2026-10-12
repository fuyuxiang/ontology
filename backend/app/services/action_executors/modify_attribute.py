from .base import BaseActionExecutor, ExecutionResult


def validate_value_expression(value):
    """Expressions are explicit so existing literal values keep their meaning."""
    if not isinstance(value, str) or not value.startswith("expr:"):
        return None
    import ast
    from app.services.function_runtime.sandbox import UnifiedSandbox
    expression = value[5:].strip()
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"赋值表达式语法错误: {exc.msg}") from exc
    validation = UnifiedSandbox().validate(expression)
    if not validation.valid:
        raise ValueError("赋值表达式安全检查失败: " + "; ".join(validation.errors))
    return ast.unparse(tree.body)


def resolve_value(value, params):
    expression = validate_value_expression(value)
    if expression is not None:
        from app.services.function_runtime.sandbox import UnifiedSandbox
        return UnifiedSandbox().execute_expression(expression, {"params": params}, timeout=2)
    return params.get(value, value) if isinstance(value, str) else value


class ModifyAttributeExecutor(BaseActionExecutor):
    async def execute(self, type_config: dict, params: dict, dry_run: bool = False) -> ExecutionResult:
        target_entity_id = type_config.get("target_entity_id")
        target_attribute = type_config.get("target_attribute")
        value_expression = type_config.get("value_expression", "")

        try:
            resolved_value = resolve_value(value_expression, params)
        except Exception as exc:
            return ExecutionResult(False, f"赋值表达式错误: {exc}", {"error": str(exc), "outcome": "failed"})

        if dry_run:
            return ExecutionResult(
                success=True,
                message=f"[Dry Run] Would set {target_attribute} = {resolved_value}",
                output={"entity_id": target_entity_id, "attribute": target_attribute, "value": resolved_value},
            )

        from app.database import SessionLocal
        from app.services.object_mutation_service import ObjectMutationService
        db = self.db or SessionLocal()
        record_id_key = type_config.get("record_id_param", "record_id")
        record_id = params.get(record_id_key, type_config.get("record_id"))
        try:
            from app.models.version import OntologyVersionEntity
            version_entity = db.get(OntologyVersionEntity, type_config["_version_entity_id"]) if type_config.get("_version_entity_id") else None
            output = ObjectMutationService(db, version_entity).update(target_entity_id, record_id, {target_attribute: resolved_value})
            return ExecutionResult(True, "实例属性已提交并回读", output)
        except Exception as exc:
            return ExecutionResult(False, f"实例修改失败: {exc}", {"error": str(exc), "outcome": getattr(exc, "outcome", "failed")})
        finally:
            if self.db is None:
                db.close()

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "target_entity_id": {"type": "string", "required": True, "description": "目标实体 ID"},
            "target_attribute": {"type": "string", "required": True, "description": "目标属性名"},
            "value_expression": {"type": "string", "required": True, "description": "参数名或字面值；表达式须以 expr: 开头，如 expr: params['price'] * 1.1"},
            "record_id_param": {"type": "string", "required": False, "description": "实例 ID 入参名，默认 record_id"},
        }

    @classmethod
    def get_label(cls) -> str:
        return "修改实体属性"

    @classmethod
    def get_description(cls) -> str:
        return "修改本体实例的属性值"
