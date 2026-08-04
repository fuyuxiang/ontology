<div align="center">

# 元枢本体 · Yuanshu Ontology

**企业级本体智能平台**

*本体驱动 · 语义织网 · 让数据可理解 · 让 AI 可信赖*

**[中文](README.md)** | **[English](README.en.md)**

[![Vue 3](https://img.shields.io/badge/Vue-3.5-4FC08D?logo=vue.js)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-6.x-3178C6?logo=typescript)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://python.org/)
[![OWL 2](https://img.shields.io/badge/W3C-OWL_2-005A9C)](https://www.w3.org/OWL/)
[![MCP](https://img.shields.io/badge/MCP-2024--11--05-8A2BE2)](https://modelcontextprotocol.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 项目简介

元枢本体是一个企业级本体智能平台。技术路线为 **「以语义网为中心，端到端智能构建」** —— 以符合语义网规范的本体作为核心资产，把数据接入、本体建模、映射绑定、真实数据校验、版本发布到 AI 消费的全链路收敛在同一平台内闭环。

在这条路线中，本体承担的角色是 **AI 与企业数据之间的语义地图**：向下锚定到物理表字段，向上为大模型提供可推理、可执行、可治理的语义坐标。平台提供从数据接入到智能体应用的端到端工作流，让团队基于治理良好的业务语义构建智能场景，而不是直接操作裸表和脚本。

---

## 为什么需要语义地图

大模型进入企业的真正瓶颈，不在模型能力，而在**语义断层**：

- 企业数据以**物理形态**存在 —— 表名 `t_cbss_sub_info`、字段 `dev_num`、散落在十几个异构系统里；
- 业务与 AI 以**语义形态**思考 —— "这个高价值宽带用户最近有没有投诉过装机质量"。

把 Schema 直接塞给大模型，本质是让模型去猜物理世界与业务世界的对应关系 —— 猜错了没有反馈，猜对了无法复用，换个场景要从头再猜。

**本体（Ontology）正是消除这层断层的语义地图。** 它用一套形式化、可版本、可治理的语义结构，同时向两端锚定：

| 地图要素 | 本体中的实现 | 锚定对象 |
|---------|------------|---------|
| **坐标系** | 对象类型（Object Type）+ 关系（Relation） | 业务概念如何构成世界 |
| **图例** | 属性（Attribute）+ 数据类型 + 约束 | 每个概念可被观测的维度 |
| **航线** | 关系基数、图遍历、血缘 | 概念之间如何抵达彼此 |
| **落点** | 对象绑定（Object Binding）| 语义属性 ↔ 物理表字段 |
| **技能标注** | 逻辑函数（Function）+ 动作（Action） | 在这张地图上能做什么 |

有了地图，AI 不再猜测：它**查询本体**得到语义坐标，**沿着绑定**落到真实数据，**调用挂载的能力**完成计算与执行 —— 每一步都可解释、可追溯、可治理。

---

## 技术路线

### 一、以语义网为中心

平台的核心资产是**符合语义网规范的本体**，而不是某个 AI 应用的私有配置。

- 建模层对齐 **OWL 2**：类、对象属性、数据属性、命名个体，支持 `subClassOf` / `equivalentClass` / `disjointWith` / `domain` / `range` / `inverseOf`，覆盖 **12 种类表达式**（存在/全称量化、最小/最大/精确基数、交/并/补、hasValue）与 **7 种对象属性特征**（functional、inverseFunctional、transitive、symmetric、asymmetric、reflexive、irreflexive）。
- 提供 **OWL/XML 双向解析与序列化**（前端 `utils/owl/`），以及 **RDF/XML + Turtle 导入**（后端 rdflib），本体可与 Protégé 等标准工具互通。
- 内置 **四种建模视图**：平台原生画布、**Protégé 风格 OWL 编辑器**（15 个组件复刻类树/属性树/公理面板）、**WebVOWL 可视化**、**VocBench 术语视图** —— 让本体工程师用熟悉的范式工作。

> 语义网不是装饰。它保证本体是**可交换的标准资产**，而非锁死在平台里的私有 Schema。

### 二、端到端智能构建

从裸数据到可被 AI 消费的语义服务，六个阶段在同一平台内闭环，**每个阶段都有 LLM 参与，但每个阶段都有确定性校验兜底**：

```
① 接入        ② 建模        ③ 映射        ④ 校验        ⑤ 发布        ⑥ 消费
Connection    5 种入口     ObjectBinding  4 阶段水合    版本/审批     MCP / OSDK
  Asset      AI+人工协同   启发式+LLM     真实数据验证   快照/回滚     Agent / AIP
```

| 阶段 | 智能化手段 | 确定性兜底 |
|-----|-----------|-----------|
| ① 接入 | 文档自动解析摘要（PDF/Word/Excel） | Schema 自动同步 + diff、连接连通性测试 |
| ② 建模 | 文档抽取 / 资产对话 / 主题域下钻，SSE 流式生成 | Pydantic 命名规范校验 + 最多 5 次重试 |
| ③ 映射 | Token Jaccard + 中文语义扩展 + 类型相容矩阵评分，低置信度交 LLM 兜底 | 置信度分层（high/medium/low），人工确认 |
| ④ 校验 | —— | 4 阶段真实数据水合：接入验证 → 实例化 → 关系 JOIN 验证 → 策略断言 |
| ⑤ 发布 | —— | 3 项质量门禁 + 审批流 + 全量组件快照 + 影响面分析 |
| ⑥ 消费 | ReAct 智能体、AIP 流程编排 | 沙箱执行、SQL 六道闸、全链路审计 |

### 三、本体即 AI 的运行时上下文

发布后的本体不是一份文档，而是**智能体的可执行上下文**：

- **MCP Server**（JSON-RPC 2.0，协议版本 `2024-11-05`）对外暴露 **15 个本体工具** —— 属性映射查询、实例查询、复杂 SQL、逻辑函数执行、动作执行、Python 工作区读写与运行；任何 MCP 客户端都能把本体接为知识与能力来源。
- **OSDK 代码生成** 按已发布本体产出 **TypeScript / Python SDK**，业务系统以 `Customer.list(client, {...})` 的对象语义访问数据，而非拼 SQL。
- **本体上下文注入** 把对象、关系、数据源映射、可用动作按 Tier 分层组织后注入智能体 system prompt，Agent 在 ReAct 循环中据此选择工具。

---

## 系统架构

![架构图](docs/images/architecture.png)

```
┌──────────────────────────────────────────────────────────────┐
│  消费层   MCP Server (15 工具) · OSDK (TS/Py) · Ontology API  │
│           ReAct 智能体 · AIP 流程编排 · Copilot               │
├──────────────────────────────────────────────────────────────┤
│  能力层   逻辑函数 (expression/sql/python) · 动作 (6 类执行器) │
│           技能 Skill (LLM 生成 + AST 校验 + 沙箱)             │
├──────────────────────────────────────────────────────────────┤
│  语义层   ★ 本体核心 ★                                        │
│           对象类型 · 属性 · 关系 · 共享属性/引用              │
│           OWL 2 建模 · 版本快照 · 审批发布 · 影响分析         │
├──────────────────────────────────────────────────────────────┤
│  绑定层   ObjectBinding (primary/enrichment/document)         │
│           映射建议 (启发式 + LLM) · 水合验证 · 血缘            │
├──────────────────────────────────────────────────────────────┤
│  数据层   Connection (5 类连接器) · Asset (table/view/doc)     │
│           统一执行闸口 · 质量规则与探针 · 执行审计            │
└──────────────────────────────────────────────────────────────┘
```

**分层原则**：上层只依赖下层的语义契约。智能体不知道 `t_cbss_sub_info` 存在，它只知道 `CbssSubscriber` —— 物理变更由绑定层吸收，语义层保持稳定。

---

## 能力全景

### 语义层 · 本体核心

| 能力 | 实现要点 |
|-----|---------|
| 对象建模 | 三层分级（T1 核心 / T2 领域 / T3 场景），属性独立表存储，支持约束与示例值 |
| 关系建模 | `has_one` / `has_many` / `belongs_to` / `many_to_many`，基数标注、无环声明 |
| OWL 2 编辑 | Protégé 风格类树/属性树/公理面板，12 种类表达式，7 种属性特征 |
| 标准互通 | OWL/XML 双向序列化；RDF/XML、Turtle、JSON、Excel 导入 |
| 跨本体复用 | 共享属性（SharedAttribute）与共享引用（SharedRef，跨本体引用整个对象，只读） |
| 图谱探索 | Vue Flow + d3-force 力导向双层画布：本体对象层（按 Tier 着色）+ 数据资产层（可切换） |
| 血缘视图 | 实体 1–5 跳邻域 BFS，交互式图谱 |

### 语义层 · 版本与治理

| 能力 | 实现要点 |
|-----|---------|
| 版本流水线 | `draft → pending_approval → published`，另有 `rejected` 分支与快捷发布 |
| 质量门禁 | ① 必须绑定数据源 ② 必须定义属性 ③ 属性映射覆盖率 ≥ 50%；关系两端一致性校验 |
| 版本快照 | 实体 / 属性 / 关系 / 逻辑函数 / 动作五类组件全量快照，发布即冻结 |
| 回滚 | 基于目标版本**创建新版本**（保留 `rollback_from` 溯源），仍走审批，不破坏历史 |
| 影响分析 | 发布前预演 breaking changes；发布后自动标记受影响的 AIP 场景与智能体为 `stale` |
| 删除保护 | 删除函数/动作前查询被哪些已发布版本、AIP 场景、技能引用，给出 `safe_to_delete` |

### 绑定层 · 从语义到物理

| 能力 | 实现要点 |
|-----|---------|
| 对象绑定 | 三种角色：`primary`（主表）/ `enrichment`（补充）/ `document_evidence`（文档佐证） |
| 映射建议 | 归一化 + snake/camel/中文分词 → Token Jaccard；30+ 中文业务词扩展（"工单"→ticket/order/wo）；类型相容矩阵；`difflib` 模糊匹配；列注释命中；主键提示。分数 ≥0.8 high / ≥0.5 medium |
| LLM 兜底 | 低置信度属性聚合后送 LLM，返回候选列 + 理由 + 分数 |
| 水合验证 | **① 接入验证** 连通性/Schema 同步/预览/画像 → **② 本体实例化** 属性列匹配命中率 → **③ 关系验证** 主键存在性 + 同连接样本 JOIN → **④ 策略断言** 主键唯一性 + 必填字段空值率（阈值 5%）。全程 SSE 推送进度 |
| 质量规则 | 建绑定时自动挂载 `row_count_min` / `freshness` / `pk_uniqueness` / `null_ratio_max`；6 类规则 × 6 种探针 |
| 血缘 | `Asset → ObjectType → Action` 资源级血缘，绑定事件与执行事件自动写入 |

### 数据层 · 接入与执行

| 能力 | 实现要点 |
|-----|---------|
| 连接器框架 | 按 `(category, type)` 双键注册，5 大类：数据库 / 对象存储 / 文件传输 / 消息队列 / API |
| 已实现连接器 | MySQL · PostgreSQL · SQL Server · Oracle · S3（兼容 OSS/COS/OBS/MinIO）· FTP · SFTP · Kafka · REST |
| 凭据安全 | Fernet 对称加密存储（`fernet://`），永不落明文；编辑态返回掩码 |
| 连接池 | 进程内 LIFO 池，5 分钟空闲回收，按连接配置容量上限 |
| 统一执行闸口 | **六道闸**：Locator 改写 → sqlglot AST 安全审查（DDL 永拒 / DML 需授权）→ 表名白名单 → 参数齐全性 → 令牌桶限流 → 执行 + 列级脱敏 + TTL 缓存 |
| 参数化 | 业务层统一 `:name` 占位符，按驱动自动转 `%(name)s` / `:name`，字符串字面量与 `::cast` 状态机绕过 |
| 数据资产 | `table` / `sql_view` / `document` 三类；文档支持上传、对象存储、目录、API、消息队列五种来源 |
| 执行审计 | 每次执行落 `ExecutionLog`：SQL 仅存 hash + 500 字预览，参数脱敏为 `<类型:长度>` |

### 能力层 · 逻辑与动作

| 能力 | 实现要点 |
|-----|---------|
| 逻辑函数 | 三种形态：`expression`（受限 eval）/ `sql`（本体对象名重写为物理表）/ `python`（沙箱） |
| 函数运行时 | AST 白名单校验 + `SIGALRM` 超时（单次 30s / 整链 120s）+ 最大递归深度 10 + A→B→A 循环检测 + `call_function` 链式调用 + 调用栈追溯 |
| 在线 IDE | 内嵌 code-server，函数/动作源码在 `workspace/` 目录直接编辑，watchdog 监听文件变更自动注册 `@Function` 装饰器元数据 |
| 动作执行器 | 6 类：`api_call`（httpx）· `sql_exec`（参数化写库）· `call_function` · `custom_script`（5s 超时）· `modify_attribute`（dry-run）· `notification`（dry-run） |
| 技能 Skill | 多轮对话收集需求 → LLM 生成工具代码与 Schema → **AST 自动校验** → 沙箱测试 → 版本化发布，支持回滚与弃用 |

### 消费层 · AI 应用

| 能力 | 实现要点 |
|-----|---------|
| ReAct 智能体 | 最多 12 轮 function-calling；打转检测（连续 2 轮相同调用签名即强制收敛）；末轮 `tool_choice=none` 强制出答案 |
| 思考过程可视化 | 后端按 `ontology` / `logic` / `action` 标注工具类别并流式推送 `tool_start` / `tool_result`；前端合成**意图识别 → 本体查询 → 逻辑计算 → 执行动作 → 生成回答**五阶段时间线，相邻重复步骤自动折叠为 `×N`，答复下方呈现本体调用链 |
| MCP Server | JSON-RPC 2.0 over HTTP，15 个工具；Bearer JWT / `X-API-Key` 双鉴权；每次调用落日志，提供调用量、耗时、错误率统计 |
| OSDK | 按已发布本体生成 TypeScript / Python SDK（客户端 + 每对象一个类 + 关系遍历方法 + 用法示例） |
| AIP 流程编排 | DAG 就绪队列调度，支持条件分支（`branch-true/false`）、并行节点、子场景、跨节点数据映射（`node.field[0].sub` 路径语法）；20+ 种节点类型 |
| 三种触发 | 自实现 5 字段 cron 调度（30 秒轮询，防同分钟重复）· 事件总线（实体动作匹配）· Webhook（HMAC-SHA256 签名校验） |
| 评测与追踪 | 评测套件按关键词断言，输出通过率 / 平均延迟；执行追踪记录输入输出、耗时、Token |

### 运维与安全

| 能力 | 实现要点 |
|-----|---------|
| RBAC | 4 内置角色（admin / editor / operator / viewer），权限格式 `{module}:{action}`，JWT（HS256）+ bcrypt |
| 审计 | 操作审计（含变更前后快照）+ 执行审计（SQL 指纹、拦截原因、缓存命中）双轨 |
| 脱敏 | 连接凭据加密、模型 API Key 掩码、查询结果按 `sensitivity_tags` 列级脱敏（`pii` 保留首 3 末 4 / `sensitive` 全掩） |
| 监控 | 10 项服务健康探测（30 秒周期）、资源指标、LLM 调用统计、告警与 WebSocket 实时推送、历史数据自动清理 |
| 模型管理 | 模型注册表统一管理多供应商（OpenAI 兼容协议），按场景绑定，支持连通性测试 |

---

## 技术栈

| 层级 | 技术选型 |
|-----|---------|
| 前端框架 | Vue 3.5 · TypeScript 6 · Vite 8 · Pinia 3 · Vue Router 4 · Ant Design Vue 4.2 |
| 前端可视化 | Vue Flow 1.48（本体图谱 / 血缘 / AIP 画布）· d3-force（力导向布局）· ECharts 6（指标图表）· 手写 SVG 语义画布 |
| 语义网 | 前端 OWL/XML 解析与序列化（`utils/owl/`）· 后端 rdflib（RDF/XML、Turtle 导入） |
| 后端框架 | FastAPI 0.115 · Uvicorn · SQLAlchemy 2.0 · Pydantic 2 · Alembic |
| 认证鉴权 | python-jose（JWT HS256）· passlib + bcrypt · RBAC 依赖注入 |
| 数据库 | SQLite（开发）/ MySQL（生产） |
| 连接器 | pymysql · psycopg2 · pymssql · oracledb · boto3 · ftplib / paramiko · 原生 Kafka 协议 · httpx |
| SQL 安全 | sqlglot（AST 解析、方言适配、危险构造拦截） |
| AI / LLM | OpenAI 兼容协议 · Function Calling · SSE 流式 · MCP JSON-RPC 2.0 |
| 文档解析 | python-docx · pdfplumber · openpyxl · pandas |
| 在线 IDE | code-server（逻辑函数与动作源码编辑） |
| 运维 | psutil（资源采集）· watchdog（函数热注册）· WebSocket 实时推送 |

**代码规模**：后端 237 个 Python 模块 / 51 张数据表 / 42 个路由模块 / 351 个 API 端点；前端 137 个 Vue 组件 / 104 个视图 / 32 条业务路由。

---

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+（使用 npm）

### 配置

在**项目根目录**创建 `.env`：

```env
# 元数据库：开发用 SQLite，生产建议 MySQL
DATABASE_URL=sqlite:///./ontology.db
# DATABASE_URL=mysql+pymysql://user:pass@host:3306/ontology?charset=utf8mb4

# 大模型（OpenAI 兼容协议）
LLM_BASE_URL=https://your-llm-endpoint/v1
LLM_API_KEY=your-api-key
LLM_MODEL=your-model-name

# 必填，缺失将拒绝启动
SECRET_KEY=replace-with-strong-random-string

# 可选
CREDENTIAL_ENCRYPTION_KEY=       # 连接凭据加密密钥，留空则每次启动随机生成
ADMIN_INITIAL_PASSWORD=          # 首个管理员初始密码，留空则为 admin
CORS_ORIGINS=http://localhost:5177
```

### 一键启动

```bash
./start.sh          # 同时拉起后端 (8001)、前端 (5177)、code-server (8443)
./stop.sh           # 停止全部服务
```

### 分别启动

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 前端
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5177`，API 文档 `http://localhost:8001/docs`，MCP 端点 `http://localhost:8001/api/v1/mcp`。

> 首次启动自动建表、执行兼容性迁移，并创建管理员账户 `admin`（密码取 `ADMIN_INITIAL_PASSWORD`，未设置则为 `admin`）。**生产环境务必设置该变量并在首登后修改。**

### 生产部署建议

使用 MySQL 存储元数据 · 生成高强度 `SECRET_KEY` 与 `CREDENTIAL_ENCRYPTION_KEY`（否则重启后已存凭据无法解密）· 凭据托管至 KMS · 关闭 code-server 或置于内网 · 开启 MCP 鉴权（`MCP_REQUIRE_AUTH=true`）· 收敛 `CORS_ORIGINS`。

---

## 项目结构

```text
backend/
├── app/
│   ├── api/v1/                      # 42 个路由模块，351 个端点
│   │   ├── entities.py              # 对象类型 CRUD、图谱、血缘
│   │   ├── relations.py             # 关系建模
│   │   ├── builder.py               # 文档抽取 / 属性关系补全 / 水合 / 落库
│   │   ├── ai_ontology.py           # AI 引导式建模（5 阶段会话）
│   │   ├── ai_builder_v2.py         # 主题域下钻式建模
│   │   ├── doc_builder.py           # 文档对话式建模与映射落库
│   │   ├── ontology_publish.py      # 版本 / 审批 / 快照 / 回滚
│   │   ├── impact_analysis.py       # 删除与发布影响面分析
│   │   ├── mcp.py                   # MCP JSON-RPC Server
│   │   ├── osdk.py                  # TS / Python SDK 生成
│   │   ├── aip_*.py                 # 场景编排、执行、Webhook
│   │   └── data_plane/              # 连接、资产、执行、探针、血缘、质量、绑定
│   ├── connectors/                  # 可插拔连接器（双键注册表）
│   ├── models/                      # 51 张 SQLAlchemy 表
│   └── services/
│       ├── agent/                   # ReAct 编排器、图引擎、上下文构建
│       ├── aip/                     # 场景运行器、调度器、事件总线、数据映射
│       ├── builder/                 # 4 阶段水合验证
│       ├── data_plane/              # 执行闸口、映射建议、绑定、质量、血缘
│       ├── function_runtime/        # 函数注册表、文件监听、统一沙箱
│       ├── action_executors/        # 6 类动作执行器
│       └── mcp_tools/               # 15 个 MCP 工具
└── requirements.txt

frontend/
├── src/
│   ├── views/
│   │   ├── builder/                 # 四种建模视图
│   │   │   └── components/protege/  # Protégé 风格 OWL 编辑器（15 组件）
│   │   ├── ontology/                # 本体列表、详情、发布
│   │   ├── dataflow/                # 本体图谱双层画布
│   │   ├── agents/                  # 智能体、思考过程时间线、技能向导
│   │   ├── aip/                     # 流程编排画布
│   │   └── ...                      # 共 104 个视图组件
│   ├── components/canvas/           # 图谱节点、边、工具条、血缘图
│   ├── utils/owl/                   # OWL/XML 解析器与序列化器
│   ├── store/                       # 9 个 Pinia 模块（含 OWL 编辑器 50 步撤销）
│   └── api/                         # 29 个类型化 API 客户端（含手写 SSE 流解析）
└── package.json

workspace/                           # 逻辑函数 / 动作源码目录（code-server 直接编辑）
```

---

## 能力边界与演进方向

保持技术路线不变的前提下，以下能力已规划但尚未实现，在此如实标注：

| 方向 | 当前状态 |
|-----|---------|
| 推理机 | 尚无 OWL 推理与一致性检查，`subClassOf` 以普通关系存储，不做运行时继承展开 |
| SPARQL | 未提供 SPARQL 端点；本体查询走 REST 与 MCP 工具 |
| RDF 导出 | 支持 OWL/XML 导出；Turtle / JSON-LD 导出待补 |
| 图数据库 | Neo4j 已预留配置与健康探测，图存储尚未启用，图谱由关系表实时计算 |
| Hive / ClickHouse | 已在连接器注册表声明类型，连接器实现待补 |
| Oracle | 连接与查询可用，Schema 自动同步待补 |
| 跨源联邦查询 | 同一连接内可跨资产 JOIN，跨连接联邦查询尚未支持 |

---

## 参与贡献

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交变更（中文 commit message，描述改动本身）
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 发起 Pull Request

---

## Star History

<a href="https://star-history.com/#854875058/ontology-driven-platform&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=854875058/ontology-driven-platform&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=854875058/ontology-driven-platform&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=854875058/ontology-driven-platform&type=Date" />
 </picture>
</a>

---

## 许可证

[MIT](LICENSE) © 元枢本体
