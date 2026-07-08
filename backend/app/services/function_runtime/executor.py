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
            namespace = {
                "params": params,
                "call_function": call_fn,
            }
            result = self.sandbox.execute(
                code, meta.func_name, namespace, timeout=context.timeout_sec
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

    def _read_source(self, source_path: str) -> str:
        with open(source_path, "r", encoding="utf-8") as f:
            return f.read()
