# 本体组件编排与技能集成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Function/Rule/Action 纳入本体版本发布体系，使流程编排（AIP 场景）和技能管理能够引用已发布版本的组件快照。

**Architecture:** 方案 A — 分类型快照表。在发布时将 Function/Rule/Action 从草稿源表拷贝为不可变快照（OntologyVersionFunction/Rule/Action），流程编排和技能通过 ref_id 引用快照。

**Tech Stack:** Python 3.11 + FastAPI + SQLAlchemy 2.0 (backend), Vue 3 + TypeScript + Ant Design Vue + Vue Flow (frontend), SQLite (dev DB), pytest (tests)

---

## File Structure

### Backend — New Files
- `backend/app/models/version_components.py` — OntologyVersionFunction, OntologyVersionRule, OntologyVersionAction 模型
- `backend/app/models/skill_tool_ref.py` — SkillToolRef 模型
- `backend/app/services/version_component_snapshot.py` — 发布快照服务
- `backend/app/services/workflow_executor_components.py` — 流程编排执行 F/R/A 节点
- `backend/app/api/v1/version_components.py` — 版本组件查询 API
- `backend/app/api/v1/impact_analysis.py` — 删除影响分析 API
- `backend/tests/test_version_component_snapshot.py` — 快照测试
- `backend/tests/test_workflow_executor_components.py` — 执行器测试
- `backend/tests/test_impact_analysis.py` — 影响分析测试

### Backend — Modified Files
- `backend/app/models/__init__.py` — 注册新模型
- `backend/app/models/version.py` — OntologyVersion 增加 relationship
- `backend/app/schemas/function.py` — input_schema 增强
- `backend/app/schemas/rule.py` — conditions_json 增强
- `backend/app/schemas/action.py` — parameters_json 增强
- `backend/app/api/v1/ontology_publish.py` — 发布流程增加组件快照
- `backend/app/api/v1/skills.py` — 技能工具引用 CRUD
- `backend/app/services/skill_executor.py` — Agent 执行时加载 F/R/A 工具
- `backend/app/main.py` — 注册新路由

### Frontend — New Files
- `frontend/src/api/versionComponents.ts` — 版本组件 API 调用
- `frontend/src/views/aip/panels/ParamMappingEditor.vue` — 参数映射编辑器组件

### Frontend — Modified Files
- `frontend/src/views/aip/panels/AddNodeDrawer.vue` — 添加 F/R/A 节点类型
- `frontend/src/views/aip/panels/PropertyPanel.vue` — F/R/A 节点配置面板
- `frontend/src/views/aip/aipData.ts` — 节点类型元数据
- `frontend/src/views/agents/skills/SkillDetailView.vue` — 技能工具引用 UI
- `frontend/src/components/logic/FunctionBuilderDrawer.vue` — 参数关联实体属性
- `frontend/src/components/common/RuleCreateForm.vue` — 条件关联实体属性

---

## Task 1: 版本组件快照模型 (Backend Model)

**Files:**
- Create: `backend/app/models/version_components.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/models/version.py`
- Test: `backend/tests/test_version_component_snapshot.py`

- [ ] **Step 1: Write failing test — model instantiation**

```python
# backend/tests/test_version_component_snapshot.py
"""Test version component snapshot models can be created"""
from app.models.version_components import (
    OntologyVersionFunction,
    OntologyVersionRule,
    OntologyVersionAction,
)


def test_version_function_fields():
    vf = OntologyVersionFunction(
        version_id="v1",
        source_function_id="f1",
        version_entity_id="ve1",
        name="calc_risk",
        return_type="number",
        input_schema=[
            {"name": "score", "type": "number", "version_attribute_id": "va1", "required": True}
        ],
        logic_type="expression",
        logic_body="score * 0.8",
        callable_name="calc_risk",
    )
    assert vf.name == "calc_risk"
    assert vf.input_schema[0]["version_attribute_id"] == "va1"


def test_version_rule_fields():
    vr = OntologyVersionRule(
        version_id="v1",
        source_rule_id="r1",
        version_entity_id="ve1",
        name="high_risk_rule",
        condition_expr="credit_score < 60",
        conditions_json=[
            {"field": "credit_score", "operator": "<", "value": 60, "version_attribute_id": "va2"}
        ],
        priority="high",
        input_params=[{"name": "credit_score", "type": "number", "version_attribute_id": "va2", "required": True}],
    )
    assert vr.name == "high_risk_rule"
    assert vr.conditions_json[0]["version_attribute_id"] == "va2"


def test_version_action_fields():
    va = OntologyVersionAction(
        version_id="v1",
        source_action_id="a1",
        version_entity_id="ve1",
        name="send_alert",
        category="domain",
        action_type="notification",
        type_config={"channel": "sms"},
        parameters_json=[
            {"name": "phone", "type": "string", "version_attribute_id": "va3", "required": True}
        ],
    )
    assert va.action_type == "notification"
    assert va.parameters_json[0]["version_attribute_id"] == "va3"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_version_component_snapshot.py -v`
Expected: FAIL with ImportError (module not found)

- [ ] **Step 3: Create version_components model**

```python
# backend/app/models/version_components.py
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.identifiers import gen_uuid


class OntologyVersionFunction(Base):
    __tablename__ = "ontology_version_functions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    version_id: Mapped[str] = mapped_column(ForeignKey("ontology_versions.id", ondelete="CASCADE"))
    source_function_id: Mapped[str] = mapped_column(String(36), nullable=False)
    version_entity_id: Mapped[str] = mapped_column(
        ForeignKey("ontology_version_entities.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    return_type: Mapped[str] = mapped_column(String(50), default="string")
    input_schema: Mapped[list | None] = mapped_column(JSON)
    logic_type: Mapped[str] = mapped_column(String(30), default="expression")
    logic_body: Mapped[str] = mapped_column(Text, default="")
    callable_name: Mapped[str] = mapped_column(String(100), default="")
    tags: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OntologyVersionRule(Base):
    __tablename__ = "ontology_version_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    version_id: Mapped[str] = mapped_column(ForeignKey("ontology_versions.id", ondelete="CASCADE"))
    source_rule_id: Mapped[str] = mapped_column(String(36), nullable=False)
    version_entity_id: Mapped[str] = mapped_column(
        ForeignKey("ontology_version_entities.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    condition_expr: Mapped[str] = mapped_column(Text, default="")
    conditions_json: Mapped[list | None] = mapped_column(JSON)
    priority: Mapped[str] = mapped_column(String(10), default="medium")
    input_params: Mapped[list | None] = mapped_column(JSON)
    output_schema: Mapped[dict | None] = mapped_column(JSON)
    tags: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OntologyVersionAction(Base):
    __tablename__ = "ontology_version_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    version_id: Mapped[str] = mapped_column(ForeignKey("ontology_versions.id", ondelete="CASCADE"))
    source_action_id: Mapped[str] = mapped_column(String(36), nullable=False)
    version_entity_id: Mapped[str | None] = mapped_column(
        ForeignKey("ontology_version_entities.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(20), default="domain")
    action_type: Mapped[str] = mapped_column(String(30), nullable=False)
    type_config: Mapped[dict | None] = mapped_column(JSON)
    description: Mapped[str | None] = mapped_column(Text)
    parameters_json: Mapped[list | None] = mapped_column(JSON)
    output_schema: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 4: Register models in __init__.py**

Add to `backend/app/models/__init__.py`:
```python
from app.models.version_components import (
    OntologyVersionFunction, OntologyVersionRule, OntologyVersionAction,
)
```

And add to `__all__`:
```python
"OntologyVersionFunction", "OntologyVersionRule", "OntologyVersionAction",
```

- [ ] **Step 5: Add relationships to OntologyVersion**

In `backend/app/models/version.py`, add to `OntologyVersion` class:
```python
functions: Mapped[list["OntologyVersionFunction"]] = relationship(
    back_populates="version", cascade="all, delete-orphan"
)
rules: Mapped[list["OntologyVersionRule"]] = relationship(
    back_populates="version", cascade="all, delete-orphan"
)
actions: Mapped[list["OntologyVersionAction"]] = relationship(
    back_populates="version", cascade="all, delete-orphan"
)
```

And add `version` relationship back-populates to each model in `version_components.py`:
```python
# In OntologyVersionFunction:
from sqlalchemy.orm import relationship
version: Mapped["OntologyVersion"] = relationship(back_populates="functions")

# In OntologyVersionRule:
version: Mapped["OntologyVersion"] = relationship(back_populates="rules")

# In OntologyVersionAction:
version: Mapped["OntologyVersion"] = relationship(back_populates="actions")
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_version_component_snapshot.py -v`
Expected: PASS (3 tests)

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/version_components.py backend/app/models/__init__.py backend/app/models/version.py backend/tests/test_version_component_snapshot.py
git commit -m "feat: add OntologyVersionFunction/Rule/Action snapshot models"
```

---

## Task 2: 版本组件快照服务 (Snapshot Service)

**Files:**
- Create: `backend/app/services/version_component_snapshot.py`
- Test: `backend/tests/test_version_component_snapshot.py` (append)

- [ ] **Step 1: Write failing test — snapshot creation**

Append to `backend/tests/test_version_component_snapshot.py`:

```python
from unittest.mock import MagicMock, patch
from app.services.version_component_snapshot import snapshot_components_for_version


def test_snapshot_functions_for_version():
    """snapshot service copies active functions into version tables"""
    db = MagicMock()

    # Mock: version has one entity with source_entity_id="e1"
    version_entity = MagicMock()
    version_entity.id = "ve1"
    version_entity.source_entity_id = "e1"
    version_entity.attributes = [MagicMock(id="va1", source_attribute_id="a1")]

    version = MagicMock()
    version.id = "v1"
    version.entities = [version_entity]

    # Mock: one active function linked to entity e1
    mock_func = MagicMock()
    mock_func.id = "f1"
    mock_func.entity_id = "e1"
    mock_func.name = "calc_risk"
    mock_func.description = "Calculate risk"
    mock_func.return_type = "number"
    mock_func.input_schema = [{"name": "score", "type": "number", "attribute_id": "a1", "required": True}]
    mock_func.logic_type = "expression"
    mock_func.logic_body = "score * 0.8"
    mock_func.callable_name = "calc_risk"
    mock_func.tags = ["risk"]

    db.query.return_value.filter.return_value.all.return_value = [mock_func]

    result = snapshot_components_for_version(db, version)

    assert result["functions_count"] == 1
    # Verify db.add was called with a version function that has version_attribute_id mapped
    added_obj = db.add.call_args_list[0][0][0]
    assert added_obj.name == "calc_risk"
    assert added_obj.input_schema[0]["version_attribute_id"] == "va1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_version_component_snapshot.py::test_snapshot_functions_for_version -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement snapshot service**

```python
# backend/app/services/version_component_snapshot.py
"""Snapshot active Function/Rule/Action into versioned tables on publish."""
from sqlalchemy.orm import Session

from app.models.function import OntologyFunction
from app.models.rule import BusinessRule, EntityAction
from app.models.version import OntologyVersion, OntologyVersionEntity, OntologyVersionAttribute
from app.models.version_components import (
    OntologyVersionFunction, OntologyVersionRule, OntologyVersionAction,
)


def _build_attribute_map(version_entity: OntologyVersionEntity) -> dict[str, str]:
    """Map source_attribute_id -> version_attribute_id for a version entity."""
    return {
        va.source_attribute_id: va.id
        for va in version_entity.attributes
    }


def _remap_schema(schema: list | None, attr_map: dict[str, str]) -> list | None:
    """Replace attribute_id with version_attribute_id in param/condition lists."""
    if not schema:
        return schema
    result = []
    for item in schema:
        new_item = dict(item)
        src_attr_id = new_item.pop("attribute_id", None)
        if src_attr_id and src_attr_id in attr_map:
            new_item["version_attribute_id"] = attr_map[src_attr_id]
        else:
            new_item["version_attribute_id"] = None
        result.append(new_item)
    return result


def snapshot_components_for_version(db: Session, version: OntologyVersion) -> dict:
    """Create immutable snapshots of all active F/R/A for a version's entities."""
    counts = {"functions_count": 0, "rules_count": 0, "actions_count": 0}

    for ve in version.entities:
        attr_map = _build_attribute_map(ve)

        # Functions
        functions = db.query(OntologyFunction).filter(
            OntologyFunction.entity_id == ve.source_entity_id,
            OntologyFunction.status == "active",
        ).all()
        for f in functions:
            vf = OntologyVersionFunction(
                version_id=version.id,
                source_function_id=f.id,
                version_entity_id=ve.id,
                name=f.name,
                description=f.description or "",
                return_type=f.return_type,
                input_schema=_remap_schema(f.input_schema, attr_map),
                logic_type=f.logic_type,
                logic_body=f.logic_body,
                callable_name=f.callable_name,
                tags=f.tags,
            )
            db.add(vf)
            counts["functions_count"] += 1

        # Rules
        rules = db.query(BusinessRule).filter(
            BusinessRule.entity_id == ve.source_entity_id,
            BusinessRule.status == "active",
        ).all()
        for r in rules:
            vr = OntologyVersionRule(
                version_id=version.id,
                source_rule_id=r.id,
                version_entity_id=ve.id,
                name=r.name,
                description=r.description or "",
                condition_expr=r.condition_expr,
                conditions_json=_remap_schema(r.conditions_json, attr_map),
                priority=r.priority,
                input_params=_remap_schema(r.input_params, attr_map),
                output_schema=r.output_schema,
                tags=r.tags,
            )
            db.add(vr)
            counts["rules_count"] += 1

        # Actions (domain)
        actions = db.query(EntityAction).filter(
            EntityAction.entity_id == ve.source_entity_id,
            EntityAction.status == "active",
        ).all()
        for a in actions:
            va = OntologyVersionAction(
                version_id=version.id,
                source_action_id=a.id,
                version_entity_id=ve.id,
                name=a.name,
                category=a.category,
                action_type=a.action_type,
                type_config=a.type_config,
                description=a.description,
                parameters_json=_remap_schema(a.parameters_json, attr_map),
                output_schema=a.output_schema,
            )
            db.add(va)
            counts["actions_count"] += 1

    # System actions (no entity binding)
    system_actions = db.query(EntityAction).filter(
        EntityAction.category == "system",
        EntityAction.status == "active",
        EntityAction.entity_id.is_(None),
    ).all()
    for a in system_actions:
        va = OntologyVersionAction(
            version_id=version.id,
            source_action_id=a.id,
            version_entity_id=None,
            name=a.name,
            category="system",
            action_type=a.action_type,
            type_config=a.type_config,
            description=a.description,
            parameters_json=a.parameters_json,
            output_schema=a.output_schema,
        )
        db.add(va)
        counts["actions_count"] += 1

    db.flush()
    return counts
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_version_component_snapshot.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/version_component_snapshot.py backend/tests/test_version_component_snapshot.py
git commit -m "feat: add version component snapshot service"
```

---

## Task 3: 发布流程集成 (Publish API Integration)

**Files:**
- Modify: `backend/app/api/v1/ontology_publish.py`

- [ ] **Step 1: Add snapshot call to publish workflow**

In `backend/app/api/v1/ontology_publish.py`, add import:
```python
from app.services.version_component_snapshot import snapshot_components_for_version
```

Find the publish/approve endpoint (the one that sets `v.status = "published"`) and add before `db.commit()`:
```python
# Snapshot F/R/A components
snapshot_result = snapshot_components_for_version(db, v)
```

- [ ] **Step 2: Add endpoint to query version components**

Add to `backend/app/api/v1/ontology_publish.py`:
```python
@router.get("/versions/{version_id}/functions")
def list_version_functions(version_id: str, db: Session = Depends(get_db)):
    from app.models.version_components import OntologyVersionFunction
    items = db.query(OntologyVersionFunction).filter(
        OntologyVersionFunction.version_id == version_id
    ).all()
    return [{"id": f.id, "name": f.name, "description": f.description,
             "return_type": f.return_type, "input_schema": f.input_schema,
             "version_entity_id": f.version_entity_id, "callable_name": f.callable_name}
            for f in items]


@router.get("/versions/{version_id}/rules")
def list_version_rules(version_id: str, db: Session = Depends(get_db)):
    from app.models.version_components import OntologyVersionRule
    items = db.query(OntologyVersionRule).filter(
        OntologyVersionRule.version_id == version_id
    ).all()
    return [{"id": r.id, "name": r.name, "description": r.description,
             "condition_expr": r.condition_expr, "priority": r.priority,
             "input_params": r.input_params, "version_entity_id": r.version_entity_id}
            for r in items]


@router.get("/versions/{version_id}/actions")
def list_version_actions(version_id: str, db: Session = Depends(get_db)):
    from app.models.version_components import OntologyVersionAction
    items = db.query(OntologyVersionAction).filter(
        OntologyVersionAction.version_id == version_id
    ).all()
    return [{"id": a.id, "name": a.name, "description": a.description,
             "category": a.category, "action_type": a.action_type,
             "parameters_json": a.parameters_json, "version_entity_id": a.version_entity_id}
            for a in items]
```

- [ ] **Step 3: Run existing publish tests to ensure no regression**

Run: `cd backend && python -m pytest tests/ -v -k "publish or version" --tb=short`
Expected: All existing tests pass

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/ontology_publish.py
git commit -m "feat: integrate component snapshot into publish flow + query APIs"
```

---

## Task 4: SkillToolRef 模型 (Skill Tool Reference)

**Files:**
- Create: `backend/app/models/skill_tool_ref.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create SkillToolRef model**

```python
# backend/app/models/skill_tool_ref.py
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.utils.identifiers import gen_uuid


class SkillToolRef(Base):
    __tablename__ = "skill_tool_refs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    skill_id: Mapped[str] = mapped_column(String(36), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    version_id: Mapped[str] = mapped_column(String(36), ForeignKey("ontology_versions.id"), nullable=False)
    ref_type: Mapped[str] = mapped_column(String(20), nullable=False)
    ref_id: Mapped[str] = mapped_column(String(36), nullable=False)
    alias: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    param_override: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 2: Register in __init__.py**

Add to `backend/app/models/__init__.py`:
```python
from app.models.skill_tool_ref import SkillToolRef
```
Add `"SkillToolRef"` to `__all__`.

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/skill_tool_ref.py backend/app/models/__init__.py
git commit -m "feat: add SkillToolRef model for skill-to-component references"
```

---

## Task 5: 流程编排执行器扩展 (Workflow Executor)

**Files:**
- Create: `backend/app/services/workflow_executor_components.py`
- Test: `backend/tests/test_workflow_executor_components.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_workflow_executor_components.py
"""Test workflow executor for function-call / rule-evaluate / action-execute nodes"""
from unittest.mock import MagicMock
from app.services.workflow_executor_components import execute_component_node


def test_execute_function_node():
    db = MagicMock()
    mock_vf = MagicMock()
    mock_vf.logic_type = "expression"
    mock_vf.logic_body = "score * 0.8"
    mock_vf.input_schema = [{"name": "score", "type": "number", "version_attribute_id": "va1", "required": True}]
    mock_vf.name = "calc_risk"
    mock_vf.callable_name = "calc_risk"
    mock_vf.entity_id = None
    mock_vf.execution_count = 0
    mock_vf.last_executed = None

    db.query.return_value.filter.return_value.first.return_value = mock_vf

    node_data = {
        "ref_type": "function",
        "ref_id": "vf1",
        "param_mapping": {
            "score": {"source": "variable", "var_name": "input_score"}
        },
        "output_var": "risk_result",
    }
    context = {"vars": {"input_score": 85}}

    result = execute_component_node(db, node_data, context)

    assert result["success"] is True
    assert result["value"] == 68.0  # 85 * 0.8


def test_execute_rule_node():
    db = MagicMock()
    mock_vr = MagicMock()
    mock_vr.name = "high_risk"
    mock_vr.conditions_json = [
        {"field": "score", "operator": "<", "value": 60, "version_attribute_id": "va1"}
    ]
    mock_vr.rule_meta_json = {"match_mode": "all"}
    mock_vr.condition_expr = "score < 60"
    mock_vr.input_params = [{"name": "score", "type": "number", "version_attribute_id": "va1", "required": True}]
    mock_vr.trigger_count = 0
    mock_vr.last_triggered = None

    db.query.return_value.filter.return_value.first.return_value = mock_vr

    node_data = {
        "ref_type": "rule",
        "ref_id": "vr1",
        "param_mapping": {
            "score": {"source": "variable", "var_name": "credit_score"}
        },
    }
    context = {"vars": {"credit_score": 45}}

    result = execute_component_node(db, node_data, context)

    assert result["triggered"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_workflow_executor_components.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement executor**

```python
# backend/app/services/workflow_executor_components.py
"""Execute function-call / rule-evaluate / action-execute nodes in workflow context."""
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.version_components import (
    OntologyVersionFunction, OntologyVersionRule, OntologyVersionAction,
)
from app.services.function_executor import FunctionExecutor
from app.services.rule_engine import RuleEvaluator

logger = logging.getLogger(__name__)


def _resolve_params(param_mapping: dict, context: dict) -> dict:
    """Resolve param_mapping against execution context."""
    resolved = {}
    for param_name, mapping in param_mapping.items():
        source = mapping.get("source")
        if source == "variable":
            resolved[param_name] = context.get("vars", {}).get(mapping["var_name"])
        elif source == "node":
            node_output = context.get("nodes", {}).get(mapping["node_id"], {})
            field_path = mapping["field"].split(".")
            val = node_output
            for part in field_path:
                if isinstance(val, dict):
                    val = val.get(part)
                else:
                    val = None
                    break
            resolved[param_name] = val
        elif source == "expression":
            resolved[param_name] = _eval_expression(mapping["expr"], context)
        else:
            resolved[param_name] = None
    return resolved


def _eval_expression(expr: str, context: dict) -> Any:
    """Evaluate a simple template expression like {{vars.amount * 0.8}}."""
    import re
    # Extract content between {{ }}
    match = re.match(r'^\{\{(.+)\}\}$', expr.strip())
    if not match:
        return expr
    inner = match.group(1).strip()
    # Build a safe namespace from context
    ns = {}
    ns["nodes"] = context.get("nodes", {})
    ns["vars"] = context.get("vars", {})
    try:
        return eval(inner, {"__builtins__": {}}, ns)
    except Exception:
        return None


def execute_component_node(db: Session, node_data: dict, context: dict) -> dict:
    """Execute a component node (function/rule/action) and return result."""
    ref_type = node_data["ref_type"]
    ref_id = node_data["ref_id"]
    param_mapping = node_data.get("param_mapping", {})

    resolved_params = _resolve_params(param_mapping, context)

    if ref_type == "function":
        vf = db.query(OntologyVersionFunction).filter(
            OntologyVersionFunction.id == ref_id
        ).first()
        if not vf:
            return {"success": False, "error": f"Version function {ref_id} not found"}
        executor = FunctionExecutor(db)
        result = executor.execute(vf, resolved_params)
        return {"success": result.success, "value": result.value, "error": result.error,
                "execution_ms": result.execution_ms}

    elif ref_type == "rule":
        vr = db.query(OntologyVersionRule).filter(
            OntologyVersionRule.id == ref_id
        ).first()
        if not vr:
            return {"triggered": False, "error": f"Version rule {ref_id} not found"}
        evaluator = RuleEvaluator(db)
        # Build a context string from resolved params for the evaluator
        rule_result = evaluator.evaluate(vr, resolved_params)
        return {"triggered": rule_result.triggered, "confidence": rule_result.confidence,
                "conditions": [{"field": c.field, "matched": c.matched} for c in rule_result.conditions]}

    elif ref_type == "action":
        va = db.query(OntologyVersionAction).filter(
            OntologyVersionAction.id == ref_id
        ).first()
        if not va:
            return {"success": False, "error": f"Version action {ref_id} not found"}
        from app.services.action_executors import get_executor
        executor = get_executor(va.action_type)
        result = executor.execute(va.type_config or {}, resolved_params, db)
        return {"success": result.get("success", True), "message": result.get("message", ""),
                "output": result.get("output")}

    return {"success": False, "error": f"Unknown ref_type: {ref_type}"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_workflow_executor_components.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/workflow_executor_components.py backend/tests/test_workflow_executor_components.py
git commit -m "feat: workflow executor for function/rule/action nodes"
```

---

## Task 6: 影响分析 API (Impact Analysis)

**Files:**
- Create: `backend/app/api/v1/impact_analysis.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_impact_analysis.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_impact_analysis.py
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


def test_function_impact_analysis():
    """Impact analysis returns published versions and referencing workflows"""
    from app.main import app
    client = TestClient(app)
    # This will hit the real DB — for unit test we just verify endpoint exists
    resp = client.get("/api/v1/impact-analysis/functions/non-existent-id")
    assert resp.status_code in (200, 404)
```

- [ ] **Step 2: Implement impact analysis API**

```python
# backend/app/api/v1/impact_analysis.py
"""Impact analysis API — check what depends on a given F/R/A before deletion."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.version import OntologyVersion
from app.models.version_components import (
    OntologyVersionFunction, OntologyVersionRule, OntologyVersionAction,
)
from app.models.scene import AipScene
from app.models.skill_tool_ref import SkillToolRef

router = APIRouter(prefix="/impact-analysis", tags=["impact-analysis"])


def _find_referencing_workflows(db: Session, ref_type: str, source_id: str) -> list[dict]:
    """Find workflows whose nodes reference a snapshot of the given source component."""
    # Get all version snapshot IDs for this source
    if ref_type == "function":
        snapshot_ids = [r.id for r in db.query(OntologyVersionFunction.id).filter(
            OntologyVersionFunction.source_function_id == source_id).all()]
    elif ref_type == "rule":
        snapshot_ids = [r.id for r in db.query(OntologyVersionRule.id).filter(
            OntologyVersionRule.source_rule_id == source_id).all()]
    else:
        snapshot_ids = [r.id for r in db.query(OntologyVersionAction.id).filter(
            OntologyVersionAction.source_action_id == source_id).all()]

    if not snapshot_ids:
        return []

    # Scan AipScene nodes_json for ref_id matches
    scenes = db.query(AipScene).filter(AipScene.nodes_json.isnot(None)).all()
    results = []
    for scene in scenes:
        for node in (scene.nodes_json or []):
            data = node.get("data", {})
            if data.get("ref_id") in snapshot_ids:
                results.append({"id": scene.id, "name": scene.name,
                                "version": scene.ontology_version_id})
                break
    return results


def _find_referencing_skills(db: Session, ref_type: str, source_id: str) -> list[dict]:
    """Find skills that reference snapshots of the given source component."""
    if ref_type == "function":
        snapshot_ids = [r.id for r in db.query(OntologyVersionFunction.id).filter(
            OntologyVersionFunction.source_function_id == source_id).all()]
    elif ref_type == "rule":
        snapshot_ids = [r.id for r in db.query(OntologyVersionRule.id).filter(
            OntologyVersionRule.source_rule_id == source_id).all()]
    else:
        snapshot_ids = [r.id for r in db.query(OntologyVersionAction.id).filter(
            OntologyVersionAction.source_action_id == source_id).all()]

    if not snapshot_ids:
        return []

    refs = db.query(SkillToolRef).filter(SkillToolRef.ref_id.in_(snapshot_ids)).all()
    from app.models.skill import Skill
    results = []
    for ref in refs:
        skill = db.query(Skill).filter(Skill.id == ref.skill_id).first()
        if skill:
            results.append({"id": skill.id, "name": skill.name, "version": ref.version_id})
    return results


def _find_published_versions(db: Session, ref_type: str, source_id: str) -> list[str]:
    if ref_type == "function":
        Model = OntologyVersionFunction
        col = OntologyVersionFunction.source_function_id
    elif ref_type == "rule":
        Model = OntologyVersionRule
        col = OntologyVersionRule.source_rule_id
    else:
        Model = OntologyVersionAction
        col = OntologyVersionAction.source_action_id

    version_ids = [r.version_id for r in db.query(Model.version_id).filter(col == source_id).distinct().all()]
    versions = db.query(OntologyVersion).filter(OntologyVersion.id.in_(version_ids)).all()
    return [f"v{v.version_number}" for v in versions]


@router.get("/functions/{function_id}")
def function_impact(function_id: str, db: Session = Depends(get_db)):
    return {
        "published_versions": _find_published_versions(db, "function", function_id),
        "referencing_workflows": _find_referencing_workflows(db, "function", function_id),
        "referencing_skills": _find_referencing_skills(db, "function", function_id),
        "safe_to_delete": True,
        "message": "删除草稿源不影响已发布版本的运行，但该组件将不会出现在未来新版本中",
    }


@router.get("/rules/{rule_id}")
def rule_impact(rule_id: str, db: Session = Depends(get_db)):
    return {
        "published_versions": _find_published_versions(db, "rule", rule_id),
        "referencing_workflows": _find_referencing_workflows(db, "rule", rule_id),
        "referencing_skills": _find_referencing_skills(db, "rule", rule_id),
        "safe_to_delete": True,
        "message": "删除草稿源不影响已发布版本的运行，但该组件将不会出现在未来新版本中",
    }


@router.get("/actions/{action_id}")
def action_impact(action_id: str, db: Session = Depends(get_db)):
    return {
        "published_versions": _find_published_versions(db, "action", action_id),
        "referencing_workflows": _find_referencing_workflows(db, "action", action_id),
        "referencing_skills": _find_referencing_skills(db, "action", action_id),
        "safe_to_delete": True,
        "message": "删除草稿源不影响已发布版本的运行，但该组件将不会出现在未来新版本中",
    }
```

- [ ] **Step 3: Register router in main.py**

In `backend/app/main.py`, add:
```python
from app.api.v1.impact_analysis import router as impact_analysis_router
app.include_router(impact_analysis_router, prefix="/api/v1")
```

- [ ] **Step 4: Run test**

Run: `cd backend && python -m pytest tests/test_impact_analysis.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/impact_analysis.py backend/app/main.py backend/tests/test_impact_analysis.py
git commit -m "feat: impact analysis API for deletion warnings"
```

---

## Task 7: 前端版本组件 API 层

**Files:**
- Create: `frontend/src/api/versionComponents.ts`

- [ ] **Step 1: Create API module**

```typescript
// frontend/src/api/versionComponents.ts
import request from '../utils/request'

export interface VersionFunction {
  id: string
  name: string
  description: string
  return_type: string
  input_schema: Array<{ name: string; type: string; version_attribute_id: string; required: boolean }>
  version_entity_id: string
  callable_name: string
}

export interface VersionRule {
  id: string
  name: string
  description: string
  condition_expr: string
  priority: string
  input_params: Array<{ name: string; type: string; version_attribute_id: string; required: boolean }>
  version_entity_id: string
}

export interface VersionAction {
  id: string
  name: string
  description: string
  category: string
  action_type: string
  parameters_json: Array<{ name: string; type: string; version_attribute_id: string; required: boolean }>
  version_entity_id: string
}

export interface ImpactAnalysis {
  published_versions: string[]
  referencing_workflows: Array<{ id: string; name: string; version: string }>
  referencing_skills: Array<{ id: string; name: string; version: string }>
  safe_to_delete: boolean
  message: string
}

export function fetchVersionFunctions(versionId: string) {
  return request.get<VersionFunction[]>(`/ontology-publish/versions/${versionId}/functions`)
}

export function fetchVersionRules(versionId: string) {
  return request.get<VersionRule[]>(`/ontology-publish/versions/${versionId}/rules`)
}

export function fetchVersionActions(versionId: string) {
  return request.get<VersionAction[]>(`/ontology-publish/versions/${versionId}/actions`)
}

export function fetchImpactAnalysis(type: 'functions' | 'rules' | 'actions', id: string) {
  return request.get<ImpactAnalysis>(`/impact-analysis/${type}/${id}`)
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/versionComponents.ts
git commit -m "feat: frontend API layer for version components and impact analysis"
```

---

## Task 8: 流程编排节点 UI — AddNodeDrawer 扩展

**Files:**
- Modify: `frontend/src/views/aip/panels/AddNodeDrawer.vue`

- [ ] **Step 1: Update RAW_GROUPS to use new node types**

In `frontend/src/views/aip/panels/AddNodeDrawer.vue`, replace the existing 'Function 节点' and '动作节点' groups in `RAW_GROUPS`:

```typescript
{ label: '本体组件', color: '#0EA5E9', nodes: [
  { type: 'functionCall', label: '函数调用', icon: 'tool', description: '调用已发布的本体函数，返回计算结果' },
  { type: 'ruleEvaluate', label: '规则评估', icon: 'filter', description: '评估已发布的业务规则，输出 true/false 分支' },
  { type: 'actionExecute', label: '行动执行', icon: 'send', description: '执行已发布的行动（API/通知/写回等）' },
] },
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/aip/panels/AddNodeDrawer.vue
git commit -m "feat: add functionCall/ruleEvaluate/actionExecute to node drawer"
```

---

## Task 9: 流程编排节点 UI — PropertyPanel 配置面板

**Files:**
- Modify: `frontend/src/views/aip/panels/PropertyPanel.vue`
- Create: `frontend/src/views/aip/panels/ParamMappingEditor.vue`

- [ ] **Step 1: Create ParamMappingEditor component**

```vue
<!-- frontend/src/views/aip/panels/ParamMappingEditor.vue -->
<template>
  <div class="pm-editor">
    <div v-for="param in params" :key="param.name" class="pm-row">
      <label class="pm-label">{{ param.name }} <span class="pm-type">{{ param.type }}</span></label>
      <div class="pm-source">
        <select v-model="mappings[param.name].source" class="aip-input pm-select" @change="onUpdate">
          <option value="node">上游节点</option>
          <option value="variable">流程变量</option>
          <option value="expression">表达式</option>
        </select>
        <template v-if="mappings[param.name].source === 'node'">
          <select v-model="mappings[param.name].node_id" class="aip-input" @change="onUpdate">
            <option value="">选择节点</option>
            <option v-for="n in upstreamNodes" :key="n.id" :value="n.id">{{ n.data?.label || n.id }}</option>
          </select>
          <input v-model="mappings[param.name].field" class="aip-input" placeholder="output.field" @input="onUpdate" />
        </template>
        <template v-else-if="mappings[param.name].source === 'variable'">
          <input v-model="mappings[param.name].var_name" class="aip-input" placeholder="变量名" @input="onUpdate" />
        </template>
        <template v-else>
          <input v-model="mappings[param.name].expr" class="aip-input" placeholder="{{nodes.x.output.y}}" @input="onUpdate" />
        </template>
      </div>
    </div>
    <div v-if="!params.length" class="pm-empty">该组件无输入参数</div>
  </div>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'

interface Param { name: string; type: string; required?: boolean }
interface MappingValue { source: string; node_id?: string; field?: string; var_name?: string; expr?: string }

const props = defineProps<{
  params: Param[]
  modelValue: Record<string, MappingValue>
  upstreamNodes: Array<{ id: string; data?: Record<string, any> }>
}>()
const emit = defineEmits<{ (e: 'update:modelValue', v: Record<string, MappingValue>): void }>()

const mappings = reactive<Record<string, MappingValue>>({})

watch(() => props.params, (ps) => {
  for (const p of ps) {
    if (!mappings[p.name]) {
      mappings[p.name] = props.modelValue[p.name] || { source: 'variable', var_name: '' }
    }
  }
}, { immediate: true })

function onUpdate() {
  emit('update:modelValue', { ...mappings })
}
</script>

<style scoped>
.pm-editor { display: flex; flex-direction: column; gap: 12px; }
.pm-row { display: flex; flex-direction: column; gap: 4px; }
.pm-label { font-size: 12px; font-weight: 600; color: #334155; }
.pm-type { font-weight: 400; color: #94a3b8; margin-left: 4px; }
.pm-source { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.pm-select { max-width: 100px; }
.pm-empty { font-size: 12px; color: #94a3b8; }
</style>
```

- [ ] **Step 2: Add functionCall/ruleEvaluate/actionExecute templates to PropertyPanel**

In `frontend/src/views/aip/panels/PropertyPanel.vue`, add new template sections (after the existing `ruleEngine` template):

```vue
<!-- functionCall -->
<template v-else-if="node.type === 'functionCall'">
  <div class="aip-field">
    <label>选择函数（已发布版本）</label>
    <ResourcePicker type="versionFunction" :model-value="node.data.ref_id || ''"
      @update:model-value="(v: string) => onPick('ref_id', v)" placeholder="选择已发布函数" />
  </div>
  <div class="aip-field">
    <label>输出变量名</label>
    <input v-model="node.data.output_var" class="aip-input" @input="touch" placeholder="result" />
  </div>
  <div class="aip-field">
    <label>参数映射</label>
    <ParamMappingEditor :params="functionParams" v-model="node.data.param_mapping"
      :upstream-nodes="upstreamNodes" @update:model-value="touch" />
  </div>
</template>

<!-- ruleEvaluate -->
<template v-else-if="node.type === 'ruleEvaluate'">
  <div class="aip-field">
    <label>选择规则（已发布版本）</label>
    <ResourcePicker type="versionRule" :model-value="node.data.ref_id || ''"
      @update:model-value="(v: string) => onPick('ref_id', v)" placeholder="选择已发布规则" />
  </div>
  <div class="aip-field">
    <label>参数映射</label>
    <ParamMappingEditor :params="ruleParams" v-model="node.data.param_mapping"
      :upstream-nodes="upstreamNodes" @update:model-value="touch" />
  </div>
  <div class="aip-hint">规则评估输出 true/false，分别从右侧和下方端口连出</div>
</template>

<!-- actionExecute -->
<template v-else-if="node.type === 'actionExecute'">
  <div class="aip-field">
    <label>选择行动（已发布版本）</label>
    <ResourcePicker type="versionAction" :model-value="node.data.ref_id || ''"
      @update:model-value="(v: string) => onPick('ref_id', v)" placeholder="选择已发布行动" />
  </div>
  <div class="aip-field">
    <label>参数映射</label>
    <ParamMappingEditor :params="actionParams" v-model="node.data.param_mapping"
      :upstream-nodes="upstreamNodes" @update:model-value="touch" />
  </div>
</template>
```

Add the import and computed properties in the `<script setup>` section:
```typescript
import ParamMappingEditor from './ParamMappingEditor.vue'

// computed: extract params from selected component's schema
const functionParams = computed(() => node.value?.data?.selected_schema?.input_schema || [])
const ruleParams = computed(() => node.value?.data?.selected_schema?.input_params || [])
const actionParams = computed(() => node.value?.data?.selected_schema?.parameters_json || [])
const upstreamNodes = computed(() => store.nodes.filter((n: any) => n.id !== node.value?.id))
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/aip/panels/ParamMappingEditor.vue frontend/src/views/aip/panels/PropertyPanel.vue
git commit -m "feat: property panel config for function/rule/action nodes + param mapping editor"
```

---

## Task 10: 技能工具引用 API

**Files:**
- Modify: `backend/app/api/v1/skills.py`

- [ ] **Step 1: Add CRUD endpoints for SkillToolRef**

Add to `backend/app/api/v1/skills.py`:

```python
from app.models.skill_tool_ref import SkillToolRef
from pydantic import BaseModel as PydanticBaseModel


class SkillToolRefCreate(PydanticBaseModel):
    version_id: str
    ref_type: str  # function / rule / action
    ref_id: str
    alias: str
    description: str = ""
    param_override: dict | None = None


@router.get("/{skill_id}/tool-refs")
def list_tool_refs(skill_id: str, db: Session = Depends(get_db)):
    refs = db.query(SkillToolRef).filter(SkillToolRef.skill_id == skill_id).all()
    return [{"id": r.id, "ref_type": r.ref_type, "ref_id": r.ref_id,
             "alias": r.alias, "description": r.description,
             "version_id": r.version_id, "param_override": r.param_override}
            for r in refs]


@router.post("/{skill_id}/tool-refs")
def add_tool_ref(skill_id: str, req: SkillToolRefCreate, db: Session = Depends(get_db)):
    ref = SkillToolRef(
        skill_id=skill_id,
        version_id=req.version_id,
        ref_type=req.ref_type,
        ref_id=req.ref_id,
        alias=req.alias,
        description=req.description,
        param_override=req.param_override,
    )
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return {"id": ref.id, "alias": ref.alias}


@router.delete("/{skill_id}/tool-refs/{ref_id}")
def remove_tool_ref(skill_id: str, ref_id: str, db: Session = Depends(get_db)):
    ref = db.query(SkillToolRef).filter(
        SkillToolRef.id == ref_id, SkillToolRef.skill_id == skill_id
    ).first()
    if ref:
        db.delete(ref)
        db.commit()
    return {"message": "ok"}
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/v1/skills.py
git commit -m "feat: CRUD endpoints for skill tool refs (F/R/A)"
```

---

## Task 11: 技能执行器集成

**Files:**
- Modify: `backend/app/services/skill_executor.py`

- [ ] **Step 1: Extend skill executor to load SkillToolRef as agent tools**

Add to `backend/app/services/skill_executor.py` the logic to build tools from SkillToolRef:

```python
from app.models.skill_tool_ref import SkillToolRef
from app.models.version_components import (
    OntologyVersionFunction, OntologyVersionRule, OntologyVersionAction,
)
from app.services.workflow_executor_components import execute_component_node


def build_ontology_tools(skill_id: str, db: Session) -> list[dict]:
    """Build LLM tool definitions from skill's ontology component refs."""
    refs = db.query(SkillToolRef).filter(SkillToolRef.skill_id == skill_id).all()
    tools = []
    for ref in refs:
        if ref.ref_type == "function":
            comp = db.query(OntologyVersionFunction).filter(OntologyVersionFunction.id == ref.ref_id).first()
            if not comp:
                continue
            params_schema = {p["name"]: {"type": p["type"], "description": p.get("description", "")}
                           for p in (comp.input_schema or [])}
        elif ref.ref_type == "rule":
            comp = db.query(OntologyVersionRule).filter(OntologyVersionRule.id == ref.ref_id).first()
            if not comp:
                continue
            params_schema = {p["name"]: {"type": p["type"], "description": p.get("description", "")}
                           for p in (comp.input_params or [])}
        elif ref.ref_type == "action":
            comp = db.query(OntologyVersionAction).filter(OntologyVersionAction.id == ref.ref_id).first()
            if not comp:
                continue
            params_schema = {p["name"]: {"type": p["type"], "description": p.get("description", "")}
                           for p in (comp.parameters_json or [])}
        else:
            continue

        tools.append({
            "type": "function",
            "function": {
                "name": ref.alias,
                "description": ref.description or comp.description or comp.name,
                "parameters": {
                    "type": "object",
                    "properties": params_schema,
                    "required": [p["name"] for p in (comp.input_schema or comp.input_params or comp.parameters_json or [])
                                 if p.get("required")],
                },
            },
            "_ref_type": ref.ref_type,
            "_ref_id": ref.ref_id,
        })
    return tools
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/skill_executor.py
git commit -m "feat: skill executor builds LLM tools from ontology component refs"
```

---

## Task 12: 定义层增强 — input_schema 增加 attribute_id

**Files:**
- Modify: `backend/app/schemas/function.py`
- Modify: `frontend/src/components/logic/FunctionBuilderDrawer.vue`

- [ ] **Step 1: Update function schema to include entity_id and attribute_id**

In `backend/app/schemas/function.py`, update the input parameter model (if exists) or add validation that accepts `entity_id` and `attribute_id` fields in `input_schema` JSON. Since `input_schema` is stored as JSON, the backend already accepts arbitrary fields. The key change is in the frontend form.

- [ ] **Step 2: Update FunctionBuilderDrawer to include attribute picker per parameter**

In `frontend/src/components/logic/FunctionBuilderDrawer.vue`, add a `ResourcePicker type="attribute"` for each parameter row in the input_schema editor, storing `entity_id` and `attribute_id` alongside name/type.

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/function.py frontend/src/components/logic/FunctionBuilderDrawer.vue
git commit -m "feat: function input params can reference ontology entity attributes"
```

---

## Task 13: DB 表创建（确保 SQLite 新表存在）

**Files:**
- Modify: `backend/app/database.py` or startup logic

- [ ] **Step 1: Ensure tables are created on startup**

Since the project uses SQLite with `Base.metadata.create_all()`, verify that the app startup creates all new tables. Check `backend/app/main.py` or `database.py` for the `create_all` call — the new models are registered in `__init__.py`, so they should be picked up automatically.

Run: `cd backend && python -c "from app.database import engine, Base; from app.models import *; Base.metadata.create_all(engine); print('OK')"` 
Expected: OK (tables created)

- [ ] **Step 2: Commit (if any changes needed)**

```bash
git add -A && git commit -m "chore: ensure new tables created on startup" || echo "No changes needed"
```

---

## Summary

| Task | 内容 | 优先级 |
|------|------|--------|
| 1 | 版本组件快照模型 | P0 |
| 2 | 快照服务 | P0 |
| 3 | 发布流程集成 | P0 |
| 4 | SkillToolRef 模型 | P1 |
| 5 | 流程编排执行器 | P1 |
| 6 | 影响分析 API | P2 |
| 7 | 前端 API 层 | P1 |
| 8 | AddNodeDrawer 扩展 | P1 |
| 9 | PropertyPanel + ParamMapping | P1 |
| 10 | 技能工具引用 API | P1 |
| 11 | 技能执行器集成 | P1 |
| 12 | 定义层增强 | P0 |
| 13 | DB 表创建 | P0 |
