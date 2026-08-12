#!/bin/bash
# archeaxis-workspace — migrate once, then launch the unified single-writer runtime.
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate

printf '%s\n' "Running one-shot schema migration..."
python -m app.runtime_entrypoint migrate

printf '%s\n' "Starting unified Core + Knowledge-Base + internal Research on port 8000"
printf '%s\n' "  Core docs:       http://127.0.0.1:8000/docs"
printf '%s\n' "  Knowledge docs:  http://127.0.0.1:8000/kb/docs"
printf '%s\n' "  Research:        mounted internally at /internal/research"
exec python -m app.runtime_entrypoint core
