#requires -Version 7.0
<#
    SYNOPSIS
      Windows/PowerShell 7 doctor for archeaxis-workspace (AXW-007A).

    DESCRIPTION
      Detects the toolchain and Windows-environment prerequisites needed to run,
      test, and package the project: Python, Node, Rust, PowerShell, Chinese and
      space-containing paths, port availability, console encoding, and writable
      directories.

      Output is strictly sanitized: it never prints secrets, tokens, cookies,
      credentials, private paths outside the declared scope, or personal body
      text. Only names, versions, availability booleans and path-layout facts are
      emitted. All results are returned as structured JSON on stdout; warnings go
      to stderr.

    OUTPUT
      A single JSON object:
      {
        "schema_version": "axw.007a.v1",
        "generated_at": "...",
        "toolchain": { "python": {...}, "node": {...}, "rust": {...}, "powershell": {...} },
        "paths": { "space_in_path": bool, "non_ascii_in_path": bool, "project_root": "<sanitized>", ... },
        "ports": { "<label>": { "port": int, "available": bool } },
        "encoding": { "console_codepage": int, "utf8_default": bool },
        "writable": [ { "label": "...", "path": "...", "writable": bool } ],
        "healthy": bool
      }

    PARAMETER ProjectRoot
      Optional absolute path to the repository root. Defaults to the script's
      parent (project checkout). Used only to detect path-layout facts and
      writable-directory checks; the emitted path is a relative or sanitized form.

    EXAMPLE
      pwsh -NoProfile -File scripts/doctor_windows.ps1
#>
[CmdletBinding()]
param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot ".."))
)

$ErrorActionPreference = "Continue"

function Test-CommandAvailable {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Get-Version([string]$Name) {
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $cmd) { return $null }
    try {
        $v = & $Name --version 2>$null | Select-Object -First 1
        return $v
    } catch { return $null }
}

function Test-PortAvailable([int]$Port) {
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
        $listener.Start()
        $listener.Stop()
        return $true
    } catch { return $false }
}

$result = [ordered]@{}

$project = [System.IO.Path]::GetFullPath((Resolve-Path $ProjectRoot).Path)

# --- Toolchain -----------------------------------------------------------
$result.schema_version = "axw.007a.v1"
$result.generated_at = (Get-Date -Format o)

$python = [ordered]@{ present = $false }
if (Test-CommandAvailable "python") { $python.present = $true; $python.version = Get-Version "python" }
if (Test-CommandAvailable "py")    { $python.launcher_present = $true }
if (-not $python.present) {
    $projectPython = Join-Path $project ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $projectPython -PathType Leaf) {
        try {
            $python.present = $true
            $python.source = "project_venv"
            $python.version = (& $projectPython --version 2>$null | Select-Object -First 1)
        } catch { $python.present = $false }
    }
}

function Get-ExternalRustTool([string]$Name) {
    $root = $env:ARCHEAXIS_RUST_TOOLCHAINS
    if (-not $root) { return $null }
    $candidate = Join-Path $root ("cargo\bin\$Name.exe")
    if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    return $null
}

$node = [ordered]@{ present = $false }
if (Test-CommandAvailable "node") { $node.present = $true; $node.version = Get-Version "node" }
if (Test-CommandAvailable "npm")  { $node.npm_present = $true }

$rust = [ordered]@{ present = $false }
$cargoCommand = Get-Command cargo -ErrorAction SilentlyContinue
if (-not $cargoCommand) { $cargoCommand = Get-ExternalRustTool "cargo" }
if ($cargoCommand) {
    $rust.present = $true
    $rust.source = if ($cargoCommand -is [string]) { "external_toolchain" } else { "path" }
    $rust.version = Get-Version ([string]$cargoCommand)
}
$rustcCommand = Get-Command rustc -ErrorAction SilentlyContinue
if (-not $rustcCommand) { $rustcCommand = Get-ExternalRustTool "rustc" }
if ($rustcCommand) { $rust.rustc_present = $true }

$ps = [ordered]@{ present = $true; version = $PSVersionTable.PSVersion.ToString() }

$result.toolchain = [ordered]@{
    python      = $python
    node        = $node
    rust        = $rust
    powershell  = $ps
}

# --- Path layout facts ---------------------------------------------------
$result.paths = [ordered]@{
    space_in_path    = $project.Contains(" ")
    non_ascii_in_path = ($project.ToCharArray() | Where-Object { [int]$_ -gt 127 } | Measure-Object).Count -gt 0
    project_root_sanitized = (Split-Path $project -Leaf)   # leaf only; no full private path
}

# --- Port availability ---------------------------------------------------
$result.ports = [ordered]@{}
foreach ($port in @(8000, 8001, 9000, 4444, 9515)) {
    $result.ports[$port.ToString()] = [ordered]@{ port = $port; available = (Test-PortAvailable $port) }
}

# --- Console encoding ----------------------------------------------------
$result.encoding = [ordered]@{
    console_codepage = [Console]::OutputEncoding.CodePage
    utf8_default     = ([Console]::OutputEncoding.WebName -eq "utf-8")
}

# --- Writable directories (project-local only) ---------------------------
$candidates = @(
    @{ label = "project_root"; path = $project },
    @{ label = "runtime_cache"; path = (Join-Path $project ".project-local/task-runtime") }
)
$result.writable = @()
foreach ($c in $candidates) {
    $target = $c.path
    $writable = $false
    try {
        New-Item -ItemType Directory -Path $target -Force -ErrorAction Stop | Out-Null
        $probe = Join-Path $target (".doctor_probe_" + [Guid]::NewGuid().ToString("N") + ".tmp")
        Set-Content -Path $probe -Value "x" -ErrorAction Stop | Out-Null
        Remove-Item -Path $probe -Force -ErrorAction Stop
        $writable = $true
    } catch {
        $writable = $false
    }
    $result.writable += [ordered]@{
        label     = $c.label
        path      = (Split-Path $target -Leaf)   # sanitized leaf only
        writable  = $writable
    }
}

# --- Public directory access ---------------------------------------------
# Keep private agent state out of this probe; report only sanitized leaf names.
$private = @('.git', '.hermes', '.zcode', '.codex', '.venv', '.project-local', 'data')
$accessBlockers = @()
foreach ($entry in (Get-ChildItem -LiteralPath $project -Directory -Force -ErrorAction SilentlyContinue)) {
    if ($private -contains $entry.Name) { continue }
    try { Get-Acl -LiteralPath $entry.FullName -ErrorAction Stop | Out-Null }
    catch { $accessBlockers += (Split-Path $entry.FullName -Leaf) }
}
# Some deny-only directories are omitted by enumeration; probe known generated
# roots explicitly so an inaccessible residue cannot hide from the report.
foreach ($name in @('.pytest_cache')) {
    $candidate = Join-Path $project $name
    if (-not (Test-Path -LiteralPath $candidate -PathType Container)) { continue }
    try { Get-Acl -LiteralPath $candidate -ErrorAction Stop | Out-Null }
    catch { $accessBlockers += $name }
}
$result.access_blockers = @($accessBlockers | Sort-Object -Unique)

# --- Overall health ------------------------------------------------------
$required = @("python")
$missing = @($required | Where-Object { -not $result.toolchain.$_.present })
$result.healthy = ($missing.Count -eq 0 -and $result.access_blockers.Count -eq 0)

$result | ConvertTo-Json -Depth 6
