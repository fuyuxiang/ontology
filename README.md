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
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 项目简介

元枢本体将分散在各系统中的企业数据资产转化为统一、可查询、可执行的语义网络。平台提供从**数据接入**到**本体建模**再到**智能体应用**的端到端工作流，让团队基于治理良好的业务语义构建智能场景，而非直接操作裸表和脚本。

### 核心亮点

- **本体优先治理** — 对齐 W3C OWL 2 标准，支持实体/属性/关系建模、版本化发布与审批流程
- **多源异构接入** — 统一连接器框架，覆盖 MySQL、PostgreSQL、Oracle、SQL Server、Hive、ClickHouse、S3、FTP、Kafka、REST API
- **AI 原生构建** — 支持文档抽取、模板实例化、AI 对话、手动录入四种建模方式，LLM 辅助映射与注水验证
- **智能体编排** — ReAct 循环 Agent，工具调用、技能管理、场景自动化，全链路执行追踪
- **生产级流水线** — 构建 → 审核 → 注水 → 发布四步流程，7 项质量门禁确保上线质量

---

## 系统架构

![ed8bd138-1c86-4393-b56a-97d2dbe182a6](/Users/fuyuxiang/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/fuyuxiangee_cbf4/temp/InputTemp/ed8bd138-1c86-4393-b56a-97d2dbe182a6.png)

---

## 功能全景

### 数据集成

| 能力 | 说明 |
|-----|------|
| 数据接入 | 可插拔连接器 — MySQL、PostgreSQL、Oracle、SQL Server、Hive、ClickHouse、S3、FTP/SFTP、Kafka、REST API |
| 资产目录 | 自动 Schema 同步、数据画像、样本预览、标签化发现 |
| 数据管道 | 可配置 ETL 管道，支持定时调度与事件驱动触发 |
| 数据血缘 | 字段级血缘追踪，交互式可视化 |
| 数据质量 | 声明式质量规则、探针执行、指标时序监控 |

### 本体中心

| 能力 | 说明 |
|-----|------|
| 手动构建 | 实体、属性、关系 CRUD，拖拽式图编辑 |
| 模板构建 | 行业标准模板，快速领域建模 |
| 文档构建 | 上传 Word/PDF/Excel，LLM 通过 SSE 流式抽取实体与关系 |
| 资产构建 | 基于已接入数据资产的 AI 对话式本体构建 |
| 对象与关系管理 | 三层级实体浏览器，支持继承、搜索、批量操作 |
| 映射管理 | 本体属性 ↔ 物理字段半自动映射（启发式评分 + LLM 兜底） |
| 图谱探索 | 力导向双层画布（本体 Schema 层 + 实例数据层），基于 AntV G6 |
| 本体发布 | 版本化 草稿 → 审核 → 注水 → 发布 流水线，支持回滚 |

### 逻辑层

| 能力 | 说明 |
|-----|------|
| 规则管理 | 声明式业务规则，表达式与结构化条件双模式 |
| 函数管理 | 派生属性计算函数，含 Schema 定义与测试沙箱 |
| 行动管理 | 参数化业务行动，支持前置条件与手动/自动触发 |

### 智能体与 AI

| 能力 | 说明 |
|-----|------|
| 智能体管理 | 创建、配置、部署 ReAct 循环 Agent，注入本体上下文 |
| 技能管理 | 注册与管理可调用工具 — 数据查询、规则求值、行动执行 |
| 流程编排 (AIP) | 可视化流程编辑器，多步骤 Agent 管道 + Webhook 触发 |
| Copilot | 内嵌对话助手，具备本体/数据/规则全上下文感知 |
| 评测 | 批量评测套件，预期输出对比与指标追踪 |
| 追踪 | 全链路执行追踪，工具调用明细与 Token 消耗统计 |

### 治理与运维

| 能力 | 说明 |
|-----|------|
| 权限控制 | 基于角色的访问控制 (RBAC)，JWT 认证 |
| 审计日志 | 操作审计链路，SQL 日志记录与敏感字段脱敏 |
| 系统监控 | 实时健康看板、API 指标、模型用量追踪 |
| 模型配置 | 多模型管理，供应商/密钥/端点统一配置 |

---

## 本体构建流水线

![f515b39c-83bc-4b85-aac8-566a618cce74](/Users/fuyuxiang/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/fuyuxiangee_cbf4/temp/InputTemp/f515b39c-83bc-4b85-aac8-566a618cce74.png)

**水合验证** — 4 阶段真实数据验证（SSE 流式推送进度）：

1. **数据接入验证** — 连接器可达性、Schema 同步、样本预览、画像计算
2. **本体实例化** — 启发式评分（Token Jaccard + 模糊匹配 + 类型兼容性）+ LLM 兜底
3. **关系映射验证** — JOIN 键存在性检查、同连接采样 JOIN 查询
4. **策略输出** — 主键唯一性断言、必填字段空值率检查

---

## 技术栈

| 层级 | 技术选型 |
|-----|---------|
| 前端框架 | Vue 3.5 · TypeScript 6 · Vite 8 · Pinia 3 · Ant Design Vue 4 |
| 可视化 | VueFlow（流程编排）· AntV G6（图谱）· Three.js / TresJS（3D）· D3-force |
| 后端框架 | FastAPI 0.115 · Uvicorn · SQLAlchemy 2.0 · Pydantic 2 · Alembic |
| 认证鉴权 | PyJWT · Passlib (bcrypt) · RBAC 中间件 |
| 数据库 | SQLite（开发）/ MySQL（生产）· Neo4j（图存储）· Redis（缓存） |
| 连接器 | MySQL · PostgreSQL · Oracle · SQL Server · Hive · ClickHouse · S3 · FTP · Kafka · HTTP |
| AI / LLM | OpenAI 兼容协议 · Tool Calling · SSE 流式 · RDFLib (OWL 2) |
| 文档解析 | python-docx · pdfplumber · openpyxl · pandas |

---

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+，pnpm 9+
- （可选）MySQL 8、Redis、Neo4j

### 启动后端

```bash
cd backend
cp .env.example .env          # 配置 DATABASE_URL、LLM_API_BASE 等
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### 启动前端

```bash
cd frontend
pnpm install
pnpm dev
```

访问 `http://localhost:5173`，API 文档地址 `http://localhost:8001/docs`。

> 首次启动自动建表、执行迁移并创建默认管理员账户（`admin` / `admin123`）。

---

## 配置说明

后端配置文件：`backend/.env`

```env
DATABASE_URL=sqlite:///./ontology.db
# DATABASE_URL=mysql+pymysql://user:pass@host:3306/ontology?charset=utf8mb4
LLM_API_BASE=https://your-llm-endpoint/v1
LLM_API_KEY=your-api-key
LLM_MODEL=your-model-name
SECRET_KEY=replace-with-strong-random-string
```

**生产部署建议：** 使用 MySQL 存储元数据 · 生成高强度随机 `SECRET_KEY` · 凭据托管至密钥管理服务 (KMS) · 修改默认密码 · 开启审计日志。

---

## 项目结构

```text
backend/
├── app/
│   ├── api/v1/                # REST 接口（40+ 路由模块）
│   │   ├── builder.py         # 本体构建流水线
│   │   ├── copilot.py         # 对话与 Agent 会话
│   │   ├── data_plane/        # 连接、资产、血缘、质量、映射
│   │   └── ...
│   ├── connectors/            # 可插拔数据库/存储连接器
│   ├── models/                # SQLAlchemy ORM 模型（25+ 表）
│   ├── services/
│   │   ├── agent/             # Agent 编排器、工具路由、图引擎
│   │   ├── aip/              # AIP 场景运行器、调度器、事件总线
│   │   ├── builder/          # 注水验证服务
│   │   ├── data_plane/       # 资产、连接、血缘、质量服务
│   │   └── ...
│   └── main.py
└── requirements.txt

frontend/
├── src/
│   ├── api/                   # 类型化 API 客户端
│   ├── components/            # 共享组件（画布、血缘、本体等）
│   ├── composables/           # Vue 组合式工具函数
│   ├── store/                 # Pinia 状态模块
│   ├── types/                 # TypeScript 类型定义
│   ├── utils/owl/             # OWL 2 序列化工具
│   └── views/                 # 42 个页面组件，覆盖 15 个业务域
└── package.json
```

---

## 参与贡献

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交变更 (`git commit -m 'Add amazing feature'`)
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

[MIT](LICENSE) © 元数本体
