#!/bin/bash

set -u

cd "$(dirname "$0")"
ROOT_DIR="$(pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_LOG="$ROOT_DIR/backend.log"
FRONTEND_LOG="$ROOT_DIR/frontend.log"
BACKEND_PID_FILE="$ROOT_DIR/.backend.pid"
FRONTEND_PID_FILE="$ROOT_DIR/.frontend.pid"
BACKEND_PORT="${BACKEND_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-5177}"
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

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Missing required command: $1"
        exit 1
    fi
}

BACKEND_PYTHON="$(choose_backend_python)"
if [ -z "$BACKEND_PYTHON" ]; then
    echo "No usable Python interpreter found."
    echo "Expected backend/venv/bin/python, backend/.venv/bin/python, or python3 in PATH."
    exit 1
fi

require_command npm
require_command lsof

echo "========================================"
echo "  Ontology Platform - Startup"
echo "========================================"
echo
echo "Backend Python: $BACKEND_PYTHON"
echo "Backend Port:   $BACKEND_PORT"
echo "Frontend Port:  $FRONTEND_PORT"
echo "Backend Reload: $BACKEND_RELOAD"
echo

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "Frontend dependencies are not installed."
    echo "Run: cd frontend && npm install"
    exit 1
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

echo "[1/3] Installing backend dependencies..."
cd "$BACKEND_DIR"
"$BACKEND_PYTHON" -m pip install -r requirements.txt --quiet 2>&1 | tail -1
echo "Dependencies ready."
echo

echo "[2/3] Starting backend (port $BACKEND_PORT)..."
cd "$BACKEND_DIR"
backend_args=(app.main:app --host 127.0.0.1 --port "$BACKEND_PORT" --log-level info)
if [ "$BACKEND_RELOAD" = "1" ]; then
    backend_args+=(--reload)
fi
nohup "$BACKEND_PYTHON" -m uvicorn "${backend_args[@]}" > "$BACKEND_LOG" 2>&1 &
echo $! > "$BACKEND_PID_FILE"
sleep 2

if ! backend_pids="$(port_pids "$BACKEND_PORT")" || [ -z "$backend_pids" ]; then
    echo "Backend failed to start. Check backend.log"
    exit 1
fi
echo "Backend running with PID(s):"
echo "$backend_pids"
echo

echo "[3/3] Starting frontend (port $FRONTEND_PORT)..."
cd "$FRONTEND_DIR"
nohup env VITE_PROXY_TARGET="$VITE_PROXY_TARGET" npx vite --host 127.0.0.1 --port "$FRONTEND_PORT" > "$FRONTEND_LOG" 2>&1 &
echo $! > "$FRONTEND_PID_FILE"
sleep 2

if ! frontend_pids="$(port_pids "$FRONTEND_PORT")" || [ -z "$frontend_pids" ]; then
    echo "Frontend failed to start. Check frontend.log"
    exit 1
fi
echo "Frontend running with PID(s):"
echo "$frontend_pids"
echo

echo "========================================"
echo "  Ready!"
echo "  Frontend: http://127.0.0.1:$FRONTEND_PORT"
echo "  Backend:  http://127.0.0.1:$BACKEND_PORT"
echo "  API Docs: http://127.0.0.1:$BACKEND_PORT/docs"
echo "========================================"
echo
echo "Logs: backend.log / frontend.log"
echo "Stop: ./stop.sh"
