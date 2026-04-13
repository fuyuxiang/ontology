#!/bin/bash
echo "========================================"
echo "  Ontology Platform - Startup"
echo "========================================"
echo

cd "$(dirname "$0")"
ROOT_DIR="$(pwd)"

echo "[1/3] Init database..."
cd "$ROOT_DIR/backend"
python3 seed.py 2>/dev/null
echo

echo "[2/3] Starting backend (port 8001)..."
cd "$ROOT_DIR/backend"
nohup uvicorn app.main:app --reload --port 8001 --log-level info > "$ROOT_DIR/backend.log" 2>&1 &
echo $! > "$ROOT_DIR/.backend.pid"
sleep 2

echo "[3/3] Starting frontend (port 5177)..."
cd "$ROOT_DIR/frontend"
nohup npm run dev > "$ROOT_DIR/frontend.log" 2>&1 &
echo $! > "$ROOT_DIR/.frontend.pid"
sleep 2

echo
echo "========================================"
echo "  Ready!"
echo "  Frontend: http://localhost:5177"
echo "  Backend:  http://localhost:8001"
echo "  API Docs: http://localhost:8001/docs"
echo "========================================"
echo
echo "Logs: backend.log / frontend.log"
echo "Stop: ./stop.sh"
