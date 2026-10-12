"""FunctionExecutor — 根据 logic_type 执行函数"""
import logging
import time
from types import SimpleNamespace
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models.function import OntologyFunction
from app.services.function_runtime.models import ExecContext, FunctionWriteRequested

logger = logging.getLogger(__name__)


@dataclass
class FunctionResult:
    success: bool
    value: Any = None
    error: str | None = None
    execution_ms: float = 0
    outcome: str | None = None
    requested_write: dict | None = None
    committed_writes: list[dict] | None = None


class FunctionExecutor:
    def __init__(self, db: Session):
        self.db = db
        self._call_stack = []

    def _nested_callable(self, func, context=None):
        context = context or ExecContext(ontology_id=getattr(func, "ontology_id", None))
        def call(name, params):
            if context.version_id:
                from app.models.version_components import OntologyVersionFunction
                rows = self.db.query(OntologyVersionFunction).filter_by(version_id=context.version_id, callable_name=name).all()
                if len(rows) != 1:
                    raise ValueError(f"函数 {name} 不在当前发布版本中")
                result = self.execute_snapshot(rows[0], params, context=context)
            else:
                result = self.execute_by_callable_name(name, params, context.ontology_id, context=context)
            if result.requested_write:
                raise FunctionWriteRequested(result.requested_write)
            if not result.success:
                error = RuntimeError(result.error)
                error.outcome = result.outcome
                raise error
            return result.value
        return call

    def execute(self, func: OntologyFunction, params: dict, context=None) -> FunctionResult:
        start = time.time()
        supplied = context or getattr(func, "_exec_context", None)
        context = supplied if isinstance(supplied, ExecContext) else ExecContext()
        ontology_id = getattr(func, "ontology_id", None)
        if isinstance(ontology_id, (str, int)):
            if context.ontology_id is not None and str(context.ontology_id) != str(ontology_id):
                return FunctionResult(False, error="函数不属于当前本体")
            context.ontology_id = ontology_id
        version_id = getattr(func, "version_id", None)
        if isinstance(version_id, str):
            if context.version_id and context.version_id != version_id:
                return FunctionResult(False, error="函数不属于当前发布版本")
            context.version_id = version_id
        name = getattr(func, "callable_name", None)
        name = name if isinstance(name, str) and name else func.name
        delegated = isinstance(getattr(func, "source_path", None), str) and not isinstance(getattr(func, "source_code", None), str)
        pushed = False
        try:
            entity_id = getattr(func, "entity_id", None)
            if entity_id is not None:
                context.check_entity(entity_id)
            identifier = getattr(func, "source_function_id", None) or getattr(func, "id", None)
            if context.function_ids is not None and identifier not in context.function_ids:
                raise PermissionError("函数不在当前授权范围内")
            if not delegated:
                if name in context.call_stack or len(context.call_stack) >= context.max_depth:
                    raise RuntimeError("函数嵌套调用循环或超过最大深度")
                context.call_stack.append(name)
                pushed = True
            if context._chain_start is None:
                context._chain_start = time.time()
            if time.time() - context._chain_start >= context.total_timeout_sec:
                raise TimeoutError("调用链总超时")
            from app.services.agent_actions import validate_parameters
            params = validate_parameters(func.input_schema, params)
            missing = self._check_required(func, params)
            if missing:
                return FunctionResult(
                    success=False,
                    error=f"缺少必填参数：{', '.join(missing)}",
                    execution_ms=(time.time() - start) * 1000,
                )
            if func.logic_type == "expression":
                result = self._execute_expression(func, params, context)
            elif func.logic_type == "sql":
                result = self._execute_sql_func(func, params)
            elif func.logic_type == "python":
                result = self._execute_python(func, params, context)
            else:
                return FunctionResult(success=False, error=f"Unknown logic_type: {func.logic_type}")

            elapsed = (time.time() - start) * 1000
            return FunctionResult(success=True, value=result, execution_ms=elapsed,
                                  outcome="committed" if context.committed_writes else None,
                                  committed_writes=list(context.committed_writes))
        except FunctionWriteRequested as request:
            return FunctionResult(success=True, execution_ms=(time.time()-start)*1000,
                                  outcome="simulated" if context.action_mode == "simulation" else "pending_confirmation",
                                  requested_write=request.request)
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            logger.warning(f"Function {func.name} execution failed: {e}")
            return FunctionResult(success=False, error=str(e), execution_ms=elapsed, outcome=context.failure_outcome(e),
                                  committed_writes=list(context.committed_writes))
        finally:
            if pushed:
                context.call_stack.pop()

    @staticmethod
    def _check_required(func: OntologyFunction, params: dict) -> list[str]:
        """返回缺失的必填参数名列表。input_schema 中 required=True 的参数必须在 params 中出现。"""
        missing = []
        for p in func.input_schema or []:
            if not isinstance(p, dict):
                continue
            name = p.get("name")
            if name and p.get("required") and name not in params:
                missing.append(name)
        return missing

    def execute_by_callable_name(self, callable_name: str, params: dict, ontology_id=None, *, context=None) -> FunctionResult:
        query = self.db.query(OntologyFunction).filter(
            (OntologyFunction.callable_name == callable_name) | (OntologyFunction.id == callable_name),
            OntologyFunction.status == "active",
        )
        if ontology_id:
            from app.models.entity import OntologyEntity
            query = query.filter((OntologyFunction.ontology_id == ontology_id) |
                                 OntologyFunction.entity_id.in_(self.db.query(OntologyEntity.id).filter_by(ontology_id=ontology_id)))
        funcs = query.all()
        if len(funcs) != 1:
            return FunctionResult(success=False, error=f"Function '{callable_name}' not found or inactive")
        return self.execute(funcs[0], params, context=context)

    def execute_snapshot(self, snapshot, params: dict, *, version_id=None, context=None) -> FunctionResult:
        """Execute the exact stored definition; nested calls stay in this version."""
        fields = {c.name: getattr(snapshot, c.name) for c in snapshot.__table__.columns} if hasattr(snapshot, "__table__") else dict(snapshot)
        fields.setdefault("entity_id", None)
        fields.setdefault("source_path", None)
        fields["version_id"] = version_id or fields.get("version_id")
        if not fields.get("entity_id") and fields.get("version_entity_id"):
            from app.models.version import OntologyVersionEntity
            entity = self.db.get(OntologyVersionEntity, fields["version_entity_id"])
            fields["entity_id"] = entity.source_entity_id if entity else None
        fields["_exec_context"] = context
        return self.execute(SimpleNamespace(**fields), params)

    def _execute_expression(self, func: OntologyFunction, params: dict, context=None) -> Any:
        if not func.logic_body or not func.logic_body.strip():
            raise ValueError("Expression body is empty")
        from app.services.function_runtime.sandbox import UnifiedSandbox
        return UnifiedSandbox().execute_expression(func.logic_body, {
            "params": params,
            "call_function": self._nested_callable(func, context),
        }, timeout=int(getattr(func, "timeout_seconds", None) or 30))

    def _execute_sql_func(self, func: OntologyFunction, params: dict) -> Any:
        if isinstance(getattr(func, "version_id", None), str):
            from app.models.version import OntologyVersionEntity
            from app.services.version_entity_data import VersionEntityDataService
            entity = self.db.query(OntologyVersionEntity).filter_by(version_id=func.version_id, source_entity_id=func.entity_id).first()
            if not entity:
                raise ValueError("SQL 函数未绑定当前发布版本的对象")
            sql_result = VersionEntityDataService(self.db, entity).execute_sql_on_entity(func.entity_id, func.logic_body, params=params, purpose="function_executor")
        else:
            sql_result = self._execute_sql(func.logic_body, params, func.entity_id)
        if sql_result.get("error"):
            raise RuntimeError(sql_result["error"])
        rows = sql_result.get("rows", [])
        if rows and rows[0]:
            return rows[0][0]
        return None

    def _execute_sql(self, sql: str, params: dict, entity_id: str | None = None) -> dict:
        from app.services.data_plane.entity_data_service import EntityDataService
        svc = EntityDataService(self.db)
        if entity_id:
            return svc.execute_sql_on_entity(entity_id, sql, params=params, purpose="function_executor")
        return {"error": "No entity_id for SQL execution", "rows": []}

    def _execute_python(self, func: OntologyFunction, params: dict, context=None) -> Any:
        # Version source is deliberately independent from mutable file paths.
        if isinstance(getattr(func, "source_code", None), str):
            from app.services.function_runtime.executor import FunctionRuntimeExecutor
            from app.services.function_runtime.models import ExecContext
            from app.services.function_runtime.registry import FunctionRegistry
            from app.services.function_runtime.sandbox import UnifiedSandbox
            context = context or ExecContext(ontology_id=getattr(func, "ontology_id", None))
            name = func.callable_name or func.name
            if context._chain_start is None:
                context._chain_start = time.time()
            remaining = context.total_timeout_sec - (time.time() - context._chain_start)
            if remaining <= 0:
                raise TimeoutError("调用链总超时")
            runtime = FunctionRuntimeExecutor(FunctionRegistry(self.db), UnifiedSandbox(), self.db)
            namespace = {"params": params, "call_function": self._nested_callable(func, context),
                         **runtime._build_ontology_helpers(context=context)}
            return UnifiedSandbox().execute(func.source_code, func.func_name or name, namespace,
                                            timeout=max(1, int(min(context.timeout_sec, remaining))))
        # Delegate to new runtime if function has source_path set (actual string path)
        if getattr(func, "source_path", None) and isinstance(func.source_path, str) and func.callable_name and isinstance(func.callable_name, str):
            from app.services.function_runtime.executor import FunctionRuntimeExecutor
            from app.services.function_runtime.registry import FunctionRegistry
            from app.services.function_runtime.sandbox import UnifiedSandbox
            registry = FunctionRegistry(self.db)
            registry.sync_from_db()
            sandbox = UnifiedSandbox()
            runtime = FunctionRuntimeExecutor(registry=registry, sandbox=sandbox, db=self.db)
            from app.services.function_runtime.models import ExecContext
            result = runtime.execute(func.callable_name, params, context)
            if result.requested_write:
                raise FunctionWriteRequested(result.requested_write)
            if result.success:
                return result.result
            error = RuntimeError(result.error)
            error.outcome = result.outcome
            raise error

        # Fallback: inline logic_body execution
        if not func.logic_body or not func.logic_body.strip():
            raise ValueError("Python body is empty")
        from textwrap import indent
        from app.services.function_runtime.sandbox import UnifiedSandbox
        code = "def inline_function(params):\n    result = None\n" + indent(func.logic_body, "    ") + "\n    return result\n"
        from app.services.function_runtime.executor import FunctionRuntimeExecutor
        from app.services.function_runtime.registry import FunctionRegistry
        runtime = FunctionRuntimeExecutor(FunctionRegistry(self.db), UnifiedSandbox(), self.db)
        remaining = context.total_timeout_sec - (time.time() - context._chain_start)
        return UnifiedSandbox().execute(code, "inline_function", {"params": params, "call_function": self._nested_callable(func, context),
            **runtime._build_ontology_helpers(context=context)}, timeout=max(1, int(min(context.timeout_sec, remaining))))
