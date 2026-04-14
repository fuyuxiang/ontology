# Ontology-Driven Platform

本体驱动智能策略平台 — 基于本体建模的电信运营智能分析系统。

## 功能模块

| 模块 | 路由 | 说明 |
|------|------|------|
| 本体管理 | `/ontology` | 三层本体对象(Tier 1/2/3)的 CRUD、属性、关系、规则管理 |
| 关系画布 | `/dataflow` | 基于 vue-flow 的交互式图谱画布，dagre 自动布局 |
| 业务逻辑 | `/logic` | 规则引擎管理，条件表达式 + 动作执行 |
| 数据看板 | `/dashboard` | KPI 统计、Tier 分布、活动流、健康状态 |
| 智能对话 | `/copilot` | AI Copilot 流式对话，推理链展示 |
| 场景分析 | `/scene/*` | 宽带退单稽核 / 政企根因分析 / FTTR 续约策划 |
| 实体详情 | `/ontology/:id` | 属性 / 关系 / 规则 / 动作 / 血缘图谱 |

## 技术栈

**前端**
- Vue 3 + TypeScript + Vite
- Pinia 状态管理
- @vue-flow/core 图谱可视化
- dagre 自动布局算法

**后端**
- FastAPI + Uvicorn
- SQLAlchemy + SQLite
- Neo4j 图数据库 (可选)
- Passlib + JWT 认证

## 项目结构

```
ontology/
├── frontend/                # Vue 3 前端
│   ├── src/
│   │   ├── api/             # Axios API 层
│   │   ├── components/      # 通用组件 + Canvas 组件
│   │   ├── composables/     # 组合式函数 (useGraphLayout)
│   │   ├── store/           # Pinia stores
│   │   ├── types/           # TypeScript 类型定义
│   │   └── views/           # 页面视图
│   └── vite.config.ts
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/          # REST API 路由
│   │   ├── models/          # SQLAlchemy 模型
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # 业务服务 (graph, audit)
│   │   └── core/            # 安全、配置、依赖
│   ├── seed.py              # 种子数据
│   └── import_schema.py     # JSON Schema 导入器
└── ctl.ps1                  # 服务管理脚本
```

## 快速启动

```bash
# 1. 后端
cd backend
py -3.12 -m venv venv
./venv/Scripts/pip install -r requirements.txt
./venv/Scripts/python seed.py
./venv/Scripts/python import_schema.py
./venv/Scripts/python -m uvicorn app.main:app --port 8001

# 2. 前端
cd frontend
npm install
npm run dev
```

或使用管理脚本：

```powershell
.\ctl.ps1 start    # 启动前后端
.\ctl.ps1 stop     # 停止服务
.\ctl.ps1 restart  # 重启
.\ctl.ps1 status   # 查看状态
.\ctl.ps1 init     # 初始化数据库
```

启动后访问：
- 前端：http://localhost:5177
- 后端 API：http://localhost:8001
- API 文档：http://localhost:8001/docs

## 本体三层架构

| Tier | 定位 | 示例 |
|------|------|------|
| Tier 1 核心 | 业务基础实体 | Customer, Order, Product, Touchpoint |
| Tier 2 领域 | 运营领域对象 | Campaign, CustomerSegment, Strategy |
| Tier 3 场景 | 场景专属对象 | FTTRSubscription, InstallOrder, MetricFormula |

## 场景数据

三个业务场景的本体 Schema 位于 `材料/` 目录：
- `场景1-宽带装机退单稽核 本体Schema v2(1).json` — 退单稽核链路
- `scenario4_ge_kpi_ontology_v5(1).json` — 政企 KPI 指标血缘
- `fttr_renewal_ontology.json` — FTTR 续约策略

通过 `import_schema.py` 导入到数据库。

## License

Internal use only.
