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
- [系统截图](#系统截图)
- [系统架构](#系统架构)
- [技术栈](#技术栈)
- [功能模块](#功能模块)
- [API 接口](#api-接口)
- [快速开始](#快速开始)
- [环境配置](#环境配置)
- [二次开发](#二次开发)

---

## 项目概述

传统运营系统面临的核心痛点：业务规则散落在代码中、数据关系隐藏在表结构里、策略决策依赖人工经验。

本平台通过 **本体建模** 将业务领域知识结构化为三层对象体系（核心层 → 领域层 → 场景层），结合知识图谱可视化、声明式规则引擎、多数据源集成和 AI Copilot 智能问答，实现从数据到洞察到行动的闭环。

### 核心能力

- **本体建模**：三层 Tier 架构（核心/领域/场景），支持实体、属性、关系、规则、动作全生命周期管理
- **双层知识图谱**：本体层（实体关系网络）+ 数据层（真实数据节点）交织可视化，基于 vue-flow + D3-force 布局
- **声明式规则引擎**：条件表达式 + 结构化条件双模式，支持真实数据源评估、置信度计算、风险等级判定
- **AI 智能问答**：双模式 Copilot（普通对话 + Agent 工具调用），本体感知上下文注入，SSE 流式响应
- **多数据源集成**：支持 MySQL / PostgreSQL / Oracle / SQL Server，自动发现表结构，从数据表一键生成本体实体
- **智能编排**：可视化工作流画布，拖拽式节点编排，支持智能体创建与发布
- **场景化分析**：内置携号转网预警、FTTR 续约策划、宽带退单稽核、政企根因分析四大电信运营场景
- **审计追踪**：全操作审计日志，记录变更快照，支持回溯

---

## 系统截图

![系统总览](docs/images/screenshot-1.png)

![本体图谱](docs/images/screenshot-2.png)

![智能编排](docs/images/screenshot-3.png)

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Frontend (Vue 3 + TypeScript)                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐ │
│  │ 本体管理  │ │ 知识图谱  │ │ 业务规则  │ │ 智能编排  │ │ AI Copilot│ │
│  │ Explorer │ │ vue-flow │ │  Logic   │ │ Harness  │ │  Agent    │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └─────┬─────┘ │
│                    Pinia Store + Axios (JWT + SSE)                   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP / SSE
┌──────────────────────────────┴──────────────────────────────────────┐
│                      Backend (FastAPI + Uvicorn)                      │
│  entities · relations · rules · copilot · datasources · agents       │
│  dashboard · auth · audit                                            │
│  CopilotService · AgentService · RuleEngine · FileImportService      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ SQLAlchemy ORM
┌──────────────────────────────┴──────────────────────────────────────┐
│                    MySQL（生产）/ SQLite（开发）                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端框架 | Vue 3.5 + TypeScript 6 | Composition API + `<script setup>` |
| 构建工具 | Vite 8 | HMR 热更新，代理后端 API |
| 状态管理 | Pinia 3 | 7 个 Store |
| 图可视化 | vue-flow 1.48 + D3-force | 交互式画布 + 力导向布局 |
| HTTP 客户端 | Axios 1.15 | JWT 拦截器 + SSE 流式解析 |
| 后端框架 | FastAPI 0.115 + Uvicorn | ASGI 异步服务器 |
| ORM | SQLAlchemy 2.0 | Mapped 声明式模型 |
| 数据验证 | Pydantic 2.11 | 请求/响应 Schema |
| 认证 | JWT (PyJWT) + Passlib (bcrypt) | Bearer Token |
| 数据库 | MySQL（生产）/ SQLite（开发） | 通过 DATABASE_URL 切换 |
| LLM | OpenAI 兼容接口 | 可替换任意 LLM |
| 数据源驱动 | pymysql / psycopg2 / oracledb / pymssql | 多数据库连接 |

---

## 功能模块

### 1. 本体管理（`/browser`）

三层 Tier 架构管理所有业务实体：

| Tier | 定位 | 示例 |
|------|------|------|
| Tier 1 核心层 | 业务基础实体 | 客户、订单、产品 |
| Tier 2 领域层 | 运营领域概念 | 营销活动、客户分群、策略 |
| Tier 3 场景层 | 场景专属对象 | 携转预警、FTTR订阅、退单工单 |

- 实体 CRUD：创建/编辑/删除，支持搜索过滤
- 属性管理：类型支持 string / number / boolean / date / json / ref / computed
- 关系管理：1:1 / 1:N / N:1 / N:N 基数，可视化血缘图谱（BFS 1-3 跳）
- 规则 & 动作：查看关联规则，手动触发动作
- 文件导入：支持 JSON / OWL / TTL 格式批量导入本体
- AI 提取：上传文档自动提取实体结构

### 2. 知识图谱（`/browser/graph`）

基于 vue-flow + D3-force 的双层交织可视化画布：

- **本体层**：实体节点（按 Tier 着色：T1 蓝 / T2 紫 / T3 绿）+ 贝塞尔关系边
- **数据层**：每个实体对应的真实数据节点（表名、记录数、字段数），虚线边连接
- 工具栏：数据层开关、布局方向切换、适应视口
- 小地图：右下角缩略图，支持拖拽导航
- 节点交互：拖拽、点击选中、hover 高亮、右侧详情面板

### 3. 业务规则（`/browser/rules`）

声明式规则引擎，将业务逻辑从代码中解耦：

- 规则列表：按状态（active/inactive）、优先级（high/medium/low）、关键词筛选
- 创建/编辑规则：条件表达式 + 结构化条件 JSON 双模式
- 手动执行：触发规则，记录执行次数和最后触发时间
- 规则评估：对指定用户 ID 评估，返回匹配明细、置信度（0-1）、风险等级

### 4. 数据源管理（`/datasource`）

外部数据库连接管理，支持 MySQL / PostgreSQL / Oracle / SQL Server：

- 创建数据源：输入连接信息，自动发现所有表
- 连接测试、表结构查看、数据预览（前 20 条）
- 启用/禁用、刷新记录数
- 从数据源一键生成本体实体（自动映射列类型）

### 5. 智能编排（`/harness`、`/agents`）

可视化工作流画布，拖拽式节点编排：

- 工作流画布：节点拖拽、连线、删除，支持浅色/深色主题
- 智能体管理：卡片网格展示，点击进入详情画布
- 智能体详情：独立编排画布 + 设置面板，节点/边持久化到数据库
- 模型管理：LLM 模型注册与配置（`/orchestration/models`）

### 6. AI 智能问答（`/copilot`）

集成 LLM 的本体感知对话助手：

- **普通对话**：自动注入本体上下文（实体/关系/规则/数据源），SSE 流式输出
- **Agent 模式**：LLM + 工具调用循环（最多 8 轮），工具包括：
  - `describe_ontology_model`：查询本体结构
  - `query_datasource`：安全执行只读 SQL（自动 LIMIT，禁止 DML/DDL）
  - `query_entity_data`：按实体查询关联数据源
  - `evaluate_rule` / `evaluate_all_rules`：规则评估
  - `execute_action`：执行业务动作

### 7. 场景分析（`/scene`）

四大电信运营场景：

| 场景 | 路由 | 说明 |
|------|------|------|
| 携号转网预警 | `/scene/mnp` | 风险图谱、实体映射、流程编排时间线 |
| FTTR 续约策划 | `/scene/fttr` | 续约策略分析 |
| 宽带退单稽核 | `/scene/broadband` | 退单列表、统计、智能收件箱、详情 |
| 政企根因分析 | `/scene/enterprise` | 根因定位与分析 |

### 8. 数据看板（`/dashboard`）

- KPI 指标卡：实体总数、关系总数、规则总数、活跃规则数
- Tier 分布统计、对象健康状态、近期操作活动

### 9. 系统治理（`/governance`）

- 审计日志：全操作记录，含变更快照
- 权限管理：角色（admin / editor / viewer）
- API 开放平台（`/app/api`）

---

## API 接口

### 实体 `/api/v1/entities`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 列表（支持 tier/status/search/namespace 过滤） |
| POST | `/` | 创建实体 |
| GET/PUT/DELETE | `/{id}` | 详情 / 更新 / 删除（级联删除属性/规则/动作） |
| GET | `/graph` | 全量图谱（节点+边） |
| GET | `/data-layer` | 数据层映射（实体→表→数据源） |
| GET | `/{id}/lineage` | 血缘图谱（BFS，支持深度控制） |
| POST | `/ai-extract` | AI 自动提取实体 |
| POST | `/import-from-datasource` | 从数据源导入实体 |

### 关系 `/api/v1/relations`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/` | 列表 / 创建 |
| DELETE | `/{id}` | 删除关系 |

### 规则 `/api/v1/rules`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/` | 列表 / 创建 |
| PUT/DELETE | `/{id}` | 更新 / 删除 |
| POST | `/{id}/execute` | 执行规则 |
| POST | `/{id}/evaluate` | 评估规则（真实数据源） |

### 数据源 `/api/v1/datasources`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/` | 列表 / 创建（自动发现所有表） |
| POST | `/test` | 测试连接 |
| POST | `/fetch-tables` | 获取表列表 |
| POST | `/{id}/toggle` | 启用/禁用 |
| POST | `/{id}/refresh-tables` | 刷新记录数 |
| GET | `/{id}/preview` | 数据预览 |
| GET | `/{id}/tables/{table}/schema` | 表结构 |

### AI 对话 `/api/v1/copilot`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/chat` | 普通对话（SSE 流式） |
| POST | `/agent-chat` | Agent 工具调用（SSE 流式） |

### 智能体 `/api/v1/agents`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/` | 列表 / 创建 |
| GET/PUT/DELETE | `/{id}` | 详情 / 更新 / 删除 |
| POST | `/{id}/run` | 执行工作流（SSE 流式） |

### 其他

| 路径 | 说明 |
|------|------|
| POST `/api/v1/auth/login` | 用户登录，返回 JWT |
| GET `/api/v1/auth/me` | 当前用户信息 |
| GET `/api/v1/dashboard/stats` | 全局统计 |
| GET `/api/health` | 健康检查 |

---

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- pnpm / npm

### 后端启动

```bash
cd backend

pip install fastapi uvicorn sqlalchemy pydantic-settings passlib[bcrypt] pyjwt openai pymysql psycopg2-binary

# 可选
pip install rdflib oracledb pymssql

uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

启动后自动完成：建表、数据库迁移、创建默认管理员（admin / admin123）

### 前端启动

```bash
cd frontend
pnpm install
pnpm dev
```

访问 `http://localhost:5173`，后端代理到 `http://localhost:8001`。

### 一键启动（Windows）

```bat
start.bat
```

---

## 环境配置

`backend/.env`：

```env
DATABASE_URL=mysql+pymysql://user:pass@host:port/ontology_platform?charset=utf8mb4
LLM_API_BASE=https://your-llm-api.com/v1
LLM_API_KEY=your-api-key
LLM_MODEL=your-model-name
SECRET_KEY=your-secret-key
```

切换数据库只需修改 `DATABASE_URL`，支持 SQLite / MySQL / PostgreSQL。

---

## 二次开发

### 新增 API 路由

1. 在 `backend/app/api/v1/` 下创建路由文件
2. 在 `backend/app/main.py` 中注册：`app.include_router(router, prefix="/api/v1")`

### 新增数据模型

1. 在 `backend/app/models/` 下定义 SQLAlchemy 模型
2. 在 `backend/app/models/__init__.py` 中导出
3. 启动时自动建表；如需迁移已有表，在 `main.py` 的 `lifespan()` 中添加 ALTER TABLE

### 新增前端页面

1. 在 `frontend/src/views/` 下创建 Vue 组件
2. 在 `frontend/src/router/index.ts` 中添加路由
3. 在 `frontend/src/components/common/AppSidebar.vue` 中添加导航项

### 新增 Agent 工具

1. 在 `backend/app/services/agent_tools.py` 的 `AGENT_TOOL_SPECS` 中添加工具定义
2. 在 `backend/app/services/agent_service.py` 的 `_execute_tool()` 中添加执行逻辑

### 替换 LLM

修改 `.env` 即可切换到任意 OpenAI 兼容接口：

```env
LLM_API_BASE=https://your-llm-api.com/v1
LLM_API_KEY=your-api-key
LLM_MODEL=your-model-name
```

---

## License

MIT
