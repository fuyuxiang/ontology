#!/bin/bash

set -u

cd "$(dirname "$0")"

BACKEND_PORT="${BACKEND_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-5177}"

stop_port() {
    local port="$1"
    local name="$2"
    local pids
    local remaining

    pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
    if [ -n "$pids" ]; then
        echo "  Stopping $name on port $port (PID(s): $(echo "$pids" | tr '\n' ' '))..."
        echo "$pids" | xargs kill 2>/dev/null || true
        sleep 1
        remaining="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
        if [ -n "$remaining" ]; then
            echo "  Force stopping $name on port $port (PID(s): $(echo "$remaining" | tr '\n' ' '))..."
            echo "$remaining" | xargs kill -9 2>/dev/null || true
        fi
    else
        echo "  $name not running on port $port."
    fi
}

echo "Stopping services..."

stop_port "$BACKEND_PORT" "backend"
stop_port "$FRONTEND_PORT" "frontend"

rm -f .backend.pid .frontend.pid

echo "Done."
