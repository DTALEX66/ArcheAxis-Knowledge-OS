#!/bin/bash
# Cognitive-Loop-OS — Launch unified runtime + research service
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "Starting Cognitive-Loop-OS services..."

source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate

echo "[1/2] Cognitive-OS + Knowledge-Base on port 8000"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers &
PID_OS=$!

echo "[2/2] Inspiration-Research on port 8001"
python -m uvicorn inspiration_research.api:app --host 127.0.0.1 --port 8001 &
PID_IR=$!


echo ""
echo "All services launched:"
echo "  Cognitive-OS        http://127.0.0.1:8000/docs"
echo "  Inspiration-Research http://127.0.0.1:8001/docs"
echo "  Knowledge-Base       http://127.0.0.1:8000/kb/docs"
echo ""
echo "Press Ctrl+C to stop all services"

trap "kill $PID_OS $PID_IR 2>/dev/null; exit 0" INT TERM
wait
