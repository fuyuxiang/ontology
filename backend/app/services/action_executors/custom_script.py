from textwrap import indent
from app.services.function_runtime.sandbox import UnifiedSandbox
from .base import BaseActionExecutor, ExecutionResult
from app.services.function_runtime.models import ExecContext

class CustomScriptExecutor(BaseActionExecutor):
    async def execute(self, type_config, params, dry_run=False):
        context = type_config.get("_exec_context") or ExecContext(ontology_id=type_config.get("ontology_id"))
        script = type_config.get("script", "")
        source = type_config.get("source_code")
        if source is None and type_config.get("source_path"):
            from pathlib import Path
            from app.config import settings
            try:
                path = Path(type_config["source_path"]).resolve()
                path.relative_to(Path(settings.WORKSPACE_ROOT).resolve())
                source = path.read_text(encoding="utf-8")
            except (OSError, ValueError) as exc:
                return ExecutionResult(False, f"行动工作区源码无法读取: {exc}")
        if source is None and not script.strip():
            return ExecutionResult(False, "脚本内容不能为空")
        code = source if source is not None else "def execute_action(params):\n    result = {}\n" + indent(script, "    ") + "\n    return result\n"
        validation = UnifiedSandbox().validate(code)
        if not validation.valid:
            return ExecutionResult(False, "脚本安全检查失败: " + "; ".join(validation.errors))
        if dry_run:
            return ExecutionResult(True, "[Dry Run] Would execute custom Python script", {"script_length": len(script), "params": params})
        try:
            from app.database import SessionLocal
            from app.services.function_executor import FunctionExecutor
            from app.services.function_runtime.executor import FunctionRuntimeExecutor
            from app.services.function_runtime.registry import FunctionRegistry
            from app.models.version import OntologyVersionEntity
            from types import SimpleNamespace
            db = self.db or SessionLocal()
            try:
                entity = db.get(OntologyVersionEntity, type_config["_version_entity_id"]) if type_config.get("_version_entity_id") else None
                version_id = entity.version_id if entity else type_config.get("version_id")
                if version_id:
                    if context.version_id and context.version_id != version_id:
                        raise PermissionError("行动不属于当前发布版本")
                    context.version_id = version_id
                runtime = FunctionRuntimeExecutor(FunctionRegistry(db), UnifiedSandbox(), db)
                nested = FunctionExecutor(db)._nested_callable(SimpleNamespace(ontology_id=type_config.get("ontology_id"), version_id=version_id), context)
                namespace = {"params": params, "call_function": nested,
                    **runtime._build_ontology_helpers(context=context)}
                result = UnifiedSandbox().execute(code, type_config.get("func_name", "execute_action") if source is not None else "execute_action", namespace, timeout=5)
            finally:
                if self.db is None:db.close()
            if not isinstance(result, dict):
                return ExecutionResult(False, "行动脚本 result 必须为对象",
                    {"outcome": "partial_committed" if context.committed_writes else "failed",
                     "committed_writes": list(context.committed_writes)})
            if context.committed_writes:
                result = {**result, "outcome": "committed", "committed_writes": list(context.committed_writes)}
            return ExecutionResult(True, "Script executed successfully", result)
        except Exception as exc:
            return ExecutionResult(False, f"Script error: {exc}", {"error": str(exc),
                "outcome": context.failure_outcome(exc) or "failed", "committed_writes": list(context.committed_writes),
                "uncertain_write": context.active_write})
    @classmethod
    def get_config_schema(cls):
        return {"script": {"type": "string", "required": True, "description": "Python 脚本，通过 params 获取输入，结果写入 result 字典"}}
    @classmethod
    def get_label(cls):
        return "自定义脚本"
    @classmethod
    def get_description(cls):
        return "运行自定义 Python 脚本"
