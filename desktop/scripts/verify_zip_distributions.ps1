param(
    [Parameter(Mandatory = $true)]
    [string]$GreenArchive,
    [Parameter(Mandatory = $true)]
    [string]$PortableArchive,
    [switch]$RequireReleaseIdentity
)

$ErrorActionPreference = 'Stop'
$projectRuntime = Join-Path $PSScriptRoot '..\..\.hermes\task-runtime'
$workRoot = Join-Path $projectRuntime ("distribution-lifecycle-" + [guid]::NewGuid().ToString('N'))
$appData = Join-Path $env:LOCALAPPDATA 'com.archeaxis.workspace'
$appDataExisted = Test-Path -LiteralPath $appData

function Wait-ArcheAxisBackend {
    param([System.Diagnostics.Process]$Shell)

    for ($attempt = 0; $attempt -lt 160; $attempt++) {
        Start-Sleep -Milliseconds 250
        $Shell.Refresh()
        if ($Shell.HasExited) {
            throw "desktop shell exited before readiness with $($Shell.ExitCode)"
        }
        $child = Get-CimInstance Win32_Process -Filter "ParentProcessId=$($Shell.Id)" -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -eq 'python.exe' } |
            Select-Object -First 1
        if (-not $child) {
            continue
        }
        $listener = Get-NetTCPConnection -OwningProcess $child.ProcessId -State Listen -ErrorAction SilentlyContinue |
            Where-Object { $_.LocalAddress -eq '127.0.0.1' } |
            Select-Object -First 1
        if ($listener) {
            return [pscustomobject]@{ Child = $child; Listener = $listener }
        }
    }
    throw 'desktop backend did not become ready'
}

function Stop-ArcheAxisShell {
    param(
        [System.Diagnostics.Process]$Shell,
        [int]$BackendProcessId
    )

    $Shell.Refresh()
    if (-not $Shell.HasExited) {
        $closeSent = $Shell.CloseMainWindow()
        if (-not $closeSent) {
            throw "desktop shell rejected WM_CLOSE; pid=$($Shell.Id)"
        }
        if (-not $Shell.WaitForExit(30000)) {
            throw "desktop shell did not exit after WM_CLOSE; pid=$($Shell.Id)"
        }
    }
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        Start-Sleep -Milliseconds 250
        if (-not (Get-Process -Id $BackendProcessId -ErrorAction SilentlyContinue)) {
            return
        }
    }
    throw "owned Python survived desktop shutdown; pid=$BackendProcessId"
}

function Assert-ReleaseIdentity {
    param([string]$BaseUrl)

    if (-not $RequireReleaseIdentity) {
        return
    }
    $version = Invoke-RestMethod "$BaseUrl/version"
    if (
        $version.release.status -ne 'released' -or
        $version.release.tag -ne 'v0.6.1' -or
        $version.capabilities.public_installer -ne 'available'
    ) {
        throw 'distribution runtime did not expose the verified public release identity'
    }
}

function Invoke-DistributionLifecycle {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root,
        [Parameter(Mandatory = $true)]
        [bool]$Portable
    )

    $executable = Join-Path $Root 'ArcheAxis.exe'
    $python = Join-Path $Root 'runtime\python\python.exe'
    if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
        throw "distribution executable is missing: $executable"
    }
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw "distribution bundled Python is missing: $python"
    }
    if ($Portable) {
        $marker = Join-Path $Root 'portable.flag'
        $dataRoot = Join-Path $Root 'data'
        if (-not (Test-Path -LiteralPath $marker -PathType Leaf)) {
            throw 'portable distribution marker is missing'
        }
        if (-not (Test-Path -LiteralPath $dataRoot -PathType Container)) {
            throw 'portable distribution data root is missing'
        }
    }

    $pycBefore = @(Get-ChildItem (Join-Path $Root 'runtime') -Filter '*.pyc' -File -Recurse).Count
    $workspaceStatus = 0
    for ($launch = 1; $launch -le 2; $launch++) {
        $shell = $null
        try {
            $shell = Start-Process -FilePath $executable -WorkingDirectory $Root -PassThru
            $ready = Wait-ArcheAxisBackend -Shell $shell
            if ($ready.Child.ExecutablePath -ne $python) {
                throw "desktop used an unexpected Python: $($ready.Child.ExecutablePath)"
            }
            if ($ready.Child.CommandLine -notmatch ' -B -I -m app\.runtime_entrypoint core$') {
                throw "desktop Python isolation arguments are invalid: $($ready.Child.CommandLine)"
            }
            $base = "http://127.0.0.1:$($ready.Listener.LocalPort)"
            $workspaceStatus = (Invoke-WebRequest "$base/workspace" -UseBasicParsing).StatusCode
            $status = Invoke-RestMethod "$base/workspace/api/status"
            if ($workspaceStatus -ne 200 -or $status.release.version -ne '0.6.1') {
                throw 'distribution Workspace returned an invalid product response'
            }
            Assert-ReleaseIdentity -BaseUrl $base
            Stop-ArcheAxisShell -Shell $shell -BackendProcessId $ready.Child.ProcessId
            $shell = $null
        }
        finally {
            if ($shell -and -not $shell.HasExited) {
                Stop-Process -Id $shell.Id -Force -ErrorAction SilentlyContinue
            }
        }
    }
    $pycAfter = @(Get-ChildItem (Join-Path $Root 'runtime') -Filter '*.pyc' -File -Recurse).Count
    if ($pycAfter -ne $pycBefore) {
        throw "distribution runtime wrote bytecode: before=$pycBefore after=$pycAfter"
    }
    if ($Portable) {
        $portableDatabase = Join-Path $Root 'data\data\archeaxis.sqlite'
        if (-not (Test-Path -LiteralPath $portableDatabase -PathType Leaf)) {
            throw 'portable launch did not retain its database under data/'
        }
    }

    return [pscustomobject]@{
        Portable = $Portable
        WorkspaceStatus = $workspaceStatus
        Restarted = $true
        PycGrowth = $pycAfter - $pycBefore
    }
}

function Expand-Distribution {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Archive,
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    if (-not (Test-Path -LiteralPath $Archive -PathType Leaf)) {
        throw "distribution archive is missing: $Archive"
    }
    $destination = Join-Path $workRoot $Name
    Expand-Archive -LiteralPath $Archive -DestinationPath $destination
    $root = Join-Path $destination $Name
    if (-not (Test-Path -LiteralPath $root -PathType Container)) {
        throw "archive root is missing: $Name"
    }
    return $root
}

try {
    New-Item -ItemType Directory -Force -Path $workRoot | Out-Null
    $greenRoot = Expand-Distribution -Archive $GreenArchive -Name 'ArcheAxis.Knowledge.Green-x64'
    $portableRoot = Expand-Distribution -Archive $PortableArchive -Name 'ArcheAxis.Knowledge.Portable-x64'
    $portable = Invoke-DistributionLifecycle -Root $portableRoot -Portable $true
    if (-not $appDataExisted -and (Test-Path -LiteralPath $appData)) {
        throw 'portable launch wrote a WebView profile under LOCALAPPDATA'
    }
    $green = Invoke-DistributionLifecycle -Root $greenRoot -Portable $false
    [pscustomobject]@{ Green = $green; Portable = $portable } | ConvertTo-Json -Compress -Depth 3
}
finally {
    if (Test-Path -LiteralPath $workRoot) {
        Remove-Item -LiteralPath $workRoot -Recurse -Force
    }
    if (-not $appDataExisted -and (Test-Path -LiteralPath $appData)) {
        Remove-Item -LiteralPath $appData -Recurse -Force
    }
}
