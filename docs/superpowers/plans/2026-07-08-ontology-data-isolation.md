# 本体数据隔离 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现本体间数据隔离，每个本体的对象/逻辑/动作/关系/共享属性默认互不可见，支持跨本体只读共享。

**Architecture:** 在核心表（ontology_entities, ontology_functions, entity_actions）上新增 `ontology_id` 外键指向 `scenario_dict.id`。新建 `ontology_shared_refs` 表管理跨本体只读引用。API 层所有列表查询必须传 `ontology_id` 参数做后端过滤。前端切换本体时重新请求数据。

**Tech Stack:** Python 3.11 / FastAPI / SQLAlchemy 2.0 / Pydantic 2 / Vue 3 / TypeScript / Pinia / Ant Design Vue

## Global Constraints

- 所有 ID 为 String(36) UUID 格式，使用 `uuid.uuid4().hex` 前缀拼接生成
- 迁移必须幂等，添加到 `backend/app/migrations/schema_compat.py`
- 遵循现有 Repository 模式：`BaseRepository[T]` + `list_with_filters()`
- 前端 API 客户端基于 `frontend/src/api/client.ts` 的 `get/post/put/del` 封装
- `scenario_codes` 字段保留不删，确保可回退
- 提交信息使用中文

---

## File Structure

### Backend - New Files
- `backend/app/models/shared_ref.py` — OntologySharedRef 模型
- `backend/app/models/shared_attribute.py` — SharedAttribute 模型
- `backend/app/repositories/shared_ref_repo.py` — 共享引用仓库
- `backend/app/repositories/shared_attribute_repo.py` — 共享属性仓库
- `backend/app/api/v1/shared_refs.py` — 共享管理 API
- `backend/app/api/v1/shared_attributes.py` — 共享属性 API
- `backend/tests/test_ontology_isolation.py` — 隔离功能测试

### Backend - Modified Files
- `backend/app/models/entity.py` — 加 ontology_id 列，改唯一约束
- `backend/app/models/function.py` — 加 ontology_id 列
- `backend/app/models/action.py` — 加 ontology_id 列
- `backend/app/models/__init__.py` — 导出新模型
- `backend/app/migrations/schema_compat.py` — 新增迁移函数
- `backend/app/migrations/__init__.py` — 注册新迁移
- `backend/app/repositories/entity_repo.py` — 加 ontology_id 过滤
- `backend/app/repositories/function_repo.py` — 加 ontology_id 过滤
- `backend/app/repositories/action_repo.py` — 加 ontology_id 过滤
- `backend/app/api/v1/entities.py` — 加 ontology_id 参数 + 写入保护
- `backend/app/api/v1/functions.py` — 加 ontology_id 参数 + 写入保护
- `backend/app/api/v1/actions.py` — 加 ontology_id 参数 + 写入保护
- `backend/app/api/v1/relations.py` — 加 ontology_id 参数过滤
- `backend/app/main.py` — 挂载新路由

### Frontend - Modified Files
- `frontend/src/types/ontology.ts` — 加 ontology_id, is_shared 字段
- `frontend/src/api/ontology.ts` — 列表查询加 ontology_id 参数
- `frontend/src/api/functions.ts` — 列表查询加 ontology_id 参数
- `frontend/src/api/actions.ts` — 列表查询加 ontology_id 参数
- `frontend/src/store/ontology.ts` — 加 currentOntologyId 状态，switchOntology 方法
- `frontend/src/views/ontology/OntologyDetailView.vue` — 移除客户端过滤，用后端数据

---

### Task 1: 数据模型 — 新增 OntologySharedRef 和 SharedAttribute 模型

**Files:**
- Create: `backend/app/models/shared_ref.py`
- Create: `backend/app/models/shared_attribute.py`
- Modify: `backend/app/models/__init__.py`

**Interfaces:**
- Consumes: `ScenarioDict` model (scenario_dict.id), `OntologyEntity` model (ontology_entities.id)
- Produces: `OntologySharedRef` class, `SharedAttribute` class — used by Task 2 migrations and Task 4/5 repositories

- [ ] **Step 1: 创建 OntologySharedRef 模型**

创建文件 `backend/app/models/shared_ref.py`:

```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


def _gen_uuid() -> str:
    return uuid.uuid4().hex


class OntologySharedRef(Base):
    __tablename__ = "ontology_shared_refs"

    id = Column(String(36), primary_key=True, default=_gen_uuid)
    source_ontology_id = Column(String(36), ForeignKey("scenario_dict.id"), nullable=False, index=True)
    target_ontology_id = Column(String(36), ForeignKey("scenario_dict.id"), nullable=False, index=True)
    entity_id = Column(String(36), ForeignKey("ontology_entities.id", ondelete="CASCADE"), nullable=False, index=True)
    shared_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    shared_by = Column(String(100), nullable=True)

    __table_args__ = (
        UniqueConstraint("target_ontology_id", "entity_id", name="uq_shared_ref_target_entity"),
    )

    source_ontology = relationship("ScenarioDict", foreign_keys=[source_ontology_id])
    target_ontology = relationship("ScenarioDict", foreign_keys=[target_ontology_id])
    entity = relationship("OntologyEntity", foreign_keys=[entity_id])
```

- [ ] **Step 2: 创建 SharedAttribute 模型**

创建文件 `backend/app/models/shared_attribute.py`:

```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint

from app.database import Base


def _gen_uuid() -> str:
    return uuid.uuid4().hex


class SharedAttribute(Base):
    __tablename__ = "ontology_shared_attributes"

    id = Column(String(36), primary_key=True, default=_gen_uuid)
    ontology_id = Column(String(36), ForeignKey("scenario_dict.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    name_cn = Column(String(100), nullable=True)
    data_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    config_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("ontology_id", "name", name="uq_shared_attr_ontology_name"),
    )
```

- [ ] **Step 3: 注册新模型到 __init__.py**

修改 `backend/app/models/__init__.py`，在已有导入末尾添加:

```python
from app.models.shared_ref import OntologySharedRef
from app.models.shared_attribute import SharedAttribute
```

- [ ] **Step 4: 验证模型可导入**

Run: `cd backend && python -c "from app.models import OntologySharedRef, SharedAttribute; print('OK')"`
Expected: `OK`

- [ ] **Step 5: 提交**

```bash
git add backend/app/models/shared_ref.py backend/app/models/shared_attribute.py backend/app/models/__init__.py
git commit -m "新增 OntologySharedRef 和 SharedAttribute 数据模型"
```

---

### Task 2: 数据模型 — 核心表添加 ontology_id 列

**Files:**
- Modify: `backend/app/models/entity.py`
- Modify: `backend/app/models/function.py`
- Modify: `backend/app/models/action.py`

**Interfaces:**
- Consumes: `ScenarioDict` model (scenario_dict.id)
- Produces: `OntologyEntity.ontology_id`, `OntologyFunction.ontology_id`, `EntityAction.ontology_id` columns — used by Task 3 migration and Task 4 repository queries

- [ ] **Step 1: OntologyEntity 添加 ontology_id**

修改 `backend/app/models/entity.py`，在 `OntologyEntity` 类中添加字段（在 `scenario_codes` 字段之后）:

```python
ontology_id = Column(String(36), ForeignKey("scenario_dict.id"), nullable=True, index=True)
```

并修改 `__table_args__`（如不存在则添加）:

```python
__table_args__ = (
    UniqueConstraint("ontology_id", "name", name="uq_entity_ontology_name"),
)
```

同时移除原来 `name` 字段上的 `unique=True` 参数。

- [ ] **Step 2: OntologyFunction 添加 ontology_id**

修改 `backend/app/models/function.py`，在 `OntologyFunction` 类中 `entity_id` 字段之后添加:

```python
ontology_id = Column(String(36), ForeignKey("scenario_dict.id"), nullable=True, index=True)
```

- [ ] **Step 3: EntityAction 添加 ontology_id**

修改 `backend/app/models/action.py`，在 `EntityAction` 类中 `entity_id` 字段之后添加:

```python
ontology_id = Column(String(36), ForeignKey("scenario_dict.id"), nullable=True, index=True)
```

- [ ] **Step 4: EntityAttribute 添加 shared_attribute_id**

修改 `backend/app/models/entity.py`，在 `EntityAttribute` 类中添加:

```python
shared_attribute_id = Column(String(36), ForeignKey("ontology_shared_attributes.id", ondelete="SET NULL"), nullable=True)
```

- [ ] **Step 5: 验证模型可导入**

Run: `cd backend && python -c "from app.models import OntologyEntity, OntologyFunction, EntityAction; print('OK')"`
Expected: `OK`

- [ ] **Step 6: 提交**

```bash
git add backend/app/models/entity.py backend/app/models/function.py backend/app/models/action.py
git commit -m "核心模型添加 ontology_id 外键列"
```

---

### Task 3: 数据迁移脚本

**Files:**
- Modify: `backend/app/migrations/schema_compat.py`
- Modify: `backend/app/migrations/__init__.py`

**Interfaces:**
- Consumes: `OntologyEntity.ontology_id`, `OntologyFunction.ontology_id`, `EntityAction.ontology_id` (from Task 2)
- Produces: 幂等迁移函数 `_migrate_ontology_isolation()` — 在应用启动时自动执行，填充 ontology_id 数据

- [ ] **Step 1: 编写迁移函数**

在 `backend/app/migrations/schema_compat.py` 文件末尾添加:

```python
def _migrate_ontology_isolation(conn, inspector, tables):
    """添加 ontology_id 列并迁移数据（幂等）。"""
    # --- ontology_entities ---
    if "ontology_entities" in tables:
        cols = {c["name"] for c in inspector.get_columns("ontology_entities")}
        if "ontology_id" not in cols:
            conn.execute(text(
                "ALTER TABLE ontology_entities ADD COLUMN ontology_id VARCHAR(36)"
            ))
            conn.commit()

    # --- ontology_functions ---
    if "ontology_functions" in tables:
        cols = {c["name"] for c in inspector.get_columns("ontology_functions")}
        if "ontology_id" not in cols:
            conn.execute(text(
                "ALTER TABLE ontology_functions ADD COLUMN ontology_id VARCHAR(36)"
            ))
            conn.commit()

    # --- entity_actions ---
    if "entity_actions" in tables:
        cols = {c["name"] for c in inspector.get_columns("entity_actions")}
        if "ontology_id" not in cols:
            conn.execute(text(
                "ALTER TABLE entity_actions ADD COLUMN ontology_id VARCHAR(36)"
            ))
            conn.commit()

    # --- entity_attributes: shared_attribute_id ---
    if "entity_attributes" in tables:
        cols = {c["name"] for c in inspector.get_columns("entity_attributes")}
        if "shared_attribute_id" not in cols:
            conn.execute(text(
                "ALTER TABLE entity_attributes ADD COLUMN shared_attribute_id VARCHAR(36)"
            ))
            conn.commit()

    # --- 数据迁移: 按 scenario_codes 分配 ontology_id ---
    if "ontology_entities" in tables and "scenario_dict" in tables:
        # 获取第一个 scenario 作为默认
        result = conn.execute(text("SELECT id FROM scenario_dict ORDER BY sort_order LIMIT 1"))
        row = result.fetchone()
        default_id = row[0] if row else None

        if default_id:
            # 处理有 scenario_codes 的实体
            entities = conn.execute(text(
                "SELECT id, scenario_codes FROM ontology_entities WHERE ontology_id IS NULL"
            )).fetchall()

            for eid, codes_raw in entities:
                import json
                codes = json.loads(codes_raw) if codes_raw else []
                if codes:
                    # 获取第一个 code 对应的 scenario id
                    sc = conn.execute(text(
                        "SELECT id FROM scenario_dict WHERE code = :code"
                    ), {"code": codes[0]}).fetchone()
                    ontology_id = sc[0] if sc else default_id
                else:
                    ontology_id = default_id

                conn.execute(text(
                    "UPDATE ontology_entities SET ontology_id = :oid WHERE id = :eid"
                ), {"oid": ontology_id, "eid": eid})

                # 多 scenario_codes 的创建共享引用
                if len(codes) > 1:
                    for code in codes[1:]:
                        sc = conn.execute(text(
                            "SELECT id FROM scenario_dict WHERE code = :code"
                        ), {"code": code}).fetchone()
                        if sc:
                            import uuid
                            ref_id = uuid.uuid4().hex
                            conn.execute(text(
                                "INSERT OR IGNORE INTO ontology_shared_refs "
                                "(id, source_ontology_id, target_ontology_id, entity_id, shared_at) "
                                "VALUES (:id, :src, :tgt, :eid, datetime('now'))"
                            ), {"id": ref_id, "src": ontology_id, "tgt": sc[0], "eid": eid})

            conn.commit()

            # functions: 跟随 entity 或归入默认
            conn.execute(text("""
                UPDATE ontology_functions SET ontology_id = (
                    SELECT ontology_id FROM ontology_entities WHERE ontology_entities.id = ontology_functions.entity_id
                ) WHERE entity_id IS NOT NULL AND ontology_id IS NULL
            """))
            conn.execute(text(
                "UPDATE ontology_functions SET ontology_id = :default WHERE ontology_id IS NULL"
            ), {"default": default_id})
            conn.commit()

            # actions: 跟随 entity 或归入默认
            conn.execute(text("""
                UPDATE entity_actions SET ontology_id = (
                    SELECT ontology_id FROM ontology_entities WHERE ontology_entities.id = entity_actions.entity_id
                ) WHERE entity_id IS NOT NULL AND ontology_id IS NULL
            """))
            conn.execute(text(
                "UPDATE entity_actions SET ontology_id = :default WHERE ontology_id IS NULL"
            ), {"default": default_id})
            conn.commit()

    logger.info("本体隔离迁移完成")
```

- [ ] **Step 2: 注册迁移函数**

修改 `backend/app/migrations/__init__.py`，添加导入和调用:

在 imports 中添加:
```python
from .schema_compat import _migrate_ontology_isolation
```

在 `run_startup_migrations` 函数末尾添加调用:
```python
_migrate_ontology_isolation(conn, inspector, tables)
```

- [ ] **Step 3: 测试迁移幂等性**

Run: `cd backend && python -c "from app.main import app; print('startup OK')"`
Expected: 输出包含 `startup OK`，无报错

再次运行验证幂等:
Run: `cd backend && python -c "from app.main import app; print('idempotent OK')"`
Expected: `idempotent OK`

- [ ] **Step 4: 提交**

```bash
git add backend/app/migrations/schema_compat.py backend/app/migrations/__init__.py
git commit -m "添加本体隔离数据迁移脚本（幂等）"
```

---

### Task 4: 后端仓库层 — 添加 ontology_id 过滤

**Files:**
- Modify: `backend/app/repositories/entity_repo.py`
- Modify: `backend/app/repositories/function_repo.py`
- Modify: `backend/app/repositories/action_repo.py`
- Create: `backend/app/repositories/shared_ref_repo.py`
- Create: `backend/app/repositories/shared_attribute_repo.py`

**Interfaces:**
- Consumes: `OntologySharedRef`, `SharedAttribute`, `OntologyEntity.ontology_id`, `OntologyFunction.ontology_id`, `EntityAction.ontology_id` (from Tasks 1-2)
- Produces: `EntityRepository.list_with_filters(ontology_id=...)`, `FunctionRepository.list_with_filters(ontology_id=...)`, `ActionRepository.list_with_filters(ontology_id=...)`, `SharedRefRepository`, `SharedAttributeRepository` — used by Task 5 API routes

- [ ] **Step 1: 修改 EntityRepository 添加 ontology_id 过滤**

修改 `backend/app/repositories/entity_repo.py`，在 `list_with_filters` 方法中增加 `ontology_id` 参数:

```python
from app.models.shared_ref import OntologySharedRef

class EntityRepository(BaseRepository[OntologyEntity]):
    model = OntologyEntity

    def list_with_filters(
        self,
        tier: int | None = None,
        status: str | None = None,
        search: str | None = None,
        namespace: str | None = None,
        ontology_id: str | None = None,
    ) -> list[OntologyEntity]:
        q = self.db.query(OntologyEntity)
        if ontology_id:
            # 自有实体
            owned_ids = self.db.query(OntologyEntity.id).filter(
                OntologyEntity.ontology_id == ontology_id
            )
            # 共享进来的实体
            shared_ids = self.db.query(OntologySharedRef.entity_id).filter(
                OntologySharedRef.target_ontology_id == ontology_id
            )
            q = q.filter(OntologyEntity.id.in_(owned_ids.union(shared_ids)))
        if tier:
            q = q.filter(OntologyEntity.tier == tier)
        if status:
            q = q.filter(OntologyEntity.status == status)
        if namespace:
            q = q.filter(OntologyEntity.id.like(f"{namespace}_%"))
        if search:
            pattern = f"%{search}%"
            q = q.filter(
                OntologyEntity.name.ilike(pattern) | OntologyEntity.name_cn.ilike(pattern)
            )
        return q.order_by(OntologyEntity.tier, OntologyEntity.name).all()

    def get_shared_entity_ids(self, ontology_id: str) -> set[str]:
        """返回被共享进当前本体的实体 ID 集合。"""
        rows = self.db.query(OntologySharedRef.entity_id).filter(
            OntologySharedRef.target_ontology_id == ontology_id
        ).all()
        return {r[0] for r in rows}
```

- [ ] **Step 2: 修改 FunctionRepository 添加 ontology_id 过滤**

修改 `backend/app/repositories/function_repo.py`，在 `list_with_filters` 方法中增加 `ontology_id` 参数:

```python
def list_with_filters(
    self,
    entity_id: str | None = None,
    status: str | None = None,
    search: str | None = None,
    ontology_id: str | None = None,
) -> list[OntologyFunction]:
    q = self.db.query(OntologyFunction)
    if ontology_id:
        # 直接归属 + 通过 entity 归属
        from app.models import OntologyEntity
        from app.models.shared_ref import OntologySharedRef
        entity_ids_in_scope = self.db.query(OntologyEntity.id).filter(
            OntologyEntity.ontology_id == ontology_id
        )
        shared_entity_ids = self.db.query(OntologySharedRef.entity_id).filter(
            OntologySharedRef.target_ontology_id == ontology_id
        )
        all_entity_ids = entity_ids_in_scope.union(shared_entity_ids)
        q = q.filter(
            (OntologyFunction.ontology_id == ontology_id) |
            (OntologyFunction.entity_id.in_(all_entity_ids))
        )
    if entity_id:
        q = q.filter(OntologyFunction.entity_id == entity_id)
    if status:
        q = q.filter(OntologyFunction.status == status)
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            OntologyFunction.name.ilike(pattern) | OntologyFunction.callable_name.ilike(pattern)
        )
    return q.order_by(OntologyFunction.created_at.desc()).all()
```

- [ ] **Step 3: 修改 ActionRepository 添加 ontology_id 过滤**

修改 `backend/app/repositories/action_repo.py`，在 `list_actions` 方法中增加 `ontology_id` 参数:

```python
def list_actions(
    self,
    entity_id: str | None = None,
    status: str | None = None,
    action_type: str | None = None,
    category: str | None = None,
    search: str | None = None,
    ontology_id: str | None = None,
) -> list[EntityAction]:
    stmt = select(EntityAction)
    if ontology_id:
        from app.models import OntologyEntity
        from app.models.shared_ref import OntologySharedRef
        entity_ids_in_scope = select(OntologyEntity.id).where(
            OntologyEntity.ontology_id == ontology_id
        )
        shared_entity_ids = select(OntologySharedRef.entity_id).where(
            OntologySharedRef.target_ontology_id == ontology_id
        )
        all_entity_ids = entity_ids_in_scope.union(shared_entity_ids)
        stmt = stmt.where(
            (EntityAction.ontology_id == ontology_id) |
            (EntityAction.entity_id.in_(all_entity_ids))
        )
    if entity_id:
        stmt = stmt.where(EntityAction.entity_id == entity_id)
    if status:
        stmt = stmt.where(EntityAction.status == status)
    if action_type:
        stmt = stmt.where(EntityAction.action_type == action_type)
    if category:
        stmt = stmt.where(EntityAction.category == category)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(EntityAction.name.ilike(pattern))
    stmt = stmt.order_by(EntityAction.created_at.desc())
    return list(self.db.execute(stmt).scalars().all())
```

- [ ] **Step 4: 创建 SharedRefRepository**

创建文件 `backend/app/repositories/shared_ref_repo.py`:

```python
from __future__ import annotations

from app.models.shared_ref import OntologySharedRef
from app.repositories.base import BaseRepository


class SharedRefRepository(BaseRepository[OntologySharedRef]):
    model = OntologySharedRef

    def list_by_target(self, target_ontology_id: str) -> list[OntologySharedRef]:
        return self.db.query(OntologySharedRef).filter(
            OntologySharedRef.target_ontology_id == target_ontology_id
        ).all()

    def list_by_source(self, source_ontology_id: str) -> list[OntologySharedRef]:
        return self.db.query(OntologySharedRef).filter(
            OntologySharedRef.source_ontology_id == source_ontology_id
        ).all()

    def find_ref(self, target_ontology_id: str, entity_id: str) -> OntologySharedRef | None:
        return self.db.query(OntologySharedRef).filter(
            OntologySharedRef.target_ontology_id == target_ontology_id,
            OntologySharedRef.entity_id == entity_id,
        ).first()
```

- [ ] **Step 5: 创建 SharedAttributeRepository**

创建文件 `backend/app/repositories/shared_attribute_repo.py`:

```python
from __future__ import annotations

from app.models.shared_attribute import SharedAttribute
from app.repositories.base import BaseRepository


class SharedAttributeRepository(BaseRepository[SharedAttribute]):
    model = SharedAttribute

    def list_by_ontology(self, ontology_id: str) -> list[SharedAttribute]:
        return self.db.query(SharedAttribute).filter(
            SharedAttribute.ontology_id == ontology_id
        ).order_by(SharedAttribute.name).all()

    def find_by_name(self, ontology_id: str, name: str) -> SharedAttribute | None:
        return self.db.query(SharedAttribute).filter(
            SharedAttribute.ontology_id == ontology_id,
            SharedAttribute.name == name,
        ).first()
```

- [ ] **Step 6: 验证导入**

Run: `cd backend && python -c "from app.repositories.shared_ref_repo import SharedRefRepository; from app.repositories.shared_attribute_repo import SharedAttributeRepository; print('OK')"`
Expected: `OK`

- [ ] **Step 7: 提交**

```bash
git add backend/app/repositories/
git commit -m "仓库层添加 ontology_id 过滤及共享引用/共享属性仓库"
```

---

### Task 5: 后端 API — 实体/逻辑/动作/关系接口添加 ontology_id 过滤与写入保护

**Files:**
- Modify: `backend/app/api/v1/entities.py`
- Modify: `backend/app/api/v1/functions.py`
- Modify: `backend/app/api/v1/actions.py`
- Modify: `backend/app/api/v1/relations.py`

**Interfaces:**
- Consumes: `EntityRepository.list_with_filters(ontology_id=...)`, `FunctionRepository.list_with_filters(ontology_id=...)`, `ActionRepository.list_actions(ontology_id=...)`, `EntityRepository.get_shared_entity_ids()` (from Task 4)
- Produces: `GET /entities?ontology_id=X`, `GET /functions?ontology_id=X`, `GET /actions?ontology_id=X` 带隔离过滤 — 前端 Task 7 依赖

- [ ] **Step 1: 实体列表 API 添加 ontology_id 参数**

修改 `backend/app/api/v1/entities.py` 的列表接口函数签名，添加:

```python
@router.get("/entities")
async def list_entities(
    tier: int | None = None,
    status: str | None = None,
    search: str | None = None,
    namespace: str | None = None,
    ontology_id: str | None = None,
    db: Session = Depends(get_db),
):
    repo = EntityRepository(db)
    entities = repo.list_with_filters(
        tier=tier, status=status, search=search, namespace=namespace, ontology_id=ontology_id
    )
    # 标记共享实体
    shared_ids = repo.get_shared_entity_ids(ontology_id) if ontology_id else set()
    result = []
    for e in entities:
        item = _entity_to_list_item(e, repo)
        item["is_shared"] = e.id in shared_ids
        result.append(item)
    return result
```

- [ ] **Step 2: 实体创建 API 添加 ontology_id**

修改创建实体的接口，在请求体 schema 中添加 `ontology_id: str` 字段，创建时写入:

```python
@router.post("/entities")
async def create_entity(body: EntityCreate, db: Session = Depends(get_db)):
    # 校验 ontology_id 内名称唯一
    repo = EntityRepository(db)
    existing = repo.list_with_filters(ontology_id=body.ontology_id, search=None)
    if any(e.name == body.name for e in existing if e.ontology_id == body.ontology_id):
        raise HTTPException(status_code=409, detail="该本体下已存在同名实体")
    entity = OntologyEntity(ontology_id=body.ontology_id, ...)
    ...
```

- [ ] **Step 3: 实体修改/删除 API 添加写入保护**

在修改和删除接口中添加校验:

```python
@router.put("/entities/{entity_id}")
async def update_entity(entity_id: str, body: EntityUpdate, ontology_id: str = Query(...), db: Session = Depends(get_db)):
    repo = EntityRepository(db)
    entity = repo.get_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="实体不存在")
    # 共享实体只读保护
    shared_ids = repo.get_shared_entity_ids(ontology_id)
    if entity.id in shared_ids:
        raise HTTPException(status_code=403, detail="共享实体为只读，不可修改")
    if entity.ontology_id != ontology_id:
        raise HTTPException(status_code=403, detail="无权修改其他本体的实体")
    ...
```

- [ ] **Step 4: 逻辑列表 API 添加 ontology_id 参数**

修改 `backend/app/api/v1/functions.py` 的列表接口:

```python
@router.get("/functions")
async def list_functions(
    entity_id: str | None = None,
    status: str | None = None,
    search: str | None = None,
    ontology_id: str | None = None,
    db: Session = Depends(get_db),
):
    repo = FunctionRepository(db)
    return repo.list_with_filters(
        entity_id=entity_id, status=status, search=search, ontology_id=ontology_id
    )
```

- [ ] **Step 5: 动作列表 API 添加 ontology_id 参数**

修改 `backend/app/api/v1/actions.py` 的列表接口:

```python
@router.get("/actions")
async def list_actions(
    entity_id: str | None = None,
    status: str | None = None,
    action_type: str | None = None,
    category: str | None = None,
    search: str | None = None,
    ontology_id: str | None = None,
    db: Session = Depends(get_db),
):
    repo = ActionRepository(db)
    return repo.list_actions(
        entity_id=entity_id, status=status, action_type=action_type,
        category=category, search=search, ontology_id=ontology_id
    )
```

- [ ] **Step 6: 逻辑/动作创建接口自动填充 ontology_id**

在创建函数和动作时，如果提供了 `entity_id`，从关联实体获取 `ontology_id` 冗余存储:

```python
# functions create
if body.entity_id:
    entity = EntityRepository(db).get_by_id(body.entity_id)
    func.ontology_id = entity.ontology_id if entity else body.ontology_id
else:
    func.ontology_id = body.ontology_id  # 必填
```

- [ ] **Step 7: 关系列表 API 添加 ontology_id 过滤**

修改 `backend/app/api/v1/relations.py` 的列表接口，添加 `ontology_id` 参数。过滤逻辑：返回 from_entity 或 to_entity 至少一端属于当前本体可见范围的关系:

```python
@router.get("/relations")
async def list_relations(
    entity_id: str | None = None,
    ontology_id: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(EntityRelation)
    if entity_id:
        q = q.filter(
            (EntityRelation.from_entity_id == entity_id) |
            (EntityRelation.to_entity_id == entity_id)
        )
    if ontology_id:
        from app.models import OntologyEntity
        from app.models.shared_ref import OntologySharedRef
        # 当前本体可见的实体 ID
        owned_ids = db.query(OntologyEntity.id).filter(OntologyEntity.ontology_id == ontology_id)
        shared_ids = db.query(OntologySharedRef.entity_id).filter(
            OntologySharedRef.target_ontology_id == ontology_id
        )
        visible_ids = owned_ids.union(shared_ids)
        q = q.filter(
            (EntityRelation.from_entity_id.in_(visible_ids)) |
            (EntityRelation.to_entity_id.in_(visible_ids))
        )
    return q.all()
```

- [ ] **Step 8: 验证 API 启动正常**

Run: `cd backend && python -c "from app.main import app; print('OK')"`
Expected: `OK`

- [ ] **Step 9: 提交**

```bash
git add backend/app/api/v1/entities.py backend/app/api/v1/functions.py backend/app/api/v1/actions.py backend/app/api/v1/relations.py
git commit -m "API 层添加 ontology_id 过滤与写入保护"
```

---

### Task 6: 后端 API — 共享管理接口

**Files:**
- Create: `backend/app/api/v1/shared_refs.py`
- Create: `backend/app/api/v1/shared_attributes.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `SharedRefRepository`, `SharedAttributeRepository` (from Task 4)
- Produces: `POST /ontology/{id}/share`, `DELETE /ontology/{id}/share/{ref_id}`, `GET /ontology/{id}/shared`, 共享属性 CRUD — 前端 Task 7 依赖

- [ ] **Step 1: 创建共享引用 API**

创建文件 `backend/app/api/v1/shared_refs.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.shared_ref import OntologySharedRef
from app.repositories.entity_repo import EntityRepository
from app.repositories.shared_ref_repo import SharedRefRepository

router = APIRouter(tags=["shared-refs"])


class ShareRequest(BaseModel):
    target_ontology_id: str
    entity_id: str


class SharedRefOut(BaseModel):
    id: str
    source_ontology_id: str
    target_ontology_id: str
    entity_id: str
    shared_at: str | None = None
    shared_by: str | None = None

    class Config:
        from_attributes = True


@router.post("/ontology/{ontology_id}/share", response_model=SharedRefOut)
async def share_entity(ontology_id: str, body: ShareRequest, db: Session = Depends(get_db)):
    entity_repo = EntityRepository(db)
    entity = entity_repo.get_by_id(body.entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="实体不存在")
    if entity.ontology_id != ontology_id:
        raise HTTPException(status_code=403, detail="只能共享自己本体的实体")
    if body.target_ontology_id == ontology_id:
        raise HTTPException(status_code=400, detail="不能共享给自己的本体")

    repo = SharedRefRepository(db)
    existing = repo.find_ref(body.target_ontology_id, body.entity_id)
    if existing:
        raise HTTPException(status_code=409, detail="该实体已共享到目标本体")

    ref = OntologySharedRef(
        source_ontology_id=ontology_id,
        target_ontology_id=body.target_ontology_id,
        entity_id=body.entity_id,
    )
    repo.create(ref)
    repo.commit()
    repo.refresh(ref)
    return ref


@router.delete("/ontology/{ontology_id}/share/{ref_id}")
async def unshare_entity(ontology_id: str, ref_id: str, db: Session = Depends(get_db)):
    repo = SharedRefRepository(db)
    ref = repo.get_by_id(ref_id)
    if not ref or ref.source_ontology_id != ontology_id:
        raise HTTPException(status_code=404, detail="共享引用不存在")
    repo.delete(ref)
    repo.commit()
    return {"detail": "已取消共享"}


@router.get("/ontology/{ontology_id}/shared")
async def list_shared(ontology_id: str, direction: str = Query("both"), db: Session = Depends(get_db)):
    repo = SharedRefRepository(db)
    result = {"shared_out": [], "shared_in": []}
    if direction in ("out", "both"):
        result["shared_out"] = [SharedRefOut.model_validate(r) for r in repo.list_by_source(ontology_id)]
    if direction in ("in", "both"):
        result["shared_in"] = [SharedRefOut.model_validate(r) for r in repo.list_by_target(ontology_id)]
    return result
```

- [ ] **Step 2: 创建共享属性 API**

创建文件 `backend/app/api/v1/shared_attributes.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.shared_attribute import SharedAttribute
from app.repositories.shared_attribute_repo import SharedAttributeRepository

router = APIRouter(tags=["shared-attributes"])


class SharedAttrCreate(BaseModel):
    ontology_id: str
    name: str
    name_cn: str | None = None
    data_type: str
    description: str | None = None
    config_json: dict | None = None


class SharedAttrUpdate(BaseModel):
    name: str | None = None
    name_cn: str | None = None
    data_type: str | None = None
    description: str | None = None
    config_json: dict | None = None


class SharedAttrOut(BaseModel):
    id: str
    ontology_id: str
    name: str
    name_cn: str | None = None
    data_type: str
    description: str | None = None
    config_json: dict | None = None

    class Config:
        from_attributes = True


@router.get("/shared-attributes", response_model=list[SharedAttrOut])
async def list_shared_attributes(ontology_id: str, db: Session = Depends(get_db)):
    repo = SharedAttributeRepository(db)
    return repo.list_by_ontology(ontology_id)


@router.post("/shared-attributes", response_model=SharedAttrOut)
async def create_shared_attribute(body: SharedAttrCreate, db: Session = Depends(get_db)):
    repo = SharedAttributeRepository(db)
    if repo.find_by_name(body.ontology_id, body.name):
        raise HTTPException(status_code=409, detail="该本体下已存在同名共享属性")
    attr = SharedAttribute(**body.model_dump())
    repo.create(attr)
    repo.commit()
    repo.refresh(attr)
    return attr


@router.put("/shared-attributes/{attr_id}", response_model=SharedAttrOut)
async def update_shared_attribute(attr_id: str, body: SharedAttrUpdate, db: Session = Depends(get_db)):
    repo = SharedAttributeRepository(db)
    attr = repo.get_by_id(attr_id)
    if not attr:
        raise HTTPException(status_code=404, detail="共享属性不存在")
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(attr, key, val)
    repo.commit()
    repo.refresh(attr)
    return attr


@router.delete("/shared-attributes/{attr_id}")
async def delete_shared_attribute(attr_id: str, db: Session = Depends(get_db)):
    repo = SharedAttributeRepository(db)
    attr = repo.get_by_id(attr_id)
    if not attr:
        raise HTTPException(status_code=404, detail="共享属性不存在")
    repo.delete(attr)
    repo.commit()
    return {"detail": "已删除"}
```

- [ ] **Step 3: 注册路由到 main.py**

修改 `backend/app/main.py`，导入并挂载新路由:

```python
from app.api.v1.shared_refs import router as shared_refs_router
from app.api.v1.shared_attributes import router as shared_attrs_router

app.include_router(shared_refs_router, prefix="/api/v1")
app.include_router(shared_attrs_router, prefix="/api/v1")
```

- [ ] **Step 4: 验证启动**

Run: `cd backend && python -c "from app.main import app; print('OK')"`
Expected: `OK`

- [ ] **Step 5: 提交**

```bash
git add backend/app/api/v1/shared_refs.py backend/app/api/v1/shared_attributes.py backend/app/main.py
git commit -m "添加共享管理和共享属性 API"
```

---

### Task 7: 前端改造 — Store、API、类型定义

**Files:**
- Modify: `frontend/src/types/ontology.ts`
- Modify: `frontend/src/api/ontology.ts`
- Modify: `frontend/src/api/functions.ts`
- Modify: `frontend/src/api/actions.ts`
- Modify: `frontend/src/store/ontology.ts`

**Interfaces:**
- Consumes: 后端 API `GET /entities?ontology_id=X`, `GET /functions?ontology_id=X`, `GET /actions?ontology_id=X` (from Task 5)
- Produces: `useOntologyStore().currentOntologyId`, `useOntologyStore().switchOntology(id)`, 带 ontology_id 参数的 API 调用 — 前端 Task 8 视图依赖

- [ ] **Step 1: 类型定义添加 ontology_id 和 is_shared**

修改 `frontend/src/types/ontology.ts`，在 `EntityListItem` 接口中添加:

```typescript
export interface EntityListItem {
  // ... 现有字段
  ontology_id?: string
  is_shared?: boolean
}
```

在 `OntologyEntity` 接口中也添加:

```typescript
export interface OntologyEntity {
  // ... 现有字段
  ontology_id?: string
}
```

- [ ] **Step 2: 实体 API 添加 ontology_id 参数**

修改 `frontend/src/api/ontology.ts`，`entityApi.list` 方法的参数类型:

```typescript
export interface EntityQuery {
  tier?: number
  search?: string
  ontology_id?: string
}

export const entityApi = {
  list(query?: EntityQuery) {
    return get<EntityListItem[]>('/entities', { params: query })
  },
  // ... 其他方法不变
}
```

- [ ] **Step 3: 函数 API 添加 ontology_id 参数**

修改 `frontend/src/api/functions.ts`，列表查询参数添加:

```typescript
export interface FunctionQuery {
  entity_id?: string
  status?: string
  search?: string
  ontology_id?: string
}

export const functionApi = {
  list(query?: FunctionQuery) {
    return get<FunctionItem[]>('/functions', { params: query })
  },
  // ...
}
```

- [ ] **Step 4: 动作 API 添加 ontology_id 参数**

修改 `frontend/src/api/actions.ts`，列表查询参数添加:

```typescript
export interface ActionQuery {
  entity_id?: string
  status?: string
  action_type?: string
  category?: string
  search?: string
  ontology_id?: string
}

export const actionApi = {
  list(query?: ActionQuery) {
    return get<ActionItem[]>('/actions', { params: query })
  },
  // ...
}
```

- [ ] **Step 5: Store 添加 currentOntologyId 和 switchOntology**

修改 `frontend/src/store/ontology.ts`:

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { entityApi } from '../api/ontology'
import { functionApi } from '../api/functions'
import { actionApi } from '../api/actions'
import type { EntityListItem, OntologyEntity, GraphData, Tier } from '../types'

export const useOntologyStore = defineStore('ontology', () => {
  const entities = ref<EntityListItem[]>([])
  const currentEntity = ref<OntologyEntity | null>(null)
  const graphData = ref<GraphData | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const currentOntologyId = ref<string | null>(null)

  const tier1 = computed(() => entities.value.filter(e => e.tier === 1))
  const tier2 = computed(() => entities.value.filter(e => e.tier === 2))
  const tier3 = computed(() => entities.value.filter(e => e.tier === 3))

  const grouped = computed(() => [
    { tier: 1 as Tier, label: 'Tier 1 核心对象', entities: tier1.value },
    { tier: 2 as Tier, label: 'Tier 2 领域对象', entities: tier2.value },
    { tier: 3 as Tier, label: 'Tier 3 场景对象', entities: tier3.value },
  ])

  async function fetchEntities(query?: { tier?: Tier; search?: string; ontology_id?: string }) {
    loading.value = true
    error.value = null
    try {
      const params = { ...query }
      if (!params.ontology_id && currentOntologyId.value) {
        params.ontology_id = currentOntologyId.value
      }
      entities.value = await entityApi.list(params)
    } catch (e: unknown) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  async function switchOntology(id: string) {
    currentOntologyId.value = id
    entities.value = []
    await fetchEntities({ ontology_id: id })
  }

  async function fetchEntity(id: string) {
    loading.value = true
    error.value = null
    try {
      currentEntity.value = await entityApi.detail(id)
    } catch (e: unknown) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  async function fetchGraph(entityId?: string) {
    loading.value = true
    try {
      graphData.value = entityId
        ? await entityApi.graph(entityId)
        : await entityApi.graphAll()
    } catch (e: unknown) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  return {
    entities, currentEntity, graphData, loading, error,
    tier1, tier2, tier3, grouped, currentOntologyId,
    fetchEntities, fetchEntity, fetchGraph, switchOntology,
  }
})
```

- [ ] **Step 6: 验证类型检查通过**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无类型错误（或仅有不相关的现有错误）

- [ ] **Step 7: 提交**

```bash
git add frontend/src/types/ontology.ts frontend/src/api/ontology.ts frontend/src/api/functions.ts frontend/src/api/actions.ts frontend/src/store/ontology.ts
git commit -m "前端 Store 和 API 添加 ontology_id 支持"
```

---

### Task 8: 前端改造 — OntologyDetailView 移除客户端过滤

**Files:**
- Modify: `frontend/src/views/ontology/OntologyDetailView.vue`

**Interfaces:**
- Consumes: `useOntologyStore().switchOntology(id)`, `useOntologyStore().entities` (from Task 7), `useScenarioStore().byCode(code)` 获取 scenario.id
- Produces: 本体详情页直接展示后端返回的按 ontology_id 过滤后的数据，共享实体标记只读

- [ ] **Step 1: 移除客户端过滤，改用 switchOntology**

修改 `frontend/src/views/ontology/OntologyDetailView.vue` 的 `<script setup>` 部分:

移除原有的 `scenarioEntities` 和 `scenarioFunctions` 计算属性:

```typescript
// 删除这些:
// const scenarioEntities = computed(() =>
//   ontologyStore.entities.filter(e => (e.scenarioCodes || []).includes(code.value))
// )
// const scenarioFunctions = computed(() =>
//   functions.value.filter(f => {
//     const ent = scenarioEntities.value.find(e => e.id === f.entity_id)
//     return !!ent
//   })
// )
```

替换为直接使用 store 数据:

```typescript
const scenarioEntities = computed(() => ontologyStore.entities)
```

修改 `onMounted`:

```typescript
onMounted(async () => {
  await scenarioStore.fetchScenarios()
  const sc = scenarioStore.byCode(code.value)
  if (sc) {
    await ontologyStore.switchOntology(sc.id)
  }
})
```

- [ ] **Step 2: 共享实体展示标记**

在实体列表模板中，为 `is_shared` 为 true 的实体添加标记:

```html
<template #name="{ record }">
  <span>{{ record.name_cn || record.name }}</span>
  <a-tag v-if="record.is_shared" color="blue" style="margin-left: 8px">共享</a-tag>
</template>
```

对共享实体禁用编辑/删除按钮:

```html
<template #action="{ record }">
  <a-button :disabled="record.is_shared" @click="editEntity(record)">编辑</a-button>
  <a-button :disabled="record.is_shared" danger @click="deleteEntity(record)">删除</a-button>
</template>
```

- [ ] **Step 3: 统计数据使用 store 数据**

修改 count 计算属性:

```typescript
const entityCount = computed(() => ontologyStore.entities.length)
const logicCount = computed(() => ontologyStore.entities.reduce((sum, e) => sum + (e.functionCount || 0), 0))
```

- [ ] **Step 4: 验证页面可编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无新增类型错误

- [ ] **Step 5: 提交**

```bash
git add frontend/src/views/ontology/OntologyDetailView.vue
git commit -m "本体详情页移除客户端过滤，使用后端隔离数据"
```

---

### Task 9: 集成测试

**Files:**
- Create: `backend/tests/test_ontology_isolation.py`

**Interfaces:**
- Consumes: 所有 Task 1-6 产出的后端代码
- Produces: 验证隔离功能正确性的自动化测试套件

- [ ] **Step 1: 编写隔离测试**

创建文件 `backend/tests/test_ontology_isolation.py`:

```python
"""本体数据隔离集成测试。"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db, SessionLocal, engine, Base


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _create_scenario(db, code: str, name: str) -> str:
    from app.models.scenario import ScenarioDict
    import uuid
    sc = ScenarioDict(id=uuid.uuid4().hex, code=code, name=name)
    db.add(sc)
    db.commit()
    return sc.id


def _create_entity(db, name: str, ontology_id: str) -> str:
    from app.models.entity import OntologyEntity
    import uuid
    entity = OntologyEntity(
        id=uuid.uuid4().hex, name=name, name_cn=name,
        tier=1, ontology_id=ontology_id
    )
    db.add(entity)
    db.commit()
    return entity.id


class TestEntityIsolation:
    def test_entities_filtered_by_ontology(self, client, db):
        ont_a = _create_scenario(db, "ont_a", "本体A")
        ont_b = _create_scenario(db, "ont_b", "本体B")
        _create_entity(db, "entity_a", ont_a)
        _create_entity(db, "entity_b", ont_b)

        resp = client.get("/api/v1/entities", params={"ontology_id": ont_a})
        assert resp.status_code == 200
        names = [e["name"] for e in resp.json()]
        assert "entity_a" in names
        assert "entity_b" not in names

    def test_same_name_different_ontology(self, client, db):
        ont_a = _create_scenario(db, "ont_a", "本体A")
        ont_b = _create_scenario(db, "ont_b", "本体B")
        _create_entity(db, "user", ont_a)
        _create_entity(db, "user", ont_b)
        # 两个都能创建成功，不冲突

        resp_a = client.get("/api/v1/entities", params={"ontology_id": ont_a})
        resp_b = client.get("/api/v1/entities", params={"ontology_id": ont_b})
        assert len(resp_a.json()) == 1
        assert len(resp_b.json()) == 1


class TestSharing:
    def test_share_entity_visible_in_target(self, client, db):
        ont_a = _create_scenario(db, "ont_a", "本体A")
        ont_b = _create_scenario(db, "ont_b", "本体B")
        entity_id = _create_entity(db, "shared_entity", ont_a)

        # 共享到 ont_b
        resp = client.post(f"/api/v1/ontology/{ont_a}/share", json={
            "target_ontology_id": ont_b,
            "entity_id": entity_id,
        })
        assert resp.status_code == 200

        # ont_b 可以看到
        resp = client.get("/api/v1/entities", params={"ontology_id": ont_b})
        names = [e["name"] for e in resp.json()]
        assert "shared_entity" in names
        # 标记为共享
        shared_item = [e for e in resp.json() if e["name"] == "shared_entity"][0]
        assert shared_item["is_shared"] is True

    def test_shared_entity_readonly(self, client, db):
        ont_a = _create_scenario(db, "ont_a", "本体A")
        ont_b = _create_scenario(db, "ont_b", "本体B")
        entity_id = _create_entity(db, "shared_entity", ont_a)

        client.post(f"/api/v1/ontology/{ont_a}/share", json={
            "target_ontology_id": ont_b,
            "entity_id": entity_id,
        })

        # 从 ont_b 尝试修改应失败
        resp = client.put(
            f"/api/v1/entities/{entity_id}",
            params={"ontology_id": ont_b},
            json={"name_cn": "新名字"},
        )
        assert resp.status_code == 403

    def test_unshare_removes_visibility(self, client, db):
        ont_a = _create_scenario(db, "ont_a", "本体A")
        ont_b = _create_scenario(db, "ont_b", "本体B")
        entity_id = _create_entity(db, "shared_entity", ont_a)

        share_resp = client.post(f"/api/v1/ontology/{ont_a}/share", json={
            "target_ontology_id": ont_b,
            "entity_id": entity_id,
        })
        ref_id = share_resp.json()["id"]

        # 取消共享
        client.delete(f"/api/v1/ontology/{ont_a}/share/{ref_id}")

        # ont_b 不再可见
        resp = client.get("/api/v1/entities", params={"ontology_id": ont_b})
        names = [e["name"] for e in resp.json()]
        assert "shared_entity" not in names
```

- [ ] **Step 2: 运行测试**

Run: `cd backend && python -m pytest tests/test_ontology_isolation.py -v`
Expected: 所有测试 PASS

- [ ] **Step 3: 提交**

```bash
git add backend/tests/test_ontology_isolation.py
git commit -m "添加本体数据隔离集成测试"
```

---

### Task 10: 端到端验证

**Files:** 无新文件，验证现有改动

**Interfaces:**
- Consumes: Tasks 1-9 全部产出
- Produces: 确认完整功能可工作

- [ ] **Step 1: 启动后端验证迁移成功**

Run: `cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
Expected: 启动日志包含 "本体隔离迁移完成"，无报错

- [ ] **Step 2: 验证 API 可用**

Run: `curl http://localhost:8000/api/health`
Expected: 200 OK

Run: `curl "http://localhost:8000/api/v1/entities?ontology_id=<existing_id>"`
Expected: 返回过滤后的实体列表（或空数组）

- [ ] **Step 3: 启动前端验证页面加载**

Run: `cd frontend && npm run dev`
Expected: 编译成功，浏览器访问本体详情页能正确加载该本体的实体列表

- [ ] **Step 4: 验证隔离效果**

在浏览器中：
1. 打开本体A详情页，确认只显示本体A的实体
2. 切换到本体B详情页，确认只显示本体B的实体
3. 创建新实体，确认自动归属当前本体

- [ ] **Step 5: 提交最终状态（如有微调）**

```bash
git add -A
git commit -m "本体数据隔离功能完成"
```
