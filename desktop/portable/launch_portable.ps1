[CmdletBinding()]
param(
    [string]$DataRoot = (Join-Path $PSScriptRoot "data")
)

$ErrorActionPreference = "Stop"
$portableExe = Join-Path $PSScriptRoot "archeaxis-desktop-shell.exe"

if (-not (Test-Path -LiteralPath $portableExe -PathType Leaf)) {
    throw "Portable desktop executable is missing: $portableExe"
}

$dataRoot = [System.IO.Path]::GetFullPath($DataRoot)
New-Item -ItemType Directory -Force -Path $dataRoot | Out-Null
$env:COGNITIVE_PORTABLE_ROOT = $dataRoot

Start-Process -FilePath $portableExe -WorkingDirectory $PSScriptRoot
