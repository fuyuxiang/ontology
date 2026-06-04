from .base import BaseActionExecutor, ExecutionResult


class ModifyAttributeExecutor(BaseActionExecutor):
    async def execute(self, type_config: dict, params: dict, dry_run: bool = False) -> ExecutionResult:
        target_entity_id = type_config.get("target_entity_id")
        target_attribute = type_config.get("target_attribute")
        value_expression = type_config.get("value_expression", "")

        resolved_value = params.get(value_expression, value_expression)

        if dry_run:
            return ExecutionResult(
                success=True,
                message=f"[Dry Run] Would set {target_attribute} = {resolved_value}",
                output={"entity_id": target_entity_id, "attribute": target_attribute, "value": resolved_value},
            )

        return ExecutionResult(
            success=True,
            message=f"Set {target_attribute} = {resolved_value}",
            output={"entity_id": target_entity_id, "attribute": target_attribute, "value": resolved_value},
        )

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "target_entity_id": {"type": "string", "required": True, "description": "目标实体 ID"},
            "target_attribute": {"type": "string", "required": True, "description": "目标属性名"},
            "value_expression": {"type": "string", "required": True, "description": "赋值表达式或参数名"},
        }

    @classmethod
    def get_label(cls) -> str:
        return "修改实体属性"

    @classmethod
    def get_description(cls) -> str:
        return "修改本体实例的属性值"
