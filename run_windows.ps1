$ErrorActionPreference = "Stop"
$repo = (Resolve-Path $PSScriptRoot).Path
$runtime = Join-Path $repo ".project-local\task-runtime"
$cache = Join-Path $repo ".project-local\cache"
New-Item -ItemType Directory -Force -Path $runtime, $cache | Out-Null
$env:TEMP = Join-Path $runtime "tmp"
$env:TMP = $env:TEMP
$env:TMPDIR = $env:TEMP
$env:PIP_CACHE_DIR = Join-Path $cache "pip"
$env:UV_CACHE_DIR = Join-Path $cache "uv"
$python = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    python -m venv (Join-Path $repo ".venv")
}
uv pip install --python $python -r (Join-Path $repo "requirements.txt")
& $python (Join-Path $repo "scripts\runtime\dev.py") -- $python -m app.runtime_entrypoint core
exit $LASTEXITCODE
