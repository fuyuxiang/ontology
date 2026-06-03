# 文档构建 — 本体→数据资产映射功能设计

## 概述

在文档构建流程中，本体抽取完成后、最终确认前，新增一个自动触发的"本体→数据资产映射"步骤。利用两阶段 LLM 匹配，将文档抽取出的实体属性和关系精确映射到 DWD 元数据表（`dwd_table_list` + `dwd_table_details`）中的数据表和字段。

## 需求约束

- 映射步骤为必经步骤，不可跳过
- 数据表范围：自动从 `dwd_table_list` 和 `dwd_table_details` 全量匹配，无需用户手动选表
- 映射粒度：实体→表、属性→字段、关系→关联字段
- 用户可手动修正映射结果
- 所有实体必须完成映射后才可进入下一步
- 映射结果融入本体 JSON 结构（不独立存储）

## 流程变更

文档构建步骤从 3 步变为 4 步：

```
Step 0: 文件上传 + 业务描述
Step 1: 多轮对话抽取本体（已有）
Step 2: 本体→数据资产映射（新增）
Step 3: 人工审核确认（已有，原 Step 2）
```

## 数据流

```
输入：文档抽取产出的本体 JSON（entities + relations）
        ↓
  第一阶段：候选表筛选
  - 组合实体名称 + 属性名称 + 关系描述为业务上下文
  - 查询 dwd_table_list 获取全量表名 + 表描述
  - LLM 筛选 Top-N 候选表（按相关性排序）
        ↓
  第二阶段：精确映射
  - 查询候选表的 dwd_table_details 获取字段详情
  - LLM 逐实体匹配：实体→表、属性→字段、关系→关联字段
        ↓
输出：带映射信息的本体 JSON
```

## 输出 JSON 结构

```json
{
  "entities": [
    {
      "name": "Customer",
      "label": "客户",
      "table": "dwd_crm_customer",
      "confidence": 0.92,
      "properties": [
        {
          "name": "customerName",
          "label": "客户名称",
          "field": "cust_name",
          "fieldType": "varchar",
          "confidence": 0.95
        }
      ]
    }
  ],
  "relations": [
    {
      "name": "belongsTo",
      "source": "Order",
      "target": "Customer",
      "sourceField": "cust_id",
      "sourceTable": "dwd_order_main",
      "targetField": "id",
      "targetTable": "dwd_crm_customer",
      "confidence": 0.88
    }
  ]
}
```

## 后端设计

### 新增文件

- `backend/app/api/v1/ontology_mapping.py` — API 路由
- `backend/app/services/ontology_mapping_service.py` — 核心映射逻辑

### API 端点

```
POST /api/v1/doc-builder/mapping
```

请求体：

```json
{
  "session_id": "xxx",
  "ontology": {
    "entities": [...],
    "relations": [...]
  }
}
```

响应：SSE 流式返回

```
event: progress
data: {"stage": "filtering", "message": "正在筛选候选表..."}

event: progress
data: {"stage": "mapping", "message": "正在映射实体 Customer..."}

event: result
data: {"entities": [...], "relations": [...]}
```

### 服务核心逻辑

```python
class OntologyMappingService:
    async def map_ontology_stream(self, ontology: dict):
        # 阶段一：候选表筛选
        all_tables = await dwd_catalog.get_all_tables_summary()
        candidate_tables = await self._filter_tables(ontology, all_tables)

        # 阶段二：精确映射
        for table in candidate_tables:
            table["fields"] = await dwd_catalog.get_table_schema(table["name"])

        result = await self._map_entities_and_relations(ontology, candidate_tables)
        return result
```

复用现有 `dwd_catalog.py` 查询元数据，复用项目已有的 LLM 客户端配置。

## LLM Prompt 设计

### 第一阶段 — 候选表筛选

```
你是数据资产匹配专家。根据以下本体信息，从数据表清单中筛选出最相关的候选表。

## 本体信息
{ontology_summary}

## 数据表清单
{tables_list}

## 要求
- 选出与本体实体最相关的表，每个实体至少匹配1张候选表
- 输出 JSON 格式：{"candidates": [{"entity": "实体名", "tables": ["表名1", "表名2"]}]}
- 宁可多选不要漏选，后续会做精确匹配
```

### 第二阶段 — 精确映射

```
你是本体映射专家。将本体中的实体、属性、关系精确映射到数据表及字段。

## 本体
{ontology_json}

## 候选表结构
{candidate_schemas}

## 映射规则
- 每个实体映射到最匹配的一张表
- 每个属性映射到表中最匹配的字段（考虑名称语义相似度和类型兼容性）
- 关系映射需指出源表关联字段和目标表关联字段
- 无法匹配的属性/关系，field 设为 null
- 为每个映射给出 confidence（0-1）

## 输出格式
（第一部分定义的完整 JSON 结构）
```

### 上下文窗口控制

- 第一阶段：表数量 >200 时分批发送（每批约 100 张），合并去重
- 第二阶段：仅传入候选表字段详情，通常不会超限

## 前端设计

### 修改文件

`frontend/src/views/builder/DocBuilderView.vue`

### 步骤条变更

从 `[上传, 对话抽取, 确认]` 变为 `[上传, 对话抽取, 资产映射, 确认]`

### 映射步骤界面

- 顶部进度状态栏：显示匹配进度
- 实体映射表格：实体名称 | 匹配表 | 置信度 | 操作
- 点击实体行展开属性级映射明细：属性名称 | 匹配字段 | 字段类型 | 置信度
- 关系映射表格：关系名称 | 源表.字段 | 目标表.字段 | 置信度 | 操作
- 底部操作栏：[重新匹配] [确认并继续]

### 交互规则

- 低置信度项（<80%）用黄色标识，提示用户重点关注
- 点击 [编辑] 弹出下拉选择器，可从候选表/字段列表中手动指定
- [重新匹配] 重新触发 LLM 映射
- 所有实体必须完成映射后 [确认并继续] 才可点击
- 未匹配实体标记为红色，用户必须手动指定

## 异常处理

| 场景 | 处理方式 |
|------|---------|
| DWD 元数据表连接失败 | 阻塞并提示"数据资产服务不可用，请检查连接后重试"，仅提供重试按钮 |
| LLM 调用超时/失败 | 支持重试，最多 2 次；仍失败则提示用户稍后重试 |
| 某实体完全无法匹配到表 | `table` 设为 null，标记为"未匹配"，用户必须手动指定后才能继续 |
| 表数量过大（>200） | 分批调用第一阶段 LLM，每批约 100 张表，合并去重 |
| LLM 返回格式异常 | 解析失败时重试一次，仍失败则提示用户重试 |

## 涉及文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/api/v1/ontology_mapping.py` | 新增 | 映射 API 路由 |
| `backend/app/services/ontology_mapping_service.py` | 新增 | 两阶段 LLM 映射服务 |
| `backend/app/api/v1/doc_builder.py` | 修改 | 注册新路由 |
| `frontend/src/views/builder/DocBuilderView.vue` | 修改 | 新增映射步骤 |
