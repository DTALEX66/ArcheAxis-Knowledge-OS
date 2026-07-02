#!/bin/bash
# Cognitive-Loop-OS — Launch all 3 B-line services
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "Starting Cognitive-Loop-OS services..."

source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate

echo "[1/3] Cognitive-OS on port 8000"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
PID_OS=$!

echo "[2/3] Inspiration-Research on port 8001"
python -m uvicorn Inspiration-Research.api:app --host 127.0.0.1 --port 8001 &
PID_IR=$!

echo "[3/3] Knowledge-Base on port 8002"
python -m uvicorn Knowledge-Base.api:app --host 127.0.0.1 --port 8002 &
PID_KB=$!

echo ""
echo "All services launched:"
echo "  Cognitive-OS        http://127.0.0.1:8000/docs"
echo "  Inspiration-Research http://127.0.0.1:8001/docs"
echo "  Knowledge-Base       http://127.0.0.1:8002/docs"
echo ""
echo "Press Ctrl+C to stop all services"

trap "kill $PID_OS $PID_IR $PID_KB 2>/dev/null; exit 0" INT TERM
wait
