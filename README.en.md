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
[![MCP](https://img.shields.io/badge/MCP-2024--11--05-8A2BE2)](https://modelcontextprotocol.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## Overview

Yuanshu Ontology is an enterprise ontology intelligence platform. Its technical direction is **semantic-web-centric, end-to-end intelligent construction** — treating an ontology that conforms to W3C Semantic Web standards as the core asset, and closing the full loop from data ingestion, ontology modeling, mapping and binding, validation against real data, and versioned publishing through to AI consumption, all on one platform.

Within that direction, the ontology serves as the **semantic map between AI and enterprise data**: anchored downward to physical table columns, and upward providing LLMs with semantic coordinates that are reasonable, executable, and governable. The platform delivers an end-to-end workflow from data integration to agent applications, letting teams build intelligent scenarios on well-governed business semantics rather than raw tables and scripts.

---

## Why a Semantic Map

The real bottleneck for LLMs in the enterprise is not model capability — it is the **semantic gap**:

- Enterprise data exists in **physical form** — table `t_cbss_sub_info`, column `dev_num`, scattered across a dozen heterogeneous systems.
- Business users and AI think in **semantic form** — "has this high-value broadband subscriber filed any complaints about installation quality lately?"

Handing a raw schema to an LLM essentially asks the model to *guess* the correspondence between the physical and the business world. A wrong guess produces no feedback, a right guess cannot be reused, and the next scenario starts guessing all over again.

**An ontology is precisely the semantic map that closes this gap.** It is a formal, versioned, governable semantic structure anchored to both ends at once:

| Map element | Implementation in the ontology | What it anchors |
|-------------|-------------------------------|-----------------|
| **Coordinate system** | Object types + relations | How business concepts compose the world |
| **Legend** | Attributes + data types + constraints | The observable dimensions of each concept |
| **Routes** | Relation cardinality, graph traversal, lineage | How concepts reach one another |
| **Landing points** | Object bindings | Semantic attribute ↔ physical table column |
| **Capability markers** | Logic functions + actions | What can actually be done on this map |

With the map in place, AI stops guessing: it **queries the ontology** for semantic coordinates, **follows the bindings** down to real data, and **invokes the mounted capabilities** to compute and act — every step explainable, traceable, and governable.

---

## Technical Direction

### 1. Semantic-Web-Centric

The platform's core asset is an **ontology conforming to W3C Semantic Web standards**, not the private configuration of some AI application.

- The modeling layer aligns with **OWL 2**: classes, object properties, data properties, and named individuals, with support for `subClassOf` / `equivalentClass` / `disjointWith` / `domain` / `range` / `inverseOf`, covering **12 class expression types** (existential and universal quantification, min/max/exact cardinality, intersection/union/complement, hasValue) and **7 object property characteristics** (functional, inverseFunctional, transitive, symmetric, asymmetric, reflexive, irreflexive).
- It provides **bidirectional OWL/XML parsing and serialization** (frontend `utils/owl/`) plus **RDF/XML and Turtle import** (backend rdflib), so ontologies interoperate with standard tools such as Protégé.
- Four built-in modeling views ship out of the box: the native platform canvas, a **Protégé-style OWL editor** (15 components reproducing the class tree, property tree, and axiom panels), a **WebVOWL visualization**, and a **VocBench terminology view** — letting ontology engineers work in the paradigm they already know.

> The Semantic Web here is not decoration. It guarantees the ontology is an **interchangeable standard asset** rather than a proprietary schema locked inside the platform.

### 2. End-to-End Intelligent Construction

Going from raw data to AI-consumable semantic services closes the loop in six stages on a single platform. **Every stage involves an LLM, and every stage has a deterministic check behind it:**

```
① Ingest      ② Model       ③ Map          ④ Validate     ⑤ Publish     ⑥ Consume
Connection    5 entry       ObjectBinding  4-phase        Version       MCP / OSDK
  Asset       points        heuristic+LLM  hydration      snapshot      Agent / AIP
```

| Stage | Intelligence | Deterministic backstop |
|-------|-------------|------------------------|
| ① Ingest | Automatic document parsing and summarization (PDF/Word/Excel) | Automatic schema sync with diff; connectivity tests |
| ② Model | Document extraction / asset conversation / domain drill-down, streamed over SSE | Pydantic naming-convention validation with up to 5 retries |
| ③ Map | Token Jaccard + Chinese semantic expansion + type-compatibility matrix scoring; low-confidence attributes fall back to the LLM | Confidence tiers (high/medium/low) with human confirmation |
| ④ Validate | — | 4-phase hydration against real data: ingestion check → instantiation → relation JOIN verification → policy assertions |
| ⑤ Publish | — | 3 quality gates + approval workflow + full component snapshot + impact analysis |
| ⑥ Consume | ReAct agents, AIP workflow orchestration | Sandboxed execution, six-gate SQL pipeline, end-to-end auditing |

### 3. The Ontology as the AI Runtime Context

Once published, the ontology is not a document — it is **the executable context of an agent**:

- An **MCP Server** (JSON-RPC 2.0, protocol version `2024-11-05`) exposes **15 ontology tools** — attribute mapping lookup, instance queries, complex SQL, logic function execution, action execution, and Python workspace read/write/run. Any MCP client can adopt the ontology as a source of both knowledge and capability.
- **OSDK code generation** emits **TypeScript / Python SDKs** from the published ontology, so downstream systems access data through object semantics such as `Customer.list(client, {...})` instead of assembling SQL.
- **Ontology context injection** organizes objects, relations, data-source mappings, and available actions by tier and injects them into the agent system prompt, guiding tool selection inside the ReAct loop.

---

## Architecture

![Architecture](docs/images/architecture.png)

```
┌──────────────────────────────────────────────────────────────┐
│  Consumption   MCP Server (15 tools) · OSDK (TS/Py)           │
│                Ontology API · ReAct agents · AIP · Copilot    │
├──────────────────────────────────────────────────────────────┤
│  Capability    Logic functions (expression/sql/python)        │
│                Actions (6 executors) · Skills (LLM+AST+sandbox)│
├──────────────────────────────────────────────────────────────┤
│  Semantic      ★ ONTOLOGY CORE ★                              │
│                Object types · Attributes · Relations          │
│                Shared attributes/refs · OWL 2 modeling        │
│                Version snapshots · Approval · Impact analysis │
├──────────────────────────────────────────────────────────────┤
│  Binding       ObjectBinding (primary/enrichment/document)    │
│                Mapping suggestions · Hydration · Lineage      │
├──────────────────────────────────────────────────────────────┤
│  Data          Connections (5 categories) · Assets            │
│                Unified execution gate · Quality rules · Audit │
└──────────────────────────────────────────────────────────────┘
```

**Layering principle:** each layer depends only on the semantic contract of the one below. An agent does not know that `t_cbss_sub_info` exists — it knows only `CbssSubscriber`. Physical change is absorbed by the binding layer while the semantic layer stays stable.

---

## Capabilities

### Semantic Layer · Ontology Core

| Capability | Implementation |
|-----------|----------------|
| Object modeling | Three tiers (T1 core / T2 domain / T3 scenario); attributes stored in a dedicated table with constraints and example values |
| Relation modeling | `has_one` / `has_many` / `belongs_to` / `many_to_many`, with cardinality annotation and acyclicity declaration |
| OWL 2 editing | Protégé-style class tree, property tree, and axiom panels; 12 class expression types; 7 property characteristics |
| Standards interop | Bidirectional OWL/XML serialization; import from RDF/XML, Turtle, JSON, and Excel |
| Cross-ontology reuse | Shared attributes and shared refs (referencing an entire object across ontologies, read-only) |
| Graph exploration | Vue Flow + d3-force dual-layer canvas: ontology object layer (colored by tier) plus a toggleable data asset layer |
| Lineage view | BFS over a 1–5 hop entity neighborhood, rendered as an interactive graph |

### Semantic Layer · Versioning and Governance

| Capability | Implementation |
|-----------|----------------|
| Version pipeline | `draft → pending_approval → published`, plus a `rejected` branch and a quick-publish path |
| Quality gates | ① a data source must be bound ② attributes must be defined ③ attribute mapping coverage ≥ 50%; plus relation endpoint consistency checks |
| Version snapshots | Full snapshots of five component types — entities, attributes, relations, logic functions, actions — frozen at publish time |
| Rollback | Creates a **new version** from the target version (retaining `rollback_from` provenance) and still goes through approval, leaving history intact |
| Impact analysis | Dry-run preview of breaking changes before publishing; affected AIP scenes and agents are automatically flagged `stale` afterwards |
| Deletion safety | Before deleting a function or action, the platform reports which published versions, AIP scenes, and skills reference it, returning `safe_to_delete` |

### Binding Layer · From Semantics to Physical Data

| Capability | Implementation |
|-----------|----------------|
| Object bindings | Three roles: `primary` (main table), `enrichment` (supplementary), `document_evidence` |
| Mapping suggestions | Normalization + snake/camel/Chinese tokenization → Token Jaccard; 30+ Chinese business-term expansions; type-compatibility matrix; `difflib` fuzzy matching; column-comment hits; primary-key hints. Scores ≥ 0.8 high, ≥ 0.5 medium |
| LLM fallback | Low-confidence attributes are batched to the LLM, which returns candidate columns with reasons and scores |
| Hydration | **① Ingestion check** connectivity, schema sync, preview, profiling → **② Instantiation** attribute-to-column hit rate → **③ Relation verification** primary-key existence plus same-connection sample JOIN → **④ Policy assertions** primary-key uniqueness and required-field null rate (5% threshold). Progress streamed over SSE |
| Quality rules | `row_count_min` / `freshness` / `pk_uniqueness` / `null_ratio_max` auto-mounted on binding creation; 6 rule kinds across 6 probe types |
| Lineage | Resource-level `Asset → ObjectType → Action` lineage, written automatically from binding and execution events |

### Data Layer · Ingestion and Execution

| Capability | Implementation |
|-----------|----------------|
| Connector framework | Registered under a `(category, type)` composite key across 5 categories: database, object storage, file transfer, message queue, API |
| Implemented connectors | MySQL · PostgreSQL · SQL Server · Oracle · S3 (compatible with OSS/COS/OBS/MinIO) · FTP · SFTP · Kafka · REST |
| Credential security | Encrypted at rest with Fernet (`fernet://`), never stored in plaintext; masked when returned for editing |
| Connection pooling | In-process LIFO pool, 5-minute idle reclamation, capacity capped per connection config |
| Unified execution gate | **Six gates:** locator rewriting → sqlglot AST security review (DDL always denied, DML requires authorization) → table allowlist → parameter completeness → token-bucket rate limiting → execution with column-level masking and TTL caching |
| Parameterization | A single `:name` placeholder style at the business layer, converted per driver to `%(name)s` or `:name`, with a state machine that skips string literals and `::cast` |
| Data assets | Three kinds — `table`, `sql_view`, `document`; documents support upload, object storage, directory, API, and message queue sources |
| Execution audit | Every execution writes an `ExecutionLog`: SQL stored only as a hash plus a 500-character preview, parameters redacted to `<type:length>` |

### Capability Layer · Logic and Actions

| Capability | Implementation |
|-----------|----------------|
| Logic functions | Three forms: `expression` (restricted eval), `sql` (ontology object names rewritten to physical tables), `python` (sandboxed) |
| Function runtime | AST allowlist validation + `SIGALRM` timeouts (30s per call, 120s per chain) + max recursion depth 10 + A→B→A cycle detection + chained `call_function` + call-stack tracing |
| Embedded IDE | Bundled code-server lets you edit function and action sources directly under `workspace/`; watchdog observes file changes and auto-registers `@Function` decorator metadata |
| Action executors | Six kinds: `api_call` (httpx) · `sql_exec` (parameterized writes) · `call_function` · `custom_script` (5s timeout) · `modify_attribute` (dry-run) · `notification` (dry-run) |
| Skills | Multi-turn requirement gathering → LLM-generated tool code and schemas → **automatic AST validation** → sandbox testing → versioned publishing, with rollback and deprecation |

### Consumption Layer · AI Applications

| Capability | Implementation |
|-----------|----------------|
| ReAct agents | Up to 12 function-calling rounds; loop detection (two consecutive identical call signatures force convergence); final round sets `tool_choice=none` to force an answer |
| Reasoning visualization | The backend tags each tool as `ontology` / `logic` / `action` and streams `tool_start` / `tool_result`; the frontend composes a five-stage timeline — **intent recognition → ontology query → logic computation → action execution → answer generation** — collapsing adjacent duplicate steps as `×N` and rendering the ontology call chain beneath the reply |
| MCP Server | JSON-RPC 2.0 over HTTP with 15 tools; dual authentication via Bearer JWT or `X-API-Key`; every call is logged with volume, latency, and error-rate statistics |
| OSDK | Generates TypeScript / Python SDKs from the published ontology (client, one class per object, relation traversal methods, usage examples) |
| AIP orchestration | DAG ready-queue scheduling with conditional branches (`branch-true/false`), parallel nodes, sub-scenes, and cross-node data mapping (`node.field[0].sub` path syntax); 20+ node types |
| Three trigger types | A self-implemented 5-field cron scheduler (30-second polling, same-minute deduplication) · an event bus (matching entity actions) · webhooks (HMAC-SHA256 signature verification) |
| Evaluation and tracing | Evaluation suites assert on keywords and report pass rate and average latency; traces record input, output, duration, and tokens |

### Operations and Security

| Capability | Implementation |
|-----------|----------------|
| RBAC | Four built-in roles (admin / editor / operator / viewer), `{module}:{action}` permission format, JWT (HS256) with bcrypt |
| Auditing | Dual-track: operation audit (including before/after snapshots) and execution audit (SQL fingerprint, block reason, cache hit) |
| Masking | Encrypted connection credentials, masked model API keys, column-level result masking driven by `sensitivity_tags` (`pii` keeps the first 3 and last 4 characters; `sensitive` is fully masked) |
| Monitoring | Health probes across 10 services on a 30-second cycle, resource metrics, LLM call statistics, alerts pushed live over WebSocket, automatic historical cleanup |
| Model management | A model registry unifies multiple providers (OpenAI-compatible protocol), binds models per scenario, and supports connectivity testing |

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Frontend | Vue 3.5 · TypeScript 6 · Vite 8 · Pinia 3 · Vue Router 4 · Ant Design Vue 4.2 |
| Frontend visualization | Vue Flow 1.48 (ontology graph / lineage / AIP canvas) · d3-force (force-directed layout) · ECharts 6 (metric charts) · hand-written SVG semantic canvas |
| Semantic Web | OWL/XML parsing and serialization on the frontend (`utils/owl/`) · rdflib on the backend (RDF/XML, Turtle import) |
| Backend | FastAPI 0.115 · Uvicorn · SQLAlchemy 2.0 · Pydantic 2 · Alembic |
| Auth | python-jose (JWT HS256) · passlib + bcrypt · RBAC dependency injection |
| Database | SQLite (dev) / MySQL (prod) |
| Connectors | pymysql · psycopg2 · pymssql · oracledb · boto3 · ftplib / paramiko · native Kafka protocol · httpx |
| SQL safety | sqlglot (AST parsing, dialect adaptation, dangerous-construct blocking) |
| AI / LLM | OpenAI-compatible protocol · function calling · SSE streaming · MCP JSON-RPC 2.0 |
| Document parsing | python-docx · pdfplumber · openpyxl · pandas |
| Embedded IDE | code-server (editing logic function and action sources) |
| Operations | psutil (resource collection) · watchdog (hot function registration) · WebSocket push |

**Codebase size:** 237 backend Python modules / 51 database tables / 42 route modules / 351 API endpoints; 137 Vue components / 104 views / 32 business routes on the frontend.

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (npm)

### Configuration

Create `.env` in the **project root**:

```env
# Metadata store: SQLite for development, MySQL recommended for production
DATABASE_URL=sqlite:///./ontology.db
# DATABASE_URL=mysql+pymysql://user:pass@host:3306/ontology?charset=utf8mb4

# LLM (OpenAI-compatible protocol)
LLM_BASE_URL=https://your-llm-endpoint/v1
LLM_API_KEY=your-api-key
LLM_MODEL=your-model-name

# Required — startup aborts if missing
SECRET_KEY=replace-with-strong-random-string

# Optional
CREDENTIAL_ENCRYPTION_KEY=       # Credential encryption key; regenerated randomly each start if empty
ADMIN_INITIAL_PASSWORD=          # Initial admin password; defaults to "admin" if empty
CORS_ORIGINS=http://localhost:5177
```

### One-Command Startup

```bash
./start.sh          # Launches backend (8001), frontend (5177), and code-server (8443)
./stop.sh           # Stops everything
```

### Manual Startup

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Frontend
cd frontend
npm install
npm run dev
```

Open `http://localhost:5177` for the UI, `http://localhost:8001/docs` for API docs, and `http://localhost:8001/api/v1/mcp` for the MCP endpoint.

> On first launch the platform creates tables, runs compatibility migrations, and provisions an `admin` account (password from `ADMIN_INITIAL_PASSWORD`, or `admin` if unset). **In production, always set this variable and change the password after first login.**

### Production Recommendations

Use MySQL for metadata · generate strong `SECRET_KEY` and `CREDENTIAL_ENCRYPTION_KEY` values (otherwise stored credentials become undecryptable after a restart) · keep credentials in a KMS · disable code-server or restrict it to an internal network · enable MCP authentication (`MCP_REQUIRE_AUTH=true`) · narrow `CORS_ORIGINS`.

---

## Project Structure

```text
backend/
├── app/
│   ├── api/v1/                      # 42 route modules, 351 endpoints
│   │   ├── entities.py              # Object type CRUD, graph, lineage
│   │   ├── relations.py             # Relation modeling
│   │   ├── builder.py               # Document extraction / suggestions / hydration / commit
│   │   ├── ai_ontology.py           # AI-guided modeling (5-phase session)
│   │   ├── ai_builder_v2.py         # Domain drill-down modeling
│   │   ├── doc_builder.py           # Document-conversation modeling and mapping
│   │   ├── ontology_publish.py      # Versions / approval / snapshots / rollback
│   │   ├── impact_analysis.py       # Deletion and publish impact analysis
│   │   ├── mcp.py                   # MCP JSON-RPC server
│   │   ├── osdk.py                  # TS / Python SDK generation
│   │   ├── aip_*.py                 # Scene orchestration, execution, webhooks
│   │   └── data_plane/              # Connections, assets, execution, probes, lineage, quality, bindings
│   ├── connectors/                  # Pluggable connectors (composite-key registry)
│   ├── models/                      # 51 SQLAlchemy tables
│   └── services/
│       ├── agent/                   # ReAct orchestrator, graph engine, context builder
│       ├── aip/                     # Scene runner, scheduler, event bus, data mapper
│       ├── builder/                 # 4-phase hydration validation
│       ├── data_plane/              # Execution gate, mapping suggestions, bindings, quality, lineage
│       ├── function_runtime/        # Function registry, file watcher, unified sandbox
│       ├── action_executors/        # 6 action executors
│       └── mcp_tools/               # 15 MCP tools
└── requirements.txt

frontend/
├── src/
│   ├── views/
│   │   ├── builder/                 # Four modeling views
│   │   │   └── components/protege/  # Protégé-style OWL editor (15 components)
│   │   ├── ontology/                # Ontology list, detail, publishing
│   │   ├── dataflow/                # Dual-layer ontology graph canvas
│   │   ├── agents/                  # Agents, reasoning timeline, skill wizard
│   │   ├── aip/                     # Workflow orchestration canvas
│   │   └── ...                      # 104 view components in total
│   ├── components/canvas/           # Graph nodes, edges, toolbar, lineage graph
│   ├── utils/owl/                   # OWL/XML parser and serializer
│   ├── store/                       # 9 Pinia modules (including 50-step OWL editor undo)
│   └── api/                         # 29 typed API clients (with hand-rolled SSE parsing)
└── package.json

workspace/                           # Logic function / action sources (edited via code-server)
```

---

## Scope and Roadmap

The technical direction stays unchanged. The following capabilities are planned but not yet implemented, stated here plainly:

| Area | Current status |
|------|----------------|
| Reasoner | No OWL reasoning or consistency checking yet; `subClassOf` is stored as an ordinary relation with no runtime inheritance expansion |
| SPARQL | No SPARQL endpoint; ontology queries go through REST and MCP tools |
| RDF export | OWL/XML export is supported; Turtle and JSON-LD export are pending |
| Graph database | Neo4j configuration and health probes are in place, but graph storage is not enabled — graphs are computed live from relational tables |
| Hive / ClickHouse | Declared in the connector registry; connector implementations pending |
| Oracle | Connection and querying work; automatic schema sync is pending |
| Federated queries | Cross-asset JOINs work within one connection; cross-connection federation is not yet supported |

---

## Contributing

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (describe the change itself)
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
