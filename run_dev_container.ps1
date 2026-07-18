[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $Command
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker Desktop with Compose is required. Install it on this computer first."
}

$compose = @("compose", "-f", "docker-compose.dev.yml")
& docker @compose build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($Command.Count -eq 0) {
    $Command = @("bash")
}

& docker @compose run --rm dev @Command
exit $LASTEXITCODE
