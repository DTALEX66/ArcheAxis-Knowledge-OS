#!/usr/bin/env bash
# Project-local environment boundary for Cognitive-Loop-OS.
# Source this file from a launcher; do not persist these values globally.
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -W 2>/dev/null || pwd)"
RUNTIME_ROOT="$PROJECT_ROOT/.hermes/task-runtime"
CACHE_ROOT="$RUNTIME_ROOT/cache"
TMP_ROOT="$RUNTIME_ROOT/tmp"

mkdir -p "$RUNTIME_ROOT" "$CACHE_ROOT" "$TMP_ROOT" "$RUNTIME_ROOT/runtime" \
  "$RUNTIME_ROOT/logs" "$RUNTIME_ROOT/pycache" \
  "$CACHE_ROOT/uv" "$CACHE_ROOT/pip" "$CACHE_ROOT/npm" \
  "$CACHE_ROOT/playwright-browsers" "$CACHE_ROOT/cargo-home"

export COGNITIVE_DATA_DIR="$RUNTIME_ROOT/runtime"
export TMP="$TMP_ROOT"
export TEMP="$TMP_ROOT"
export TMPDIR="$TMP_ROOT"
export PYTHONPYCACHEPREFIX="$RUNTIME_ROOT/pycache"
export UV_CACHE_DIR="$CACHE_ROOT/uv"
export PIP_CACHE_DIR="$CACHE_ROOT/pip"
export NPM_CONFIG_CACHE="$CACHE_ROOT/npm"
export PLAYWRIGHT_BROWSERS_PATH="$CACHE_ROOT/playwright-browsers"
export CARGO_HOME="$CACHE_ROOT/cargo-home"
export HERMES_PROJECT_ROOT="$PROJECT_ROOT"
export HERMES_PROJECT_RUNTIME_ROOT="$RUNTIME_ROOT"
export HERMES_PROJECT_ARTIFACTS="$PROJECT_ROOT/.hermes/task-artifacts"
export HERMES_PROJECT_LOGS="$RUNTIME_ROOT/logs"
