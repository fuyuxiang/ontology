<div align="center">

# 元枢本体 · Yuanshu Ontology

**面向企业 AI 的可运行本体智能平台**

**AI 自动构建 · 业务语义建模 · 数据接地 · 逻辑行动 · Agent 运行**

**一图 · 一体 · 一闭环**

业务成图 · 能力入体 · 智能成环

**[中文](README.md)** · **[English](README.en.md)**

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-18%2B-green.svg)](https://nodejs.org/)

</div>

---

## 元枢是什么？

**元枢（Yuanshu Ontology）是一个开源的企业级可运行本体平台。**

它将企业分散在数据库、文档、业务规则、算法模型和系统接口中的业务知识，组织为统一的**对象、关系、状态、事件、逻辑和行动**，形成可被业务人员、应用系统和 AI Agent 共同理解与调用的企业业务语义。

元枢不仅用于“描述业务世界”，还进一步连接真实数据、承载业务逻辑和模型、定义可执行动作，并通过 MCP、SDK、Agent 与智能流程对外提供能力，使本体成为企业 AI 的**运行时业务上下文**。

与传统从空白画布开始的人工建模方式不同，元枢将 AI 引入本体生产过程，通过文档理解、数据资产分析、语义抽取、关系发现、规则识别和智能映射，辅助完成从业务知识到可运行本体的构建。

> **从企业数据与知识出发，自动构建业务语义，并让语义真正进入运行。**

---

## 核心理念 · 一图 · 一体 · 一闭环

### 一图

**业务语义地图**

统一描述企业业务世界中的：

- 对象
- 属性
- 关系
- 状态
- 事件
- 证据

让业务人员、应用系统与 AI 使用同一套业务语义。

### 一体

**可运行本体**

在统一业务语义之上进一步组织：

- 事实
- 规则
- 函数
- 模型
- 行动
- 治理

让业务语义从“可以理解”进一步变成“可以运行”。

### 一闭环

**本体智能闭环**

贯通：

- 智能构建
- 数据接地
- 本体服务
- 业务执行
- 结果回写
- 持续演化

让本体从一次性模型变成持续演进的企业智能资产。

**业务成图 · 能力入体 · 智能成环**

---

## 为什么需要可运行本体？

企业已经拥有大量数据平台、业务系统、规则、模型和知识库，但这些资产通常以不同形式存在：

- 数据存在于表、字段和指标中；
- 业务知识存在于制度、文档和专家经验中；
- 业务逻辑存在于 SQL、代码、规则引擎和算法模型中；
- 执行能力存在于 API、工作流和生产系统中；
- AI 面对的却往往只是零散的数据、文本和工具。

当 AI 从问答和辅助分析进一步进入业务判断与执行时，仅有数据访问或 RAG 并不足以稳定描述企业完整的业务上下文。

元枢通过本体把这些能力组织到统一的业务对象之上：

```text
     数据 · 文档 · 规则 · 模型 · API
                     │
                     ▼
          ┌────────────────────┐
          │    业务语义地图    │
          ├────────────────────┤
          │  Object            │
          │  Relation          │
          │  State             │
          │  Event             │
          │  Evidence          │
          └────────────────────┘
                     │
                     ▼
          ┌────────────────────┐
          │     可运行本体     │
          ├────────────────────┤
          │  Fact              │
          │  Logic             │
          │  Model             │
          │  Action            │
          │  Governance        │
          └────────────────────┘
                     │
                     ▼
            MCP · SDK · Agent
             Workflow · API
                     │
                     ▼
        理解 · 判断 · 执行 · 回写
```

本体因此不只是 Schema，也不是一张静态关系图，而是企业 AI 可以持续使用的业务运行层。

---

## 核心能力

### 1. AI 原生的本体自动化构建

元枢将 AI 作为本体生产过程中的协作者，而不是要求用户完全依赖手工建模。

支持从企业已有数据与知识中辅助识别：

- 业务对象与对象属性
- 对象之间的业务关系
- 状态与业务事件
- 业务规则与约束
- 计算逻辑与模型能力
- 可执行动作
- 术语、证据与治理信息

平台提供多种智能构建入口，包括文档驱动、数据资产驱动和交互式引导等方式。

整体采用：

**AI 生成 + 程序校验 + 人工确认**

的协同机制。

```text
业务材料 / 数据资产
        │
        ▼
   知识解析与理解
        │
        ▼
   候选语义抽取
        │
        ▼
对象 · 属性 · 关系
规则 · 模型 · 行动
        │
        ▼
结构与语义校验
        │
        ▼
     专家确认
        │
        ▼
     本体模型
```

AI 负责提高知识发现和建模效率，确定性程序负责结构约束与质量校验，专家负责关键业务语义确认。

---

### 2. 可运行本体建模

元枢不仅建模实体和关系，还围绕真实业务运行组织完整的本体能力。

#### 对象

描述企业业务世界中的实体、事件和业务概念。

支持：

- Object Type
- Attribute
- Unique Identifier
- State
- Event
- Shared Attribute
- Shared Reference
- 分层本体组织

#### 关系

描述对象之间稳定、明确的业务连接。

支持：

- 关系方向
- 关系基数
- 一对一 / 一对多 / 多对多
- 关系约束
- 跨对象引用
- 图遍历
- 关系血缘

#### Logic

把企业中的规则、计算和专家经验转化为可被系统与 Agent 调用的逻辑能力。

支持：

- Expression
- SQL
- Python
- Function 调用
- Function 组合
- 规则与约束
- 模型能力挂载

#### Action

把系统接口和业务操作封装成与业务对象关联的执行能力。

支持：

- API Call
- SQL Execution
- Function Call
- Custom Script
- Attribute Modification
- Notification

Action 可以与前置条件、权限控制、审批和执行审计结合，使 AI 能够调用企业能力，同时保持明确的执行边界。

#### Governance

治理贯穿本体设计、发布和运行全过程。

包括：

- 责任归属
- 权限控制
- 版本管理
- 审核发布
- 影响分析
- 运行监控
- 审计追溯
- 回滚恢复

---

### 3. 数据接地

本体模型描述业务世界如何被理解，**数据接地（Data Grounding）**负责把这些业务定义连接到企业真实数据。

元枢通过 `ObjectBinding` 建立业务对象与物理数据之间的映射。

支持：

- Primary 主数据绑定
- Enrichment 补充数据绑定
- Document Evidence 文档证据绑定
- 属性映射建议
- 数据类型兼容检查
- 主键识别
- LLM 辅助映射
- 关系验证
- 数据质量检查
- 数据血缘

```text
物理数据
Database / Table / Document / API
              │
              ▼
        Object Binding
              │
              ▼
对象 · 属性 · 关系 · 事件 · 证据
              │
              ▼
           本体实例
```

元枢明确区分：

**本体建模**负责形成业务语义规范；

**数据接地**负责将语义规范映射到真实业务事实；

两者协同，但不是同一过程。

---

### 4. 真实数据验证

完成数据绑定后，元枢可以进一步基于真实数据验证本体与数据之间的连接质量。

验证过程包括：

1. 数据源连接与 Schema 检查
2. 对象属性实例化验证
3. 对象关系与 JOIN 验证
4. 数据质量与策略断言

结合数据质量规则、映射置信度和运行探针，减少“模型定义正确、实际数据无法运行”的问题。

---

### 5. Logic 与 Action Runtime

发布后的本体不仅可查询，还可以直接承载业务运行能力。

#### Logic Runtime

逻辑函数支持：

- Expression
- SQL
- Python

并提供：

- AST 安全校验
- 沙箱执行
- 调用超时
- 调用链追踪
- Function 嵌套调用
- 循环调用检测

同时提供在线工作空间，可直接维护 Logic 与 Action 源码。

#### Action Runtime

平台提供统一的 Action Executor，将不同系统能力抽象为可治理的业务动作。

Action 与本体对象关联，使调用方关注：

> “对哪个业务对象执行什么业务动作”

而不是底层：

> “调用哪个接口、修改哪张表、更新哪个字段”。

---

### 6. 面向 AI / Agent 的本体服务

发布后的本体可以作为 AI Agent 的运行时业务上下文。

元枢将：

- 对象
- 属性
- 关系
- 数据映射
- Logic
- Action
- 权限信息

组织为 Agent 可以理解和调用的能力。

#### MCP Server

内置 MCP Server，通过标准协议向外部 Agent 与 MCP Client 暴露本体能力。

当前提供覆盖以下类别的 MCP Tools：

- 本体查询
- 对象实例查询
- 属性映射查询
- 数据访问
- Logic 执行
- Action 执行
- Python Workspace

支持：

- JSON-RPC 2.0
- Bearer JWT
- API Key
- 调用日志
- 调用统计

#### Ontology SDK

元枢可以根据已经发布的本体自动生成：

- TypeScript SDK
- Python SDK

业务应用可以直接围绕对象语义进行开发，而无需将物理表结构传播到上层应用。

#### ReAct Agent

内置 Agent Runtime，可以基于本体上下文完成：

```text
理解意图
   ↓
查询本体
   ↓
获取业务事实
   ↓
调用 Logic
   ↓
执行 Action
   ↓
生成结果
```

Agent 工具调用过程支持流式追踪与调用链展示。

---

### 7. 智能流程编排

对于需要多步骤协同的业务任务，元枢提供可视化流程编排能力。

支持：

- DAG 执行
- 条件分支
- 并行节点
- 子流程
- 跨节点数据映射
- Logic 调用
- Action 调用
- Agent 节点
- 定时触发
- 事件触发
- Webhook

本体负责提供统一的业务对象与能力，流程负责组织这些能力如何协同运行。

---

### 8. 本体全生命周期治理

元枢将本体作为长期维护的企业资产进行管理。

#### 版本生命周期

```text
Draft
  │
  ▼
Pending Approval
  │
  ├────► Rejected
  │
  ▼
Published
```

支持：

- Draft 管理
- 发布审批
- 版本快照
- 版本比较
- 回滚
- Breaking Change 分析
- 依赖检查
- 删除保护

本体、Logic 和 Action 的变更可以被追踪，并分析对已发布能力和上层应用的影响。

---

### 9. 数据接入与连接器

元枢提供统一的数据连接器框架。

当前支持：

#### Database

- MySQL
- PostgreSQL
- SQL Server
- Oracle

#### Object Storage

- Amazon S3
- MinIO
- OSS / COS / OBS 等 S3 兼容存储

#### File Transfer

- FTP
- SFTP

#### Streaming

- Kafka

#### API

- REST API

数据资产统一抽象为：

- Table
- SQL View
- Document

为本体构建和数据接地提供统一的数据入口。

---

### 10. 安全与治理

企业本体不仅需要语义统一，也需要保证数据访问和行动执行处于受控状态。

元枢提供：

- RBAC 权限体系
- JWT 身份认证
- API Key 鉴权
- 连接凭据加密
- 敏感字段脱敏
- SQL AST 安全检查
- 表级访问控制
- 参数化查询
- 执行限流
- 操作审计
- 执行审计
- 服务健康监控
- LLM 调用统计

权限、执行与审计贯穿数据、本体、Logic、Action 和 Agent 调用链。

---

## 本体全生命周期

元枢覆盖从业务知识进入平台，到本体进入 AI 与业务运行的完整生命周期。

```text
  知识与数据
      │
      ▼
  AI 智能构建
      │
      ▼
  本体建模
      │
      ▼
  数据接地
      │
      ▼
  验证与发布
      │
      ▼
  本体服务
      │
      ▼
  Logic / Action / Agent
      │
      ▼
  业务回写
      │
      ▼
  运行反馈 ──────────────► 持续演化
                              │
      ▲                       │
      └───────────────────────┘
```

这也是元枢的核心技术路线：

> **业务成图 · 能力入体 · 智能成环**

---

## 系统架构

```text
┌───────────────────────────────────────────────────────────────┐
│                      AI & Applications                        │
│                                                               │
│   Agent | Workflow | Copilot | Business App                   │
├───────────────────────────────────────────────────────────────┤
│                      Ontology Services                        │
│                                                               │
│   MCP Server | Ontology API | TypeScript SDK | Python SDK     │
├───────────────────────────────────────────────────────────────┤
│                       Runtime Layer                           │
│                                                               │
│   Logic | Function | Model | Action | Event                   │
├───────────────────────────────────────────────────────────────┤
│                       Ontology Core                           │
│                                                               │
│   Object | Attribute | Relation | State | Event               │
│   Logic | Action | Governance                                 │
├───────────────────────────────────────────────────────────────┤
│                       Data Grounding                          │
│                                                               │
│   ObjectBinding | Mapping | Validation | Quality | Lineage    │
├───────────────────────────────────────────────────────────────┤
│                        Data Sources                           │
│                                                               │
│   Database | Analytics DB | Document | Object Storage         │
│   Kafka | API                                                 │
└───────────────────────────────────────────────────────────────┘

     Permission | Version | Approval | Audit | Monitor
              Governance across all layers
```

---

## AI 自动构建与确定性运行

元枢在设计上区分两类问题：

### 适合 AI 的问题

例如：

- 理解业务文档
- 发现候选业务对象
- 补全属性
- 识别关系
- 抽取规则
- 生成映射建议
- 生成 Logic / Skill

这些环节充分利用大模型的语义理解能力。

### 必须确定执行的问题

例如：

- Schema 校验
- 数据类型校验
- 主键检查
- JOIN 验证
- 权限检查
- SQL 安全检查
- Action 执行
- 发布审批
- 版本快照
- 审计记录

这些环节由确定性程序和治理机制负责。

因此元枢的 AI 原则不是：

> **让 LLM 决定一切**

而是：

> **让 AI 负责理解和生成，让程序负责验证和执行，让人在关键节点做最终确认。**

---

## 开放与互操作

元枢的核心定位是**可运行企业本体平台**，同时支持与标准本体和外部工具之间的数据交换。

当前支持包括：

- OWL/XML
- RDF/XML
- Turtle
- JSON
- Excel

并提供：

- 平台原生可视化建模
- Protégé 风格编辑界面
- WebVOWL 可视化
- 术语视图

这些能力用于模型交换、已有本体迁移和专业本体工程协作，而不是限定元枢的本体运行模型。

---

## Quick Start

### Requirements

- Python 3.11+
- Node.js 18+
- npm

---

### 1. Clone

```bash
git clone https://github.com/fuyuxiang/ontology.git
cd ontology
```

---

### 2. Configure

在项目根目录创建 `.env`：

```env
# Metadata database
DATABASE_URL=sqlite:///./ontology.db

# MySQL example
# DATABASE_URL=mysql+pymysql://user:pass@host:3306/ontology?charset=utf8mb4

# LLM - OpenAI compatible API
LLM_BASE_URL=https://your-llm-endpoint/v1
LLM_API_KEY=your-api-key
LLM_MODEL=your-model-name

# Required
SECRET_KEY=replace-with-strong-random-string

# Optional
CREDENTIAL_ENCRYPTION_KEY=
ADMIN_INITIAL_PASSWORD=
CORS_ORIGINS=http://localhost:5177
```

---

### 3. Start

Linux / macOS：

```bash
./start.sh
```

Windows：

```powershell
.\start.bat
```

启动后：

| Service     | Address                            |
| ----------- | ---------------------------------- |
| Web UI      | `http://localhost:5177`            |
| API         | `http://localhost:8001`            |
| API Docs    | `http://localhost:8001/docs`       |
| MCP Server  | `http://localhost:8001/api/v1/mcp` |
| Code Server | `http://localhost:8443`            |

首次启动会自动初始化数据库并创建管理员账户。

> 生产环境请配置高强度 `SECRET_KEY`、`CREDENTIAL_ENCRYPTION_KEY` 和管理员密码，并限制 Code Server、CORS 与 MCP 的访问范围。

停止服务：

```bash
./stop.sh
```

---

## Development

### Backend

```bash
cd backend

pip install -r requirements.txt

uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8001 \
  --reload
```

### Frontend

```bash
cd frontend

npm install

npm run dev
```

---

## 技术栈

| Layer             | Technology                                          |
| ----------------- | --------------------------------------------------- |
| Frontend          | Vue 3 · TypeScript · Vite · Pinia · Ant Design Vue  |
| Visualization     | Vue Flow · d3-force · ECharts                       |
| Backend           | FastAPI · Uvicorn · SQLAlchemy · Pydantic · Alembic |
| Metadata DB       | SQLite · MySQL                                      |
| AI / LLM          | OpenAI-compatible API · Function Calling · ReAct    |
| Agent Protocol    | MCP · JSON-RPC 2.0                                  |
| SQL               | sqlglot                                             |
| Documents         | python-docx · pdfplumber · openpyxl · pandas        |
| Runtime Workspace | code-server                                         |
| Auth              | JWT · bcrypt · RBAC                                 |
| Realtime          | SSE · WebSocket                                     |

---

## 项目结构

```text
ontology/
│
├── backend/
│   └── app/
│       ├── api/
│       │   └── v1/
│       │       ├── entities.py
│       │       ├── relations.py
│       │       ├── builder.py
│       │       ├── ai_ontology.py
│       │       ├── ai_builder_v2.py
│       │       ├── doc_builder.py
│       │       ├── ontology_publish.py
│       │       ├── impact_analysis.py
│       │       ├── mcp.py
│       │       ├── osdk.py
│       │       └── data_plane/
│       │
│       ├── connectors/
│       ├── models/
│       │
│       └── services/
│           ├── agent/
│           ├── aip/
│           ├── builder/
│           ├── data_plane/
│           ├── function_runtime/
│           ├── action_executors/
│           └── mcp_tools/
│
├── frontend/
│   └── src/
│       ├── views/
│       │   ├── builder/
│       │   ├── ontology/
│       │   ├── dataflow/
│       │   ├── agents/
│       │   └── aip/
│       │
│       ├── components/
│       ├── utils/
│       ├── store/
│       └── api/
│
├── workspace/
│
├── code-server/
│
├── docs/
│
└── tools/
```

---

## 设计原则

元枢遵循几个核心原则。

### Business Semantics First

上层应用和 AI 应围绕稳定的业务对象工作，而不是直接依赖底层表和字段。

### AI for Construction, Determinism for Execution

AI 用于理解、发现和生成；确定性程序负责校验、执行和治理。

### Ontology as Runtime

本体不是建模结束后的静态文档，而是应用、Agent 和业务流程共同使用的运行时业务上下文。

### Govern Everything

对象、关系、Logic、Action、数据访问和 Agent 执行都应拥有明确的权限、版本和审计边界。

### Build Once, Reuse Across Applications

统一业务语义和能力应能够被多个 Agent、流程和业务应用持续复用，而不是随场景重复建设。

---

## Contributing

欢迎参与元枢的建设。

我们尤其欢迎以下方向的贡献：

- AI Ontology Building
- Ontology Modeling
- Data Grounding
- Data Connectors
- Logic Runtime
- Action Runtime
- MCP Tools
- Agent Runtime
- Workflow
- Visualization
- Governance & Security

贡献流程：

1. Fork 本仓库

2. 创建功能分支

   ```bash
   git checkout -b feature/amazing-feature
   ```

3. 提交代码

4. 推送分支

   ```bash
   git push origin feature/amazing-feature
   ```

5. 创建 Pull Request

对于较大的功能设计，建议先通过 Issue 讨论设计方案。

---

## Community

如果你：

- 正在研究企业本体与 AI Agent；
- 希望完善自动化本体构建能力；
- 正在建设新的数据连接器；
- 希望贡献新的 Logic / Action / MCP Tool；
- 对企业语义建模、知识工程或 Agent Runtime 感兴趣；

欢迎通过 GitHub Issues 与 Pull Requests 参与讨论和建设。

---

## License

[MIT License](LICENSE)

---

<div align="center">

### 元枢本体 · Yuanshu Ontology

**让企业业务可理解，让智能能力可运行，让本体资产可进化。**

**业务成图 · 能力入体 · 智能成环**

</div>
