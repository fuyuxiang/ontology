#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
EXDB_DIR="${ROOT_DIR}/exDB2TTL"
DEFAULT_CONFIG="${EXDB_DIR}/project.json"
CONFIG_PATH="${1:-${EXDB2TTL_CONFIG:-${DEFAULT_CONFIG}}}"

print_line() {
  printf '%s\n' "$*"
}

fail() {
  print_line "ERROR: $*" >&2
  exit 1
}

resolve_python() {
  if [ -n "${EXDB2TTL_PYTHON:-}" ] && [ -x "${EXDB2TTL_PYTHON}" ]; then
    print_line "${EXDB2TTL_PYTHON}"
    return 0
  fi

  if [ -x "${ROOT_DIR}/backend/.venv/bin/python" ]; then
    print_line "${ROOT_DIR}/backend/.venv/bin/python"
    return 0
  fi

  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi

  fail "Python interpreter not found. Set EXDB2TTL_PYTHON or create backend/.venv."
}

PYTHON_BIN="$(resolve_python)"

[ -f "${CONFIG_PATH}" ] || fail "Config file not found: ${CONFIG_PATH}. Run: ${PYTHON_BIN} -m exDB2TTL bootstrap --database-name <db> --dialect <sqlite|mysql|csv> --table <table>"

cd "${ROOT_DIR}"

CONFIG_INFO="$("${PYTHON_BIN}" - "${CONFIG_PATH}" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as handle:
    payload = json.load(handle)

database = payload.get("database") or {}
llm = payload.get("llm") or {}
output = payload.get("output") or {}

print(f"DIALECT={database.get('dialect', '')}")
print(f"API_KEY_ENV={llm.get('api_key_env', '')}")
print(f"OUTPUT_DIR={output.get('directory', '')}")
PY
)"

while IFS='=' read -r key value; do
  case "${key}" in
    DIALECT) DIALECT="${value}" ;;
    API_KEY_ENV) API_KEY_ENV="${value}" ;;
    OUTPUT_DIR) OUTPUT_DIR="${value}" ;;
  esac
done <<EOF
${CONFIG_INFO}
EOF

print_line "Using Python: ${PYTHON_BIN}"
print_line "Using config: ${CONFIG_PATH}"
print_line "Database dialect: ${DIALECT:-unknown}"

if ! "${PYTHON_BIN}" -m compileall exDB2TTL >/dev/null 2>&1; then
  fail "exDB2TTL compilation check failed"
fi

if [ -n "${API_KEY_ENV:-}" ] && [ -z "${!API_KEY_ENV:-}" ]; then
  fail "Environment variable ${API_KEY_ENV} is not set. exDB2TTL needs it to call the LLM."
fi

if [ "${DIALECT:-}" = "mysql" ]; then
  if ! "${PYTHON_BIN}" - <<'PY' >/dev/null 2>&1
import importlib
importlib.import_module("pymysql")
PY
  then
    fail "MySQL mode requires pymysql in the selected interpreter. Install it or switch to csv mode."
  fi
fi

if ! "${PYTHON_BIN}" - <<'PY' >/dev/null 2>&1
import importlib
import sys

required = ["rdflib", "pyshacl"]
missing = []
for name in required:
    try:
        importlib.import_module(name)
    except Exception:
        missing.append(name)

if missing:
    raise SystemExit(",".join(missing))
PY
then
  fail "Missing required Python packages. exDB2TTL needs rdflib and pyshacl in the selected interpreter."
fi

print_line ""
print_line "Step 1/1: run full exDB2TTL pipeline"
"${PYTHON_BIN}" -m exDB2TTL run --config "${CONFIG_PATH}"

print_line ""
print_line "Done. Output directory: ${OUTPUT_DIR:-<see config>}"
