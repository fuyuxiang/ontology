# 文档构建 — 映射结果自动落库到映射管理

## 概述

在文档构建流程的 Review 步骤之后、注水验证之前，新增"映射确认"步骤（Step3）。将 LLM 产生的本体→数据表映射结果转换为 ObjectBinding 记录持久化，使映射管理模块可直接看到并管理这些映射。

## 动机

当前文档构建的 LLM 映射结果是临时的，不会落库。用户在构建完本体后进入映射管理时看不到任何已有映射，需要重新通过 AI 推荐走一遍流程。这是重复劳动，且可能产生不一致的结果。

## 流程变更

文档构建从 3 步变为 4 步：

```
Step1: 上传文档 + LLM抽取本体
Step2: Review 本体结构（实体、属性、关系）
Step3: 映射确认（新增）
Step4: 注水验证（原Step3）
```

## 设计决策

| 决策点 | 结论 |
|--------|------|
| 落库时机 | 用户在 Step3 确认后落库 |
| 低置信度映射 | 全部落库（包括 field=null），映射管理中后续补全 |
| 冲突处理 | Review 界面标出冲突，用户选择覆盖或保留旧的 |
| 未注册 Asset | 给用户选择：一键注册为 Asset 或跳过 |
| 关系映射 | 本次不处理，仅落实体+属性映射 |

## 后端接口

### POST /doc-builder/mapping/preview

将 LLM 映射结果解析为可落库的预览数据，执行 table_name → Asset 查找，检测冲突。

请求：
```json
{
  "session_id": "xxx",
  "mapping_result": {
    "entities": [
      {"name": "...", "table": "dwd_xxx", "confidence": 0.9, "properties": [{"name": "...", "field": "...", "confidence": 0.85}]}
    ]
  }
}
```

响应：
```json
{
  "items": [
    {
      "entity_name": "Customer",
      "entity_id": "ontology_entities中的id或null",
      "table_name": "dwd_customer_info",
      "asset_id": "Asset.id或null",
      "asset_registered": true,
      "confidence": 0.9,
      "conflict": null,
      "field_mappings": [
        {"attribute_name": "phone", "attribute_id": "...", "source_column": "mobile", "confidence": 0.85},
        {"attribute_name": "age", "attribute_id": "...", "source_column": null, "confidence": 0}
      ]
    }
  ]
}
```

conflict 非 null 时结构：`{"existing_binding_id": "...", "existing_asset_name": "..."}`

### POST /doc-builder/mapping/apply

用户确认后批量落库。

请求：
```json
{
  "session_id": "xxx",
  "items": [
    {
      "entity_id": "...",
      "asset_id": "...(已注册时有值)",
      "conflict_action": "overwrite | keep | null",
      "register_asset": false,
      "table_name": "dwd_xxx",
      "field_mappings": [{"attribute_id": "...", "source_column": "mobile"}]
    }
  ]
}
```

逻辑：
- `register_asset=true`：自动创建 kind=table 的 Asset（connection_id 从 dwd_catalog 连接推导）
- `conflict_action=overwrite`：更新已有 Binding 的 field_mappings
- `conflict_action=keep`：跳过该条目
- 其余：新建 ObjectBinding（role=primary）
- 兼容期：同步反写 EntityAttribute.source_table/source_field

响应：返回创建/更新/跳过的条目统计和 Binding ID 列表。

## 前端组件

### Step3MappingConfirm.vue

插入 DocBuilder 流程，位于 Step2Review 和 Step4Hydrate（原Step3）之间。

布局：
- 顶部：映射概览统计（已匹配数/总数、冲突数、未注册数）
- 左侧：实体列表，显示状态图标（✓正常 / ⚠冲突 / ✗未注册）和置信度
- 右侧：选中实体的映射明细表格（属性→字段→置信度）
- 右侧交互区：冲突时显示新旧对比+覆盖/保留选择；未注册时显示"一键注册"按钮
- 用户可手动修改字段映射（下拉选择 Asset schema_snapshot 中的列）
- 底部：[上一步] [确认映射并落库]

### DocBuilderView 改动

- 步骤条从 3 步变为 4 步
- Step2 确认后调用 preview 接口，进入 Step3
- 原 Step3Hydrate 的 step index 改为 3→4

## 数据流

```
Step2 确认 → 前端持有 mapping_result（LLM原始JSON）
  → POST /doc-builder/mapping/preview
  → 后端：entity.name → 查 ontology_entities 拿 entity_id
         entity.table → AssetRepo.find_table_by_connection_table() 查 Asset
         查 ObjectBinding 检测冲突
  → 返回预览数据
  → 用户操作（处理冲突、注册资产、调整映射）
  → POST /doc-builder/mapping/apply
  → 后端：注册Asset → 创建/更新ObjectBinding → 反写兼容字段
  → 前端进入 Step4 注水
```

## 边界情况

| 场景 | 处理 |
|------|------|
| entity_name 在 ontology_entities 找不到 | 从 session 草稿中查找 entity_id |
| 同一张表被映射给多个实体 | 正常，ObjectBinding 支持多 ObjectType 绑同一 Asset |
| 用户跳过 Step3 | 不允许，必须确认（可保持默认直接点确认） |
| source_column 为 null | 照样落库，后续在映射管理中补全 |
| Asset 注册时缺少 connection_id | 从 dwd_catalog 使用的数据库连接信息推导 |

## 不在范围内

- 关系映射的落库
- 映射结果的版本对比
- 自动合并策略（智能解决冲突）
- 资产构建流程的映射落库（仅文档构建）
