# PowerShell 7 entrypoint; both shells share the same resolver.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$interpreter = $env:ARCHEAXIS_PYTHON
if (-not $interpreter) {
    $interpreter = Join-Path $projectRoot '.project-local/build/venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $interpreter)) {
        # Keep the historical root .venv as a compatibility fallback only;
        # dev.py creates the managed environment under .project-local/build.
        $interpreter = Join-Path $projectRoot '.venv/Scripts/python.exe'
        if (-not (Test-Path -LiteralPath $interpreter)) {
            $interpreter = (Get-Command python -ErrorAction Stop).Source
        }
    }
}
$testArgs = @($args)
if ($testArgs.Count -gt 0 -and $testArgs[0] -eq '--') {
    $testArgs = @($testArgs | Select-Object -Skip 1)
}
$modeArgs = @('--pytest')
if ($testArgs.Count -gt 0 -and $testArgs[0] -eq '--full') {
    $modeArgs += '--full'
    $testArgs = @($testArgs | Select-Object -Skip 1)
}
& $interpreter -B (Join-Path $projectRoot 'scripts/runtime/dev.py') @modeArgs -- @testArgs
exit $LASTEXITCODE
