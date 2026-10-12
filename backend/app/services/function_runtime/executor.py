"""FunctionRuntimeExecutor: core execution engine with call_function injection,
circular call detection, and max depth enforcement."""
from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from app.services.function_runtime.models import ExecContext, ExecResult, FunctionWriteRequested
from app.services.function_runtime.registry import FunctionRegistry
from app.services.function_runtime.sandbox import UnifiedSandbox

logger = logging.getLogger(__name__)


class CircularCallError(Exception):
    pass


class MaxDepthError(Exception):
    pass


def _coerce_param(value: Any, declared_type: str) -> Any:
    """按函数声明的参数类型强制转换入参。

    入参多来自 JSON(MCP/HTTP)，数字常被传成字符串(如 "50")，函数内部
    直接参与数值运算会抛 '<' not supported between int and str。这里按
    ParamSchema.type 收口转换，转换失败则原样返回(交由函数自身校验)。
    """
    if value is None:
        return None
    t = (declared_type or "").lower()
    try:
        if t in ("number", "float", "double", "decimal"):
            return float(value)
        if t in ("integer", "int"):
            if isinstance(value, bool):
                return value
            numeric = float(value)
            return int(numeric) if numeric.is_integer() else value
        if t in ("boolean", "bool"):
            if isinstance(value, str):
                normalized = value.strip().lower()
                if normalized in ("true", "1", "yes", "y"):
                    return True
                if normalized in ("false", "0", "no", "n"):
                    return False
                return value
            return bool(value)
        if t in ("string", "str", "text"):
            return value if isinstance(value, str) else str(value)
    except (TypeError, ValueError):
        return value
    return value


def _coerce_params(params: dict, param_schemas: list) -> dict:
    """按 FunctionMeta.params 逐项做类型强制，未声明的参数保持原样。"""
    if not params or not param_schemas:
        return params
    type_by_name = {p.name: p.type for p in param_schemas if getattr(p, "name", None)}
    coerced = dict(params)
    for name, decl_type in type_by_name.items():
        if name in coerced:
            coerced[name] = _coerce_param(coerced[name], decl_type)
    return coerced


class FunctionRuntimeExecutor:
    def __init__(self, registry: FunctionRegistry, sandbox: UnifiedSandbox, db: Session, session_factory=None):
        self.registry = registry
        self.sandbox = sandbox
        self.db = db
        self.session_factory = session_factory

    def execute(
        self, callable_name: str, params: dict, context: ExecContext | None = None
    ) -> ExecResult:
        if self.session_factory:
            with self.session_factory() as db:
                return FunctionRuntimeExecutor(self.registry, self.sandbox, db).execute(callable_name, params, context)
        start = time.time()
        if context is None:
            context = ExecContext(call_stack=[])
        if context.version_id:
            from app.models.version_components import OntologyVersionFunction
            from app.services.function_executor import FunctionExecutor
            matches = self.db.query(OntologyVersionFunction).filter_by(version_id=context.version_id, callable_name=callable_name).all()
            if len(matches) != 1:
                return ExecResult(False, None, "函数不在当前发布版本中", 0, list(context.call_stack))
            result = FunctionExecutor(self.db).execute_snapshot(matches[0], params, context=context)
            return ExecResult(result.success, result.value, result.error, int(result.execution_ms), list(context.call_stack),
                result.outcome, result.requested_write, result.committed_writes or [])

        # Initialize chain start time on first call
        if context._chain_start is None:
            context._chain_start = time.time()

        # Enforce total chain timeout
        elapsed_chain = time.time() - context._chain_start
        if elapsed_chain > context.total_timeout_sec:
            return ExecResult(
                success=False,
                result=None,
                error=f"调用链总超时 (>{context.total_timeout_sec}s)",
                execution_ms=int((time.time() - start) * 1000),
                call_trace=list(context.call_stack),
            )

        meta = self.registry.get(callable_name, context.ontology_id) if context.ontology_id else self.registry.get(callable_name)
        if meta is None:
            return ExecResult(
                success=False,
                result=None,
                error=f"函数 '{callable_name}' 未找到 (not found)",
                execution_ms=int((time.time() - start) * 1000),
                call_trace=list(context.call_stack),
            )

        # Max depth enforcement (checked first to handle self-recursion)
        if len(context.call_stack) >= context.max_depth:
            return ExecResult(
                success=False,
                result=None,
                error=f"超过最大递归深度 (depth): {context.max_depth}",
                execution_ms=int((time.time() - start) * 1000),
                call_trace=list(context.call_stack),
            )

        # Circular call detection (A -> B -> A pattern, excludes self-recursion
        # which is handled by max depth above)
        if callable_name in context.call_stack and callable_name != context.call_stack[-1]:
            return ExecResult(
                success=False,
                result=None,
                error=f"检测到循环调用 (circular): {' → '.join(context.call_stack)} → {callable_name}",
                execution_ms=int((time.time() - start) * 1000),
                call_trace=list(context.call_stack),
            )

        context.call_stack.append(callable_name)

        try:
            if context.entity_ids is not None or context.function_ids is not None:
                from app.models.function import OntologyFunction
                query = self.db.query(OntologyFunction).filter_by(callable_name=callable_name, status="active")
                if context.ontology_id is not None:
                    query = query.filter_by(ontology_id=str(context.ontology_id))
                matches = query.all()
                if len(matches) != 1:
                    raise PermissionError("函数不在当前授权范围内")
                if matches[0].entity_id is not None:
                    context.check_entity(matches[0].entity_id)
                if context.function_ids is not None and matches[0].id not in context.function_ids:
                    raise PermissionError("函数不在当前授权范围内")
            # 按声明的参数类型强制转换入参(JSON 传来的 "50" → 50)，收口点覆盖
            # MCP run_logic、tool_router run_logic/run_action 及 call_function 链式调用
            params = _coerce_params(params, meta.params)
            from app.services.agent_actions import validate_parameters
            params = validate_parameters([{**p.schema, "name": p.name, "type": p.type, "required": p.required} for p in meta.params], params)
            if context.ontology_id and meta.ontology_id and str(context.ontology_id) != str(meta.ontology_id):
                raise PermissionError("函数不属于当前本体")
            if context.ontology_id is None:
                context.ontology_id = meta.ontology_id or None
            code = self._read_source(meta.source_path)
            call_fn = self._build_call_function(context)
            ontology_helpers = self._build_ontology_helpers(context=context)
            namespace = {
                "params": params,
                "call_function": call_fn,
                **ontology_helpers,
            }
            # Calculate remaining time for this individual call
            remaining = context.total_timeout_sec - (time.time() - context._chain_start)
            effective_timeout = max(1, int(min(context.timeout_sec, remaining)))
            result = self.sandbox.execute(
                code, meta.func_name, namespace, timeout=effective_timeout
            )
            elapsed = int((time.time() - start) * 1000)
            return ExecResult(
                success=True,
                result=result,
                error=None,
                execution_ms=elapsed,
                call_trace=list(context.call_stack),
                outcome="committed" if context.committed_writes else None,
                committed_writes=list(context.committed_writes),
            )
        except FunctionWriteRequested as request:
            return ExecResult(success=True, result=None, error=None,
                execution_ms=int((time.time()-start)*1000), call_trace=list(context.call_stack),
                outcome="simulated" if context.action_mode == "simulation" else "pending_confirmation",
                requested_write=request.request)
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return ExecResult(
                success=False,
                result=None,
                error=str(e),
                execution_ms=elapsed,
                call_trace=list(context.call_stack),
                outcome=context.failure_outcome(e),
                committed_writes=list(context.committed_writes),
            )
        finally:
            context.call_stack.pop()

    def _build_call_function(self, context: ExecContext):
        """Build the call_function helper injected into sandbox namespace."""
        def call_function(name: str, params: dict) -> Any:
            if context.version_id:
                from app.services.function_executor import FunctionExecutor
                from app.models.version_components import OntologyVersionFunction
                matches = self.db.query(OntologyVersionFunction).filter_by(version_id=context.version_id, callable_name=name).all()
                if len(matches) != 1:
                    raise ValueError("函数不在当前发布版本中")
                result = FunctionExecutor(self.db).execute_snapshot(matches[0], params, context=context)
                if result.requested_write:
                    raise FunctionWriteRequested(result.requested_write)
                if not result.success:
                    error = RuntimeError(result.error)
                    error.outcome = result.outcome
                    raise error
                return result.value
            if self.registry.get(name, context.ontology_id) is None:
                from app.services.function_executor import FunctionExecutor
                executor = FunctionExecutor(self.db)
                executor._call_stack = context.call_stack
                result = executor.execute_by_callable_name(name, params, context.ontology_id, context=context)
                if result.requested_write:
                    raise FunctionWriteRequested(result.requested_write)
                if not result.success:
                    error = RuntimeError(f"call_function('{name}') failed: {result.error}")
                    error.outcome = result.outcome
                    raise error
                return result.value
            result = self.execute(name, params, context)
            if result.requested_write:
                raise FunctionWriteRequested(result.requested_write)
            if not result.success:
                error = RuntimeError(f"call_function('{name}') failed: {result.error}")
                error.outcome = result.outcome
                raise error
            return result.result
        return call_function

    def _build_ontology_helpers(self, ontology_id=None, version_id=None, *, context=None) -> dict[str, Any]:
        """Build query_object/query_objects/update_object helpers for sandbox."""
        from app.models import OntologyEntity
        from app.services.data_plane.entity_data_service import EntityDataService

        db = self.db
        context = context or ExecContext(ontology_id=ontology_id, version_id=version_id)
        ontology_id, version_id = context.ontology_id, context.version_id
        svc = EntityDataService(db)

        def _service(entity_name):
            if version_id:
                from app.models.version import OntologyVersionEntity
                from app.services.version_entity_data import VersionEntityDataService
                entity = db.query(OntologyVersionEntity).filter_by(version_id=version_id, name=entity_name).first()
                if not entity:
                    raise ValueError(f"对象 {entity_name} 不在当前发布版本中")
                context.check_entity(entity.source_entity_id)
                return VersionEntityDataService(db, entity), entity.source_entity_id
            entity_id = _resolve_entity_id(entity_name)
            context.check_entity(entity_id)
            return svc, entity_id

        def _resolve_entity_id(entity_name: str) -> str | None:
            query = db.query(OntologyEntity).filter(
                (OntologyEntity.name == entity_name) | (OntologyEntity.name_cn == entity_name)
            )
            if ontology_id:
                query = query.filter(OntologyEntity.ontology_id == str(ontology_id))
            entities = query.all()
            if len(entities) != 1:
                raise ValueError(f"对象 {entity_name} 不存在或名称有歧义，请指定本体")
            return entities[0].id

        def query_object(entity_name: str, filters: dict) -> dict | None:
            source_service, entity_id = _service(entity_name)
            if not entity_id:
                return None
            result = source_service.query_entity_data(entity_id, filters=filters, limit=1)
            if result.get("error"):
                raise RuntimeError(result["error"])
            if not result.get("rows"):
                return None
            columns = result["columns"]
            row = result["rows"][0]
            return dict(zip(columns, row, strict=True))

        def query_objects(entity_name: str, filters: dict, limit: int = 100) -> list[dict]:
            source_service, entity_id = _service(entity_name)
            if not entity_id:
                return []
            result = source_service.query_entity_data(entity_id, filters=filters, limit=limit)
            if result.get("error"):
                raise RuntimeError(result["error"])
            if not result.get("rows"):
                return []
            columns = result["columns"]
            return [dict(zip(columns, row, strict=True)) for row in result["rows"]]

        def update_object(entity_name: str, record_id: str, updates: dict) -> bool:
            from app.services.object_mutation_service import ObjectMutationService
            source_service, entity_id = _service(entity_name)
            if context.allowed_tools is not None and "run_action" not in context.allowed_tools:
                raise PermissionError("业务写入需要授权的 run_action 工具")
            if context.action_mode not in {"simulation", "confirm", "execute"}:
                raise PermissionError("当前函数执行为只读，业务写入必须通过行动执行")
            version_entity = getattr(source_service, "version_entity", None)
            entity = version_entity or db.get(OntologyEntity, entity_id)
            attrs = {a.name: a for a in entity.attributes}
            if record_id is None or not isinstance(updates, dict) or not updates or set(updates)-set(attrs):
                raise ValueError("必须提供实例 ID 和当前对象的有效更新属性")
            from app.services.agent_actions import validate_parameters
            validate_parameters([{"name": n, "type": attrs[n].type} for n in updates], updates)
            if context.action_mode == "simulation":
                raise FunctionWriteRequested({"entity_name": entity_name, "entity_id": entity_id,
                    "record_id": record_id, "updates": dict(updates)})
            from app.core.permissions import has_permission
            if not (has_permission(context.user, "rule:execute", db) or has_permission(context.user, "rule:write", db)):
                raise PermissionError("当前身份没有业务动作执行权限")
            if context.action_mode == "confirm":
                raise FunctionWriteRequested({"entity_name": entity_name, "entity_id": entity_id,
                    "record_id": record_id, "updates": dict(updates)})
            context.active_write = {"entity_name": entity_name, "entity_id": entity_id,
                "record_id": record_id, "updates": dict(updates)}
            try:
                receipt = ObjectMutationService(db, version_entity).update(entity_id, record_id, updates, user_id=context.user.id)
            except Exception:
                context.active_write = None
                raise
            context.committed_writes.append(receipt)
            context.active_write = None
            return True

        return {
            "query_object": query_object,
            "query_objects": query_objects,
            "update_object": update_object,
        }

    def _read_source(self, source_path: str) -> str:
        with open(source_path, encoding="utf-8") as f:
            return f.read()
