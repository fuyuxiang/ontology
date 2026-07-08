"""FunctionRuntimeExecutor: core execution engine with call_function injection,
circular call detection, and max depth enforcement."""
from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from app.services.function_runtime.models import ExecContext, ExecResult, FunctionMeta
from app.services.function_runtime.registry import FunctionRegistry
from app.services.function_runtime.sandbox import UnifiedSandbox

logger = logging.getLogger(__name__)


class CircularCallError(Exception):
    pass


class MaxDepthError(Exception):
    pass


class FunctionRuntimeExecutor:
    def __init__(self, registry: FunctionRegistry, sandbox: UnifiedSandbox, db: Session):
        self.registry = registry
        self.sandbox = sandbox
        self.db = db

    def execute(
        self, callable_name: str, params: dict, context: ExecContext | None = None
    ) -> ExecResult:
        start = time.time()
        if context is None:
            context = ExecContext(call_stack=[])

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

        meta = self.registry.get(callable_name)
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
            code = self._read_source(meta.source_path)
            call_fn = self._build_call_function(context)
            ontology_helpers = self._build_ontology_helpers()
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
            )
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return ExecResult(
                success=False,
                result=None,
                error=str(e),
                execution_ms=elapsed,
                call_trace=list(context.call_stack),
            )
        finally:
            context.call_stack.pop()

    def _build_call_function(self, context: ExecContext):
        """Build the call_function helper injected into sandbox namespace."""
        def call_function(name: str, params: dict) -> Any:
            result = self.execute(name, params, context)
            if not result.success:
                raise RuntimeError(f"call_function('{name}') failed: {result.error}")
            return result.result
        return call_function

    def _build_ontology_helpers(self) -> dict[str, Any]:
        """Build query_object/query_objects/update_object helpers for sandbox."""
        from app.models import OntologyEntity
        from app.services.data_plane.entity_data_service import EntityDataService

        db = self.db
        svc = EntityDataService(db)

        def _resolve_entity_id(entity_name: str) -> str | None:
            entity = db.query(OntologyEntity).filter(
                (OntologyEntity.name == entity_name) | (OntologyEntity.name_cn == entity_name)
            ).first()
            return entity.id if entity else None

        def query_object(entity_name: str, filters: dict) -> dict | None:
            entity_id = _resolve_entity_id(entity_name)
            if not entity_id:
                return None
            result = svc.query_entity_data(entity_id, filters=filters, limit=1)
            if result.get("error") or not result.get("rows"):
                return None
            columns = result["columns"]
            row = result["rows"][0]
            return dict(zip(columns, row))

        def query_objects(entity_name: str, filters: dict, limit: int = 100) -> list[dict]:
            entity_id = _resolve_entity_id(entity_name)
            if not entity_id:
                return []
            result = svc.query_entity_data(entity_id, filters=filters, limit=limit)
            if result.get("error") or not result.get("rows"):
                return []
            columns = result["columns"]
            return [dict(zip(columns, row)) for row in result["rows"]]

        def update_object(entity_name: str, record_id: str, updates: dict) -> bool:
            # update_object is a no-op placeholder for now (would need write-back support)
            logger.info(f"update_object({entity_name}, {record_id}, {updates}) — write-back not implemented")
            return True

        return {
            "query_object": query_object,
            "query_objects": query_objects,
            "update_object": update_object,
        }

    def _read_source(self, source_path: str) -> str:
        with open(source_path, "r", encoding="utf-8") as f:
            return f.read()
