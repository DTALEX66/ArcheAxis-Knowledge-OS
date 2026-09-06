#!/usr/bin/env bash
# Both shells share one resolver. ARCHEAXIS_PYTHON selects an installed interpreter.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [ -n "${ARCHEAXIS_PYTHON:-}" ]; then
  PYTHON="$ARCHEAXIS_PYTHON"
elif [ -x "$ROOT/.venv/Scripts/python.exe" ]; then
  PYTHON="$ROOT/.venv/Scripts/python.exe"
elif [ -x "$ROOT/.venv/bin/python" ]; then
  PYTHON="$ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
else
  PYTHON=python
fi
if [ "${1:-}" = "--" ]; then shift; fi
FULL=()
if [ "${1:-}" = "--full" ]; then FULL=(--full); shift; fi
exec "$PYTHON" -B "$ROOT/scripts/runtime/dev.py" --pytest "${FULL[@]}" -- "$@"
