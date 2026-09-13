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
$uvCommand = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvCommand) {
    $uvCandidate = Join-Path $env:LOCALAPPDATA "hermes\bin\uv.exe"
    if (Test-Path -LiteralPath $uvCandidate -PathType Leaf) { $uvCommand = Get-Item -LiteralPath $uvCandidate }
}
if (-not $uvCommand) { throw "uv executable is required; add uv to PATH or install the approved project toolchain" }
$uv = $uvCommand.Source
$python = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    & $uv venv (Join-Path $repo ".venv")
}
& $uv pip install --python $python -r (Join-Path $repo "requirements.txt")
& $python (Join-Path $repo "scripts\runtime\dev.py") -- $python -m app.runtime_entrypoint core
exit $LASTEXITCODE
