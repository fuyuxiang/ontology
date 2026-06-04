"""FunctionExecutor — 根据 logic_type 执行函数"""
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.function import OntologyFunction

logger = logging.getLogger(__name__)


@dataclass
class FunctionResult:
    success: bool
    value: Any = None
    error: str | None = None
    execution_ms: float = 0


class FunctionExecutor:
    def __init__(self, db: Session):
        self.db = db

    def execute(self, func: OntologyFunction, params: dict) -> FunctionResult:
        start = time.time()
        try:
            if func.logic_type == "expression":
                result = self._execute_expression(func, params)
            elif func.logic_type == "sql":
                result = self._execute_sql_func(func, params)
            elif func.logic_type == "python":
                result = self._execute_python(func, params)
            else:
                return FunctionResult(success=False, error=f"Unknown logic_type: {func.logic_type}")

            elapsed = (time.time() - start) * 1000
            return FunctionResult(success=True, value=result, execution_ms=elapsed)
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            logger.warning(f"Function {func.name} execution failed: {e}")
            return FunctionResult(success=False, error=str(e), execution_ms=elapsed)

    def execute_by_callable_name(self, callable_name: str, params: dict) -> FunctionResult:
        func = self.db.query(OntologyFunction).filter(
            OntologyFunction.callable_name == callable_name,
            OntologyFunction.status == "active",
        ).first()
        if not func:
            return FunctionResult(success=False, error=f"Function '{callable_name}' not found or inactive")
        return self.execute(func, params)

    def _execute_expression(self, func: OntologyFunction, params: dict) -> Any:
        if not func.logic_body or not func.logic_body.strip():
            raise ValueError("Expression body is empty")
        safe_globals = {
            "__builtins__": {},
            "params": params,
            "abs": abs, "max": max, "min": min, "round": round, "len": len,
            "int": int, "float": float, "str": str, "bool": bool,
        }
        return eval(func.logic_body, safe_globals)

    def _execute_sql_func(self, func: OntologyFunction, params: dict) -> Any:
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

    def _execute_python(self, func: OntologyFunction, params: dict) -> Any:
        if not func.logic_body or not func.logic_body.strip():
            raise ValueError("Python body is empty")
        local_ns: dict = {"params": params, "result": None}
        safe_builtins = {
            "abs": abs, "max": max, "min": min, "round": round, "len": len,
            "int": int, "float": float, "str": str, "bool": bool,
            "list": list, "dict": dict, "range": range, "enumerate": enumerate,
            "sum": sum, "sorted": sorted, "zip": zip, "map": map, "filter": filter,
        }
        exec(func.logic_body, {"__builtins__": safe_builtins}, local_ns)
        return local_ns.get("result")
