#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
ROOT_DIR="$(pwd)"
if [ -f "$ROOT_DIR/.env" ]; then
    set -a
    source "$ROOT_DIR/.env"
    set +a
fi
PYTHON="${BACKEND_PYTHON:-}"
if [ -z "$PYTHON" ]; then
    for candidate in "$ROOT_DIR/backend/venv/bin/python" "$ROOT_DIR/backend/.venv/bin/python" "$(command -v python3 || true)"; do
        if [ -x "$candidate" ]; then PYTHON="$candidate"; break; fi
    done
fi
if [ -z "$PYTHON" ]; then
    echo "Python is required to validate managed PID records; no process was stopped."
    exit 1
fi
for service in code-server frontend backend; do
    "$PYTHON" "$ROOT_DIR/scripts/process_manager.py" stop "$ROOT_DIR/.$service.pid" "$ROOT_DIR"
done
echo "Managed services stopped. Unrelated port listeners were preserved."
