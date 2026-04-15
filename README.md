<div align="center">

# 本体驱动智能策略平台

**Ontology-Driven Intelligent Strategy Platform**

*将领域知识图谱与 AI 推理引擎深度融合的下一代运营决策系统*

[![Vue 3](https://img.shields.io/badge/Vue-3.5-4FC08D?logo=vue.js)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-6.x-3178C6?logo=typescript)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 目录

- [项目概述](#项目概述)
- [系统架构](#系统架构)
- [技术栈](#技术栈)
- [功能模块详解](#功能模块详解)
- [数据模型](#数据模型)
- [API 接口文档](#api-接口文档)
- [服务层架构](#服务层架构)
- [前端架构](#前端架构)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [环境配置](#环境配置)
- [文件导入规范](#文件导入规范)
- [二次开发指南](#二次开发指南)

---

## 项目概述

传统运营系统面临的核心痛点：业务规则散落在代码中、数据关系隐藏在表结构里、策略决策依赖人工经验。

本平台通过 **本体建模 (Ontology Modeling)** 将业务领域知识结构化为三层对象体系（核心层 → 领域层 → 场景层），结合 **知识图谱可视化**、**声明式规则引擎**、**多数据源集成** 和 **AI Copilot 智能问答**，实现从数据到洞察到行动的闭环。

### 核心能力

- **本体建模**：三层 Tier 架构（核心/领域/场景），支持实体、属性、关系、规则、动作的全生命周期管理
- **知识图谱画布**：基于 vue-flow + dagre 的交互式关系画布，支持自动布局、拖拽、缩放、血缘探索
- **声明式规则引擎**：条件表达式 + 结构化条件双模式，支持真实数据源评估、置信度计算、风险等级判定
- **AI 智能问答**：双模式 Copilot（普通对话 + Agent 工具调用），本体感知上下文注入，SSE 流式响应
- **多数据源集成**：支持 MySQL / PostgreSQL / Oracle / SQL Server，自动发现表结构，从数据表一键生成本体实体
- **场景化分析**：内置携号转网预警、FTTR 续约策划、宽带退单稽核、政企根因分析四大电信运营场景
- **审计追踪**：全操作审计日志，记录变更快照，支持回溯

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend (Vue 3 + TypeScript)                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐ │
│  │ 本体管理  │ │ 关系画布  │ │ 业务规则  │ │ 数据看板  │ │ AI Copilot │ │
│  │ Explorer │ │ vue-flow │ │  Logic   │ │Dashboard │ │  Agent    │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └─────┬─────┘ │
│       └─────────────┴────────────┴─────────────┴─────────────┘       │
│                          Pinia Store + Axios                         │
│                          (JWT Auth + SSE)                            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP / SSE
┌──────────────────────────────┴──────────────────────────────────────┐
│                        Backend (FastAPI + Uvicorn)                    │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                      API Layer (v1 Router)                      │ │
│  │  entities · relations · rules · copilot · datasources           │ │
│  │  dashboard · auth                                               │ │
│  └──────────────────────────┬──────────────────────────────────────┘ │
│  ┌──────────────────────────┴──────────────────────────────────────┐ │
│  │                      Service Layer                              │ │
│  │  CopilotService · AgentService · RuleEngine · FileImport       │ │
│  │  AuditService · DatasourceUtils                                │ │
│  └──────────────────────────┬──────────────────────────────────────┘ │
│  ┌──────────────────────────┴──────────────────────────────────────┐ │
│  │                      Data Layer                                 │ │
│  │  SQLAlchemy ORM · SQLite (默认) · Neo4j (可选)                   │ │
│  │  外部数据源 (MySQL/PostgreSQL/Oracle/SQL Server)                 │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                               │
                    ┌──────────┴──────────┐
                    │   LLM (Qwen 3.5+)   │
                    │  OpenAI 兼容接口      │
                    │  DashScope API       │
                    └─────────────────────┘
```

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端框架** | Vue 3.5 + TypeScript 6 | Composition API + `<script setup>` |
| **构建工具** | Vite 8 | HMR 热更新，代理后端 API |
| **状态管理** | Pinia 3 | 6 个 Store（ontology/rules/auth/copilot/datasource/audit） |
| **图可视化** | vue-flow 1.48 + dagre 0.8 | 交互式画布 + 自动布局算法 |
| **HTTP 客户端** | Axios 1.15 | JWT 拦截器 + SSE 流式解析 |
| **Markdown 渲染** | marked 18 | AI 回答渲染 |
| **后端框架** | FastAPI 0.115 + Uvicorn | ASGI 异步服务器 |
| **ORM** | SQLAlchemy 2.0 | Mapped 声明式模型 |
| **数据验证** | Pydantic 2.11 | 请求/响应 Schema |
| **认证** | JWT (PyJWT) + Passlib (bcrypt) | Bearer Token 认证 |
| **默认数据库** | SQLite | 零配置启动，文件 `ontology.db` |
| **图数据库** | Neo4j（可选） | 图遍历加速（当前基础功能不依赖） |
| **LLM** | Qwen 3.5 Plus (阿里云 DashScope) | OpenAI 兼容接口，可替换任意 LLM |
| **数据源驱动** | pymysql / psycopg2 / oracledb / pymssql | 多数据库连接 |

---

## 功能模块详解

### 1. 本体管理（OntologyExplorer）

路由：`/browser`

本体管理是平台的核心模块，管理所有本体实体的全生命周期。

**三层 Tier 架构：**

| Tier | 定位 | 说明 |
|------|------|------|
| Tier 1 | 核心对象 | 业务基础实体，如客户、订单、产品 |
| Tier 2 | 领域对象 | 运营领域概念，如营销活动、客户分群、策略 |
| Tier 3 | 场景对象 | 场景专属对象，如携转预警、FTTR订阅、退单工单 |

**功能清单：**
- 实体列表：按 Tier 分组展示，支持搜索过滤
- 新建实体：手动创建，指定名称、中文名、Tier、描述
- 编辑实体：修改实体基本信息
- 属性管理：查看实体属性列表（名称、类型、描述、是否必填）
- 关系管理：查看/添加/删除实体间关系，支持 1:1、1:N、N:1、N:N 基数
- 规则管理：查看关联的业务规则
- 动作管理：查看/执行关联的业务动作
- 血缘图谱：EntityLineageGraph 组件，BFS N 跳邻域遍历（1-3 跳深度）
- 从数据源创建：连接外部数据库表，自动生成实体和属性

### 2. 关系画布（DataflowView）

路由：`/browser/graph`

基于 vue-flow 的全量知识图谱可视化画布。

- 全量图谱：展示所有实体节点和关系边
- dagre 自动布局：支持 LR（左右）和 TB（上下）方向
- 节点交互：拖拽移动、点击选中、hover 高亮
- 缩放漫游：鼠标滚轮缩放、拖拽平移
- 适应画布：一键自适应视口
- 节点信息：显示中文名、Tier 徽章、关系数量
- 边标签：显示关系名称和基数

**自定义组件：**
- `OntologyNode`：自定义节点，按 Tier 着色（T1 蓝 / T2 紫 / T3 绿）
- `CanvasEdgeLabel`：自定义边标签
- `CanvasToolbar`：画布工具栏（布局方向、缩放控制）
- `CanvasNodePalette`：节点面板
- `CanvasConfigPanel`：配置面板

### 3. 业务规则（LogicView）

路由：`/browser/rules`

声明式规则引擎，将业务逻辑从代码中解耦。

- 规则列表：支持按状态（active/inactive）、优先级（high/medium/low）、关键词筛选
- 规则统计：总数、活跃、告警、禁用数量
- 创建规则：指定关联实体、条件表达式、动作描述、优先级
- 编辑/删除规则
- 手动执行：触发规则并记录执行次数和最后触发时间
- 规则评估：对指定用户 ID 评估规则，返回结构化判断结果（匹配条件明细、置信度、风险等级）
- 结构化条件（conditions_json）：支持字段引用、操作符、期望值的精确定义
- 规则元数据（rule_meta_json）：存储规则 ID、风险等级等扩展信息

### 4. 数据看板（DashboardView）

路由：`/dashboard`

平台运营数据的全局视图。

- KPI 指标卡：实体总数、关系总数、规则总数、活跃规则数
- Tier 分布：按核心/领域/场景三层统计实体数量和占比
- 对象健康状态：所有实体的状态一览（active/warning/error）
- 近期活动：从审计日志取最近 10 条操作记录

### 5. 数据源管理（DataSourceView）

路由：`/datasource`

外部数据库连接管理，是规则引擎真实数据评估的基础。

**支持的数据库类型：**
- MySQL（pymysql）
- PostgreSQL（psycopg2）
- Oracle（oracledb）
- SQL Server（pymssql）

**功能清单：**
- 创建数据源：输入连接信息（host/port/database/username/password），自动发现所有表，每张表创建一条数据源记录
- 连接测试：Socket 连通性检测
- 表列表获取：无需创建数据源即可预览数据库表
- 数据预览：查看表前 20 条数据
- 表结构查看：列名、类型、是否主键、注释
- 启用/禁用管道：toggle 开关控制数据源可用性
- 刷新记录数：同步数据表当前记录条数
- 从数据源创建实体：选择表 → 自动映射列为属性 → 生成本体实体

**数据库类型到本体类型的映射：**
```
varchar/char/text → string
int/bigint/float/decimal → number
date/datetime/timestamp → date
boolean/tinyint(1) → boolean
json/jsonb → json
```

### 6. AI 智能对话（CopilotView）

路由：`/copilot`

集成 LLM 的智能对话助手，提供两种对话模式。

**模式一：普通对话（/copilot/chat）**
- 本体感知上下文：自动将全部实体、关系、规则、数据源映射注入 system prompt
- SSE 流式响应：逐 token 推送，前端实时渲染
- Markdown 渲染：支持代码块、表格、列表等格式
- 实体上下文：可指定聚焦实体，注入该实体的详细属性信息

**模式二：Agent 智能问答（/copilot/agent-chat）**
- 工具调用循环：LLM 规划 → 执行工具 → 收集结果 → 继续推理（最多 8 轮）
- 推理链展示：前端展示每步工具调用的名称、参数、结果摘要
- 建议和动作：AI 回答末尾可附带后续建议和可执行动作

**Agent 可用工具（9 个）：**

| 工具名 | 功能 |
|--------|------|
| `describe_ontology_model` | 返回本体模型概览（实体/关系/规则） |
| `list_datasources` | 列出所有已启用数据源 |
| `get_table_schema` | 获取数据表列元数据 |
| `query_datasource` | 执行只读 SQL 查询（仅 SELECT） |
| `get_entity_detail` | 获取实体详情（属性/关系/规则） |
| `query_entity_data` | 通过实体名查询真实数据（自动解析数据源） |
| `get_business_rules` | 查询业务规则列表 |
| `evaluate_rule` | 对指定用户评估单条规则 |
| `evaluate_all_rules` | 对指定用户评估所有活跃规则 |
| `execute_action` | 执行/模拟执行业务动作 |

### 7. 场景化分析

平台内置四大电信运营场景，每个场景基于本体模型构建完整的业务流程。

#### 7.1 携号转网预警（MnpWorkbench）

路由：`/scene/mnp`

基于本体实体间的流程驱动，展示携转预警从信号感知到任务分发的端到端编排。

**三层架构：**
- 语义层（Signal）：MobileSubscriber、PortabilityQuery、UserContract、UserArrears、ComplaintWorkOrder
- 动力层（Aggregate）：MonthlyBilling、VoiceCallRecord、ConvergencePackage
- 动态层（Decision）：RetentionRecord

**功能：**
- 流程编排时间线（ProcessOrchTimeline）：7 个阶段的端到端流程可视化
- 实体参与面板（EntityParticipantPanel）：展示每个阶段参与的实体
- 实体映射表（EntityMappingTable）：实体与数据源的映射关系
- 动作驱动面板（ActionDriverPanel）：展示可执行的业务动作
- KPI 指标栏：流程阶段数、参与实体数、关联规则数、驱动动作数
- 层级统计：从后端 `/entities/scene-layer-stats` 接口获取实时统计

#### 7.2 FTTR 续约策划（FttrScene）

路由：`/scene/fttr`

精准续约方案推荐，提升用户 ARPU。

#### 7.3 宽带退单稽核（BroadbandScene）

路由：`/scene/broadband`

识别虚假退单，降低装机失败率。

#### 7.4 政企根因分析（EnterpriseScene）

路由：`/scene/enterprise`

KPI 指标血缘追溯，定位业绩根因。

### 8. 实体详情（EntityDetail）

路由：`/ontology/:id`

单个实体的完整详情页，包含属性列表、关系图谱、关联规则、血缘可视化。

### 9. 认证与权限

- JWT Token 认证：登录获取 token，存储于 localStorage
- 自动附加：Axios 请求拦截器自动添加 Bearer Token
- 401 处理：token 过期自动跳转登录
- 默认管理员：admin / admin123（启动时自动创建）

**角色权限矩阵：**

| 权限 | admin | editor | operator | viewer |
|------|-------|--------|----------|--------|
| entity:read | ✓ | ✓ | ✓ | ✓ |
| entity:write | ✓ | ✓ | | |
| entity:delete | ✓ | | | |
| rule:read | ✓ | ✓ | ✓ | ✓ |
| rule:write | ✓ | ✓ | | |
| rule:execute | ✓ | | ✓ | |
| strategy:read | ✓ | ✓ | ✓ | ✓ |
| strategy:execute | ✓ | | ✓ | |
| audit:read | ✓ | ✓ | ✓ | |
| admin:users | ✓ | | | |

### 10. 审计日志

全操作审计追踪，记录所有增删改执行操作。

- 操作类型：create / update / delete / execute / evaluate
- 目标类型：entity / relation / rule / action / file
- 变更记录：changes_json 记录字段级变更（oldValue → newValue）
- 快照：snapshot_before / snapshot_after 记录操作前后状态
- 看板集成：最近 10 条操作显示在数据看板

### 11. 文件导入

支持从文件批量导入本体 Schema。

**支持格式：**
- JSON（V1.1 本体规范）：导入 object_types、link_types、business_rules、actions
- OWL/TTL（RDF 本体）：解析 owl:Class → 实体，owl:DatatypeProperty → 属性，owl:ObjectProperty → 关系

**导入内容：**
- 实体（OntologyEntity）：name、name_cn（display_name）、tier、description
- 属性（EntityAttribute）：name、type、description、required、constraints
- 计算属性（computed_properties）：expression 表达式
- 关系（EntityRelation）：source_type → target_type，支持跨命名空间引用
- 规则（BusinessRule）：condition_expr、action_desc、conditions_json（结构化条件）
- 动作（EntityAction）：type、parameters_json、preconditions_json、effects_json

---

## 数据模型

### ER 关系图

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ OntologyEntity  │────<│ EntityAttribute  │     │  EntityRelation  │
│─────────────────│     │──────────────────│     │─────────────────│
│ id (PK)         │     │ id (PK)          │     │ id (PK)         │
│ name (unique)   │     │ entity_id (FK)   │     │ from_entity_id  │
│ name_cn         │     │ name             │     │ to_entity_id    │
│ tier (1/2/3)    │     │ type             │     │ name            │
│ status          │     │ description      │     │ rel_type        │
│ description     │     │ required         │     │ cardinality     │
│ schema_json     │     │ example          │     │ acyclic         │
│ created_at      │     │ constraints_json │     │ description     │
│ updated_at      │     └──────────────────┘     │ created_at      │
│ created_by      │                               └─────────────────┘
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───┴──────────┐  ┌─────────────────┐
│ BusinessRule │  │  EntityAction   │
│──────────────│  │─────────────────│
│ id (PK)      │  │ id (PK)         │
│ entity_id    │  │ entity_id (FK)  │
│ name         │  │ name            │
│ condition_expr│  │ type            │
│ action_desc  │  │ status          │
│ status       │  │ impact_count    │
│ priority     │  │ parameters_json │
│ trigger_count│  │ preconditions_json│
│ last_triggered│ │ effects_json    │
│ conditions_json│ │ action_meta_json│
│ rule_meta_json│  │ created_at      │
│ created_at   │  └─────────────────┘
│ updated_at   │
└──────────────┘

┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│     User        │  │   AuditLog      │  │   DataSource    │
│─────────────────│  │─────────────────│  │─────────────────│
│ id (PK)         │  │ id (PK)         │  │ id (PK)         │
│ username        │  │ timestamp       │  │ name (unique)   │
│ password_hash   │  │ user_id         │  │ type            │
│ name            │  │ user_name       │  │ host / port     │
│ role            │  │ action          │  │ database        │
│ created_at      │  │ target_type     │  │ username / pwd  │
└─────────────────┘  │ target_id       │  │ table_name      │
                     │ target_name     │  │ record_count    │
                     │ changes_json    │  │ enabled         │
                     │ snapshot_before │  │ params (JSON)   │
                     │ snapshot_after  │  │ status          │
                     └─────────────────┘  │ created_at      │
                                          └─────────────────┘
```

### 属性类型枚举

| 类型 | 说明 |
|------|------|
| `string` | 字符串 |
| `number` | 数值 |
| `boolean` | 布尔 |
| `date` | 日期时间 |
| `ref` | 引用类型 |
| `json` | JSON 对象/数组 |
| `computed` | 计算属性（含 expression 表达式） |

### schema_json 结构

实体的 `schema_json` 字段存储扩展元数据：

```json
{
  "namespace": "s5",
  "primary_key": "user_id",
  "datasource_ref": "cbss_subscriber",
  "datasource_id": "xxx",
  "datasource_name": "xxx",
  "table_name": "cbss_subscriber"
}
```

---

## API 接口文档

### 实体管理 `/api/v1/entities`

| 方法 | 路径 | 说明 | 参数 |
|------|------|------|------|
| GET | `/` | 实体列表 | `tier`, `status`, `search`, `namespace` |
| GET | `/graph` | 全量知识图谱（nodes + edges） | - |
| GET | `/scene-layer-stats` | 场景层级统计 | `namespace` (如 "s5") |
| GET | `/{id}` | 实体详情（含属性/关系/规则/动作） | - |
| GET | `/{id}/lineage` | 实体血缘图（BFS N-hop） | `depth` (1-5, 默认 2) |
| POST | `/` | 创建实体 | EntityCreate body |
| POST | `/from-datasource` | 从数据源表创建实体 | `datasource_id`, `table_name`, `name_cn`, `tier`, `namespace` |
| POST | `/import` | 文件导入 | `file` (上传文件), `file_type` (json/owl/ttl), `namespace` |
| PUT | `/{id}` | 更新实体 | EntityUpdate body |
| DELETE | `/{id}` | 删除实体（级联删除属性/规则/动作） | - |

### 关系管理 `/api/v1/relations`

| 方法 | 路径 | 说明 | 参数 |
|------|------|------|------|
| GET | `/` | 关系列表 | `entity_id` (可选，按实体过滤) |
| POST | `/` | 创建关系 | `from_entity_id`, `to_entity_id`, `name`, `rel_type`, `cardinality` |
| DELETE | `/{id}` | 删除关系 | - |

### 规则管理 `/api/v1/rules`

| 方法 | 路径 | 说明 | 参数 |
|------|------|------|------|
| GET | `/` | 规则列表 | `entity_id`, `status`, `priority`, `search` |
| GET | `/{id}` | 规则详情 | - |
| POST | `/` | 创建规则 | RuleCreate body |
| PUT | `/{id}` | 更新规则 | RuleUpdate body |
| DELETE | `/{id}` | 删除规则 | - |
| POST | `/{id}/execute` | 执行规则（递增触发计数） | - |
| POST | `/{id}/evaluate` | 评估规则（真实数据源查询） | `user_id` |

### 数据源管理 `/api/v1/datasources`

| 方法 | 路径 | 说明 | 参数 |
|------|------|------|------|
| GET | `/` | 数据源列表 | `type`, `status`, `q` |
| GET | `/{id}` | 数据源详情 | - |
| POST | `/` | 创建数据源（自动发现所有表） | DataSourceCreate body |
| POST | `/test` | 测试连接（无需创建） | DataSourceCreate body |
| POST | `/fetch-tables` | 获取表列表（无需创建） | DataSourceCreate body |
| PUT | `/{id}` | 更新数据源 | DataSourceUpdate body |
| DELETE | `/{id}` | 删除数据源 | - |
| POST | `/{id}/test` | 测试已有数据源连接 | - |
| POST | `/{id}/toggle` | 启用/禁用数据源 | - |
| POST | `/{id}/refresh-tables` | 刷新记录数 | - |
| GET | `/{id}/preview` | 预览数据（前 20 条） | - |
| GET | `/{id}/tables/{table}/preview` | 预览指定表数据 | - |
| GET | `/{id}/tables/{table}/schema` | 获取表结构 | - |

### AI 对话 `/api/v1/copilot`

| 方法 | 路径 | 说明 | 参数 |
|------|------|------|------|
| POST | `/chat` | 普通对话（SSE 流式） | `messages[]`, `entity_id`, `stream` |
| POST | `/agent-chat` | Agent 智能问答（SSE 流式） | `question`, `entity_id` |

### 认证 `/api/v1/auth`

| 方法 | 路径 | 说明 | 参数 |
|------|------|------|------|
| POST | `/login` | 用户登录 | `username`, `password` |
| GET | `/me` | 获取当前用户信息 | Bearer Token |

### 看板 `/api/v1/dashboard`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/stats` | 全局统计（实体/关系/规则数、Tier 分布、健康状态、近期活动） |

### 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 服务健康检查 |

---

## 服务层架构

### CopilotService (`app/services/copilot.py`)

本体感知的 AI 对话服务。

**核心机制：**
1. `build_ontology_context()`：自动构建本体上下文，包含：
   - 按 Tier 分组的实体列表及其属性
   - 实体间关系（含基数）
   - 活跃业务规则（含结构化条件信息）
   - 实体→数据源映射
   - 可执行动作列表
2. 上下文注入 system prompt，LLM 基于完整本体知识回答
3. 支持流式（SSE）和同步两种响应模式

### AgentService (`app/services/agent_service.py`)

智能问答核心编排，实现 LLM + 工具调用的 Agent 循环。

**执行流程：**
```
用户提问 → 构建 system prompt（本体上下文 + 工具目录 + 数据源摘要）
         → LLM 决策是否调用工具
         → 是：执行工具 → 将结果反馈 LLM → 继续推理（最多 8 轮）
         → 否：解析最终回答 → 提取建议和动作 → SSE 流式输出
```

**工具执行映射：**
- `describe_ontology_model` → 查询所有实体/关系/规则
- `query_datasource` → `execute_readonly_sql()`（SQL 注入防护 + 自动 LIMIT）
- `query_entity_data` → 自动解析实体对应数据源，构建 SQL
- `evaluate_rule` → `RuleEvaluator.evaluate()`
- `evaluate_all_rules` → `RuleEvaluator.evaluate_all()`
- `execute_action` → `ActionExecutor.execute()`

### RuleEngine (`app/services/rule_engine.py`)

规则引擎，三个核心组件：

**FieldResolver：**
- 将 `"EntityName.property"` 解析为真实数据库查询
- 自动查找实体 → 关联数据源 → 构建 SQL → 返回值
- 支持计算属性（computed）：解析 expression 表达式
- 支持计数查询：`resolve_count()` 带时间窗口过滤

**RuleEvaluator：**
- 解析 `conditions_json` 中的结构化条件
- 逐条评估：解析字段引用 → 查询真实值 → 比较操作符
- 支持操作符：`>`, `<`, `>=`, `<=`, `==`, `!=`, `in`, `not_in`, `contains`, `exists`
- 聚合模式：`all`（全部匹配）/ `any`（任一匹配）
- 计算置信度：matched_count / total_count
- 风险等级判定：confidence ≥ 0.7 → high，≥ 0.4 → medium，否则 low
- `evaluate_all()`：批量评估所有活跃规则，返回综合风险

**ActionExecutor：**
- 校验动作参数
- 检查前置条件（preconditions_json）
- 支持 dry_run 模拟执行
- 返回执行结果和预期效果（effects_json）

### FileImportService (`app/services/file_import.py`)

文件导入服务，支持两种格式：

- **JSON 导入**：按 V1.1 本体规范解析 object_types / link_types / business_rules / actions
- **OWL/TTL 导入**：使用 rdflib 解析 RDF 图，owl:Class → 实体，owl:DatatypeProperty → 属性，owl:ObjectProperty → 关系
- 命名空间感知：支持跨命名空间的实体引用
- 幂等导入：已存在的实体/关系自动跳过

### DatasourceUtils (`app/services/datasource_utils.py`)

数据源工具函数，供 Agent 和 API 共用。

- `get_connection()`：根据数据源类型创建数据库连接
- `list_tables()`：获取数据库所有表名
- `preview_table()`：查询表前 20 条数据
- `get_table_schema()`：查询表列元数据（列名/类型/主键/注释）
- `execute_readonly_sql()`：安全执行只读 SQL（禁止 DML/DDL，自动加 LIMIT，最大 200 行）

### AuditService (`app/services/audit.py`)

审计日志写入服务，`write_audit()` 函数记录所有操作。

---

## 前端架构

### 状态管理（Pinia Stores）

| Store | 文件 | 职责 |
|-------|------|------|
| `useOntologyStore` | `store/ontology.ts` | 实体列表、详情、图数据，按 Tier 分组 |
| `useRulesStore` | `store/rules.ts` | 规则列表、筛选、统计、执行 |
| `useAuthStore` | `store/auth.ts` | 用户认证、token 管理、权限检查 |
| `useCopilotStore` | `store/copilot.ts` | 对话消息、流式响应、会话管理 |
| `useDataSourceStore` | `store/datasource.ts` | 数据源列表、统计 |
| `useAuditStore` | `store/audit.ts` | 审计日志、分页查询 |
| `useThemeStore` | `store/theme.ts` | 暗色模式切换 |

### API 客户端（`src/api/`）

基于 Axios 封装，统一的请求/响应处理：

- `client.ts`：Axios 实例，baseURL `/api/v1`，JWT 拦截器，401 处理
- `ontology.ts`：实体 CRUD + 图数据 + 导入 + 数据源创建
- `relations.ts`：关系 CRUD
- `rules.ts`：规则 CRUD + 执行 + 评估
- `copilot.ts`：SSE 流式对话（async generator）+ 同步对话
- `datasource.ts`：数据源 CRUD + 连接测试 + 表操作
- `dashboard.ts`：看板统计
- `auth.ts`：登录/获取用户
- `audit.ts`：审计日志查询

### 组件体系

**通用组件（`components/common/`）：**
- `AppSidebar`：侧边栏导航
- `AppTopbar`：顶部栏（搜索、用户信息）
- `ModalDialog`：模态弹窗
- `EntityCard`：实体卡片（Tier 徽章 + 属性/关系/规则计数）
- `EntityCreateForm` / `EntityEditForm`：实体表单
- `TierBadge`：Tier 等级徽章
- `MetricCard`：指标卡片
- `ReasoningChain`：AI 推理链展示
- `SearchCommand`：全局搜索
- `ToastContainer`：消息提示
- `PageState`：页面状态（加载/空/错误）

**画布组件（`components/canvas/`）：**
- `OntologyNode`：自定义图节点
- `CanvasEdgeLabel`：自定义边标签
- `CanvasToolbar`：画布工具栏
- `CanvasNodePalette`：节点面板
- `CanvasConfigPanel`：配置面板
- `EntityLineageGraph`：血缘图谱

**场景组件（`components/mnp/`）：**
- `ProcessOrchTimeline`：流程编排时间线
- `EntityParticipantPanel`：实体参与面板
- `EntityMappingTable`：实体映射表
- `ActionDriverPanel`：动作驱动面板
- `RiskGraph`：风险图谱

### Composables

- `useGraphLayout`：dagre 图布局算法封装，将后端 GraphData 转换为 vue-flow 的 nodes/edges

### 样式系统

- CSS 变量主题系统：`--semantic-*`（蓝）、`--kinetic-*`（紫）、`--dynamic-*`（绿）
- Tier 专属色：T1 蓝 `#4c6ef5`、T2 紫 `#7950f2`、T3 绿 `#20c997`
- 暗色模式支持：`data-theme="dark"` 切换
- Scoped CSS：组件级样式隔离

---

## 项目结构

```
bonc-ontology/
├── README.md
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI 入口（CORS、路由注册、启动迁移、种子数据）
│   │   ├── config.py                  # 环境配置（数据库/Redis/Neo4j/LLM/JWT）
│   │   ├── database.py                # SQLAlchemy 引擎和会话工厂
│   │   ├── core/
│   │   │   ├── security.py            # JWT 生成/验证、bcrypt 密码哈希
│   │   │   └── deps.py                # FastAPI 依赖注入（当前用户提取）
│   │   ├── models/
│   │   │   ├── entity.py              # OntologyEntity + EntityAttribute
│   │   │   ├── relation.py            # EntityRelation
│   │   │   ├── rule.py                # BusinessRule + EntityAction
│   │   │   ├── user.py                # User
│   │   │   ├── audit.py               # AuditLog
│   │   │   └── datasource.py          # DataSource
│   │   ├── schemas/
│   │   │   ├── entity.py              # 实体/属性/关系/规则/动作/图数据 Schema
│   │   │   ├── rule.py                # 规则创建/更新/执行/评估 Schema
│   │   │   ├── datasource.py          # 数据源 CRUD/测试/表操作 Schema
│   │   │   └── auth.py                # 登录/Token/用户/角色权限 Schema
│   │   ├── api/v1/
│   │   │   ├── entities.py            # 实体 CRUD + 图数据 + 导入 + 数据源创建
│   │   │   ├── relations.py           # 关系 CRUD
│   │   │   ├── rules.py               # 规则 CRUD + 执行 + 评估
│   │   │   ├── copilot.py             # AI 对话（普通 + Agent）
│   │   │   ├── datasources.py         # 数据源管理
│   │   │   ├── dashboard.py           # 看板统计
│   │   │   └── auth.py                # 认证登录
│   │   └── services/
│   │       ├── copilot.py             # LLM 对话（本体上下文构建 + 流式/同步）
│   │       ├── agent_service.py       # Agent 编排（工具调用循环）
│   │       ├── agent_tools.py         # Agent 工具定义（9 个工具的 schema）
│   │       ├── rule_engine.py         # 规则引擎（FieldResolver + RuleEvaluator + ActionExecutor）
│   │       ├── file_import.py         # 文件导入（JSON + OWL/TTL）
│   │       ├── datasource_utils.py    # 数据源工具（连接/查表/预览/只读SQL）
│   │       ├── audit.py               # 审计日志写入
│   │       └── graph.py               # 图服务（Neo4j 相关）
│   ├── import_schema.py               # 独立脚本：JSON Schema 导入
│   ├── write_neo4j.py                 # 独立脚本：SQLite → Neo4j 同步
│   ├── test_import_v2.py              # 导入测试脚本
│   ├── test_schema_data.py            # Schema 数据测试
│   └── ontology.db                    # SQLite 数据库文件
├── frontend/
│   ├── package.json                   # 依赖和脚本
│   ├── vite.config.ts                 # Vite 配置（代理 /api → 后端）
│   ├── tsconfig.json                  # TypeScript 配置
│   └── src/
│       ├── App.vue                    # 应用外壳（侧边栏 + 顶栏 + 路由视图 + 状态栏）
│       ├── router/index.ts            # 路由配置（12 个路由）
│       ├── api/                       # API 客户端（8 个模块）
│       ├── store/                     # Pinia 状态管理（7 个 Store）
│       ├── types/                     # TypeScript 类型定义
│       ├── composables/               # 组合式函数（useGraphLayout）
│       ├── styles/                    # 全局样式和设计 Token
│       ├── components/
│       │   ├── common/                # 通用组件（15 个）
│       │   ├── canvas/                # 画布组件（6 个）
│       │   └── mnp/                   # 场景组件（5 个）
│       └── views/
│           ├── browser/               # 本体浏览器（Tab 容器）
│           ├── ontology/              # 本体管理（Explorer）
│           ├── dataflow/              # 关系画布
│           ├── logic/                 # 业务规则
│           ├── dashboard/             # 数据看板
│           ├── datasource/            # 数据源管理
│           ├── copilot/               # AI 对话
│           ├── detail/                # 实体详情
│           └── scene/                 # 场景分析（4 个场景）
└── 携号转网-v2.json                    # 携号转网场景的本体 Schema 文件
```

---

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- pnpm / npm

### 后端启动

```bash
cd backend

# 安装依赖
pip install fastapi uvicorn sqlalchemy pydantic-settings passlib[bcrypt] pyjwt openai pymysql psycopg2-binary

# 可选：OWL/TTL 导入支持
pip install rdflib

# 可选：Oracle / SQL Server 支持
pip install oracledb pymssql

# 启动服务（默认 0.0.0.0:8001）
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

启动后自动完成：
1. 创建 SQLite 数据库和所有表
2. 执行数据库迁移（新增列）
3. 创建默认管理员账户（admin / admin123）

### 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器（默认 http://localhost:5177）
npm run dev

# 构建生产版本
npm run build
```

### 导入本体数据

```bash
# 通过 API 导入 JSON Schema
curl -X POST http://localhost:8001/api/v1/entities/import \
  -F "file=@携号转网-v2.json" \
  -F "file_type=json" \
  -F "namespace=s5"
```

---

## 环境配置

后端通过 `.env` 文件或环境变量配置，所有配置项及默认值：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `DATABASE_URL` | `sqlite:///./ontology.db` | 数据库连接字符串 |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接（预留） |
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j 连接（可选） |
| `NEO4J_USER` | `neo4j` | Neo4j 用户名 |
| `NEO4J_PASSWORD` | `ontology123` | Neo4j 密码 |
| `SECRET_KEY` | `change-me-in-production` | JWT 签名密钥 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | Token 过期时间（分钟） |
| `LLM_API_BASE` | `https://coding.dashscope.aliyuncs.com/v1` | LLM API 地址 |
| `LLM_API_KEY` | (空) | LLM API Key |
| `LLM_MODEL` | `qwen3.5-plus` | LLM 模型名称 |
| `HOST` | `0.0.0.0` | 服务监听地址 |
| `PORT` | `8001` | 服务监听端口 |
| `DEBUG` | `true` | 调试模式 |

前端通过 `vite.config.ts` 配置：
- API 代理：`/api` → `http://127.0.0.1:8001`（通过 `BACKEND_URL` 环境变量覆盖）
- 开发端口：`5177`（通过 `FRONTEND_PORT` 环境变量覆盖）

---

## 文件导入规范

### JSON V1.1 本体规范

```json
{
  "scenario": {
    "name": "场景名称",
    "namespace": "s5",
    "description": "场景描述"
  },
  "object_types": [
    {
      "name": "EntityName",
      "display_name": "实体中文名",
      "tier": 3,
      "description": "实体描述",
      "primary_key": "user_id",
      "datasource_ref": "table_name",
      "properties": [
        {
          "name": "prop_name",
          "display_name": "属性中文名",
          "type": "string|number|boolean|datetime|enum|reference|array|object",
          "description": "属性描述",
          "required": true,
          "default": "默认值",
          "enum_values": ["A", "B"],
          "enum_labels": ["标签A", "标签B"],
          "min": 0,
          "max": 100,
          "pattern": "正则表达式",
          "indexed": true,
          "precision": 2
        }
      ],
      "computed_properties": [
        {
          "name": "computed_prop",
          "display_name": "计算属性名",
          "description": "描述",
          "expression": "SQL 表达式"
        }
      ]
    }
  ],
  "link_types": [
    {
      "name": "关系名称",
      "source_type": "SourceEntity",
      "target_type": "TargetEntity",
      "source_namespace": "s5",
      "target_namespace": "s5",
      "cardinality": "one_to_many|many_to_one|one_to_one|many_to_many",
      "acyclic": false,
      "description": "关系描述"
    }
  ],
  "business_rules": [
    {
      "name": "规则名称",
      "entity_name": "关联实体名",
      "condition_expr": "条件表达式文本",
      "action_desc": "动作描述文本",
      "priority": "high|medium|low",
      "rule_id": "规则编号",
      "risk_level": "high|medium|low",
      "conditions": [
        {
          "field": "EntityName.property",
          "display": "条件显示名",
          "operator": ">|<|>=|<=|==|!=|in|not_in|contains|exists",
          "value": "期望值",
          "resolve_type": "direct|count|computed",
          "since_days": 90
        }
      ]
    }
  ],
  "actions": [
    {
      "name": "动作中文名",
      "action_name": "ActionEnglishName",
      "entity_name": "关联实体名",
      "type": "auto_trigger|manual|scheduled",
      "parameters": [
        { "name": "param_name", "type": "string", "required": true, "description": "参数描述" }
      ],
      "preconditions": [
        { "expression": "EntityName EXISTS for field_name", "description": "前置条件描述" }
      ],
      "effects": [
        { "target": "EntityName.property", "action": "set|increment|append", "value": "值", "description": "效果描述" }
      ]
    }
  ]
}
```

---

## 二次开发指南

### 新增本体实体类型

无需修改代码，通过以下方式添加：
1. **界面操作**：本体管理 → 新建本体对象
2. **数据源导入**：数据源管理 → 选择表 → 创建实体
3. **文件导入**：准备 JSON/OWL 文件 → 调用导入 API

### 新增 API 端点

1. 在 `backend/app/api/v1/` 下创建路由文件
2. 在 `backend/app/main.py` 中注册路由：`app.include_router(new_router, prefix="/api/v1")`
3. 在 `backend/app/schemas/` 下定义请求/响应 Schema

### 新增数据模型

1. 在 `backend/app/models/` 下定义 SQLAlchemy 模型
2. 在 `backend/app/models/__init__.py` 中导出
3. 启动时自动建表（`Base.metadata.create_all`）
4. 如需迁移已有表，在 `main.py` 的 `lifespan()` 中添加 ALTER TABLE

### 新增前端页面

1. 在 `frontend/src/views/` 下创建 Vue 组件
2. 在 `frontend/src/router/index.ts` 中添加路由
3. 在 `frontend/src/components/common/AppSidebar.vue` 中添加导航项
4. 如需状态管理，在 `frontend/src/store/` 下创建 Pinia Store
5. 如需 API 调用，在 `frontend/src/api/` 下创建 API 模块

### 新增 Agent 工具

1. 在 `backend/app/services/agent_tools.py` 的 `AGENT_TOOL_SPECS` 中添加工具定义
2. 在 `backend/app/services/agent_service.py` 的 `_execute_tool()` 中添加执行逻辑
3. 工具自动注册到 LLM function calling 和前端工具目录

### 新增业务场景

1. 准备场景的本体 JSON Schema 文件
2. 通过导入 API 导入（指定 namespace）
3. 在 `backend/app/api/v1/entities.py` 的 `_SCENE_LAYER_MAP` 中添加层级映射
4. 在 `frontend/src/views/scene/` 下创建场景页面
5. 在路由中注册

### 替换 LLM

修改 `.env` 文件即可切换到任意 OpenAI 兼容接口的 LLM：

```env
LLM_API_BASE=https://your-llm-api.com/v1
LLM_API_KEY=your-api-key
LLM_MODEL=your-model-name
```

### 切换数据库

修改 `DATABASE_URL` 即可切换到 PostgreSQL / MySQL 等：

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/ontology
DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/ontology
```

---

## License

MIT
