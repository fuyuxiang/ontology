<div align="center">

# 元枢本体 · Yuanshu Ontology

**A Runnable Ontology Platform for Enterprise AI**

**AI-Native Construction · Business Semantic Modeling · Data Grounding · Logic & Action · Agent Runtime**

**One Map · One Body · One Loop**

Map the Business · Embody the Capability · Close the Intelligence Loop

**[中文](README.md)** · **[English](README.en.md)**

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-18%2B-green.svg)](https://nodejs.org/)

</div>

---

## What Is Yuanshu?

**Yuanshu Ontology is an open-source, enterprise-grade runnable ontology platform.**

It organizes business knowledge scattered across databases, documents, business rules, algorithmic models, and system interfaces into unified **objects, relations, states, events, logic, and actions**, forming an enterprise business semantics that business users, applications, and AI agents can all understand and invoke.

Yuanshu goes beyond "describing the business world": it connects to real data, carries business logic and models, defines executable actions, and exposes these capabilities through MCP, SDKs, agents, and intelligent workflows — making the ontology the **runtime business context** for enterprise AI.

Unlike traditional manual modeling that starts from a blank canvas, Yuanshu brings AI into ontology production, using document understanding, data asset analysis, semantic extraction, relation discovery, rule recognition, and intelligent mapping to assist the path from business knowledge to a runnable ontology.

> **Start from enterprise data and knowledge, construct business semantics automatically, and bring those semantics into actual operation.**

---

## Core Philosophy · One Map · One Body · One Loop

### One Map

**Business Semantic Map**

A unified description of what exists in the enterprise business world:

- Objects
- Attributes
- Relations
- States
- Events
- Evidence

So that business users, applications, and AI share one set of business semantics.

### One Body

**Runnable Ontology**

Organized on top of unified business semantics:

- Facts
- Rules
- Functions
- Models
- Actions
- Governance

Advancing business semantics from "understandable" to "runnable."

### One Loop

**Ontology Intelligence Loop**

Connecting end to end:

- Intelligent construction
- Data grounding
- Ontology services
- Business execution
- Result write-back
- Continuous evolution

Turning the ontology from a one-off model into a continuously evolving enterprise intelligence asset.

**Map the Business · Embody the Capability · Close the Intelligence Loop**

---

## Why a Runnable Ontology?

Enterprises already own plenty of data platforms, business systems, rules, models, and knowledge bases, but these assets usually exist in different forms:

- Data lives in tables, columns, and metrics;
- Business knowledge lives in policies, documents, and expert experience;
- Business logic lives in SQL, code, rule engines, and algorithmic models;
- Execution capability lives in APIs, workflows, and production systems;
- What AI actually faces, however, is often just fragmented data, text, and tools.

As AI moves from Q&A and assisted analysis into business judgment and execution, data access or RAG alone is not enough to describe an enterprise's complete business context reliably.

Yuanshu organizes these capabilities onto unified business objects through the ontology:

```text
        Data · Document · Rule · Model · API
                          │
                          ▼
          ┌────────────────────┐
          │ Business Semantics │
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
          │ Runnable Ontology  │
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
     Understand · Decide · Execute · Write Back
```

The ontology is therefore more than a schema and more than a static relationship diagram: it is a business runtime layer that enterprise AI can use continuously.

---

## Core Capabilities

### 1. AI-Native Automated Ontology Construction

Yuanshu treats AI as a collaborator in ontology production instead of requiring users to rely entirely on manual modeling.

It supports assisted identification from existing enterprise data and knowledge:

- Business objects and object attributes
- Business relations between objects
- States and business events
- Business rules and constraints
- Computational logic and model capabilities
- Executable actions
- Terminology, evidence, and governance information

The platform offers multiple intelligent construction entry points, including document-driven, data-asset-driven, interactive guided, and domain drill-down approaches.

The overall mechanism is:

**AI generation + programmatic validation + human confirmation**

```text
Business Materials / Data Assets
              │
              ▼
     Knowledge Parsing
              │
              ▼
   Candidate Extraction
              │
              ▼
 Object · Attribute · Relation
    Rule · Model · Action
              │
              ▼
Structural & Semantic Checks
              │
              ▼
   Expert Confirmation
              │
              ▼
      Ontology Model
```

AI improves the efficiency of knowledge discovery and modeling, deterministic programs handle structural constraints and quality validation, and experts confirm the critical business semantics.

---

### 2. Runnable Ontology Modeling

Yuanshu models more than entities and relations — it organizes complete ontology capabilities around real business operation.

#### Objects

Describe the entities, events, and business concepts in the enterprise business world.

Supported:

- Object Type
- Attribute
- Unique Identifier
- State
- Event
- Shared Attribute
- Shared Reference
- Layered ontology organization

#### Relations

Describe stable, well-defined business connections between objects.

Supported:

- Relation direction
- Relation cardinality
- One-to-one / one-to-many / many-to-many
- Relation constraints
- Cross-object references
- Graph traversal
- Relation lineage

#### Logic

Turn enterprise rules, computations, and expert experience into logic capabilities that systems and agents can invoke.

Supported:

- Expression
- SQL
- Python
- Function invocation
- Function composition
- Rules and constraints
- Model capability mounting

#### Action

Encapsulate system interfaces and business operations into execution capabilities associated with business objects.

Supported:

- API Call
- SQL Execution
- Function Call
- Custom Script
- Attribute Modification
- Notification

Actions can be combined with preconditions, permission control, approval, and execution auditing, so AI can invoke enterprise capabilities while execution boundaries stay explicit.

#### Governance

Governance runs through the entire process of ontology design, publishing, and operation.

Including:

- Ownership
- Permission control
- Version management
- Review and publishing
- Impact analysis
- Runtime monitoring
- Audit traceability
- Rollback and recovery

---

### 3. Data Grounding

The ontology model describes how the business world is understood; **Data Grounding** connects those business definitions to real enterprise data.

Yuanshu establishes the mapping between business objects and physical data through `ObjectBinding`.

Supported:

- Primary data binding
- Enrichment data binding
- Document evidence binding
- Attribute mapping suggestions
- Data type compatibility checks
- Primary key identification
- LLM-assisted mapping
- Relation validation
- Data quality checks
- Data lineage

```text
Physical Data
Database / Table / Document / API
                  │
                  ▼
           Object Binding
                  │
                  ▼
Object · Attribute · Relation · Event · Evidence
                  │
                  ▼
          Ontology Instance
```

Yuanshu draws an explicit distinction:

**Ontology modeling** produces the business semantic specification;

**Data grounding** maps that specification onto real business facts;

The two work together as separate processes.

---

### 4. Validation Against Real Data

Once data binding is complete, Yuanshu can validate the connection quality between ontology and data against real data.

The validation process covers:

1. Data source connectivity and schema checks
2. Object attribute instantiation validation
3. Object relation and JOIN validation
4. Data quality and policy assertions

Combined with data quality rules, mapping confidence, and runtime probes, this reduces cases where the model is defined correctly but cannot actually run against the data.

---

### 5. Logic and Action Runtime

A published ontology is not only queryable — it can directly carry business execution capability.

#### Logic Runtime

Logic functions support:

- Expression
- SQL
- Python

And provide:

- AST security validation
- Sandboxed execution
- Call timeouts
- Call chain tracing
- Nested function invocation
- Circular call detection

An online workspace is also available for maintaining Logic and Action source code directly.

#### Action Runtime

The platform provides a unified Action Executor that abstracts capabilities across different systems into governable business actions.

Actions are associated with ontology objects, so callers focus on:

> "which business action to perform on which business object"

rather than the underlying:

> "which interface to call, which table to modify, which column to update."

---

### 6. Ontology Services for AI and Agents

A published ontology can serve as the runtime business context for AI agents.

Yuanshu organizes:

- Objects
- Attributes
- Relations
- Data mappings
- Logic
- Action
- Permission information

into capabilities that agents can understand and invoke.

#### MCP Server

A built-in MCP Server exposes ontology capabilities to external agents and MCP clients over a standard protocol.

MCP tools currently cover these categories:

- Ontology queries
- Object instance queries
- Attribute mapping queries
- Data access
- Logic execution
- Action execution
- Python Workspace

Supported:

- JSON-RPC 2.0
- Bearer JWT
- API Key
- Call logging
- Call statistics

#### Ontology SDK

Yuanshu can generate the following automatically from a published ontology:

- TypeScript SDK
- Python SDK

Business applications can develop directly against object semantics, without propagating physical table structures into upper layers.

#### ReAct Agent

A built-in agent runtime can operate on ontology context:

```text
   Understand Intent
          ↓
     Query Ontology
          ↓
Retrieve Business Facts
          ↓
      Invoke Logic
          ↓
     Execute Action
          ↓
    Generate Result
```

Agent tool invocation supports streaming traces and call chain visualization.

---

### 7. Intelligent Workflow Orchestration

For business tasks requiring multi-step coordination, Yuanshu provides visual workflow orchestration.

Supported:

- DAG execution
- Conditional branching
- Parallel nodes
- Subflows
- Cross-node data mapping
- Logic invocation
- Action invocation
- Agent nodes
- Scheduled triggers
- Event triggers
- Webhook

The ontology provides unified business objects and capabilities; the workflow organizes how those capabilities run together.

---

### 8. Full Ontology Lifecycle Governance

Yuanshu manages the ontology as a long-lived enterprise asset.

#### Version Lifecycle

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

Supported:

- Draft management
- Publishing approval
- Version snapshots
- Version comparison
- Rollback
- Breaking change analysis
- Dependency checks
- Deletion protection

Changes to the ontology, Logic, and Action can be tracked, along with analysis of their impact on published capabilities and upper-layer applications.

---

### 9. Data Integration and Connectors

Yuanshu provides a unified data connector framework.

Currently supported:

#### Database

- MySQL
- PostgreSQL
- SQL Server
- Oracle

#### Object Storage

- Amazon S3
- MinIO
- S3-compatible storage such as OSS / COS / OBS

#### File Transfer

- FTP
- SFTP

#### Streaming

- Kafka

#### API

- REST API

Data assets are uniformly abstracted as:

- Table
- SQL View
- Document

providing a single data entry point for ontology construction and data grounding.

---

### 10. Security and Governance

An enterprise ontology needs more than unified semantics — it needs data access and action execution to stay under control.

Yuanshu provides:

- RBAC permission system
- JWT authentication
- API Key authentication
- Connection credential encryption
- Sensitive field masking
- SQL AST security checks
- Table-level access control
- Parameterized queries
- Execution rate limiting
- Operation auditing
- Execution auditing
- Service health monitoring
- LLM call statistics

Permissions, execution, and auditing run through the entire chain of data, ontology, Logic, Action, and agent invocation.

---

## Full Ontology Lifecycle

Yuanshu covers the complete lifecycle from business knowledge entering the platform to the ontology entering AI and business operation.

```text
  Knowledge & Data
      │
      ▼
  AI Construction
      │
      ▼
  Ontology Modeling
      │
      ▼
  Data Grounding
      │
      ▼
  Validation & Publishing
      │
      ▼
  Ontology Services
      │
      ▼
  Logic / Action / Agent
      │
      ▼
  Business Write-Back
      │
      ▼
  Runtime Feedback ─────► Continuous Evolution
                              │
      ▲                       │
      └───────────────────────┘
```

This is also Yuanshu's core technical direction:

> **Map the Business · Embody the Capability · Close the Intelligence Loop**

---

## Architecture

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
│   Database | Warehouse | Document | Object Storage            │
│   Kafka | API                                                 │
└───────────────────────────────────────────────────────────────┘

     Permission | Version | Approval | Audit | Monitor
              Governance across all layers
```

---

## AI Construction and Deterministic Execution

Yuanshu distinguishes two classes of problems by design.

### Problems Suited to AI

For example:

- Understanding business documents
- Discovering candidate business objects
- Completing attributes
- Identifying relations
- Extracting rules
- Generating mapping suggestions
- Generating Logic / Skills

These steps take full advantage of the semantic understanding of large models.

### Problems That Must Execute Deterministically

For example:

- Schema validation
- Data type validation
- Primary key checks
- JOIN validation
- Permission checks
- SQL security checks
- Action execution
- Publishing approval
- Version snapshots
- Audit records

These steps are handled by deterministic programs and governance mechanisms.

Yuanshu's AI principle is therefore not:

> **let the LLM decide everything**

but:

> **let AI handle understanding and generation, let programs handle validation and execution, and let humans make the final call at critical points.**

---

## Openness and Interoperability

Yuanshu positions itself as a **runnable enterprise ontology platform**, while also supporting data exchange with standard ontologies and external tools.

Currently supported:

- OWL/XML
- RDF/XML
- Turtle
- JSON
- Excel

Along with:

- Native platform visual modeling
- Protégé-style editing interface
- WebVOWL visualization
- Terminology view

These capabilities serve model exchange, migration of existing ontologies, and collaboration with professional ontology engineering, without constraining Yuanshu's own ontology runtime model.

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

Create `.env` in the project root:

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

Linux / macOS:

```bash
./start.sh
```

Windows:

```powershell
.\start.bat
```

Once started:

| Service     | Address                            |
| ----------- | ---------------------------------- |
| Web UI      | `http://localhost:5177`            |
| API         | `http://localhost:8001`            |
| API Docs    | `http://localhost:8001/docs`       |
| MCP Server  | `http://localhost:8001/api/v1/mcp` |
| Code Server | `http://localhost:8443`            |

The first startup initializes the database and creates an administrator account automatically.

> For production, configure a strong `SECRET_KEY`, `CREDENTIAL_ENCRYPTION_KEY`, and administrator password, and restrict access to Code Server, CORS, and MCP.

Stop the services:

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

## Tech Stack

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

## Project Structure

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

## Design Principles

Yuanshu follows several core principles.

### Business Semantics First

Upper-layer applications and AI should work against stable business objects rather than depending directly on underlying tables and columns.

### AI for Construction, Determinism for Execution

AI is used for understanding, discovery, and generation; deterministic programs handle validation, execution, and governance.

### Ontology as Runtime

The ontology is a runtime business context shared by applications, agents, and business processes — not a static document produced once modeling ends.

### Govern Everything

Objects, relations, Logic, Action, data access, and agent execution should all have explicit permission, version, and audit boundaries.

### Build Once, Reuse Across Applications

Unified business semantics and capabilities should be continuously reusable across multiple agents, workflows, and business applications, instead of being rebuilt per scenario.

---

## Contributing

Contributions to Yuanshu are welcome.

We especially welcome contributions in these areas:

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

Contribution flow:

1. Fork this repository

2. Create a feature branch

   ```bash
   git checkout -b feature/amazing-feature
   ```

3. Commit your changes

4. Push the branch

   ```bash
   git push origin feature/amazing-feature
   ```

5. Open a Pull Request

For larger feature designs, we recommend discussing the approach in an Issue first.

---

## Community

If you are:

- Researching enterprise ontologies and AI agents;
- Looking to improve automated ontology construction;
- Building new data connectors;
- Interested in contributing new Logic / Action / MCP tools;
- Interested in enterprise semantic modeling, knowledge engineering, or agent runtimes;

you are welcome to join the discussion through GitHub Issues and Pull Requests.

---

## License

[MIT License](LICENSE)

---

<div align="center">

### 元枢本体 · Yuanshu Ontology

**Make enterprise business understandable, intelligent capability runnable, and ontology assets evolvable.**

**Map the Business · Embody the Capability · Close the Intelligence Loop**

</div>
