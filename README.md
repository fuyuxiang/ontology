<div align="center">

# Yuanshu Ontology · Enterprise Ontology Intelligence Platform

*Anchored in ontology · Woven with semantics · Making data understandable · Making AI trustworthy*

**[English](README.md)** | **[中文](README.zh-CN.md)**

[![Vue 3](https://img.shields.io/badge/Vue-3.5-4FC08D?logo=vue.js)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-6.x-3178C6?logo=typescript)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://python.org/)
[![OWL](https://img.shields.io/badge/W3C-OWL-005A9C)](https://www.w3.org/OWL/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## Overview

**Yuanshu Ontology** is an enterprise-grade ontology intelligence platform for data governance and intelligent application building. Built on a three-layer architecture — **Semantic Layer, Power Layer, and Dynamic Layer** — it unifies business objects, relationships, rules, actions, and agents scattered across systems into a queryable, analyzable, executable, and evolvable enterprise semantic network.

> 💡 Use cases: Data asset governance · Business object modeling · AI agent building · Rule-driven analytics · Scenario-based operations · Cross-system orchestration.

<details>
<summary><b>📖 Table of Contents</b></summary>

- [Core Philosophy](#core-philosophy)
- [Key Capabilities](#key-capabilities)
- [System Architecture](#system-architecture)
- [Feature Modules](#feature-modules)
- [AI Copilot](#ai-copilot)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [License](#license)

</details>

---

## Core Philosophy

The platform moves enterprise data from static table structures into a business semantic space, enabling data, rules, processes, and AI applications to collaborate around unified business objects.

```text
┌──────────────────────────────────────────────┐
│              Dynamic Layer                    │
│  Scenario runtime / Agent orchestration /     │
│  Workflow execution / Feedback loops          │
├──────────────────────────────────────────────┤
│              Power Layer                      │
│  Rules / Functions / Actions / APIs /          │
│  Workflows                                    │
├──────────────────────────────────────────────┤
│              Semantic Layer                   │
│  Entities / Attributes / Relations /           │
│  Mappings / Data objects                      │
└──────────────────────────────────────────────┘
```

**Semantic Layer** — Defines core business objects and their relationships. Maps database tables, fields, and API data into a unified object model. Capabilities: entity/attribute/relation modeling, object graph, data source mapping, entity resolution, data lineage.

**Power Layer** — Describes business logic and execution capabilities above objects. Organizes rules, functions, actions, APIs, and workflows as reusable capability units. Capabilities: rule engine, compute functions, action encapsulation, API service publishing, SDK generation, visual workflow orchestration.

**Dynamic Layer** — Runs scenarios, orchestration, and feedback loops. Provides semantic objects and business capabilities to Copilot, Agent, workflow, and scenario applications. Capabilities: Copilot conversations, Agent tool calling, scenario apps, workflow execution, tracing, evaluation.

---

## Key Capabilities

| 🧱 Modeling & Integration | ⚙️ Logic & Execution | 🚀 Service & Operations |
|---|---|---|
| **Ontology Modeling** — Entity, attribute, relation, and object graph governance | **Rules & Actions** — Declarative rules, compute functions, executable actions | **Service Output** — API services, OSDK generation, Agent interfaces |
| **Data Integration** — Multi-source DB connections, table discovery, field mapping | **Workflow Orchestration** — Drag-and-drop visual workflows | **Scenario Apps** — MNP, FTTR, broadband audit, enterprise root-cause |
| **Hydration Verification** — 4-phase real-data validation before publishing | **AI Copilot** — Chat + Agent mode with ontology context | **Governance** — Versioning, approval, rollback, audit, tracing |

---

## System Architecture

```text
┌───────────────────────────────────────────────────────────────┐
│                          Frontend                              │
│   Vue 3 · TypeScript · Vite · Pinia · Ant Design Vue · VueFlow │
│   Ontology Modeling / Data Mapping / Workflow / Scenarios       │
└───────────────────────────┬───────────────────────────────────┘
                            │ HTTP · SSE · JWT
┌───────────────────────────┴───────────────────────────────────┐
│                          Backend                               │
│   FastAPI · SQLAlchemy · Pydantic · Uvicorn                    │
│   Object mgmt / Rule eval / Action exec / Agent / Audit / API  │
└───────┬─────────────────────────┬─────────────────────┬───────┘
        │                         │                     │
┌───────┴────────┐    ┌───────────┴────────────┐ ┌──────┴──────┐
│  Metadata DB   │    │   External Data Sources│ │     LLM     │
│ SQLite / MySQL │    │ MySQL · PostgreSQL ·   │ │ OpenAI-     │
│                │    │ Oracle · SQL Server    │ │ compatible  │
└────────────────┘    └────────────────────────┘ └─────────────┘
```

---

## Feature Modules

### Ontology Center

| Module | Route | Description |
|--------|-------|-------------|
| Data Workshop | `/datasource` | Data ingestion / pipelines / hydration drill |
| Ontology Modeling | `/browser` | 3-tier entity CRUD, attributes, relations, AI extraction |
| Ontology Studio | `/studio` | Card + triple-box view with object/instance/rule coverage |
| Ontology Graph | `/browser/graph` | Dual-layer canvas: ontology + data layer, force-directed layout |
| Field Mapping | `/data/mapping` | Ontology ↔ physical column mapping with coverage stats |
| Entity Resolution | `/data/resolution` | ID normalization and cross-source conflict arbitration |
| Publishing | `/ontology/publish` | Draft → validation → approval → go-live with full traceability |

#### Ontology Builder (4-Step Pipeline)

```text
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Step 1     │    │   Step 2     │    │   Step 3     │    │   Step 4     │
│   Build      │ →  │   Review     │ →  │   Hydrate    │ →  │   Publish    │
│              │    │              │    │              │    │              │
│ · Manual     │    │ · Per-object │    │ · Data ingest│    │ · Version    │
│ · Import     │    │   approval   │    │ · Field map  │    │   freeze     │
│ · Extract    │    │ · PK check   │    │ · Relation   │    │ · 7-gate     │
│ · Chat (AI)  │    │ · Rule/Action│    │   JOIN verify│    │   checklist  │
│              │    │   handling   │    │ · PK/null    │    │ · Rollback   │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

**Hydration Verification** — 4-phase real-data validation via SSE streaming:

1. **Data Ingest** — Verify connector reachability, sync schema, sample preview, compute profile
2. **Ontology Instantiation** — Heuristic scoring (token Jaccard + fuzzy match + type compatibility) with LLM fallback
3. **Relation Mapping** — JOIN key existence check, same-connection sample JOIN queries
4. **Strategy Output** — Primary key uniqueness, required field null-ratio checks

### Data Integration

| Module | Route | Description |
|--------|-------|-------------|
| Connections | `/data/connections` | MySQL / PostgreSQL / Oracle / SQL Server / Hive / ClickHouse / S3 / FTP / Kafka / REST |
| Asset Catalog | `/data/assets` | Asset registration, auto schema sync, profile, preview |
| Data Lineage | `/data/lineage` | End-to-end lineage with column-level visualization |
| Data Quality | `/data/quality` | Quality rules, probe execution, metric monitoring |
| Field Mapping | `/data/mapping` | Semi-automatic attribute ↔ column mapping (heuristic + LLM) |
| Execution Audit | `/data/audit` | SQL audit logs, rate limiting, data masking |

**Connector Capability Matrix:**

| Connector | Schema | Preview | Profile | SQL |
|-----------|:------:|:-------:|:-------:|:---:|
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

### Logic Center

| Module | Route | Description |
|--------|-------|-------------|
| Actions | `/logic/actions` | Business action parameters, preconditions, manual triggers |
| Functions | `/logic/functions` | Derived attributes / compute functions with schemas and tests |
| Rules | `/logic/rules` | Declarative rules: expression + structured condition dual mode |

### Ontology Services

| Module | Route | Description |
|--------|-------|-------------|
| API Service | `/service/api` | Auto-generated REST APIs from ontology |
| OSDK | `/service/osdk` | One-click TypeScript / Python SDK generation |
| Agent | `/service/agent` | Agent card grid + detail canvas |
| Workflow | `/service/workflow` | Drag-and-drop visual workflow canvas |

### Business Scenarios

| Scenario | Route | Highlights |
|----------|-------|------------|
| MNP Risk Alert | `/scene/mnp` | Risk graph + entity mapping + workflow timeline |
| FTTR Renewal | `/scene/fttr` | Renewal strategy and value analysis |
| Broadband Audit | `/scene/broadband` | List + dashboard + smart inbox + detail view |
| Enterprise Root Cause | `/scene/enterprise` | Cross-entity aggregated root cause analysis |

### Operations & Observability

| Module | Route | Description |
|--------|-------|-------------|
| Sandbox | `/harness` | End-to-end validation of rules, actions, Copilot |
| Agent Evaluation | `/ops/evals` | Eval suites, batch execution, result comparison |
| Traces | `/ops/traces` | Full-chain trace with tool call and token drill-down |

---

## AI Copilot

Copilot is an intelligent assistant woven throughout the platform. It reads ontology context, data sources, entity relationships, rules, and execution results to assist with queries, analysis, and decision-making.

| Mode | Use Cases |
|------|-----------|
| **Chat Mode** | Natural language Q&A, object explanation, rule description, data lineage queries |
| **Agent Mode** | Autonomous tool calling — data queries, entity resolution, rule evaluation, action triggers, workflow orchestration |

### Agent Tool Matrix

| Category | Tools | Description |
|----------|-------|-------------|
| 🧩 Ontology | `describe_ontology_model` · `get_entity_detail` | Schema and entity details |
| 🗄️ Data | `list_datasources` · `get_table_schema` · `query_datasource` | Sources, schemas, read-only SQL |
| 📊 Instance | `query_entity_data` | Query instance data via entity |
| 📐 Rules | `evaluate_rule` · `evaluate_all_rules` · `screen_users_by_rule` | Rule evaluation and screening |
| ⚡ Actions | `execute_action` | Trigger business actions |

---

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| 🎨 Frontend | Vue 3 + TypeScript + Vite + Pinia | Composition API · HMR · State management |
| 🧱 UI | Ant Design Vue + Vue Flow | Enterprise components · Force-directed canvas |
| 🌐 HTTP | Axios | JWT auto-injection · SSE streaming |
| 🚀 Backend | FastAPI + Uvicorn | ASGI · Async IO · OpenAPI docs |
| 🗃️ ORM | SQLAlchemy 2.0 + Pydantic 2 | Declarative models · Type-safe schemas |
| 🔐 Auth | PyJWT + Passlib (bcrypt) | Bearer Token · RBAC |
| 💾 Database | SQLite / MySQL | Switchable via `DATABASE_URL` |
| 🔌 Connectors | MySQL · PG · Oracle · SQL Server · Hive · ClickHouse | Multi-source heterogeneous access |
| 🤖 LLM | OpenAI-compatible protocol | Tool calling · SSE · Tracing |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- pnpm 9+ or npm 10+
- Optional: MySQL 8

### Start Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Start Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

Visit `http://localhost:5173`. API docs at `http://localhost:8001/docs`

> 💡 Auto-creates tables, runs migrations, and sets up default admin `admin / admin123` on startup.

---

## Configuration

Backend config: `backend/.env`

```env
DATABASE_URL=sqlite:///./ontology.db
# DATABASE_URL=mysql+pymysql://user:password@host:3306/ontology_platform?charset=utf8mb4
LLM_API_BASE=https://your-llm-api.com/v1
LLM_API_KEY=your-api-key
LLM_MODEL=your-model-name
SECRET_KEY=replace-with-strong-random-string
```

> ⚠️ Production: Use MySQL · Strong random SECRET_KEY · KMS for credentials · Change default password · Enable audit

---

## Project Structure

```text
backend/
├── app/
│   ├── api/v1/                    # REST API endpoints
│   │   ├── builder.py             # Ontology building (extract/chat/hydrate/finalize)
│   │   └── data_plane/            # Data plane (assets/connections/execute/quality)
│   ├── connectors/                # Database connectors
│   ├── models/                    # SQLAlchemy data models
│   ├── repositories/              # Data access layer
│   ├── services/
│   │   ├── agent/                 # Agent orchestration, tool router, graph engine
│   │   ├── builder/               # Hydration verification service
│   │   └── data_plane/            # Asset/connection/execute/quality/lineage
│   └── main.py
└── requirements.txt

frontend/
├── src/
│   ├── api/                       # API clients
│   ├── components/                # Shared components
│   ├── store/                     # Pinia state management
│   ├── types/                     # TypeScript types
│   └── views/
│       ├── builder/               # Ontology builder (4-step pipeline)
│       ├── datasource/            # Data integration
│       ├── ontology/              # Ontology browsing
│       ├── governance/            # Governance (permissions/audit/impact)
│       └── workspace/             # Workspace & dashboard
└── package.json
```

---

## Star History

<a href="https://star-history.com/#fuyuxiang/ontology&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=fuyuxiang/ontology&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=fuyuxiang/ontology&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=fuyuxiang/ontology&type=Date" />
 </picture>
</a>

---

## License

MIT © Yuanshu Ontology
