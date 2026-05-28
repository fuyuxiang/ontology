<div align="center">

# 元枢 Ontology · 企业级本体智能平台

*以本体为锚 · 以语义为网 · 让数据可懂 · 让 AI 可信*

**[English](README.md)** | **[中文](README.zh-CN.md)**

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
- [AI Copilot](#ai-copilot)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [环境配置](#环境配置)
- [项目结构](#项目结构)
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

**语义层** — 定义企业的核心业务对象及其关系。将数据库表、字段、接口数据和业务概念映射为统一的对象模型。能力：实体/属性/关系建模 · 业务对象图谱 · 数据源接入与字段映射 · 实体解析与 ID 归一 · 数据血缘追踪

**动力层** — 描述对象之上的业务逻辑和执行能力。将规则、函数、动作、API 和工作流组织为可复用的能力单元。能力：规则配置与评估 · 函数计算与派生属性 · 业务动作封装 · API 服务发布 · SDK 生成 · 可视化流程编排

**动态层** — 面向具体场景的运行、编排和反馈。将语义对象和业务能力提供给 Copilot、Agent、工作流和场景应用使用。能力：Copilot 对话 · Agent 工具调用 · 场景化业务应用 · 工作流执行 · 运行追踪 · 评测与监控

---

## 核心能力

| 🧱 建模与接入 | ⚙️ 逻辑与执行 | 🚀 服务与运营 |
|---|---|---|
| **本体建模** — 实体、属性、关系与对象图谱统一治理 | **规则动作** — 声明式规则、计算函数与可执行动作 | **服务输出** — API 服务、OSDK 生成、Agent 接口三种赋能形态 |
| **数据接入** — 多源数据库连接、表发现与字段映射 | **流程编排** — 拖拽式可视化工作流，支持节点 / 连线 / 主题切换 | **场景应用** — 携号转网、FTTR、宽带退单、政企根因等行业样板 |
| **水合验证** — 发布前 4 阶段真实数据端到端校验 | **AI Copilot** — 对话模式 + Agent 模式，本体上下文感知 | **治理运维** — 版本发布、审批、回滚、审计、追踪与 Agent 评测 |

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
│   对象管理 / 规则评估 / 动作执行 / Agent 调用 / 审计 / API 服务   │
└───────┬─────────────────────────┬─────────────────────┬───────┘
        │                         │                     │
┌───────┴────────┐    ┌───────────┴────────────┐ ┌──────┴──────┐
│  Metadata DB   │    │   External Data Sources│ │     LLM     │
│ SQLite / MySQL │    │ MySQL · PostgreSQL ·   │ │ OpenAI-     │
│ 模型 / 版本快照 │    │ Oracle · SQL Server    │ │ compatible  │
└────────────────┘    └────────────────────────┘ └─────────────┘
```

---

## 功能模块

### 本体中心

| 模块 | 路由 | 能力简述 |
|------|------|----------|
| 数据工坊 | `/datasource` | 数据接入 / 数据管道 / 水合演练 |
| 本体建模 | `/browser` | 三层 Tier 实体 CRUD、属性、关系、AI 提取与批量导入 |
| 本体工作室 | `/studio` | 卡片视图 + 三盒视图，呈现对象、实例规模与规则覆盖 |
| 本体图谱 | `/browser/graph` | 双层交织画布：本体层 + 数据层，力导向布局与血缘 BFS |
| 本体映射 | `/data/mapping` | 本体字段 ↔ 物理字段映射、覆盖率统计 |
| 实体解析 | `/data/resolution` | ID 归一与冲突仲裁，支撑跨源同名实体识别 |
| 本体发布 | `/ontology/publish` | 草稿 → 校验 → 审批 → 上线 / 回滚，全过程留痕 |

#### 本体构建器（4 步流水线）

```text
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Step 1     │    │   Step 2     │    │   Step 3     │    │   Step 4     │
│   构建本体    │ →  │   走测审批    │ →  │   水合验证    │ →  │   发布上线    │
│              │    │              │    │              │    │              │
│ · 手工建模   │    │ · 逐对象审核  │    │ · 数据接入   │    │ · 版本冻结   │
│ · 文件导入   │    │ · 主键校验   │    │ · 字段映射   │    │ · 7 道门禁   │
│ · 文档抽取   │    │ · 规则/动作   │    │ · 关系 JOIN  │    │ · 消费方对接  │
│ · 对话生成   │    │   建议处理   │    │ · PK/空值率  │    │ · 回滚方案   │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

**水合验证**（Hydration Drill）是发布前的关键质量门禁，通过 SSE 流式调用后端 4 阶段验证：

1. **数据接入** — 验证连接器可达性、同步 schema、采样 preview、计算 profile
2. **本体实例化** — 启发式打分（token Jaccard + 模糊匹配 + 类型相容）+ LLM 兜底映射
3. **关系映射验证** — JOIN key 存在性检查、同连接样本 JOIN 查询
4. **策略输出** — 主键唯一性校验、必填字段空值率检查

### 数据集成

| 模块 | 路由 | 能力简述 |
|------|------|----------|
| 数据接入 | `/data/connections` | MySQL / PostgreSQL / Oracle / SQL Server / Hive / ClickHouse / S3 / FTP / Kafka / REST |
| 资产目录 | `/data/assets` | 数据资产注册、schema 自动同步、profile 分析、preview 预览 |
| 数据血缘 | `/data/lineage` | 端到端血缘追踪，支持列级映射可视化 |
| 数据质量 | `/data/quality` | 质量规则定义、探针执行、质量指标监控 |
| 字段映射 | `/data/mapping` | 本体属性 ↔ 物理列的半自动映射推荐（启发式 + LLM） |
| 执行审计 | `/data/audit` | SQL 执行审计日志、限流、脱敏 |

**连接器能力矩阵：**

| 连接器 | Schema 发现 | 数据预览 | Profile | SQL 执行 |
|--------|:-----------:|:--------:|:-------:|:--------:|
| MySQL | ✅ | ✅ | ✅ | ✅ |
| PostgreSQL | ✅ | ✅ | ✅ | ✅ |
| Oracle | ✅ | ✅ | ✅ | ✅ |
| SQL Server | ✅ | ✅ | ✅ | ✅ |
| Hive | ✅ | ✅ | ✅ | ✅ |
| ClickHouse | ✅ | ✅ | ✅ | ✅ |
| S3 | - | ✅ | - | - |
| FTP/SFTP | - | ✅ | - | - |
| Kafka | - | ✅ | - | - |
| REST API | - | ✅ | - | - |

### 逻辑中心

| 模块 | 路由 | 能力简述 |
|------|------|----------|
| Actions 管理 | `/logic/actions` | 业务动作的参数 Schema、前置条件与手动触发 |
| Functions 管理 | `/logic/functions` | 派生属性 / 计算函数定义，支持入参 Schema 与单元测试 |
| Rules 管理 | `/logic/rules` | 声明式规则：条件表达式 + 结构化条件双模式 |

### 本体服务

| 模块 | 路由 | 能力简述 |
|------|------|----------|
| API 服务 | `/service/api` | 基于本体自动生成对外 REST 接口 |
| OSDK 生成 | `/service/osdk` | 一键产出 TypeScript / Python SDK |
| Agent 交互 | `/service/agent` | 智能体卡片网格 + 详情画布，节点 / 边持久化 |
| 流程编排 | `/service/workflow` | 拖拽式可视化工作流画布 |

### 业务场景

| 场景 | 路由 | 能力点 |
|------|------|--------|
| 携号转网预警 | `/scene/mnp` | 风险图谱 + 实体映射 + 流程编排时间线 |
| FTTR 续约策划 | `/scene/fttr` | 续约策略与价值分析 |
| 宽带退单稽核 | `/scene/broadband` | 列表 + 统计大屏 + 智能收件箱 + 详情四件套 |
| 政企根因分析 | `/scene/enterprise` | 关联实体聚合的根因定位 |

### 运营观测

| 模块 | 路由 | 能力简述 |
|------|------|----------|
| 本体试车场 | `/harness` | 本体能力沙箱，端到端验证规则、动作、Copilot 行为 |
| Agent 评测 | `/ops/evals` | 评测套件 / 用例管理、批量执行与结果对比 |
| 运行追踪 | `/ops/traces` | 全链路 Trace，下钻到工具调用与 Token 消耗 |

### 系统设置

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
| 🗄️ **数据源** | `list_datasources` · `get_table_schema` · `query_datasource` | 数据源、表结构与只读 SQL 查询 |
| 📊 **实例** | `query_entity_data` | 按实体查询关联数据源中的实例数据 |
| 📐 **规则** | `evaluate_rule` · `evaluate_all_rules` · `screen_users_by_rule` | 规则查询、评估与人群筛选 |
| ⚡ **动作** | `execute_action` | 触发预定义业务动作 |

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 🎨 前端 | Vue 3 + TypeScript + Vite + Pinia | Composition API · HMR · 状态管理 |
| 🧱 UI | Ant Design Vue + Vue Flow | 企业级控件 · 双层力导向画布 |
| 🌐 通信 | Axios | JWT 自动注入 · SSE 流式解析 |
| 🚀 后端 | FastAPI + Uvicorn | ASGI · 异步 IO · OpenAPI 文档 |
| 🗃️ ORM | SQLAlchemy 2.0 + Pydantic 2 | 声明式模型 · 类型安全 Schema |
| 🔐 认证 | PyJWT + Passlib (bcrypt) | Bearer Token · 角色权限 |
| 💾 数据库 | SQLite / MySQL | 通过 `DATABASE_URL` 切换 |
| 🔌 连接器 | MySQL · PostgreSQL · Oracle · SQL Server · Hive · ClickHouse | 多源异构接入 |
| 🤖 LLM | OpenAI 兼容协议 | 工具调用 · SSE 流式 · 链路追踪 |

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

### 启动前端

```bash
cd frontend
pnpm install
pnpm dev
```

访问 `http://localhost:5173`，后端接口文档 `http://localhost:8001/docs`

> 💡 启动时自动建表 · 迁移 · 创建默认管理员 `admin / admin123`

---

## 环境配置

后端配置文件：`backend/.env`

```env
DATABASE_URL=sqlite:///./ontology.db
# DATABASE_URL=mysql+pymysql://user:password@host:3306/ontology_platform?charset=utf8mb4
LLM_API_BASE=https://your-llm-api.com/v1
LLM_API_KEY=your-api-key
LLM_MODEL=your-model-name
SECRET_KEY=replace-with-strong-random-string
```

> ⚠️ 生产环境：使用 MySQL · 强随机 SECRET_KEY · KMS 管理凭据 · 修改默认密码 · 开启审计

---

## 项目结构

```text
backend/
├── app/
│   ├── api/v1/                    # REST API 端点
│   │   ├── builder.py             # 本体构建（extract/chat/hydrate/finalize）
│   │   └── data_plane/            # 数据平面（assets/connections/execute/quality）
│   ├── connectors/                # 数据库连接器
│   ├── models/                    # SQLAlchemy 数据模型
│   ├── repositories/              # 数据访问层
│   ├── services/
│   │   ├── agent/                 # Agent 编排、工具路由、图引擎
│   │   ├── builder/               # 水合验证服务
│   │   └── data_plane/            # 资产/连接/执行/质量/血缘
│   └── main.py
└── requirements.txt

frontend/
├── src/
│   ├── api/                       # API 客户端
│   ├── components/                # 通用组件
│   ├── store/                     # Pinia 状态管理
│   ├── types/                     # TypeScript 类型
│   └── views/
│       ├── builder/               # 本体构建器（4 步流水线）
│       ├── datasource/            # 数据集成
│       ├── ontology/              # 本体浏览
│       ├── governance/            # 治理（权限/审计/影响分析）
│       └── workspace/             # 工作台
└── package.json
```

---

## License

MIT © 元枢 Ontology
