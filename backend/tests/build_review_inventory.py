"""Record registered entry points and current source anchors, without starting services."""
from __future__ import annotations

import ast
import inspect
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/review/evidence"
os.environ.setdefault("SECRET_KEY", "isolated-review-inventory")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("MONITOR_ENABLED", "false")
os.environ.setdefault("DATA_PLANE_REFRESH_ENABLED", "false")

from app.main import app  # noqa: E402

CORE_ANCHORS = {
    "CORE-001": [("backend/app/main.py", "lifespan"), ("backend/app/core/deps.py", "get_current_user"), ("backend/app/core/security.py", "decode_token")],
    "CORE-002": [("backend/app/api/v1/auth.py", "refresh"), ("backend/app/api/v1/auth.py", "logout"), ("backend/app/migrations/schema_compat.py", "_migrate_users")],
    "CORE-003": [("frontend/src/api/client.ts", "refreshRequest"), ("frontend/src/store/auth.ts", "fetchUser")],
    "CORE-004": [("backend/app/api/v1/sso.py", ""), ("backend/app/models/auth_challenge.py", "")],
    "CORE-005": [("backend/app/api/v1/system_config.py", "_mask_value"), ("backend/app/api/v1/system_config.py", "save_config"), ("backend/app/services/llm_resolver.py", "get_llm_client")],
    "CORE-006": [("backend/app/api/v1/entities.py", "create_attribute"), ("backend/app/api/v1/entities.py", "update_attribute"), ("backend/app/api/v1/shared_attributes.py", "update_shared_attribute"), ("backend/app/api/v1/relations.py", "update_relation")],
    "CORE-007": [("backend/app/services/file_import.py", "parse_json_ontology"), ("backend/app/services/file_import.py", "parse_owl_ontology"), ("backend/app/api/v1/entities.py", "create_from_asset")],
    "CORE-008": [("backend/app/api/v1/entities.py", "_sync_attribute_mappings"), ("backend/app/api/v1/entities.py", "get_data_layer")],
    "CORE-009": [("backend/app/api/v1/ontology_workspace.py", "create_group"), ("backend/app/api/v1/ontology_workspace.py", "tasks")],
    "CORE-010": [("backend/app/migrations/schema_compat.py", "_drop_business_rules"), ("backend/app/migrations/__init__.py", "run_startup_migrations")],
    "CORE-011": [("backend/app/main.py", "lifespan"), ("backend/app/main.py", "health")],
    "CORE-012": [("backend/app/connectors/sqlite.py", ""), ("backend/app/config.py", "")],
    "CORE-013": [("backend/app/services/llm_resolver.py", "_instrument_client"), ("backend/app/services/llm_resolver.py", "get_llm_client")],
    "CORE-014": [("backend/app/services/ontology_constraints.py", "validate_and_retry"), ("backend/app/api/v1/entities.py", "ai_extract_entities")],
    "CORE-015": [("backend/app/api/v1/scenarios.py", "list_scenarios"), ("frontend/src/views/ontology/OntologyListView.vue", "active_version_id")],
    "CORE-016": [("backend/app/api/v1/auth.py", "seed_admin")],
    "CORE-017": [("backend/app/api/v1/auth.py", "platform_config"), ("backend/app/api/v1/system_config.py", "save_config"), ("frontend/src/store/platformConfig.ts", ""), ("frontend/src/views/settings/SystemConfigView.vue", "handleSave")],
    "CORE-018": [("backend/app/api/v1/builder.py", "suggest_attributes"), ("backend/app/api/v1/builder.py", "suggest_relations"), ("backend/app/api/v1/builder.py", "_parse_suggestion_list"), ("frontend/src/views/builder/components/Step2Review.vue", "async function suggestAttributes")],
    "CORE-019": [("backend/app/api/v1/builder.py", "builder_finalize"), ("backend/app/api/v1/builder.py", "finalize_draft")],
}


def source_anchor(content, path, symbol):
    if content is None:
        return {"present": False}
    lines = content.splitlines()
    line = 1
    found = not symbol
    if symbol and path.endswith(".py"):
        node = next((node for node in ast.walk(ast.parse(content)) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == symbol), None)
        if node:
            line, found = node.lineno, True
    elif symbol:
        match = next((i for i, text in enumerate(lines, 1) if symbol in text), None)
        if match:
            line, found = match, True
    return {"present": True, "symbol_found": found, "line": line if found else None,
            "excerpt": "\n".join(lines[line - 1:line + 6]) if found else "symbol absent in this source"}


def module_for(path: str) -> str:
    segment = path.removeprefix("/api/v1/").split("/", 1)[0]
    groups = {
        "M-01": {"auth"},
        "M-02": {"system-config", "models", "prompt-templates"},
        "M-03": {"health"},
        "M-04": {"connections", "assets", "business-documents"},
        "M-05": {"entities", "relations", "shared-attributes", "shared-refs", "scenarios", "ontology"},
        "M-06": {"builder", "doc-builder", "ai-builder", "ai-builder-v2", "ai-ontology"},
        "M-07": {"object-bindings", "mapping", "lineage", "quality", "probes", "execute", "resolution", "ontology-mapping"},
        "M-08": {"functions", "registry", "ai-code"},
        "M-09": {"actions"},
        "M-10": {"ontology-publish", "impact-analysis"},
        "M-11": {"skills"},
        "M-12": {"agents", "open", "copilot"},
        "M-13": {"mcp", "mcp-stats", "ontology-api", "osdk"},
        "M-14": {"monitor", "dashboard", "governance", "traces", "evals", "events", "audit", "execution-logs"},
    }
    return next((key for key, values in groups.items() if segment in values), "M-03")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    routes = []
    for index, route in enumerate(app.routes, 1):
        endpoint = getattr(route, "endpoint", None)
        filename = inspect.getsourcefile(endpoint) if endpoint else None
        relative = None
        if filename:
            try:
                relative = str(Path(filename).relative_to(ROOT))
            except ValueError:
                relative = str(Path(filename).name)
        try:
            line = inspect.getsourcelines(endpoint)[1] if endpoint else None
        except (OSError, TypeError):
            line = None
        routes.append({
            "entry_id": f"E-{index:03d}", "module_id": module_for(route.path),
            "path": route.path, "methods": sorted(getattr(route, "methods", []) or []),
            "transport": "websocket" if route.__class__.__name__.endswith("WebSocketRoute") else "http",
            "function": getattr(endpoint, "__qualname__", None), "source": relative, "line": line,
            "review_evidence": "MODULE_MATRIX.md + corresponding module report (not an E2E claim)",
        })
    (OUT / "endpoint-inventory.json").write_text(json.dumps(routes, ensure_ascii=False, indent=2) + "\n")
    for category, locations in {
        "backend-source-inventory.txt": ["backend/app"],
        "core-code-anchors.txt": [
            "backend/app/core", "backend/app/api/v1/auth.py", "backend/app/api/v1/sso.py",
            "backend/app/api/v1/system_config.py", "backend/app/api/v1/entities.py",
            "backend/app/api/v1/scenarios.py", "backend/app/api/v1/relations.py",
            "backend/app/api/v1/shared_attributes.py", "backend/app/api/v1/shared_refs.py",
            "backend/app/api/v1/ontology_workspace.py", "backend/app/services/llm_resolver.py",
            "backend/app/services/ontology_constraints.py", "backend/app/connectors/sqlite.py",
            "backend/app/main.py", "backend/app/migrations", "backend/tests/test_core_review.py",
            "backend/tests/test_sso_review.py", "backend/tests/test_llm_monitor_review.py",
            "backend/tests/test_legacy_extract_review.py",
        ],
    }.items():
        paths = set()
        for location in locations:
            path = ROOT / location
            paths.update(path.rglob("*.py") if path.is_dir() else [path])
        lines = []
        for path in sorted(paths):
            relative = path.relative_to(ROOT)
            if category.startswith("backend-source"):
                lines.append(str(relative))
            else:
                tree = ast.parse(path.read_text())
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        lines.append(f"{relative}:{node.lineno} {node.name}")
        (OUT / category).write_text("\n".join(lines) + "\n")
    findings = []
    for finding_id, anchors in CORE_ANCHORS.items():
        code = []
        for relative, symbol in anchors:
            path = ROOT / relative
            old = subprocess.run(["git", "show", f"HEAD:{relative}"], cwd=ROOT, capture_output=True, text=True)
            code.append({"file": relative, "function_or_symbol": symbol or "module",
                         "baseline": source_anchor(old.stdout if old.returncode == 0 else None, relative, symbol),
                         "delivery": source_anchor(path.read_text() if path.exists() else None, relative, symbol)})
        findings.append({"finding_id": finding_id, "baseline_commit": "29c48ca4881b7d29e17eeb1e123c8b02ef665423", "code": code,
                         "root_cause_fix_validation": "CORE_REVIEW.md row with same finding_id"})
    (OUT / "core-findings-code.json").write_text(json.dumps(findings, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"routes": len(routes), "evidence": str(OUT.relative_to(ROOT))}))


if __name__ == "__main__":
    main()
