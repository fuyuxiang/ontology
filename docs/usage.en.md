# Usage Guide

[Back to README](../README.en.md) · [中文](usage.md)

This guide starts with your first business dataset after login and explains how to publish ontology capabilities for applications and agents. See the [README](../README.en.md) for installation, startup, and initial administrator configuration.

## The shortest path

```text
Connections / Assets → Object definitions → Data mapping → Final review → Validate and publish
                                                                          ↓
                                                     Functions / Actions → Skills → Agent
                                                                          ↓
                                                                   MCP / API / SDK
```

For the first login, use `admin` and the `ADMIN_INITIAL_PASSWORD` configured during initialization. There is no default administrator password. Configure an available model endpoint and credentials before AI construction or chat; real data access also requires the corresponding data connection.

## 1. Connect data and register assets

Create a connection under Data Connections, enter the service address, parameters, and credentials, and test it. Then register the required tables, SQL views, or documents in the Asset Catalog.

Start with a manageable business table that has a stable primary key. Inspect its fields, types, and data preview before adding other objects. Document construction accepts business materials; legacy `.doc/.xls/.ppt` conversion requires LibreOffice `soffice`.

Object bindings include Primary data, Enrichment data, and document evidence. The primary binding defines instance identity; enrichment data requires explicit join keys, while document evidence provides business context.

The Kafka connector provides connection testing, topic listing, and bounded message sampling. Data assets can refresh periodically according to their configuration.

Related code: [Connection API](../backend/app/api/v1/data_plane/connections.py), [Asset service](../backend/app/services/data_plane/asset_service.py), [Kafka connector](../backend/app/connectors/kafka.py).

## 2. Define objects, map data, and complete review

Select or create an ontology in the Ontology List, then choose manual, template, document, or asset construction. Review AI output as a proposed model and confirm its details.

Template construction previews and imports JSON / Excel and OWL, RDF/XML, and Turtle files. Standard ontologies can also be opened in the Protégé-style editing view. Check imported objects, relations, and types before mapping and review.

1. **Object definitions**: check business names, attribute types, required fields, primary keys, and relation direction.
2. **Data mapping**: select assets and map attributes to physical fields; check primary keys, enrichment joins, and relation join fields.
3. **Final review**: confirm objects, relations, and the mappings actually retained; review again after editing approved content.
4. **Validate and publish**: run connection, field mapping, instance primary key, and relation checks; resolve failures before publishing.

When document mapping retains an existing binding, final publication uses the retained mapping. Confirm that it still matches the current object definition.

Published versions capture snapshots of objects, relations, bindings, functions, and actions. Runtime uses the selected published definitions and reads current business data through those bindings.

Related code: [Builder steps](../frontend/src/views/builder/components/BuilderShell.vue), [Publication API](../backend/app/api/v1/ontology_publish.py), [Component snapshots](../backend/app/services/version_component_snapshot.py).

## 3. Configure functions and actions

In Logic Modeling, configure Expression, SQL, or Python functions. Define input parameters, output schemas, and object scope, then test with concrete business inputs.

In Action Modeling, configure API calls, SQL execution, attribute modification, notifications, function calls, or custom scripts. Set the required connections, parameter mappings, and service configuration, then include the capabilities in the relevant ontology release before using them from skills and agents.

Function tests simulate writes: execution shows a preview and stops at the first requested business write. Branches after that write have therefore not been exercised by that test.

Python functions and scripts undergo AST validation and use allowed module interfaces, restricted built-ins, and execution deadlines. Host system modules, private attributes, and reflective string formatting are prohibited; use f-strings to format text.

Related code: [Function execution](../backend/app/services/function_executor.py), [Action executors](../backend/app/services/action_executors/__init__.py), [Python sandbox](../backend/app/services/function_runtime/sandbox.py).

## 4. Test and publish business skills

Under Ontology Applications → Business Skills, select a published ontology version and object scope. Associate available Functions, Actions, and reference materials, then write Markdown operating instructions and input/output contracts.

Add at least one test case with an input and expected keywords or tool calls. Save the draft and run tests. Tests use the configured model and authorized tools, so they require valid model credentials and accessible data.

All cases for the current draft and its dependencies must pass runtime tests before publishing a fixed skill version. Changes to instructions, cases, or dependencies require another test run.

Skills can be private or visible to the workspace. Archiving stops new attachments while preserving existing release references. Application or historical release references protect a skill from deletion.

Related code: [Skill API](../backend/app/api/v1/skills.py), [Skill versions and tests](../backend/app/services/skill_service.py).

## 5. Configure, test, and publish an Agent

Under Ontology Applications → Agent Applications, create an Agent and choose its model, published ontology version, object scope, and fixed skill versions. Configure its instructions and tool scope.

The skills' ontology version must match the Agent, and their required objects must fall within the Agent's authorized scope. The default action mode is `simulation`; choose `confirm` when actual operations are needed.

Save the configuration and complete a chat test for the current draft in the workbench. Inspect tool results, skill loading, and pending actions before publishing. Test and publish again after changing configuration, upgrading skills, or restoring historical configuration.

The public endpoint is `POST /api/v1/open/agents/{id}/chat`, authenticated with `X-Agent-Key`. Set `stream: false` in the request to receive a complete JSON run result.

Related code: [Agent API](../backend/app/api/v1/agents.py), [Release and dependency checks](../backend/app/services/agent_management.py).

## Versions, approval, and live operation

| Operation | Effect on published capabilities |
| --- | --- |
| Save an Agent or skill draft | Existing releases continue using their snapshots |
| Publish an Agent | Pins ontology and skill versions and model behavior configuration |
| Update business data at its source | Subsequent queries read current data through published bindings |
| Submit an ontology for approval | Moves from Draft to Pending Approval, then Published after approval |
| Roll back an ontology | Creates a new version from history, effective after approval |

Versions pin definitions and behavior configuration; credentials can rotate. Upstream ontology changes may flag stale dependencies, so review their impact before updating applications. Rolling back ontology definitions does not undo committed business writes.

## Action authorization and receipts

Simulation mode does not write business data. Confirmation mode requires an authorized signed-in user to approve each action. Rejected or expired requests do not execute, and each authorization request executes at most once. Canvas actions follow the same boundary.

The public Agent endpoint has no signed-in user identity and cannot confirm writes on a user's behalf. API keys and application keys do not automatically grant user action confirmation permissions.

Assess execution together with its receipt. For `unknown`, `partial_committed`, or `committed_unrecorded`, check the data source, external service, and run records first. Then use the available reconciliation or recovery controls to avoid duplicate execution from direct retries.

Related code: [Action authorization](../backend/app/services/agent_actions.py), [Confirmation and reconciliation API](../backend/app/api/v1/agents.py), [Execution context](../backend/app/services/function_runtime/models.py).

## Connect MCP, instance APIs, and SDKs

Inspect published objects and capabilities under Ontology Services. The MCP endpoint is `POST /api/v1/mcp`, currently offering HTTP JSON-RPC 2.0 methods `initialize`, `tools/list`, and `tools/call`.

MCP accepts a signed-in user's Bearer JWT, or a key configured in the `MCP_API_KEYS` environment variable and passed as `X-API-Key`. API keys currently grant read access only; execution and write tools require a JWT user with the corresponding permissions.

```bash
curl http://localhost:8001/api/v1/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_MCP_READ_KEY" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

TypeScript / Python SDKs are generated from currently active published ontologies. You can also call `POST /api/v1/osdk/generate` with `language` and optional `entity_ids`. Follow the returned usage instructions to configure the client address and authentication.

Instance identity comes from the published primary key attribute, declared as `id_property` in endpoint and query metadata. A business field named `id` can keep its original value; use the actual primary key property to locate an instance.

Relation queries support `limit`, `offset`, `relation_id`, and `max_nodes`. When `pagination.has_more` is true, follow `pagination.next`, which is relative to `/api/v1`. Also inspect `traversal.truncated` and `continuations` to handle bounded multi-hop traversal.

Related code: [MCP authentication](../backend/app/services/mcp_tools/auth.py), [MCP API](../backend/app/api/v1/mcp.py), [Instance API](../backend/app/api/v1/ontology_api.py), [SDK generation](../backend/app/services/osdk_generator.py).

## Permissions and single sign-on

RBAC checks persisted role configuration and current account status. Default administrator, editor, and viewer permissions can be changed through management configuration; a role name does not replace a permission check.

Skill visibility, object scope, run records, and conversation access also follow their own access rules. If testing, publication, or execution fails on permissions, inspect the current role permissions and application dependencies.

Single sign-on currently supports OIDC and requires a real identity provider, client configuration, and callback address. SAML/LDAP still require integration and validation.

Related code: [Permission checks](../backend/app/core/permissions.py), [OIDC login](../backend/app/api/v1/sso.py).

## Configuration and Deployment

Backend configuration reads `.env` at the repository root; see [backend/.env.example](../backend/.env.example). When starting `uvicorn` directly, process environment variables take precedence for declared Settings fields. `start.sh` and `ctl.ps1` first load the root `.env`, overwriting matching process variables.

| Setting | Default and usage |
| --- | --- |
| `DATABASE_URL` | `sqlite:///./ontology.db`; relative paths resolve from the startup working directory, which is `backend/` in the startup scripts |
| `WORKSPACE_ROOT` | `workspace/` at the repository root; the source workspace for functions and actions |
| `LOCAL_DATA_ROOT` | `local-data/` at the repository root; the permitted scope for local data sources |
| `CODE_SERVER_PUBLIC_URL` | Empty by default; set the editor's public base URL when using a reverse proxy, such as `https://example.com/code-server` |
| `MONITOR_ENABLED` | `true` by default; set to `false` to disable monitoring collection during local development |
| `CORS_ORIGINS` | Explicitly list frontend origins allowed to access the API, separated by commas |

Keep `SECRET_KEY` stable for JWT signing. Configure a separate valid Fernet `CREDENTIAL_ENCRYPTION_KEY`; when empty, the connection credential encryption key is derived from `SECRET_KEY`. Changing the encryption key affects decryption of existing credentials, so retain the original key and handle credential migration.

In your created virtual environment, install backend dependencies from the repository root, then generate each key separately and save its output in the root `.env`:

```bash
python -m pip install -r backend/requirements.txt
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

`MCP_API_KEYS` and `MCP_REQUIRE_AUTH` read the process environment directly; they are not Settings fields. Startup scripts import the root `.env` into the process. When running `uvicorn` directly, explicitly set these variables in its startup environment.

Startup scripts run the Vite development server and code-server for local development. For production, run `npm run build` in `frontend/`, serve the resulting `dist/` through a web server, and configure reverse proxies for `/api` and the editor. Restrict backend and editor listening addresses, and configure authentication, HTTPS, and explicit CORS origins.

Configure OIDC in system settings with its enabled state, the `oidc` provider, `issuer_url`, `client_id`, `client_secret` as required by your identity provider, and the full `redirect_uri` with path `/api/v1/auth/sso/callback`. The backend must reach the provider's discovery document, token endpoint, and JWKS. Use HTTPS for deployed URLs; isolated local tests may use HTTP.

Related code: [Backend Settings](../backend/app/config.py), [Linux/macOS startup](../start.sh), [Windows control script](../ctl.ps1), [Credential encryption](../backend/app/services/data_plane/credential_vault.py), [Frontend build commands](../frontend/package.json).
