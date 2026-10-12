#!/bin/bash

set -euo pipefail

cd "$(dirname "$0")"
ROOT_DIR="$(pwd)"
if [ -f "$ROOT_DIR/.env" ]; then
    set -a
    source "$ROOT_DIR/.env"
    set +a
fi
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_LOG="$ROOT_DIR/backend.log"
FRONTEND_LOG="$ROOT_DIR/frontend.log"
BACKEND_PID_FILE="$ROOT_DIR/.backend.pid"
FRONTEND_PID_FILE="$ROOT_DIR/.frontend.pid"
CODE_SERVER_PID_FILE="$ROOT_DIR/.code-server.pid"
CODE_SERVER_LOG="$ROOT_DIR/code-server.log"
CODE_SERVER_CONFIG="$ROOT_DIR/code-server/config.yaml"
CODE_SERVER_USER_DATA="${CODE_SERVER_USER_DATA_DIR:-$ROOT_DIR/.code-server-data}"
CODE_SERVER_EXTENSIONS="${CODE_SERVER_EXTENSIONS_DIR:-$ROOT_DIR/.code-server-extensions}"
WORKSPACE_DIR="${WORKSPACE_ROOT:-$ROOT_DIR/workspace}"
BACKEND_PORT="${BACKEND_PORT:-${PORT:-8001}}"
FRONTEND_PORT="${FRONTEND_PORT:-5177}"
CODE_SERVER_PORT="${CODE_SERVER_PORT:-8443}"
CODE_SERVER_BIND_HOST="${CODE_SERVER_BIND_HOST:-127.0.0.1}"
BACKEND_RELOAD="${BACKEND_RELOAD:-0}"
VITE_PROXY_TARGET="${VITE_PROXY_TARGET:-http://127.0.0.1:$BACKEND_PORT}"

choose_backend_python() {
    local candidate
    for candidate in \
        "$BACKEND_DIR/venv/bin/python" \
        "$BACKEND_DIR/.venv/bin/python" \
        "$(command -v python3 2>/dev/null)"
    do
        if [ -n "$candidate" ] && [ -x "$candidate" ]; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

port_pids() {
    lsof -tiTCP:"$1" -sTCP:LISTEN 2>/dev/null
}

# Vite binds the port even when the app fails to compile, so a listening port
# is not proof of success. Return the first fatal build/scan error in the log.
frontend_log_error() {
    grep -aE 'PARSE_ERROR|Failed to scan for dependencies|Build failed with [0-9]+ error|Pre-transform error|Transform failed|Internal server error' "$FRONTEND_LOG" 2>/dev/null | head -1
}

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Missing required command: $1"
        exit 1
    fi
}

BACKEND_PYTHON="$(choose_backend_python || true)"
if [ -z "$BACKEND_PYTHON" ]; then
    echo "No usable Python interpreter found."
    echo "Expected backend/venv/bin/python, backend/.venv/bin/python, or python3 in PATH."
    exit 1
fi

require_command npm
require_command lsof
require_command node
require_command curl

created_services=()
cleanup_failed_start() {
    local code=$?
    trap - EXIT
    if [ "$code" -ne 0 ]; then
        for service in "${created_services[@]}"; do
            "$BACKEND_PYTHON" "$ROOT_DIR/scripts/process_manager.py" stop "$ROOT_DIR/.$service.pid" "$ROOT_DIR" || true
        done
    fi
    exit "$code"
}
trap cleanup_failed_start EXIT

record_process() {
    "$BACKEND_PYTHON" "$ROOT_DIR/scripts/process_manager.py" record "$ROOT_DIR/.$1.pid" "$ROOT_DIR" "$2" "$1"
    created_services+=("$1")
}
owns_port() {
    "$BACKEND_PYTHON" "$ROOT_DIR/scripts/process_manager.py" owns-port "$ROOT_DIR/.$1.pid" "$ROOT_DIR" "$2"
}

echo "========================================"
echo "  Ontology Platform - Startup"
echo "========================================"
echo
echo "Backend Python: $BACKEND_PYTHON"
echo "Backend Port:   $BACKEND_PORT"
echo "Frontend Port:  $FRONTEND_PORT"
echo "Code Server:    $CODE_SERVER_PORT"
echo "Backend Reload: $BACKEND_RELOAD"
echo

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "Frontend dependencies are not installed."
    echo "Run: cd frontend && npm install"
    exit 1
fi

if ! command -v code-server >/dev/null 2>&1; then
    if [ "${SKIP_DEPENDENCY_INSTALL:-0}" = "1" ]; then
        echo "code-server is required; install it or remove SKIP_DEPENDENCY_INSTALL."
        exit 1
    fi
    echo "code-server not found. Installing..."
    curl -fsSL https://code-server.dev/install.sh | sh
    if ! command -v code-server >/dev/null 2>&1; then
        echo "code-server installation failed."
        exit 1
    fi
    echo "code-server installed."
fi

if backend_pids="$(port_pids "$BACKEND_PORT")" && [ -n "$backend_pids" ]; then
    echo "Backend port $BACKEND_PORT is already in use by PID(s):"
    echo "$backend_pids"
    echo "Run ./stop.sh or choose another BACKEND_PORT."
    exit 1
fi

if frontend_pids="$(port_pids "$FRONTEND_PORT")" && [ -n "$frontend_pids" ]; then
    echo "Frontend port $FRONTEND_PORT is already in use by PID(s):"
    echo "$frontend_pids"
    echo "Run ./stop.sh or choose another FRONTEND_PORT."
    exit 1
fi

if cs_pids="$(port_pids "$CODE_SERVER_PORT")" && [ -n "$cs_pids" ]; then
    echo "Code-server port $CODE_SERVER_PORT is already in use by PID(s):"
    echo "$cs_pids"
    echo "Run ./stop.sh or choose another CODE_SERVER_PORT."
    exit 1
fi

echo "[1/4] Installing backend dependencies..."
cd "$BACKEND_DIR"
if [ "${SKIP_DEPENDENCY_INSTALL:-0}" != "1" ]; then
    "$BACKEND_PYTHON" -m pip install -r requirements.txt --quiet
else
    echo "Dependency installation explicitly skipped; startup validates the installed environment."
fi
echo "Dependencies ready."
echo

export PORT="$BACKEND_PORT"
export CODE_SERVER_PORT
export WORKSPACE_ROOT="${WORKSPACE_ROOT:-$WORKSPACE_DIR}"
WORKSPACE_DIR="$WORKSPACE_ROOT"

echo "[2/4] Starting backend (port $BACKEND_PORT)..."
cd "$BACKEND_DIR"
backend_args=(app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" --log-level info)
if [ "$BACKEND_RELOAD" = "1" ]; then
    backend_args+=(--reload)
fi
nohup "$BACKEND_PYTHON" -m uvicorn "${backend_args[@]}" > "$BACKEND_LOG" 2>&1 &
backend_pid=$!
record_process backend "$backend_pid"

# 后端 lifespan startup 会先跑完建表/迁移/seed/Function Runtime 扫描才绑定端口。
# 冷启动本地 MySQL 约 18s；内网 MySQL + 26 个 workspace 函数全量扫描约 75-90s，
# 给到 100s 留余量，避免误判失败导致前端与 code-server 不启动。
backend_pids=""
for i in $(seq 1 100); do
    sleep 1
    if ! kill -0 "$backend_pid" 2>/dev/null; then break; fi
    if owns_port backend "$BACKEND_PORT"; then
        backend_pids="$(port_pids "$BACKEND_PORT")"
        break
    fi
    printf "  waiting... (%ds)\n" "$i"
done

if [ -z "$backend_pids" ]; then
    echo "Backend failed to start after 100s. Check backend.log"
    exit 1
fi
if ! curl -fsS "http://127.0.0.1:$BACKEND_PORT/api/health" >/dev/null; then
    echo "Backend is listening but readiness failed. Check backend.log"
    exit 1
fi
echo "Backend running with PID(s):"
echo "$backend_pids"
echo

echo "[3/4] Starting frontend (port $FRONTEND_PORT)..."
cd "$FRONTEND_DIR"
nohup env VITE_PROXY_TARGET="$VITE_PROXY_TARGET" node "$FRONTEND_DIR/node_modules/vite/bin/vite.js" --host 0.0.0.0 --port "$FRONTEND_PORT" --strictPort > "$FRONTEND_LOG" 2>&1 &
frontend_pid=$!
record_process frontend "$frontend_pid"

frontend_pids=""
fe_error=""
for i in $(seq 1 15); do
    sleep 1
    if fe_error="$(frontend_log_error)" && [ -n "$fe_error" ]; then
        break
    fi
    if ! kill -0 "$frontend_pid" 2>/dev/null; then break; fi
    if owns_port frontend "$FRONTEND_PORT"; then
        frontend_pids="$(port_pids "$FRONTEND_PORT")"
        break
    fi
    printf "  waiting... (%ds)\n" "$i"
done

# Port may bind before the dependency scan finishes; give errors a moment to surface.
if [ -n "$frontend_pids" ] && [ -z "$fe_error" ]; then
    sleep 2
    fe_error="$(frontend_log_error || true)"
fi

if [ -n "$fe_error" ]; then
    echo "Frontend started but failed to compile:"
    echo "  $fe_error"
    echo "See frontend.log for details."
    exit 1
fi

if [ -z "$frontend_pids" ]; then
    echo "Frontend failed to start after 15s. Check frontend.log"
    exit 1
fi
echo "Frontend running with PID(s):"
echo "$frontend_pids"
echo

echo "[4/4] Starting code-server (port $CODE_SERVER_PORT)..."
mkdir -p "$WORKSPACE_DIR"
mkdir -p "$CODE_SERVER_USER_DATA" "$CODE_SERVER_EXTENSIONS"
cd "$ROOT_DIR"
if [ -z "${CODE_SERVER_PASSWORD:-}" ]; then
    if [ ! -f "$ROOT_DIR/.code-server-password" ]; then
        umask 077
        "$BACKEND_PYTHON" -c 'import secrets; print(secrets.token_urlsafe(32))' > "$ROOT_DIR/.code-server-password"
    fi
    chmod 600 "$ROOT_DIR/.code-server-password"
    CODE_SERVER_PASSWORD="$(cat "$ROOT_DIR/.code-server-password")"
fi
export PASSWORD="$CODE_SERVER_PASSWORD"
if [ "${SKIP_EXTENSION_INSTALL:-0}" != "1" ] && [ "${SKIP_DEPENDENCY_INSTALL:-0}" != "1" ]; then
    code-server --user-data-dir "$CODE_SERVER_USER_DATA" --extensions-dir "$CODE_SERVER_EXTENSIONS" --install-extension ms-python.python > /dev/null 2>&1 || true
fi
nohup env PORT="$CODE_SERVER_PORT" code-server --config "$CODE_SERVER_CONFIG" --user-data-dir "$CODE_SERVER_USER_DATA" --extensions-dir "$CODE_SERVER_EXTENSIONS" --bind-addr "$CODE_SERVER_BIND_HOST:$CODE_SERVER_PORT" --auth password "$WORKSPACE_DIR" > "$CODE_SERVER_LOG" 2>&1 &
cs_pid=$!
record_process code-server "$cs_pid"

cs_pids=""
for i in $(seq 1 15); do
    sleep 1
    if ! kill -0 "$cs_pid" 2>/dev/null; then break; fi
    if owns_port code-server "$CODE_SERVER_PORT"; then
        cs_pids="$(port_pids "$CODE_SERVER_PORT")"
        break
    fi
    printf "  waiting... (%ds)\n" "$i"
done

if [ -z "$cs_pids" ]; then
    echo "code-server failed to start after 15s. Check code-server.log"
    exit 1
fi
if ! curl -fsS "http://127.0.0.1:$CODE_SERVER_PORT/healthz" >/dev/null; then
    echo "code-server readiness failed."
    exit 1
fi
echo "code-server running with PID(s):"
echo "$cs_pids"
echo "Editor password: CODE_SERVER_PASSWORD or local .code-server-password file (not printed)."
echo

echo "========================================"
echo "  Ready!"
echo "  Frontend:    http://0.0.0.0:$FRONTEND_PORT"
echo "  Backend:     http://0.0.0.0:$BACKEND_PORT"
echo "  API Docs:    http://0.0.0.0:$BACKEND_PORT/docs"
echo "  Code Server: http://0.0.0.0:$CODE_SERVER_PORT"
echo "========================================"
echo
echo "Logs: backend.log / frontend.log / code-server.log"
echo "Stop: ./stop.sh"
