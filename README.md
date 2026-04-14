<div align="center">

# Ontology-Driven Intelligent Strategy Platform

**本体驱动智能策略平台**

*将领域知识图谱与 AI 推理引擎深度融合的下一代运营决策系统*

[![Vue 3](https://img.shields.io/badge/Vue-3.5-4FC08D?logo=vue.js)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?logo=typescript)](https://www.typescriptlang.org/)
[![Neo4j](https://img.shields.io/badge/Neo4j-Graph_DB-008CC1?logo=neo4j)](https://neo4j.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## Overview

传统运营系统面临的核心痛点：业务规则散落在代码中、数据关系隐藏在表结构里、策略决策依赖人工经验。

本平台通过 **本体建模 (Ontology Modeling)** 将业务领域知识结构化为三层对象体系，结合 **知识图谱可视化**、**规则引擎** 和 **AI Copilot**，实现从数据到洞察到行动的闭环。

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Copilot (LLM + RAG)                   │
├──────────┬──────────┬──────────┬──────────┬─────────────────┤
│  本体管理 │ 关系画布  │ 规则引擎  │ 数据看板  │   场景分析      │
├──────────┴──────────┴──────────┴──────────┴─────────────────┤
│              Ontology Core (三层本体模型)                     │
│         Tier 1 核心 → Tier 2 领域 → Tier 3 场景              │
├─────────────────────────────────────────────────────────────┤
│         Graph Engine (Neo4j + SQLite + BFS/DFS)             │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### Knowledge Graph Canvas
基于 **vue-flow** 的交互式知识图谱画布，支持 dagre 自动布局、节点拖拽、缩放漫游、实时关系探索。34+ 本体对象、40+ 语义关系一览无余。

### Three-Tier Ontology Architecture

独创的三层本体建模体系，从核心业务实体到场景专属对象逐层展开：

| Tier | 定位 | 对象数 | 示例 |
|------|------|--------|------|
| **Tier 1** 核心层 | 业务基础实体 | 7 | Customer, Order, Product, Touchpoint, Contract |
| **Tier 2** 领域层 | 运营领域对象 | 4 | Campaign, CustomerSegment, Strategy, RuleSet |
| **Tier 3** 场景层 | 场景专属对象 | 23 | FTTRSubscription, InstallOrder, MetricFormula |

### Rule Engine & Strategy Automation
声明式规则引擎，支持条件表达式编写、优先级管理、触发执行与效果追踪。将业务逻辑从代码中解耦，运营人员可直接配置策略规则。

### Data Lineage Visualization
实体血缘图谱，BFS N 跳邻域遍历，可视化展示数据流向与依赖关系。支持 1-3 跳深度探索，快速定位上下游影响链路。

### AI Copilot
集成 LLM 的智能对话助手，支持流式响应、推理链展示、上下文关联推荐。自然语言驱动的本体查询与策略建议。

### Multi-Scenario Analysis
内置三大电信运营场景的完整本体 Schema：

| 场景 | 对象数 | 关系数 | 业务目标 |
|------|--------|--------|----------|
| **宽带退单稽核** | 8 | 7 | 识别虚假退单，降低装机失败率 |
| **政企根因分析** | 9 | 13 | KPI 指标血缘追溯，定位业绩根因 |
| **FTTR 续约策划** | 6 | 10 | 精准续约方案，提升用户 ARPU |

## Tech Stack

```
Frontend                          Backend                         Data Layer
─────────────────                 ─────────────────               ─────────────────
Vue 3.5 + TypeScript              FastAPI 0.115                   SQLite (default)
Vite 6 (HMR + Build)             Uvicorn (ASGI)                  Neo4j (graph, optional)
Pinia (State)                     SQLAlchemy 2.0 (ORM)            JSON Schema Import
vue-flow (Graph Canvas)           Pydantic 2.11 (Validation)
dagre (Auto Layout)               JWT + Passlib (Auth)
Axios (HTTP)                      Alembic (Migration)
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         Frontend (Vue 3)                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────┐ │
│  │ Ontology │ │  Canvas  │ │  Logic   │ │Dashboard │ │Copilot│ │
│  │ Explorer │ │ vue-flow │ │  Rules   │ │  Stats   │ │  LLM  │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬───┘ │
│       └─────────────┴────────────┴─────────────┴───────────┘     │
│                         Pinia Store Layer                        │
│                         Axios API Client                         │
├──────────────────────────────────────────────────────────────────┤
│                      REST API (FastAPI)                           │
│  /entities  /relations  /rules  /dashboard  /copilot  /auth      │
├──────────────────────────────────────────────────────────────────┤
│                      Service Layer                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ Graph Engine │  │ Rule Engine │  │ Audit Trail │              │
│  │ BFS/DFS/DAG │  │ Eval + Exec │  │  Event Log  │              │
│  └──────┬──────┘  └─────────────┘  └─────────────┘              │
├─────────┴────────────────────────────────────────────────────────┤
│  SQLAlchemy ORM          │           Neo4j Driver                │
│  SQLite / PostgreSQL     │           Graph Database              │
└──────────────────────────┴───────────────────────────────────────┘
```

## Quick Start

```bash
# Clone
git clone https://github.com/854875058/ontology-driven-platform.git
cd ontology-driven-platform

# Backend
cd backend
python -m venv venv
./venv/Scripts/pip install -r requirements.txt
./venv/Scripts/python seed.py              # 种子数据
./venv/Scripts/python import_schema.py     # 导入场景 Schema
./venv/Scripts/python -m uvicorn app.main:app --port 8001

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

访问 **http://localhost:5177** 开始使用。API 文档：**http://localhost:8001/docs**

## Project Structure

```
├── frontend/
│   ├── src/
│   │   ├── api/                 # API client layer
│   │   ├── components/
│   │   │   ├── canvas/          # Graph canvas components (OntologyNode, EdgeLabel...)
│   │   │   └── common/          # Shared UI components
│   │   ├── composables/         # useGraphLayout (dagre integration)
│   │   ├── store/               # Pinia stores (ontology, rules, auth, copilot)
│   │   ├── types/               # TypeScript type definitions
│   │   └── views/               # Page views (7 modules)
│   └── vite.config.ts
├── backend/
│   ├── app/
│   │   ├── api/v1/              # REST endpoints
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── services/            # Business logic (graph traversal, audit logging)
│   │   └── core/                # Security (JWT), config, dependencies
│   ├── seed.py                  # Seed data (11 core entities, 14 relations, 9 rules)
│   └── import_schema.py         # JSON Schema importer (3 scenarios, 21 objects, 235 attrs)
└── ctl.ps1                      # Service management (start/stop/restart/status/init)
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/entities` | 实体列表 (支持 tier/status/namespace/search 筛选) |
| `GET` | `/api/v1/entities/graph` | 全量知识图谱 (nodes + edges) |
| `GET` | `/api/v1/entities/{id}/lineage` | 实体血缘 (BFS N-hop traversal) |
| `POST` | `/api/v1/entities` | 创建实体 |
| `GET` | `/api/v1/relations` | 关系列表 |
| `POST` | `/api/v1/relations` | 创建关系 |
| `GET` | `/api/v1/rules` | 规则列表 |
| `POST` | `/api/v1/rules/{id}/execute` | 执行规则 |
| `GET` | `/api/v1/dashboard/stats` | 看板统计 |
| `POST` | `/api/v1/copilot/chat` | AI 对话 (SSE streaming) |
| `POST` | `/api/v1/auth/login` | 用户认证 |

## License

MIT
