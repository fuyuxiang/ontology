# 本体发布与技能/流程联动设计

## 背景

当前本体版本发布后，仅作为快照归档存在，与下游的技能管理（Agent）和流程编排（AipScene）没有实质联动。下游系统直接引用草稿态的实体，当本体发布新版本时（实体删除、改名），下游无从感知，可能导致运行时引用失效。

## 目标

让本体发布成为下游系统可感知的事件：发布新版本后，自动检测结构性破坏变更，在受影响的流程和 Agent 上标记"依赖已过期"通知。

## 设计约束

- 不阻断发布流程（纯通知，不强制升级）
- 引用粒度为实体级别
- 仅检测结构性破坏：实体删除、实体改名
- 不追踪属性级变更、语义变化

## 一、数据模型变更

### AipScene 新增字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `ontology_version_id` | String(36), nullable | 该场景基于哪个已发布版本构建 |
| `ontology_stale` | Boolean, default=False | 是否有新版本导致依赖过期 |
| `ontology_stale_detail` | JSON, nullable | 过期详情（哪些实体被删/改名） |

保留现有 `ontology_bindings`（实体名称列表）作为依赖声明。

### Agent 新增字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `ontology_version_id` | String(36), nullable | 基于哪个已发布版本 |
| `ontology_stale` | Boolean, default=False | 依赖是否过期 |
| `ontology_stale_detail` | JSON, nullable | 过期详情 |

保留现有 `entity_ids` 作为实体级引用声明。

### 不新增表

依赖关系通过现有字段 + 新增版本绑定字段管理，不引入中央注册表。

## 二、发布时影响分析逻辑

### 触发时机

本体版本发布成功后（status 变为 published），同步执行影响分析。

### Diff 计算

对比新发布版本和上一个已发布版本（is_active=True）的实体快照：

- **删除的实体**：旧版本有、新版本没有的 OntologyVersionEntity
- **改名的实体**：source_entity_id 相同但 name 变了的实体

### 影响扫描

拿到破坏性变更的实体名称/ID 列表后：

- 扫描 `AipScene`：`ontology_bindings` 中包含被删/改名实体名称的场景
- 扫描 `Agent`：`entity_ids` 中包含被删实体 ID 的 Agent

### 标记更新

对受影响的 Scene/Agent 更新：

- `ontology_stale = True`
- `ontology_stale_detail` 格式：

```json
{
  "version_id": "新版本ID",
  "published_at": "2026-06-03T10:00:00",
  "breaking_changes": [
    {"entity_name": "OldCustomer", "change_type": "renamed", "new_name": "Customer"},
    {"entity_name": "Contract", "change_type": "deleted"}
  ]
}
```

### 清除标记

用户在 Scene/Agent 中确认更新引用后，将 `ontology_stale` 重置为 False。

## 三、API 接口

### 发布接口改造

`ontology_publish.py` 的 approve 端点发布成功后追加影响分析，内部调用 `_mark_stale_dependents(old_version, new_version, db)`。

### 新增端点

| 端点 | 方法 | 用途 |
|------|------|------|
| `/ontology-publish/versions/{id}/impact` | GET | 预览影响面 |
| `/aip-scenes/{id}/acknowledge-stale` | POST | 场景确认过期提醒，重置标记 |
| `/agents/{id}/acknowledge-stale` | POST | Agent 确认过期提醒，重置标记 |

## 四、前端展示

### 列表页

- `ontology_stale = True` 的条目显示橙色告警徽标："本体依赖已更新"
- 点击徽标展开详情

### 详情页

- 顶部横幅提醒，附带"查看变更"和"确认已知"按钮
- "确认已知"调用 acknowledge 端点清除标记

### 发布页（可选增强）

- 提交审批前可点击"预览影响"调用 impact 端点
- 纯信息展示，不阻断发布流程

## 五、数据迁移与边界处理

### 存量数据

- 新增字段 nullable，不做强制回填
- 存量 `ontology_version_id` 为 None，`ontology_stale` 默认 False
- 下次本体发布时存量数据会被扫描并自然获得标记

### 边界场景

| 场景 | 处理方式 |
|------|----------|
| 首次发布（无旧版本） | 跳过影响分析 |
| ontology_bindings 为空 | 不受影响，跳过 |
| entity_ids 为空 | 不受影响，跳过 |
| 实体改名（旧名不在新版本中） | 视为"删除"标记 |
| 连续发布多个版本 | 每次覆盖 stale_detail，保留最新变更 |

### 明确不做

- 不阻断发布流程
- 不自动修改下游引用
- 不追踪属性级变更
- 不引入消息推送/邮件通知
