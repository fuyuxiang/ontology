# 本体数据隔离设计

## 概述

为本体平台实现数据隔离机制：每个本体的对象、逻辑、动作、共享属性等数据默认互不可见，同时支持跨本体只读共享。

## 需求总结

- 默认隔离，可选共享（只读引用模式）
- 实体名称本体内唯一（不同本体可同名）
- 逻辑/动作跟随关联实体归属；无关联实体的通过 `ontology_id` 直接归属
- 共享实体在目标本体中只读，源本体修改后自动可见最新版
- API 层按 `ontology_id` 后端过滤，不再全量拉取
- 迁移按现有 `scenario_codes` 自动分配归属

---

## 数据模型变更

### 核心表加 `ontology_id`

#### ontology_entities

```python
ontology_id = Column(Integer, ForeignKey("scenario_dict.id"), nullable=False, index=True)
# 唯一约束: UniqueConstraint("ontology_id", "name")
```

#### ontology_functions

```python
ontology_id = Column(Integer, ForeignKey("scenario_dict.id"), nullable=True, index=True)
# entity_id 不为空时，ontology_id 冗余存储（方便查询）
# entity_id 为空时，ontology_id 必填
```

#### entity_actions

```python
ontology_id = Column(Integer, ForeignKey("scenario_dict.id"), nullable=True, index=True)
# 规则同 ontology_functions
```

#### entity_relations

不加 `ontology_id`，隔离通过 from/to entity 的归属推断。

#### entity_attributes

不加字段，跟随 entity_id 归属。

### 新建共享引用表

```python
class OntologySharedRef(Base):
    __tablename__ = "ontology_shared_refs"

    id = Column(Integer, primary_key=True)
    source_ontology_id = Column(Integer, ForeignKey("scenario_dict.id"), nullable=False)
    target_ontology_id = Column(Integer, ForeignKey("scenario_dict.id"), nullable=False)
    entity_id = Column(Integer, ForeignKey("ontology_entities.id"), nullable=False)
    shared_at = Column(DateTime, default=func.now())
    shared_by = Column(String(100))

    __table_args__ = (
        UniqueConstraint("target_ontology_id", "entity_id"),
    )
```

### 共享属性表

```python
class SharedAttribute(Base):
    __tablename__ = "ontology_shared_attributes"

    id = Column(Integer, primary_key=True)
    ontology_id = Column(Integer, ForeignKey("scenario_dict.id"), nullable=False)
    name = Column(String(100), nullable=False)
    name_cn = Column(String(100))
    data_type = Column(String(50), nullable=False)
    description = Column(Text)
    config_json = Column(JSON)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        UniqueConstraint("ontology_id", "name"),
    )
```

共享属性是本体内的属性模板复用机制。实体"应用"共享属性时在 `entity_attributes` 中创建记录并附加 `shared_attribute_id` 外键（nullable，普通属性为 NULL），修改共享属性定义时引用它的实体属性同步更新元信息（名称、类型等）。

#### entity_attributes 变更

```python
shared_attribute_id = Column(Integer, ForeignKey("ontology_shared_attributes.id"), nullable=True)
# NULL = 普通属性，非 NULL = 从共享属性模板应用而来
```

---

## API 层变更

### 查询接口

```
GET /entities?ontology_id=1        → 本体自有实体 + 共享进来的实体（标记 is_shared=true）
GET /functions?ontology_id=1       → 本体自有 + 共享实体上的 function（只读）
GET /actions?ontology_id=1         → 同上
GET /relations?ontology_id=1       → 两端实体至少一端属于当前本体可见范围的关系
```

### 查询逻辑

```python
def get_entities_for_ontology(ontology_id: int):
    owned = select(OntologyEntity).where(OntologyEntity.ontology_id == ontology_id)

    shared_ids = select(OntologySharedRef.entity_id).where(
        OntologySharedRef.target_ontology_id == ontology_id
    )
    shared = select(OntologyEntity).where(OntologyEntity.id.in_(shared_ids))

    return merge(owned, shared)  # 共享实体标记 is_shared=True, readonly=True
```

### 写入保护

- 创建时必须指定 `ontology_id`（自动从当前本体上下文获取）
- 修改/删除校验：目标资源 `ontology_id` 必须等于当前操作本体
- 共享实体在目标本体中只读，拒绝修改请求返回 403

### 共享管理接口

```
POST   /ontology/{id}/share          → 将实体共享到目标本体
DELETE /ontology/{id}/share/{ref_id}  → 取消共享
GET    /ontology/{id}/shared          → 查看共享出去/共享进来列表
```

### 参数校验

- 列表查询接口未传 `ontology_id` 时返回 400（防止数据泄露）
- 仅管理员接口保留无 ontology_id 的全量查询能力

---

## 前端改造

### 全局状态

```typescript
// store/ontology.ts
const currentOntologyId = ref<number | null>(null)

function switchOntology(id: number) {
  currentOntologyId.value = id
  entities.value = []
  functions.value = []
  actions.value = []
  fetchEntities({ ontology_id: id })
  fetchFunctions({ ontology_id: id })
  fetchActions({ ontology_id: id })
}
```

### API 请求

所有列表查询附带 `ontology_id` 参数。进入本体详情页时通过路由参数解析 ontology_id 并调用 `switchOntology`。

### 共享实体展示

- 加视觉标记（图标或 tag 标注"来自 xxx 本体"）
- 禁用编辑/删除按钮
- 提供"取消共享"操作入口

### 创建/编辑表单

- 自动绑定 `currentOntologyId`，无需用户选择
- 移除现有 `scenario_codes` 多选逻辑（渐进式，先隐藏再删除）

### 移除的逻辑

- `OntologyDetailView.vue` 中的 `scenarioEntities` 客户端过滤
- Store 中全量拉取逻辑，改为按本体分次请求

---

## 数据迁移策略

### 实体迁移

```python
for entity in all_entities:
    codes = entity.scenario_codes or []
    if len(codes) == 1:
        entity.ontology_id = get_scenario_id(codes[0])
    elif len(codes) > 1:
        entity.ontology_id = get_scenario_id(codes[0])
        for code in codes[1:]:
            create_shared_ref(source=entity.ontology_id, target=get_scenario_id(code), entity_id=entity.id)
    else:
        entity.ontology_id = default_ontology_id
```

### Function / Action 迁移

```python
for func in all_functions:
    if func.entity_id:
        func.ontology_id = func.entity.ontology_id
    else:
        func.ontology_id = default_ontology_id
```

### 迁移步骤

1. 新增 `ontology_id` 列（nullable）和共享引用表
2. 运行迁移脚本填充数据
3. 验证数据完整性（检查 NULL 值）
4. 将 `ontology_id` 改为 NOT NULL（entities 表）
5. 修改唯一约束：`name` → `(ontology_id, name)`
6. `scenario_codes` 字段暂时保留，待新逻辑稳定后废弃

### 异常处理

- `scenario_codes` 引用不存在的 code → 记录日志，跳过
- 迁移后检查 `ontology_id = NULL` 记录 → 报告异常数据

### 回滚

迁移前备份数据库，`scenario_codes` 保留不删，可回退到旧逻辑。

---

## 错误处理与边界情况

| 场景 | 处理方式 |
|------|---------|
| 修改/删除共享只读实体 | 后端 403，前端禁用操作按钮 |
| 本体内实体名重复 | 后端 409，提示"该本体下已存在同名实体" |
| 删除本体时仍有共享引用 | 提示先取消共享关系，或级联取消 |
| 删除实体时被共享到其他本体 | 确认后级联删除共享引用 |
| API 缺少 ontology_id 参数 | 返回 400 |

### 共享级联行为

- 源本体删除实体 → 级联删除共享引用记录
- 源本体修改实体 → 目标本体自动看到最新版本
- 共享实体上的 function/action 在目标本体可见但只读
