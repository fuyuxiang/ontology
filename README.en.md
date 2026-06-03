<div align="center">

# Yuanshu Ontology

**Enterprise Ontology Intelligence Platform**

*Ontology-Driven · Semantic Web · Make Data Understandable · Make AI Trustworthy*

**[中文](README.md)** | **[English](README.en.md)**

[![Vue 3](https://img.shields.io/badge/Vue-3.5-4FC08D?logo=vue.js)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-6.x-3178C6?logo=typescript)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://python.org/)
[![OWL 2](https://img.shields.io/badge/W3C-OWL_2-005A9C)](https://www.w3.org/OWL/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## Overview

Yuanshu Ontology transforms scattered enterprise data assets into a unified, queryable, and executable semantic network. The platform provides an end-to-end workflow from **data integration** to **ontology modeling** to **agent applications**, enabling teams to build intelligent scenarios based on well-governed business semantics rather than raw tables and scripts.

### Key Highlights

- **Ontology-First Governance** — Aligned with W3C OWL 2 standards, supporting entity/property/relationship modeling, versioned publishing, and approval workflows
- **Multi-Source Heterogeneous Integration** — Unified connector framework covering MySQL, PostgreSQL, Oracle, SQL Server, Hive, ClickHouse, S3, FTP, Kafka, REST API
- **AI-Native Construction** — Four modeling approaches: document extraction, template instantiation, AI conversation, and manual entry; LLM-assisted mapping and hydration validation
- **Agent Orchestration** — ReAct-loop agents with tool calling, skill management, scenario automation, and full execution tracing
- **Production-Grade Pipeline** — Build → Review → Hydrate → Publish four-step workflow with 7 quality gates ensuring release quality

---

## Feature Overview

### Data Integration

| Capability | Description |
|-----------|-------------|
| Data Ingestion | Pluggable connectors — MySQL, PostgreSQL, Oracle, SQL Server, Hive, ClickHouse, S3, FTP/SFTP, Kafka, REST API |
| Asset Catalog | Automatic schema sync, data profiling, sample preview, tag-based discovery |
| Data Pipelines | Configurable ETL pipelines with scheduled and event-driven triggers |
| Data Lineage | Field-level lineage tracking with interactive visualization |
| Data Quality | Declarative quality rules, probe execution, time-series metric monitoring |

### Ontology Center

| Capability | Description |
|-----------|-------------|
| Manual Construction | Entity, property, relationship CRUD with drag-and-drop graph editing |
| Template Construction | Industry-standard templates for rapid domain modeling |
| Document Construction | Upload Word/PDF/Excel, LLM extracts entities and relationships via SSE streaming |
| Asset Construction | AI conversational ontology building based on integrated data assets |
| Object & Relationship Management | Three-tier entity browser with inheritance, search, and batch operations |
| Mapping Management | Semi-automatic ontology property ↔ physical field mapping (heuristic scoring + LLM fallback) |
| Graph Exploration | Force-directed dual-layer canvas (ontology schema layer + instance data layer), powered by AntV G6 |
| Ontology Publishing | Versioned Draft → Review → Hydrate → Publish pipeline with rollback support |

### Logic Layer

| Capability | Description |
|-----------|-------------|
| Rule Management | Declarative business rules with expression and structured condition modes |
| Function Management | Derived property computation functions with schema definition and test sandbox |
| Action Management | Parameterized business actions with preconditions and manual/automatic triggers |

### Agents & AI

| Capability | Description |
|-----------|-------------|
| Agent Management | Create, configure, and deploy ReAct-loop agents with injected ontology context |
| Skill Management | Register and manage callable tools — data queries, rule evaluation, action execution |
| Process Orchestration (AIP) | Visual workflow editor, multi-step agent pipelines + webhook triggers |
| Copilot | Embedded conversational assistant with full ontology/data/rule context awareness |
| Evaluation | Batch evaluation suites with expected output comparison and metric tracking |
| Tracing | Full execution tracing with tool call details and token consumption statistics |

### Governance & Operations

| Capability | Description |
|-----------|-------------|
| Access Control | Role-based access control (RBAC) with JWT authentication |
| Audit Logging | Operation audit trail with SQL logging and sensitive field masking |
| System Monitoring | Real-time health dashboard, API metrics, model usage tracking |
| Model Configuration | Multi-model management with unified provider/key/endpoint configuration |

---

## Ontology Build Pipeline

**Hydration Validation** — 4-stage real data verification (SSE streaming progress):

1. **Data Ingestion Validation** — Connector reachability, schema sync, sample preview, profile computation
2. **Ontology Instantiation** — Heuristic scoring (Token Jaccard + fuzzy matching + type compatibility) + LLM fallback
3. **Relationship Mapping Validation** — JOIN key existence check, same-connection sample JOIN queries
4. **Policy Output** — Primary key uniqueness assertion, required field null-rate check

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Frontend | Vue 3.5 · TypeScript 6 · Vite 8 · Pinia 3 · Ant Design Vue 4 |
| Visualization | VueFlow (workflow) · AntV G6 (graph) · Three.js / TresJS (3D) · D3-force |
| Backend | FastAPI 0.115 · Uvicorn · SQLAlchemy 2.0 · Pydantic 2 · Alembic |
| Auth | PyJWT · Passlib (bcrypt) · RBAC middleware |
| Database | SQLite (dev) / MySQL (prod) · Neo4j (graph store) · Redis (cache) |
| Connectors | MySQL · PostgreSQL · Oracle · SQL Server · Hive · ClickHouse · S3 · FTP · Kafka · HTTP |
| AI / LLM | OpenAI-compatible protocol · Tool Calling · SSE streaming · RDFLib (OWL 2) |
| Document Parsing | python-docx · pdfplumber · openpyxl · pandas |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+, pnpm 9+
- (Optional) MySQL 8, Redis, Neo4j

### Start Backend

```bash
cd backend
cp .env.example .env          # Configure DATABASE_URL, LLM_API_BASE, etc.
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Start Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

Visit `http://localhost:5173` for the UI, `http://localhost:8001/docs` for API documentation.

> On first launch, tables are auto-created, migrations run, and a default admin account (`admin` / `admin123`) is created.

---

## Configuration

Backend config file: `backend/.env`

```env
DATABASE_URL=sqlite:///./ontology.db
# DATABASE_URL=mysql+pymysql://user:pass@host:3306/ontology?charset=utf8mb4
LLM_API_BASE=https://your-llm-endpoint/v1
LLM_API_KEY=your-api-key
LLM_MODEL=your-model-name
SECRET_KEY=replace-with-strong-random-string
```

**Production recommendations:** Use MySQL for metadata storage · Generate a strong random `SECRET_KEY` · Store credentials in a key management service (KMS) · Change default passwords · Enable audit logging.

---

## Project Structure

```text
backend/
├── app/
│   ├── api/v1/                # REST endpoints (40+ route modules)
│   │   ├── builder.py         # Ontology build pipeline
│   │   ├── copilot.py         # Conversation & agent sessions
│   │   ├── data_plane/        # Connections, assets, lineage, quality, mapping
│   │   └── ...
│   ├── connectors/            # Pluggable database/storage connectors
│   ├── models/                # SQLAlchemy ORM models (25+ tables)
│   ├── services/
│   │   ├── agent/             # Agent orchestrator, tool router, graph engine
│   │   ├── aip/              # AIP scenario runner, scheduler, event bus
│   │   ├── builder/          # Hydration validation service
│   │   ├── data_plane/       # Asset, connection, lineage, quality services
│   │   └── ...
│   └── main.py
└── requirements.txt

frontend/
├── src/
│   ├── api/                   # Typed API client
│   ├── components/            # Shared components (canvas, lineage, ontology, etc.)
│   ├── composables/           # Vue composable utilities
│   ├── store/                 # Pinia state modules
│   ├── types/                 # TypeScript type definitions
│   ├── utils/owl/             # OWL 2 serialization utilities
│   └── views/                 # 42 page components covering 15 business domains
└── package.json
```

---

## Contributing

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

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

## License

[MIT](LICENSE) © Yuanshu Ontology
