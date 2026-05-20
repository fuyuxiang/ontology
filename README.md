<div align="center">

# 元枢 Ontology · 企业级本体智能平台

**Yuanshu Ontology — Enterprise Ontology Intelligence Platform**

*以本体为锚 · 以语义为网 · 让数据可懂 · 让 AI 可信*

[![Vue 3](https://img.shields.io/badge/Vue-3.5-4FC08D?logo=vue.js)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-6.x-3178C6?logo=typescript)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://python.org/)
[![OWL](https://img.shields.io/badge/W3C-OWL-005A9C)](https://www.w3.org/OWL/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 概述

**元枢 Ontology** 是一款面向企业数据治理与智能应用构建的本体智能平台。平台以"**语义层 · 动力层 · 动态层**"三层架构为核心，将分散在业务系统、数据库与流程中的对象、关系、规则、动作与智能体统一组织，形成可查询、可分析、可执行、可持续演进的企业语义网络，让数据从"看得见的表"进化为"用得起的知识"，驱动数据治理、规则推理与智能体应用一体协同。

> 💡 适用场景：数据资产治理 · 业务对象建模 · 智能体应用构建 · 规则驱动分析 · 场景化运营 · 跨系统能力编排。

<details>
<summary><b>📖 目录</b></summary>

- [核心理念](#核心理念)
- [核心能力](#核心能力)
- [系统架构](#系统架构)
- [功能模块](#功能模块)
  - [本体中心](#本体中心)
  - [逻辑中心](#逻辑中心)
  - [本体服务](#本体服务)
  - [业务场景](#业务场景)
  - [运营观测](#运营观测)
  - [系统设置](#系统设置)
- [AI Copilot](#ai-copilot)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [环境配置](#环境配置)
- [API 文档](#api-文档)
- [项目结构](#项目结构)
- [二次开发](#二次开发)
- [License](#license)

</details>

---

## 核心理念

元枢的设计目标是让企业数据从静态表结构进入业务语义空间，使数据、规则、流程和 AI 应用能够围绕统一的业务对象协同工作。

平台采用三层架构：

```text
┌──────────────────────────────────────────────┐
│                动态层 Dynamic Layer           │
│  场景运行 / Agent 编排 / 流程执行 / 反馈闭环     │
├──────────────────────────────────────────────┤
│                动力层 Power Layer             │
│  规则 / 函数 / 动作 / 服务接口 / 工作流          │
├──────────────────────────────────────────────┤
│                语义层 Semantic Layer          │
│  实体 / 属性 / 关系 / 映射 / 数据对象            │
└──────────────────────────────────────────────┘
```

### 语义层

语义层负责定义企业的核心业务对象及其关系。

它将数据库表、字段、接口数据和业务概念映射为统一的对象模型，解决跨系统数据口径不一致、对象识别困难、字段含义不清晰等问题。

主要能力包括：

- 实体、属性、关系建模
- 业务对象图谱
- 数据源接入与字段映射
- 实体解析与 ID 归一
- 数据血缘与对象关系追踪

### 动力层

动力层负责描述对象之上的业务逻辑和执行能力。

它将规则、函数、动作、API 和工作流组织为可复用的能力单元，使本体不只用于查询和展示，也可以驱动业务判断、流程执行和系统调用。

主要能力包括：

- 规则配置与评估
- 函数计算与派生属性
- 业务动作封装
- API 服务发布
- SDK 生成
- 可视化流程编排

### 动态层

动态层负责面向具体场景的运行、编排和反馈。

它将语义对象和业务能力提供给 Copilot、Agent、工作流和场景应用使用，支持基于上下文的分析、推理、执行和追踪。

主要能力包括：

- Copilot 对话
- Agent 工具调用
- 场景化业务应用
- 工作流执行
- 运行追踪
- 评测与监控

---

## 核心能力

| 🧱 建模与接入 | ⚙️ 逻辑与执行 | 🚀 服务与运营 |
|---|---|---|
| **本体建模** — 实体、属性、关系与对象图谱统一治理 | **规则动作** — 声明式规则、计算函数与可执行动作 | **服务输出** — API 服务、OSDK 生成、Agent 接口三种赋能形态 |
| **数据接入** — 多源数据库连接、表发现与字段映射 | **流程编排** — 拖拽式可视化工作流，支持节点 / 连线 / 主题切换 | **场景应用** — 携号转网、FTTR、宽带退单、政企根因等行业样板 |
| **实体解析** — 跨源对象识别、ID 归一与冲突仲裁 | **AI Copilot** — 对话模式 + Agent 模式，本体上下文感知 | **治理运维** — 版本发布、审批、回滚、审计、追踪与 Agent 评测 |

---

## 系统架构

```text
┌───────────────────────────────────────────────────────────────┐
│                          Frontend                              │
│   Vue 3 · TypeScript · Vite · Pinia · Ant Design Vue · VueFlow │
│   本体建模 / 数据映射 / 流程编排 / 场景应用 / 运行观测            │
└───────────────────────────┬───────────────────────────────────┘
                            │ HTTP · SSE · JWT
┌───────────────────────────┴───────────────────────────────────┐
│                          Backend                               │
│   FastAPI · SQLAlchemy · Pydantic · Uvicorn                    │
│   ┌────────────┬─────────────┬─────────────┬───────────────┐  │
│   │ Rule Engine│Agent Service│Workflow Svc │ OSDK Generator│  │
│   └────────────┴─────────────┴─────────────┴───────────────┘  │
│   对象管理 / 规则评估 / 动作执行 / Agent 调用 / 审计 / API 服务   │
└───────┬─────────────────────────┬─────────────────────┬───────┘
        │                         │                     │
┌───────┴────────┐    ┌───────────┴────────────┐ ┌──────┴──────┐
│  Metadata DB   │    │   External Data Sources│ │     LLM     │
│ SQLite / MySQL │    │ MySQL · PostgreSQL ·   │ │ OpenAI-     │
│ 模型 / 版本快照 │    │ Oracle · SQL Server    │ │ compatible  │
└────────────────┘    └────────────────────────┘ └─────────────┘
```

| 组件 | 职责 |
|------|------|
| **Frontend** | 本体建模、数据映射、流程编排、场景应用与运行观测等全部交互能力 |
| **Backend** | 对象管理、规则评估、动作执行、Agent 调用、SDK 生成、权限审计与 API 服务 |
| **Metadata Database** | 保存本体模型、映射关系、规则配置、版本快照与运行记录 |
| **External Data Sources** | 通过连接器接入业务库，支撑数据发现、字段映射、查询预览与实体解析 |
| **LLM** | 通过 OpenAI 兼容协议接入，驱动 Copilot、Agent 与智能建模能力 |

---

## 功能模块

平台共六大功能域，与左侧导航一一对应。

### 本体中心

> 建设企业统一语义模型——从原始数据到可消费的知识对象。

| 模块 | 路由 | 能力简述 |
|------|------|----------|
| 数据工坊 | `/datasource` | 数据接入 / 数据管道 / 水合演练 三 Tab 一站式 |
| 本体建模 | `/browser` | 三层 Tier 实体 CRUD、属性、关系、AI 提取与批量导入 |
| 本体工作室 | `/studio` | 卡片视图 + 三盒视图，呈现对象、实例规模与规则覆盖 |
| 本体图谱 | `/browser/graph` | 双层交织画布：本体层 + 数据层，力导向布局与血缘 BFS |
| 本体映射 | `/data/mapping` | 本体字段 ↔ 物理字段映射、覆盖率统计 |
| 实体解析 | `/data/resolution` | ID 归一与冲突仲裁，支撑跨源同名实体识别 |
| 本体发布 | `/ontology/publish` | 草稿 → 校验 → 审批 → 上线 / 回滚，全过程留痕 |

### 逻辑中心

> 让规则与函数成为本体的一部分——业务逻辑可被推理、被调用、被复用。

| 模块 | 路由 | 能力简述 |
|------|------|----------|
| Actions 管理 | `/logic/actions` | 业务动作的参数 Schema、前置条件与手动触发 |
| Functions 管理 | `/logic/functions` | 派生属性 / 计算函数定义，支持入参 Schema 与单元测试 |
| Rules 管理 | `/logic/rules` | 声明式规则：条件表达式 + 结构化条件双模式 |

### 本体服务

> 把平台能力开放给外部系统与智能体——本体即接口，能力即服务。

| 模块 | 路由 | 能力简述 |
|------|------|----------|
| API 服务 | `/service/api` | 基于本体自动生成对外 REST 接口 |
| OSDK 生成 | `/service/osdk` | 一键产出 TypeScript / Python SDK |
| Agent 交互 | `/service/agent` | 智能体卡片网格 + 详情画布，节点 / 边持久化 |
| 流程编排 | `/service/workflow` | 拖拽式可视化工作流画布 |

### 业务场景

> 即开即用的行业样板，可作 Demo 亦可作底座。

| 场景 | 路由 | 能力点 |
|------|------|--------|
| 携号转网预警 | `/scene/mnp` | 风险图谱 + 实体映射 + 流程编排时间线 |
| FTTR 续约策划 | `/scene/fttr` | 续约策略与价值分析 |
| 宽带退单稽核 | `/scene/broadband` | 列表 + 统计大屏 + 智能收件箱 + 详情四件套 |
| 政企根因分析 | `/scene/enterprise` | 关联实体聚合的根因定位 |

### 运营观测

> 让 AI 可解释、可衡量、可追溯。

| 模块 | 路由 | 能力简述 |
|------|------|----------|
| 本体试车场 | `/harness` | 本体能力沙箱，端到端验证规则、动作、Copilot 行为 |
| Agent 评测 | `/ops/evals` | 评测套件 / 用例管理、批量执行与结果对比 |
| 运行追踪 | `/ops/traces` | 全链路 Trace，下钻到工具调用与 Token 消耗 |

### 系统设置

> 治理与运维——让平台稳得住、管得清。

| 模块 | 路由 | 能力简述 |
|------|------|----------|
| 模型管理 | `/settings/models` | LLM 模型注册、Endpoint / Key 配置 |
| 权限审计 | `/governance/audit` | 全操作审计日志 + 变更快照 |
| 运维监控 | `/settings/monitor` | 资源指标、服务状态、安全事件、系统信息 |
| 系统配置 | `/settings/general` | 角色（admin / editor / viewer）与平台参数 |

---

## AI Copilot

Copilot 是贯穿平台的智能助手能力。它可以读取本体上下文、数据源摘要、实体关系、规则配置与运行结果，辅助用户完成对象查询、规则分析、流程解释与场景决策。

| 模式 | 适用场景 |
|------|----------|
| **对话模式** | 自然语言问答、对象解释、规则说明、数据口径查询、场景分析 |
| **Agent 模式** | 工具调用与任务执行——Agent 自主完成数据查询、实体解析、规则评估、动作触发与流程编排 |

### Agent 工具矩阵

| 类别 | 工具 | 说明 |
|------|------|------|
| 🧩 **本体** | `describe_ontology_model` · `get_entity_detail` | 查询本体 Schema 与实体详情 |
| 🗄️ **数据源** | `list_datasources` · `get_table_schema` · `query_datasource` | 数据源、表结构与只读 SQL 查询（自动 LIMIT，禁止 DML/DDL） |
| 📊 **实例** | `query_entity_data` | 按实体查询关联数据源中的实例数据 |
| 📐 **规则** | `get_business_rules` · `evaluate_rule` · `evaluate_all_rules` · `screen_users_by_rule` | 规则查询、单规则与全量评估、人群筛选 |
| ⚡ **动作** | `execute_action` | 触发预定义业务动作 |

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 🎨 **前端框架** | Vue 3 + TypeScript | Composition API + `<script setup>` |
| 🛠️ **构建 / 状态** | Vite + Pinia | HMR 热更新 · 多 Store 状态管理 |
| 🧱 **UI / 可视化** | Ant Design Vue + Vue Flow | 企业级控件 · 双层力导向画布 |
| 🌐 **HTTP / 流** | Axios | JWT 自动注入 · SSE 流式解析 |
| 🚀 **后端框架** | FastAPI + Uvicorn | ASGI · 异步 IO · OpenAPI 自动文档 |
| 🗃️ **ORM / 校验** | SQLAlchemy 2.0 + Pydantic 2 | Mapped 声明式模型 · 类型安全 Schema |
| 🔐 **认证** | PyJWT + Passlib (bcrypt) | Bearer Token · 角色权限 |
| 💾 **元数据库** | SQLite / MySQL | 通过 `DATABASE_URL` 一键切换 |
| 🔌 **外部数据源** | MySQL · PostgreSQL · Oracle · SQL Server | pymysql / psycopg2 / oracledb / pymssql |
| 🤖 **LLM** | OpenAI 兼容协议 | 任意厂商，支持工具调用、SSE 流式与执行链路追踪 |

---

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- pnpm 9+ 或 npm 10+
- 可选：MySQL 8

### 启动后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

安装核心依赖：

```bash
pip install fastapi uvicorn sqlalchemy pydantic-settings \
            passlib[bcrypt] pyjwt openai \
            pymysql psycopg2-binary
```

可选数据源依赖：

```bash
pip install rdflib oracledb pymssql
```

后端启动后，接口文档地址为：

```text
http://localhost:8001/docs
```

> 💡 启动时自动完成建表 · 数据库迁移 · 创建默认管理员 `admin / admin123`，开箱即用。

### 启动前端

```bash
cd frontend
pnpm install
pnpm dev
```

前端访问地址：

```text
http://localhost:5173
```

开发环境下，前端请求会代理到后端服务：

```text
http://localhost:8001
```

### 一键脚本

Windows：

```bash
start.bat
stop.bat
ctl.bat
```

macOS / Linux：

```bash
./start.sh
./stop.sh
./restart.sh
```

---

## 环境配置

后端配置文件位于：

```text
backend/.env
```

示例配置：

```env
# 元数据库
DATABASE_URL=sqlite:///./ontology.db

# MySQL 示例
# DATABASE_URL=mysql+pymysql://user:password@host:3306/ontology_platform?charset=utf8mb4

# LLM
LLM_API_BASE=https://your-llm-api.com/v1
LLM_API_KEY=your-api-key
LLM_MODEL=your-model-name

# 安全配置
SECRET_KEY=replace-with-strong-random-string
```

生产环境建议：

> ⚠️ **生产部署清单**
> - 使用 **MySQL** 作为元数据库（避免 SQLite 并发瓶颈）
> - 使用强随机值配置 `SECRET_KEY`，建议通过 `openssl rand -hex 32` 生成
> - 通过密钥管理服务（KMS / Vault）管理数据库密码与模型服务 Key
> - **务必修改默认管理员账号和密码**（`admin / admin123`）
> - 开启审计、访问日志与基于角色的访问控制

---

## API 文档

后端启动后访问 Swagger UI：

```text
http://localhost:8001/docs
```

所有业务接口默认挂载在：

```text
/api/v1
```

> 💡 平台后端共注册 28 个路由域，覆盖本体、数据、规则、动作、Agent、Copilot、版本发布、运维监控等全部能力。详细接口以 Swagger UI 和后端路由定义为准。

---

## 项目结构

```text
.
├── backend
│   ├── app
│   │   ├── api
│   │   ├── models
│   │   ├── services
│   │   ├── schemas
│   │   └── main.py
│   └── .env
│
├── frontend
│   ├── src
│   │   ├── views
│   │   ├── components
│   │   ├── router
│   │   ├── stores
│   │   └── main.ts
│   └── package.json
│
├── docs
└── README.md
```

---

## 二次开发

常见扩展方向包括：

- 新增业务实体和关系
- 新增数据源连接器
- 新增规则类型
- 新增业务动作
- 新增 Agent 工具
- 新增行业场景页面
- 新增外部系统 API 集成

建议将详细开发说明维护在：

```text
docs/development.md
```

---

## License

MIT © 元枢 Ontology
