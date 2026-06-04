# 规则与函数管理 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the full rule & function management module with enhanced models, structured condition builder, multi-type function editor, registry API for skill integration, and entity logic tab.

**Architecture:** Backend-first approach — extend models, add new fields, build FunctionExecutor service and registry API, then enhance frontend with drawer-based builders replacing modal forms. No migration system; SQLAlchemy `create_all` handles schema.

**Tech Stack:** FastAPI + SQLAlchemy (backend), Vue 3 + Pinia + CodeMirror (frontend), pytest (tests)

---

### Task 1: Extend Backend Models — Add New Fields

**Files:**
- Modify: `backend/app/models/rule.py`
- Modify: `backend/app/models/function.py`

- [ ] **Step 1: Add fields to BusinessRule model**

```python
# In backend/app/models/rule.py, add to BusinessRule class after existing fields:
    description: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[list | None] = mapped_column(JSON)
    input_params: Mapped[list | None] = mapped_column(JSON)
    output_schema: Mapped[dict | None] = mapped_column(JSON)
    action_id: Mapped[str | None] = mapped_column(ForeignKey("entity_actions.id", ondelete="SET NULL"), nullable=True)
```

- [ ] **Step 2: Add fields to OntologyFunction model**

```python
# In backend/app/models/function.py, add to OntologyFunction class after existing fields:
    tags: Mapped[list | None] = mapped_column(JSON)
    callable_name: Mapped[str] = mapped_column(String(100), default="")
```

- [ ] **Step 3: Verify app starts without errors**

Run: `cd backend && python -c "from app.models.rule import BusinessRule; from app.models.function import OntologyFunction; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/rule.py backend/app/models/function.py
git commit -m "feat: extend BusinessRule and OntologyFunction models with registry fields"
```

---

### Task 2: Update Schemas for New Fields

**Files:**
- Modify: `backend/app/schemas/rule.py`
- Modify: `backend/app/schemas/function.py`

- [ ] **Step 1: Update rule schemas**

```python
# backend/app/schemas/rule.py — update RuleCreate:
class RuleCreate(BaseModel):
    entity_id: str
    name: str
    description: str = ""
    condition_expr: str = ""
    action_desc: str = ""
    status: str = "active"
    priority: str = "medium"
    conditions_json: list | None = None
    rule_meta_json: dict | None = None
    tags: list[str] | None = None
    input_params: list[dict] | None = None
    output_schema: dict | None = None
    action_id: str | None = None

# Update RuleUpdate — add new optional fields:
class RuleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    condition_expr: str | None = None
    action_desc: str | None = None
    status: str | None = None
    priority: str | None = None
    conditions_json: list | None = None
    rule_meta_json: dict | None = None
    tags: list[str] | None = None
    input_params: list[dict] | None = None
    output_schema: dict | None = None
    action_id: str | None = None
```

- [ ] **Step 2: Add RuleOut schema in rule.py (move from entity schema)**

```python
class RuleOut(BaseModel):
    id: str
    name: str
    description: str = ""
    entity_id: str
    entity_name: str = ""
    condition_expr: str = ""
    action_desc: str = ""
    status: str
    priority: str
    trigger_count: int = 0
    last_triggered: datetime | None = None
    conditions_json: list | None = None
    rule_meta_json: dict | None = None
    tags: list[str] | None = None
    input_params: list[dict] | None = None
    output_schema: dict | None = None
    action_id: str | None = None
    ref_count: int = 0
    model_config = {"from_attributes": True}
```

- [ ] **Step 3: Update function schemas**

```python
# backend/app/schemas/function.py — update FunctionCreate:
class FunctionCreate(BaseModel):
    entity_id: str | None = None
    name: str
    callable_name: str = ""
    description: str = ""
    return_type: str = "string"
    input_schema: list | None = None
    logic_type: str = "expression"
    logic_body: str = ""
    is_derived_property: bool = False
    status: str = "active"
    tags: list[str] | None = None

# Update FunctionUpdate:
class FunctionUpdate(BaseModel):
    name: str | None = None
    callable_name: str | None = None
    entity_id: str | None = None
    description: str | None = None
    return_type: str | None = None
    input_schema: list | None = None
    logic_type: str | None = None
    logic_body: str | None = None
    is_derived_property: bool | None = None
    status: str | None = None
    tags: list[str] | None = None

# Update FunctionOut:
class FunctionOut(BaseModel):
    id: str
    entity_id: str | None = None
    entity_name: str = ""
    name: str
    callable_name: str = ""
    description: str = ""
    return_type: str
    input_schema: list | None = None
    logic_type: str
    logic_body: str = ""
    is_derived_property: bool = False
    status: str
    execution_count: int = 0
    last_executed: datetime | None = None
    tags: list[str] | None = None
    ref_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/rule.py backend/app/schemas/function.py
git commit -m "feat: update rule and function schemas with tags, callable_name, registry fields"
```

---

### Task 3: Build FunctionExecutor Service

**Files:**
- Create: `backend/app/services/function_executor.py`
- Create: `backend/tests/test_function_executor.py`

- [ ] **Step 1: Write tests for FunctionExecutor**

```python
# backend/tests/test_function_executor.py
import pytest
from unittest.mock import MagicMock, patch
from app.services.function_executor import FunctionExecutor, FunctionResult


def _make_function(logic_type="expression", logic_body="", input_schema=None):
    fn = MagicMock()
    fn.id = "fn-001"
    fn.name = "test_func"
    fn.logic_type = logic_type
    fn.logic_body = logic_body
    fn.input_schema = input_schema or []
    fn.execution_count = 0
    fn.last_executed = None
    return fn


class TestExpressionExecution:
    def test_simple_arithmetic(self):
        fn = _make_function("expression", "params['a'] + params['b']")
        db = MagicMock()
        executor = FunctionExecutor(db)
        result = executor.execute(fn, {"a": 3, "b": 4})
        assert result.success is True
        assert result.value == 7

    def test_expression_error(self):
        fn = _make_function("expression", "1 / 0")
        db = MagicMock()
        executor = FunctionExecutor(db)
        result = executor.execute(fn, {})
        assert result.success is False
        assert result.error is not None

    def test_empty_body(self):
        fn = _make_function("expression", "")
        db = MagicMock()
        executor = FunctionExecutor(db)
        result = executor.execute(fn, {})
        assert result.success is False


class TestSqlExecution:
    def test_sql_returns_mock_result(self):
        fn = _make_function("sql", "SELECT COUNT(*) FROM users")
        db = MagicMock()
        executor = FunctionExecutor(db)
        with patch.object(executor, '_execute_sql', return_value={"rows": [[42]], "columns": ["count"]}):
            result = executor.execute(fn, {})
            assert result.success is True
            assert result.value == 42


class TestPythonExecution:
    def test_python_sandbox(self):
        fn = _make_function("python", "result = params['x'] * 2")
        db = MagicMock()
        executor = FunctionExecutor(db)
        result = executor.execute(fn, {"x": 5})
        assert result.success is True
        assert result.value == 10
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_function_executor.py -v`
Expected: ImportError or FAIL (module doesn't exist yet)

- [ ] **Step 3: Implement FunctionExecutor**

```python
# backend/app/services/function_executor.py
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
        safe_globals = {"__builtins__": {}, "params": params, "abs": abs, "max": max, "min": min, "round": round, "len": len}
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
        exec(func.logic_body, {"__builtins__": {"abs": abs, "max": max, "min": min, "round": round, "len": len, "int": int, "float": float, "str": str, "list": list, "dict": dict, "range": range, "enumerate": enumerate, "sum": sum, "sorted": sorted}}, local_ns)
        return local_ns.get("result")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_function_executor.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/function_executor.py backend/tests/test_function_executor.py
git commit -m "feat: add FunctionExecutor service with expression/sql/python support"
```

---

### Task 4: Add Registry API Endpoints

**Files:**
- Create: `backend/app/api/v1/registry.py`
- Modify: `backend/app/main.py` (register router)

- [ ] **Step 1: Create registry API**

```python
# backend/app/api/v1/registry.py
"""注册中心 API — 供技能编辑器查询可用规则和函数"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import OntologyEntity, BusinessRule
from app.models.function import OntologyFunction
from app.models.skill import Skill

router = APIRouter(prefix="/registry", tags=["registry"])


class RegistryItem(BaseModel):
    id: str
    type: str  # "rule" or "function"
    name: str
    callable_name: str = ""
    description: str = ""
    entity_id: str | None = None
    entity_name: str = ""
    tags: list[str] = []
    input_params: list[dict] = []
    output_info: str = ""
    ref_count: int = 0


class RegistryGroup(BaseModel):
    entity_id: str | None
    entity_name: str
    items: list[RegistryItem]


@router.get("/items", response_model=list[RegistryItem])
def list_registry_items(
    type: str | None = None,
    entity_id: str | None = None,
    search: str | None = None,
    tags: list[str] = Query(default=[]),
    db: Session = Depends(get_db),
):
    items: list[RegistryItem] = []

    if type != "function":
        rules = db.query(BusinessRule).filter(BusinessRule.status == "active").all()
        for r in rules:
            if entity_id and r.entity_id != entity_id:
                continue
            if search and search.lower() not in (r.name + (r.description or "")).lower():
                continue
            if tags and not set(tags).intersection(set(r.tags or [])):
                continue
            entity = db.get(OntologyEntity, r.entity_id)
            items.append(RegistryItem(
                id=r.id, type="rule", name=r.name,
                description=r.description or "",
                entity_id=r.entity_id,
                entity_name=entity.name if entity else "",
                tags=r.tags or [],
                input_params=r.input_params or [],
                output_info="triggered, confidence, risk_level",
                ref_count=_count_rule_refs(r.id, db),
            ))

    if type != "rule":
        funcs = db.query(OntologyFunction).filter(OntologyFunction.status == "active").all()
        for f in funcs:
            if entity_id and f.entity_id != entity_id:
                continue
            if search and search.lower() not in (f.name + (f.description or "")).lower():
                continue
            if tags and not set(tags).intersection(set(f.tags or [])):
                continue
            entity = db.get(OntologyEntity, f.entity_id) if f.entity_id else None
            items.append(RegistryItem(
                id=f.id, type="function", name=f.name,
                callable_name=f.callable_name or "",
                description=f.description or "",
                entity_id=f.entity_id,
                entity_name=entity.name if entity else "",
                tags=f.tags or [],
                input_params=f.input_schema or [],
                output_info=f.return_type,
                ref_count=_count_func_refs(f.id, db),
            ))

    return items


@router.get("/grouped", response_model=list[RegistryGroup])
def list_registry_grouped(
    search: str | None = None,
    db: Session = Depends(get_db),
):
    items = list_registry_items(type=None, entity_id=None, search=search, tags=[], db=db)
    groups: dict[str, RegistryGroup] = {}
    for item in items:
        key = item.entity_id or "__standalone__"
        if key not in groups:
            groups[key] = RegistryGroup(
                entity_id=item.entity_id,
                entity_name=item.entity_name or "独立函数",
                items=[],
            )
        groups[key].items.append(item)
    return list(groups.values())


@router.get("/refs/{item_type}/{item_id}")
def get_references(item_type: str, item_id: str, db: Session = Depends(get_db)):
    refs = []
    skills = db.query(Skill).filter(Skill.status == "active").all()
    for s in skills:
        tools = s.tools or []
        for t in tools:
            if t.get(f"{item_type}_id") == item_id or t.get("rule_id") == item_id or t.get("function_id") == item_id:
                refs.append({"type": "skill", "id": s.id, "name": s.name})
                break

    if item_type == "function":
        rules = db.query(BusinessRule).filter(BusinessRule.status == "active").all()
        for r in rules:
            for cond in (r.conditions_json or []):
                if cond.get("function_id") == item_id:
                    refs.append({"type": "rule", "id": r.id, "name": r.name})
                    break
    return {"item_id": item_id, "item_type": item_type, "references": refs}


def _count_rule_refs(rule_id: str, db: Session) -> int:
    count = 0
    skills = db.query(Skill).filter(Skill.status == "active").all()
    for s in skills:
        for t in (s.tools or []):
            if t.get("rule_id") == rule_id:
                count += 1
                break
    return count


def _count_func_refs(func_id: str, db: Session) -> int:
    count = 0
    skills = db.query(Skill).filter(Skill.status == "active").all()
    for s in skills:
        for t in (s.tools or []):
            if t.get("function_id") == func_id:
                count += 1
                break
    rules = db.query(BusinessRule).filter(BusinessRule.status == "active").all()
    for r in rules:
        for cond in (r.conditions_json or []):
            if cond.get("function_id") == func_id:
                count += 1
                break
    return count
```

- [ ] **Step 2: Register router in main.py**

Find the section in `backend/app/main.py` where routers are included (look for `app.include_router`) and add:

```python
from app.api.v1.registry import router as registry_router
app.include_router(registry_router, prefix="/api/v1")
```

- [ ] **Step 3: Verify server starts**

Run: `cd backend && python -c "from app.api.v1.registry import router; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/registry.py backend/app/main.py
git commit -m "feat: add registry API for skill integration"
```

---

### Task 5: Update Rules API with New Fields

**Files:**
- Modify: `backend/app/api/v1/rules.py`

- [ ] **Step 1: Update _rule_to_out to include new fields**

Update `_rule_to_out` in `backend/app/api/v1/rules.py`:

```python
from app.schemas.rule import RuleOut  # use local RuleOut instead of entity schema

def _rule_to_out(r: BusinessRule, entity_name: str, ref_count: int = 0) -> RuleOut:
    return RuleOut(
        id=r.id, name=r.name, description=r.description or "",
        entity_id=r.entity_id, entity_name=entity_name,
        condition_expr=r.condition_expr, action_desc=r.action_desc,
        status=r.status, priority=r.priority,
        trigger_count=r.trigger_count, last_triggered=r.last_triggered,
        conditions_json=r.conditions_json, rule_meta_json=r.rule_meta_json,
        tags=r.tags, input_params=r.input_params,
        output_schema=r.output_schema, action_id=r.action_id,
        ref_count=ref_count,
    )
```

- [ ] **Step 2: Update create_rule to handle new fields**

In `create_rule`, add new fields to `BusinessRule(...)`:
```python
    rule = BusinessRule(
        entity_id=data.entity_id, name=data.name,
        description=data.description,
        condition_expr=data.condition_expr, action_desc=data.action_desc,
        status=data.status, priority=data.priority,
        conditions_json=data.conditions_json, rule_meta_json=data.rule_meta_json,
        tags=data.tags, input_params=data.input_params,
        output_schema=data.output_schema, action_id=data.action_id,
    )
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/v1/rules.py
git commit -m "feat: update rules API to support new registry fields"
```

---

### Task 6: Update Functions API with New Fields

**Files:**
- Modify: `backend/app/api/v1/functions.py`

- [ ] **Step 1: Update _func_to_out and create_function**

Update `_func_to_out`:
```python
def _func_to_out(f: OntologyFunction, entity_name: str, ref_count: int = 0) -> FunctionOut:
    return FunctionOut(
        id=f.id, entity_id=f.entity_id, entity_name=entity_name,
        name=f.name, callable_name=f.callable_name or "",
        description=f.description, return_type=f.return_type,
        input_schema=f.input_schema, logic_type=f.logic_type,
        logic_body=f.logic_body, is_derived_property=f.is_derived_property,
        status=f.status, execution_count=f.execution_count,
        last_executed=f.last_executed, tags=f.tags,
        ref_count=ref_count,
        created_at=f.created_at, updated_at=f.updated_at,
    )
```

Update `create_function` to include `callable_name` and `tags`:
```python
    func = OntologyFunction(
        entity_id=data.entity_id, name=data.name,
        callable_name=data.callable_name,
        description=data.description, return_type=data.return_type,
        input_schema=data.input_schema, logic_type=data.logic_type,
        logic_body=data.logic_body, is_derived_property=data.is_derived_property,
        status=data.status, tags=data.tags,
    )
```

- [ ] **Step 2: Replace test endpoint with FunctionExecutor**

Update `test_function` endpoint to use `FunctionExecutor`:
```python
@router.post("/{func_id}/test", response_model=FunctionTestResult)
def test_function(
    func_id: str,
    data: FunctionTestRequest | None = None,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    repo = FunctionRepository(db)
    func = repo.get_by_id(func_id)
    if not func:
        raise HTTPException(status_code=404, detail="函数不存在")

    from app.services.function_executor import FunctionExecutor
    executor = FunctionExecutor(db)
    params = data.params if data else {}
    result = executor.execute(func, params)

    if result.success:
        func.execution_count += 1
        func.last_executed = datetime.utcnow()
        repo.commit()

    return FunctionTestResult(
        success=result.success,
        result=result.value,
        error=result.error,
        execution_ms=result.execution_ms,
    )
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/v1/functions.py
git commit -m "feat: update functions API with callable_name, tags, and FunctionExecutor"
```

---

### Task 7: Integrate Function Calls in Rule Engine

**Files:**
- Modify: `backend/app/services/rule_engine.py`

- [ ] **Step 1: Update RuleEvaluator._evaluate_condition to handle function_call type**

Add function call handling at the top of `_evaluate_condition`:

```python
    def _evaluate_condition(self, cond: dict, user_id: str) -> ConditionResult:
        """评估单个条件"""
        # Handle function_call type
        if cond.get("type") == "function_call":
            return self._evaluate_function_condition(cond, user_id)

        # ... existing code unchanged ...
```

- [ ] **Step 2: Add _evaluate_function_condition method**

```python
    def _evaluate_function_condition(self, cond: dict, user_id: str) -> ConditionResult:
        """评估函数调用类型条件"""
        callable_name = cond.get("callable_name", "")
        params = dict(cond.get("params", {}))
        operator = cond.get("operator", "==")
        expected = cond.get("value")
        display = cond.get("display", f"{callable_name}()")

        # Replace $context.user_id with actual user_id
        for k, v in params.items():
            if v == "$context.user_id":
                params[k] = user_id

        try:
            from app.services.function_executor import FunctionExecutor
            executor = FunctionExecutor(self.db)
            result = executor.execute_by_callable_name(callable_name, params)

            if not result.success:
                return ConditionResult(
                    field=callable_name, display=display, operator=operator,
                    expected=expected, matched=False, error=result.error,
                )

            actual = result.value
            matched = _compare(actual, operator, expected)
            return ConditionResult(
                field=callable_name, display=display, operator=operator,
                expected=expected, actual=actual, matched=matched,
            )
        except Exception as e:
            logger.warning(f"Function condition evaluation failed {callable_name}: {e}")
            return ConditionResult(
                field=callable_name, display=display, operator=operator,
                expected=expected, matched=False, error=str(e),
            )
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/rule_engine.py
git commit -m "feat: support function_call condition type in rule engine"
```

---

### Task 8: Frontend API Layer — Registry and Updated Types

**Files:**
- Create: `frontend/src/api/registry.ts`
- Modify: `frontend/src/api/rules.ts`
- Modify: `frontend/src/api/functions.ts`

- [ ] **Step 1: Create registry API**

```typescript
// frontend/src/api/registry.ts
import { get } from './client'

export interface RegistryItem {
  id: string
  type: 'rule' | 'function'
  name: string
  callable_name: string
  description: string
  entity_id: string | null
  entity_name: string
  tags: string[]
  input_params: Record<string, any>[]
  output_info: string
  ref_count: number
}

export interface RegistryGroup {
  entity_id: string | null
  entity_name: string
  items: RegistryItem[]
}

export interface RefInfo {
  type: string
  id: string
  name: string
}

export const registryApi = {
  listItems(query?: { type?: string; entity_id?: string; search?: string; tags?: string[] }) {
    return get<RegistryItem[]>('/registry/items', { params: query })
  },

  listGrouped(search?: string) {
    return get<RegistryGroup[]>('/registry/grouped', { params: { search } })
  },

  getRefs(itemType: string, itemId: string) {
    return get<{ item_id: string; item_type: string; references: RefInfo[] }>(`/registry/refs/${itemType}/${itemId}`)
  },
}
```

- [ ] **Step 2: Update rules API types**

Add new fields to `RuleQuery` and update the `BusinessRule` type usage in `frontend/src/api/rules.ts`:

```typescript
export interface RuleQuery {
  entityId?: string
  status?: RuleStatus
  priority?: Priority
  search?: string
  tags?: string[]
}
```

- [ ] **Step 3: Update functions API types**

Add `callable_name` and `tags` to `FunctionItem` interface in `frontend/src/api/functions.ts`:

```typescript
export interface FunctionItem {
  id: string
  entity_id: string | null
  entity_name: string
  name: string
  callable_name: string
  description: string
  return_type: string
  input_schema: any[] | null
  logic_type: string
  logic_body: string
  is_derived_property: boolean
  status: string
  execution_count: number
  last_executed: string | null
  tags: string[] | null
  ref_count: number
  created_at: string | null
  updated_at: string | null
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/registry.ts frontend/src/api/rules.ts frontend/src/api/functions.ts
git commit -m "feat(frontend): add registry API and update rule/function types"
```

---

### Task 9: Frontend — Rule Builder Drawer Component

**Files:**
- Create: `frontend/src/components/logic/RuleBuilderDrawer.vue`
- Create: `frontend/src/components/logic/ConditionBuilder.vue`

- [ ] **Step 1: Create ConditionBuilder component**

This is the structured condition assembly component. It renders a list of conditions with field selector (entity attributes + functions), operator selector, and value input. Supports AND/OR groups.

```vue
<!-- frontend/src/components/logic/ConditionBuilder.vue -->
<template>
  <div class="condition-builder">
    <div class="condition-builder__mode">
      <label>匹配方式</label>
      <select v-model="matchMode" class="form-input">
        <option value="all">全部满足 (AND)</option>
        <option value="at_least_1">至少满足一条</option>
        <option value="at_least_2">至少满足两条</option>
      </select>
    </div>

    <div v-for="(cond, idx) in conditions" :key="idx" class="condition-row">
      <div class="condition-row__num">{{ idx + 1 }}</div>
      <select v-model="cond.source" class="form-input condition-row__source" @change="onSourceChange(idx)">
        <optgroup label="实体属性">
          <option v-for="attr in entityAttributes" :key="attr.field" :value="attr.field">{{ attr.label }}</option>
        </optgroup>
        <optgroup label="函数调用">
          <option v-for="fn in availableFunctions" :key="fn.callable_name" :value="'$fn.' + fn.callable_name">{{ fn.name }}</option>
        </optgroup>
      </select>
      <select v-model="cond.operator" class="form-input condition-row__op">
        <option v-for="op in getOperators(cond)" :key="op.value" :value="op.value">{{ op.label }}</option>
      </select>
      <input v-model="cond.value" class="form-input condition-row__value" placeholder="值" />
      <button class="btn-icon" @click="removeCondition(idx)" title="删除条件">×</button>
    </div>

    <button class="btn-text" @click="addCondition">+ 添加条件</button>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'

interface Condition {
  source: string
  operator: string
  value: string
}

const props = defineProps<{
  modelValue: any[]
  entityId: string
  entityAttributes: { field: string; label: string; type: string }[]
  availableFunctions: { callable_name: string; name: string }[]
}>()
const emit = defineEmits<{ 'update:modelValue': [val: any[]] }>()

const matchMode = ref('all')
const conditions = ref<Condition[]>([{ source: '', operator: '==', value: '' }])

function addCondition() {
  conditions.value.push({ source: '', operator: '==', value: '' })
}

function removeCondition(idx: number) {
  conditions.value.splice(idx, 1)
}

function onSourceChange(idx: number) {
  conditions.value[idx].operator = '=='
  conditions.value[idx].value = ''
}

function getOperators(cond: Condition) {
  const attr = props.entityAttributes.find(a => a.field === cond.source)
  if (attr?.type === 'number') return [
    { value: '>=', label: '>=' }, { value: '>', label: '>' },
    { value: '<=', label: '<=' }, { value: '<', label: '<' },
    { value: '==', label: '==' }, { value: '!=', label: '!=' },
  ]
  if (attr?.type === 'boolean') return [{ value: '==', label: '==' }]
  return [
    { value: '==', label: '==' }, { value: '!=', label: '!=' },
    { value: '>=', label: '>=' }, { value: '<=', label: '<=' },
  ]
}

watch(conditions, () => {
  const output = conditions.value
    .filter(c => c.source && c.operator)
    .map(c => {
      if (c.source.startsWith('$fn.')) {
        const callableName = c.source.replace('$fn.', '')
        return {
          type: 'function_call',
          callable_name: callableName,
          params: { user_id: '$context.user_id' },
          operator: c.operator,
          value: parseValue(c.value),
          display: `${callableName}() ${c.operator} ${c.value}`,
        }
      }
      return {
        field: c.source,
        operator: c.operator,
        value: parseValue(c.value),
        display: `${c.source} ${c.operator} ${c.value}`,
      }
    })
  emit('update:modelValue', output)
}, { deep: true })

function parseValue(v: string): any {
  if (v === 'true') return true
  if (v === 'false') return false
  const n = Number(v)
  if (!isNaN(n) && v.trim() !== '') return n
  return v
}
</script>
```

- [ ] **Step 2: Create RuleBuilderDrawer component**

```vue
<!-- frontend/src/components/logic/RuleBuilderDrawer.vue -->
<template>
  <Transition name="drawer">
    <div v-if="visible" class="drawer-overlay" @click.self="$emit('close')">
      <div class="drawer-panel">
        <div class="drawer-panel__header">
          <h2>{{ editId ? '编辑规则' : '新建规则' }}</h2>
          <button class="btn-icon" @click="$emit('close')">×</button>
        </div>

        <div class="drawer-panel__body">
          <section class="form-section">
            <h3 class="form-section__title">基本信息</h3>
            <div class="form-row"><label>规则名称</label><input v-model="form.name" class="form-input" required /></div>
            <div class="form-row"><label>描述</label><input v-model="form.description" class="form-input" /></div>
            <div class="form-row">
              <label>关联实体</label>
              <select v-model="form.entity_id" class="form-input" :disabled="!!lockedEntityId" required>
                <option value="" disabled>选择实体...</option>
                <option v-for="e in entities" :key="e.id" :value="e.id">{{ e.name }}</option>
              </select>
            </div>
            <div class="form-row">
              <label>优先级</label>
              <div class="radio-group">
                <label v-for="p in ['high','medium','low']" :key="p"><input type="radio" v-model="form.priority" :value="p" /> {{ p }}</label>
              </div>
            </div>
            <div class="form-row"><label>标签</label><input v-model="tagsInput" class="form-input" placeholder="逗号分隔，如：预警,用户" /></div>
          </section>

          <section class="form-section">
            <h3 class="form-section__title">触发条件</h3>
            <div class="mode-switch">
              <button :class="{ active: condMode === 'structured' }" @click="condMode = 'structured'">结构化模式</button>
              <button :class="{ active: condMode === 'expression' }" @click="condMode = 'expression'">表达式模式</button>
            </div>
            <ConditionBuilder
              v-if="condMode === 'structured'"
              v-model="form.conditions_json"
              :entity-id="form.entity_id"
              :entity-attributes="entityAttrs"
              :available-functions="availFunctions"
            />
            <textarea v-else v-model="form.condition_expr" class="form-input form-input--code" rows="4" placeholder="输入条件表达式..." />
          </section>

          <section class="form-section">
            <h3 class="form-section__title">关联行动</h3>
            <select v-model="form.action_id" class="form-input">
              <option value="">不关联行动</option>
              <option v-for="a in actions" :key="a.id" :value="a.id">{{ a.name }}</option>
            </select>
            <input v-model="form.action_desc" class="form-input" placeholder="动作描述（备注）" style="margin-top: 8px" />
          </section>

          <section class="form-section">
            <h3 class="form-section__title">输入参数</h3>
            <div v-for="(p, idx) in form.input_params" :key="idx" class="param-row">
              <input v-model="p.name" placeholder="参数名" class="form-input" />
              <select v-model="p.type" class="form-input"><option value="string">string</option><option value="number">number</option></select>
              <label><input type="checkbox" v-model="p.required" /> 必填</label>
              <button class="btn-icon" @click="form.input_params.splice(idx, 1)">×</button>
            </div>
            <button class="btn-text" @click="form.input_params.push({ name: '', type: 'string', required: true })">+ 添加参数</button>
          </section>
        </div>

        <div class="drawer-panel__footer">
          <button class="btn-secondary" @click="$emit('close')">取消</button>
          <button class="btn-primary" @click="handleSubmit" :disabled="submitting">{{ submitting ? '保存中...' : '保存规则' }}</button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted, computed } from 'vue'
import ConditionBuilder from './ConditionBuilder.vue'
import { ruleApi } from '../../api/rules'
import { functionApi } from '../../api/functions'
import { entityApi } from '../../api/ontology'
import { useToast } from '../../composables/useToast'

const props = defineProps<{
  visible: boolean
  editId?: string
  lockedEntityId?: string
}>()
const emit = defineEmits<{ close: []; saved: [rule: { id: string; name: string }] }>()
const toast = useToast()

const submitting = ref(false)
const condMode = ref<'structured' | 'expression'>('structured')
const entities = ref<{ id: string; name: string }[]>([])
const actions = ref<{ id: string; name: string }[]>([])
const entityAttrs = ref<{ field: string; label: string; type: string }[]>([])
const availFunctions = ref<{ callable_name: string; name: string }[]>([])
const tagsInput = ref('')

const form = reactive({
  name: '', description: '', entity_id: '', priority: 'medium',
  condition_expr: '', conditions_json: [] as any[],
  action_id: '', action_desc: '',
  input_params: [] as { name: string; type: string; required: boolean }[],
})

onMounted(async () => {
  entities.value = await entityApi.list() as any
  const funcs = await functionApi.list({ status: 'active' })
  availFunctions.value = (funcs as any[]).filter((f: any) => f.callable_name).map((f: any) => ({ callable_name: f.callable_name, name: f.name }))
})

watch(() => props.lockedEntityId, (id) => { if (id) form.entity_id = id }, { immediate: true })

async function handleSubmit() {
  if (!form.name || !form.entity_id) { toast.error('请填写必要字段'); return }
  submitting.value = true
  const payload = {
    ...form,
    tags: tagsInput.value ? tagsInput.value.split(',').map(t => t.trim()).filter(Boolean) : [],
    rule_meta_json: { match_mode: 'all' },
  }
  try {
    if (props.editId) {
      await ruleApi.update(props.editId, payload)
      toast.success('规则已更新')
      emit('saved', { id: props.editId, name: form.name })
    } else {
      const created = await ruleApi.create(payload) as any
      toast.success('规则已创建')
      emit('saved', { id: created.id, name: created.name })
    }
  } catch (e: any) {
    toast.error(e.message || '保存失败')
  } finally {
    submitting.value = false
  }
}
</script>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/logic/RuleBuilderDrawer.vue frontend/src/components/logic/ConditionBuilder.vue
git commit -m "feat(frontend): add RuleBuilderDrawer with structured condition builder"
```

---

### Task 10: Frontend — Function Builder Drawer Component

**Files:**
- Create: `frontend/src/components/logic/FunctionBuilderDrawer.vue`

- [ ] **Step 1: Create FunctionBuilderDrawer**

```vue
<!-- frontend/src/components/logic/FunctionBuilderDrawer.vue -->
<template>
  <Transition name="drawer">
    <div v-if="visible" class="drawer-overlay" @click.self="$emit('close')">
      <div class="drawer-panel">
        <div class="drawer-panel__header">
          <h2>{{ editId ? '编辑函数' : '新建函数' }}</h2>
          <button class="btn-icon" @click="$emit('close')">×</button>
        </div>

        <div class="drawer-panel__body">
          <section class="form-section">
            <h3 class="form-section__title">基本信息</h3>
            <div class="form-row"><label>函数名称</label><input v-model="form.name" class="form-input" required /></div>
            <div class="form-row"><label>调用名称</label><input v-model="form.callable_name" class="form-input form-input--code" placeholder="如 calc_churn_score" /></div>
            <div class="form-row"><label>描述</label><input v-model="form.description" class="form-input" /></div>
            <div class="form-row">
              <label>关联实体（可选）</label>
              <select v-model="form.entity_id" class="form-input" :disabled="!!lockedEntityId">
                <option value="">不关联实体</option>
                <option v-for="e in entities" :key="e.id" :value="e.id">{{ e.name }}</option>
              </select>
            </div>
            <div class="form-row-inline">
              <div class="form-row" style="flex:1"><label>返回类型</label>
                <select v-model="form.return_type" class="form-input">
                  <option value="number">number</option><option value="string">string</option>
                  <option value="boolean">boolean</option><option value="object">object</option>
                </select>
              </div>
              <div class="form-row" style="flex:1"><label>派生属性</label>
                <div class="radio-group"><label><input type="radio" v-model="form.is_derived_property" :value="true" /> 是</label><label><input type="radio" v-model="form.is_derived_property" :value="false" /> 否</label></div>
              </div>
            </div>
            <div class="form-row"><label>标签</label><input v-model="tagsInput" class="form-input" placeholder="逗号分隔" /></div>
          </section>

          <section class="form-section">
            <h3 class="form-section__title">输入参数</h3>
            <div v-for="(p, idx) in form.input_schema" :key="idx" class="param-row">
              <input v-model="p.name" placeholder="参数名" class="form-input" />
              <select v-model="p.type" class="form-input"><option value="string">string</option><option value="number">number</option></select>
              <label><input type="checkbox" v-model="p.required" /> 必填</label>
              <input v-model="p.description" placeholder="说明" class="form-input" style="flex:2" />
              <button class="btn-icon" @click="form.input_schema.splice(idx, 1)">×</button>
            </div>
            <button class="btn-text" @click="form.input_schema.push({ name: '', type: 'string', required: true, description: '' })">+ 添加参数</button>
          </section>

          <section class="form-section">
            <h3 class="form-section__title">逻辑体</h3>
            <div class="mode-switch">
              <button :class="{ active: form.logic_type === 'expression' }" @click="form.logic_type = 'expression'">表达式</button>
              <button :class="{ active: form.logic_type === 'sql' }" @click="form.logic_type = 'sql'">SQL</button>
              <button :class="{ active: form.logic_type === 'python' }" @click="form.logic_type = 'python'">Python</button>
            </div>
            <textarea v-model="form.logic_body" class="form-input form-input--code" rows="6" :placeholder="logicPlaceholder" />
          </section>

          <section class="form-section">
            <h3 class="form-section__title">测试</h3>
            <textarea v-model="testInput" class="form-input form-input--code" rows="2" placeholder='{"user_id": "U001"}' />
            <button class="btn-secondary" style="margin-top: 8px" @click="runTest" :disabled="testing">{{ testing ? '执行中...' : '运行测试' }}</button>
            <div v-if="testResult" class="test-result" :class="{ 'test-result--ok': testResult.success, 'test-result--err': !testResult.success }">
              <div>{{ testResult.success ? '✓ 成功' : '✗ 失败' }}</div>
              <div v-if="testResult.success">输出: {{ testResult.result }}</div>
              <div v-else>错误: {{ testResult.error }}</div>
              <div class="text-caption">耗时: {{ testResult.execution_ms?.toFixed(1) }}ms</div>
            </div>
          </section>
        </div>

        <div class="drawer-panel__footer">
          <button class="btn-secondary" @click="$emit('close')">取消</button>
          <button class="btn-primary" @click="handleSubmit" :disabled="submitting">{{ submitting ? '保存中...' : '保存函数' }}</button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted, computed } from 'vue'
import { functionApi } from '../../api/functions'
import { entityApi } from '../../api/ontology'
import { useToast } from '../../composables/useToast'

const props = defineProps<{ visible: boolean; editId?: string; lockedEntityId?: string }>()
const emit = defineEmits<{ close: []; saved: [fn: { id: string; name: string }] }>()
const toast = useToast()

const submitting = ref(false)
const testing = ref(false)
const testInput = ref('{}')
const testResult = ref<any>(null)
const entities = ref<{ id: string; name: string }[]>([])
const tagsInput = ref('')

const form = reactive({
  name: '', callable_name: '', description: '', entity_id: '',
  return_type: 'number', is_derived_property: false, logic_type: 'expression',
  logic_body: '', input_schema: [] as any[], status: 'active',
})

const logicPlaceholder = computed(() => {
  if (form.logic_type === 'expression') return "params['a'] * 0.8 + params['b']"
  if (form.logic_type === 'sql') return "SELECT COUNT(*) FROM table WHERE user_id = :user_id"
  return "result = params['x'] * 2"
})

onMounted(async () => { entities.value = await entityApi.list() as any })
watch(() => props.lockedEntityId, (id) => { if (id) form.entity_id = id }, { immediate: true })

async function runTest() {
  if (!props.editId) { toast.error('请先保存函数再测试'); return }
  testing.value = true
  try {
    const params = JSON.parse(testInput.value)
    testResult.value = await functionApi.test(props.editId, params)
  } catch (e: any) {
    testResult.value = { success: false, error: e.message }
  } finally {
    testing.value = false
  }
}

async function handleSubmit() {
  if (!form.name) { toast.error('请填写函数名称'); return }
  submitting.value = true
  const payload = { ...form, tags: tagsInput.value ? tagsInput.value.split(',').map(t => t.trim()).filter(Boolean) : [] }
  try {
    if (props.editId) {
      await functionApi.update(props.editId, payload)
      toast.success('函数已更新')
      emit('saved', { id: props.editId, name: form.name })
    } else {
      const created = await functionApi.create(payload) as any
      toast.success('函数已创建')
      emit('saved', { id: created.id, name: created.name })
    }
  } catch (e: any) {
    toast.error(e.message || '保存失败')
  } finally {
    submitting.value = false
  }
}
</script>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/logic/FunctionBuilderDrawer.vue
git commit -m "feat(frontend): add FunctionBuilderDrawer with multi-type editor and test panel"
```

---

### Task 11: Frontend — Update LogicView to Use Drawer Builders

**Files:**
- Modify: `frontend/src/views/logic/LogicView.vue`
- Modify: `frontend/src/views/logic/FunctionsView.vue`

- [ ] **Step 1: Replace modal form with drawer in LogicView.vue**

In `LogicView.vue`, replace the `RuleCreateForm` and edit modal with `RuleBuilderDrawer`:

Replace the import:
```typescript
// Remove: import RuleCreateForm from '../../components/common/RuleCreateForm.vue'
import RuleBuilderDrawer from '../../components/logic/RuleBuilderDrawer.vue'
```

Replace template references — remove `<RuleCreateForm ... />` and `<ModalDialog ...>` for edit, add:
```vue
<RuleBuilderDrawer
  :visible="showAdd || showEdit"
  :edit-id="editingRuleId"
  @close="showAdd = false; showEdit = false; editingRuleId = undefined"
  @saved="onRuleSaved"
/>
```

Add `editingRuleId` ref:
```typescript
const editingRuleId = ref<string | undefined>()
function openEdit(rule: any) { editingRuleId.value = rule.id; showEdit.value = true }
function onRuleSaved() { showAdd.value = false; showEdit.value = false; editingRuleId.value = undefined; store.fetchRules() }
```

- [ ] **Step 2: Do the same for FunctionsView.vue**

Import and use `FunctionBuilderDrawer` instead of the inline modal form.

- [ ] **Step 3: Verify the app compiles**

Run: `cd frontend && npm run build`
Expected: Build succeeds (or only unrelated warnings)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/logic/LogicView.vue frontend/src/views/logic/FunctionsView.vue
git commit -m "feat(frontend): replace modal forms with drawer builders in logic views"
```

---

### Task 12: Frontend — Drawer and Builder Styles

**Files:**
- Modify: `frontend/src/views/logic/logic-shared.css`

- [ ] **Step 1: Add drawer styles**

Append to `frontend/src/views/logic/logic-shared.css`:

```css
/* Drawer */
.drawer-overlay {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0,0,0,0.3);
  display: flex; justify-content: flex-end;
}
.drawer-panel {
  width: 640px; max-width: 90vw; height: 100vh;
  background: var(--neutral-0, #fff);
  display: flex; flex-direction: column;
  box-shadow: -4px 0 24px rgba(0,0,0,0.1);
}
.drawer-panel__header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 24px; border-bottom: 1px solid var(--neutral-200, #e9ecef);
}
.drawer-panel__header h2 { font-size: 18px; font-weight: 600; margin: 0; }
.drawer-panel__body { flex: 1; overflow-y: auto; padding: 24px; }
.drawer-panel__footer {
  display: flex; justify-content: flex-end; gap: 12px;
  padding: 16px 24px; border-top: 1px solid var(--neutral-200, #e9ecef);
}

/* Form sections */
.form-section { margin-bottom: 24px; }
.form-section__title { font-size: 14px; font-weight: 600; margin-bottom: 12px; color: var(--neutral-700, #495057); }

/* Mode switch */
.mode-switch { display: flex; gap: 0; margin-bottom: 12px; border: 1px solid var(--neutral-200); border-radius: 6px; overflow: hidden; }
.mode-switch button { flex: 1; padding: 6px 12px; font-size: 13px; border: none; background: var(--neutral-50); cursor: pointer; }
.mode-switch button.active { background: var(--semantic-500, #5c7cfa); color: #fff; }

/* Condition builder */
.condition-builder__mode { margin-bottom: 12px; }
.condition-row { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
.condition-row__num { width: 20px; font-size: 12px; color: var(--neutral-500); text-align: center; }
.condition-row__source { flex: 3; }
.condition-row__op { width: 80px; }
.condition-row__value { flex: 2; }

/* Param row */
.param-row { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
.param-row .form-input { flex: 1; }

/* Test result */
.test-result { margin-top: 8px; padding: 12px; border-radius: 6px; font-size: 13px; }
.test-result--ok { background: #e6f9e6; border: 1px solid #b7e1b7; }
.test-result--err { background: #fde8e8; border: 1px solid #f5c6c6; }

/* Drawer transitions */
.drawer-enter-active, .drawer-leave-active { transition: opacity 0.2s; }
.drawer-enter-active .drawer-panel, .drawer-leave-active .drawer-panel { transition: transform 0.25s ease; }
.drawer-enter-from, .drawer-leave-to { opacity: 0; }
.drawer-enter-from .drawer-panel, .drawer-leave-to .drawer-panel { transform: translateX(100%); }
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/logic/logic-shared.css
git commit -m "feat(frontend): add drawer and condition builder styles"
```

---

### Task 13: Frontend — Registry Panel Component for Skill Editor

**Files:**
- Create: `frontend/src/components/logic/RegistryPanel.vue`

- [ ] **Step 1: Create RegistryPanel**

```vue
<!-- frontend/src/components/logic/RegistryPanel.vue -->
<template>
  <div class="registry-panel">
    <div class="registry-panel__header">
      <h3>添加能力</h3>
      <button class="btn-icon" @click="$emit('close')">×</button>
    </div>
    <div class="registry-panel__toolbar">
      <input v-model="search" class="form-input" placeholder="搜索规则或函数..." />
      <div class="filter-tags">
        <button :class="{ active: typeFilter === 'all' }" @click="typeFilter = 'all'">全部</button>
        <button :class="{ active: typeFilter === 'rule' }" @click="typeFilter = 'rule'">规则</button>
        <button :class="{ active: typeFilter === 'function' }" @click="typeFilter = 'function'">函数</button>
      </div>
    </div>
    <div class="registry-panel__body">
      <div v-for="group in filteredGroups" :key="group.entity_id || '__standalone__'" class="registry-group">
        <div class="registry-group__title">{{ group.entity_name }}</div>
        <div v-for="item in group.items" :key="item.id" class="registry-item">
          <div class="registry-item__icon">{{ item.type === 'rule' ? '⚡' : 'ƒ' }}</div>
          <div class="registry-item__info">
            <div class="registry-item__name">{{ item.name }} <span class="badge">{{ item.type === 'rule' ? '规则' : '函数' }}</span></div>
            <div class="registry-item__desc text-caption">{{ item.description }}</div>
            <div class="registry-item__meta text-caption">
              输入: {{ item.input_params.map((p: any) => p.name).join(', ') || '无' }}
              · 输出: {{ item.output_info }}
            </div>
          </div>
          <button class="btn-text" @click="$emit('add', item)">+ 添加</button>
        </div>
      </div>
      <div v-if="filteredGroups.length === 0" class="registry-empty text-caption">无匹配结果</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { registryApi, type RegistryGroup } from '../../api/registry'

defineEmits<{ close: []; add: [item: any] }>()

const search = ref('')
const typeFilter = ref('all')
const groups = ref<RegistryGroup[]>([])

onMounted(async () => { groups.value = await registryApi.listGrouped() as any })

const filteredGroups = computed(() => {
  return groups.value
    .map(g => ({
      ...g,
      items: g.items.filter(item => {
        if (typeFilter.value !== 'all' && item.type !== typeFilter.value) return false
        if (search.value && !(item.name + item.description).toLowerCase().includes(search.value.toLowerCase())) return false
        return true
      }),
    }))
    .filter(g => g.items.length > 0)
})
</script>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/logic/RegistryPanel.vue
git commit -m "feat(frontend): add RegistryPanel component for skill editor integration"
```

---

### Task 14: Add Entity Logic Tab (Entity Detail Integration)

**Files:**
- Create: `frontend/src/components/logic/EntityLogicTab.vue`

- [ ] **Step 1: Create EntityLogicTab component**

```vue
<!-- frontend/src/components/logic/EntityLogicTab.vue -->
<template>
  <div class="entity-logic-tab">
    <!-- Rules section -->
    <div class="logic-section">
      <div class="logic-section__header">
        <h3>规则 ({{ rules.length }})</h3>
        <button class="btn-text" @click="showRuleBuilder = true">+ 新建规则</button>
      </div>
      <div v-for="r in rules" :key="r.id" class="logic-item" @click="editRule(r)">
        <span class="logic-item__status" :class="`status--${r.status}`"></span>
        <span class="logic-item__name">{{ r.name }}</span>
        <span class="logic-item__priority badge" :class="`priority--${r.priority}`">{{ r.priority }}</span>
        <span class="logic-item__stat text-caption">{{ r.status }} · 触发{{ r.trigger_count }}次</span>
      </div>
      <div v-if="rules.length === 0" class="logic-empty text-caption">暂无规则</div>
    </div>

    <!-- Functions section -->
    <div class="logic-section">
      <div class="logic-section__header">
        <h3>函数 ({{ functions.length }})</h3>
        <button class="btn-text" @click="showFuncBuilder = true">+ 新建函数</button>
      </div>
      <div v-for="fn in functions" :key="fn.id" class="logic-item" @click="editFunc(fn)">
        <span class="logic-item__icon">ƒ</span>
        <span class="logic-item__name">{{ fn.name }}</span>
        <span class="badge">{{ fn.is_derived_property ? '派生属性' : '独立函数' }}</span>
        <span class="logic-item__stat text-caption">{{ fn.return_type }} · 调用{{ fn.execution_count }}次</span>
      </div>
      <div v-if="functions.length === 0" class="logic-empty text-caption">暂无函数</div>
    </div>

    <!-- Actions section -->
    <div class="logic-section">
      <div class="logic-section__header">
        <h3>行动 ({{ actions.length }})</h3>
      </div>
      <div v-for="a in actions" :key="a.id" class="logic-item">
        <span class="logic-item__icon">▶</span>
        <span class="logic-item__name">{{ a.name }}</span>
        <span class="badge">{{ a.type }}</span>
        <span class="logic-item__stat text-caption">{{ a.status }}</span>
      </div>
      <div v-if="actions.length === 0" class="logic-empty text-caption">暂无行动</div>
    </div>

    <RuleBuilderDrawer :visible="showRuleBuilder" :locked-entity-id="entityId" :edit-id="editingRuleId" @close="showRuleBuilder = false; editingRuleId = undefined" @saved="onSaved" />
    <FunctionBuilderDrawer :visible="showFuncBuilder" :locked-entity-id="entityId" :edit-id="editingFuncId" @close="showFuncBuilder = false; editingFuncId = undefined" @saved="onSaved" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import RuleBuilderDrawer from './RuleBuilderDrawer.vue'
import FunctionBuilderDrawer from './FunctionBuilderDrawer.vue'
import { ruleApi } from '../../api/rules'
import { functionApi } from '../../api/functions'

const props = defineProps<{ entityId: string }>()

const rules = ref<any[]>([])
const functions = ref<any[]>([])
const actions = ref<any[]>([])
const showRuleBuilder = ref(false)
const showFuncBuilder = ref(false)
const editingRuleId = ref<string>()
const editingFuncId = ref<string>()

onMounted(() => loadData())

async function loadData() {
  rules.value = await ruleApi.list({ entityId: props.entityId }) as any
  functions.value = await functionApi.list({ entity_id: props.entityId }) as any
}

function editRule(r: any) { editingRuleId.value = r.id; showRuleBuilder.value = true }
function editFunc(fn: any) { editingFuncId.value = fn.id; showFuncBuilder.value = true }
function onSaved() { showRuleBuilder.value = false; showFuncBuilder.value = false; editingRuleId.value = undefined; editingFuncId.value = undefined; loadData() }
</script>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/logic/EntityLogicTab.vue
git commit -m "feat(frontend): add EntityLogicTab for entity detail integration"
```

---

### Task 15: Wire Up Skill Executor to Support Rule/Function Tools

**Files:**
- Modify: `backend/app/services/skill_executor.py`

- [ ] **Step 1: Add evaluate_rule and call_function tool handlers**

Add after the existing `execute_generated_skill` function:

```python
def execute_skill_tool_call(tool_type: str, tool_config: dict, params: dict, db: Session) -> dict:
    """Execute a rule or function tool referenced by a skill"""
    if tool_type == "rule":
        rule_id = tool_config.get("rule_id")
        if not rule_id:
            return {"success": False, "summary": "Missing rule_id", "data": {}}
        rule = db.query(BusinessRule).get(rule_id)
        if not rule:
            return {"success": False, "summary": f"Rule {rule_id} not found", "data": {}}
        user_id = params.get("user_id", "")
        evaluator = RuleEvaluator(db)
        result = evaluator.evaluate(rule, user_id)
        db.commit()
        return {
            "success": True,
            "summary": f"Rule '{result.rule_name}' {'triggered' if result.triggered else 'not triggered'}",
            "data": {
                "triggered": result.triggered,
                "confidence": result.confidence,
                "risk_level": result.risk_level,
                "matched_count": result.matched_count,
                "total_count": result.total_count,
            },
        }

    elif tool_type == "function":
        from app.services.function_executor import FunctionExecutor
        callable_name = tool_config.get("callable_name")
        func_id = tool_config.get("function_id")
        executor = FunctionExecutor(db)
        if callable_name:
            result = executor.execute_by_callable_name(callable_name, params)
        elif func_id:
            from app.models.function import OntologyFunction
            func = db.get(OntologyFunction, func_id)
            if not func:
                return {"success": False, "summary": f"Function {func_id} not found", "data": {}}
            result = executor.execute(func, params)
        else:
            return {"success": False, "summary": "Missing callable_name or function_id", "data": {}}

        return {
            "success": result.success,
            "summary": f"Function returned: {result.value}" if result.success else f"Error: {result.error}",
            "data": {"value": result.value, "execution_ms": result.execution_ms},
        }

    return {"success": False, "summary": f"Unknown tool type: {tool_type}", "data": {}}
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/skill_executor.py
git commit -m "feat: add skill tool call handler for rule/function invocation"
```

---

### Task 16: Final Integration Test

**Files:**
- Create: `backend/tests/test_rule_function_integration.py`

- [ ] **Step 1: Write integration test**

```python
# backend/tests/test_rule_function_integration.py
"""Integration test: rule with function_call condition"""
import pytest
from unittest.mock import MagicMock, patch
from app.services.rule_engine import RuleEvaluator
from app.services.function_executor import FunctionExecutor


def test_rule_evaluates_function_call_condition():
    """A rule condition of type function_call should invoke FunctionExecutor"""
    db = MagicMock()

    rule = MagicMock()
    rule.name = "test_rule"
    rule.conditions_json = [
        {
            "type": "function_call",
            "callable_name": "calc_score",
            "params": {"user_id": "$context.user_id"},
            "operator": ">=",
            "value": 0.7,
            "display": "calc_score() >= 0.7",
        }
    ]
    rule.rule_meta_json = {"match_mode": "all"}
    rule.trigger_count = 0
    rule.last_triggered = None

    mock_func = MagicMock()
    mock_func.logic_type = "expression"
    mock_func.logic_body = "0.85"
    mock_func.status = "active"
    mock_func.callable_name = "calc_score"
    mock_func.entity_id = None
    mock_func.name = "calc_score"
    mock_func.input_schema = []
    mock_func.execution_count = 0
    mock_func.last_executed = None

    db.query.return_value.filter.return_value.first.return_value = mock_func

    evaluator = RuleEvaluator(db)
    result = evaluator.evaluate(rule, "user-001")

    assert result.triggered is True
    assert result.confidence == 1.0
    assert result.conditions[0].matched is True
    assert result.conditions[0].actual == 0.85
```

- [ ] **Step 2: Run test**

Run: `cd backend && python -m pytest tests/test_rule_function_integration.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_rule_function_integration.py
git commit -m "test: add integration test for rule with function_call conditions"
```
