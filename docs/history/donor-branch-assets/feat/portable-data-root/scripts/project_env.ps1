# Project-local environment boundary for Cognitive-Loop-OS.
# Dot-source this file from a launcher; do not persist these values globally.
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RuntimeRoot = Join-Path $ProjectRoot ".hermes\task-runtime"
$CacheRoot = Join-Path $RuntimeRoot "cache"
$TmpRoot = Join-Path $RuntimeRoot "tmp"

@($RuntimeRoot, $CacheRoot, $TmpRoot,
  (Join-Path $RuntimeRoot "runtime"),
  (Join-Path $RuntimeRoot "logs"),
  (Join-Path $RuntimeRoot "pycache"),
  (Join-Path $CacheRoot "uv"),
  (Join-Path $CacheRoot "pip"),
  (Join-Path $CacheRoot "npm"),
  (Join-Path $CacheRoot "playwright-browsers"),
  (Join-Path $CacheRoot "cargo-home")) | ForEach-Object {
    New-Item -ItemType Directory -Force -Path $_ | Out-Null
}

$env:COGNITIVE_DATA_DIR = Join-Path $RuntimeRoot "runtime"
$env:TMP = $TmpRoot
$env:TEMP = $TmpRoot
$env:TMPDIR = $TmpRoot
$env:PYTHONPYCACHEPREFIX = Join-Path $RuntimeRoot "pycache"
$env:UV_CACHE_DIR = Join-Path $CacheRoot "uv"
$env:PIP_CACHE_DIR = Join-Path $CacheRoot "pip"
$env:NPM_CONFIG_CACHE = Join-Path $CacheRoot "npm"
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $CacheRoot "playwright-browsers"
$env:CARGO_HOME = Join-Path $CacheRoot "cargo-home"
$env:HERMES_PROJECT_ROOT = $ProjectRoot
$env:HERMES_PROJECT_RUNTIME_ROOT = $RuntimeRoot
$env:HERMES_PROJECT_ARTIFACTS = Join-Path $ProjectRoot ".hermes\task-artifacts"
$env:HERMES_PROJECT_LOGS = Join-Path $RuntimeRoot "logs"
