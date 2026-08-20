param(
    [Parameter(Mandatory = $true)]
    [string]$Installer,
    [switch]$RequireReleaseIdentity
)

$ErrorActionPreference = 'Stop'
$installRoot = Join-Path $env:LOCALAPPDATA 'ArcheAxis Knowledge'
$appData = Join-Path $env:LOCALAPPDATA 'com.archeaxis.workspace'
$uninstallKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*'
$appDataExisted = Test-Path $appData
$ownsInstall = $false
$activeShell = $null

function Get-ArcheAxisRegistryEntries {
    return @(
        Get-ItemProperty $uninstallKey -ErrorAction SilentlyContinue |
            Where-Object { $_.DisplayName -eq 'ArcheAxis Knowledge' }
    )
}

function Wait-ArcheAxisBackend {
    param([System.Diagnostics.Process]$Shell)

    for ($attempt = 0; $attempt -lt 160; $attempt++) {
        Start-Sleep -Milliseconds 250
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
    throw 'installed desktop backend did not become ready'
}

function Wait-ArcheAxisWindow {
    param([System.Diagnostics.Process]$Shell)

    for ($attempt = 0; $attempt -lt 80; $attempt++) {
        Start-Sleep -Milliseconds 250
        $Shell.Refresh()
        if ($Shell.HasExited) {
            throw "desktop shell exited before its main window became ready with $($Shell.ExitCode)"
        }
        if ($Shell.MainWindowHandle -ne [IntPtr]::Zero) {
            return $Shell.MainWindowHandle
        }
    }
    throw "desktop shell main window was not ready; pid=$($Shell.Id) handle=$($Shell.MainWindowHandle)"
}

function Stop-ArcheAxisInstallation {
    $uninstaller = Join-Path $installRoot 'uninstall.exe'
    if (Test-Path $uninstaller) {
        $process = Start-Process -FilePath $uninstaller -ArgumentList '/S' -Wait -PassThru
        if ($process.ExitCode -ne 0) {
            throw "NSIS uninstaller exited with $($process.ExitCode)"
        }
        Start-Sleep -Seconds 3
    }
}

if (-not (Test-Path -LiteralPath $Installer -PathType Leaf)) {
    throw "NSIS installer is missing: $Installer"
}
if ((Test-Path $installRoot) -or (Get-ArcheAxisRegistryEntries).Count -ne 0) {
    throw 'refusing to overwrite an existing ArcheAxis Knowledge installation'
}

try {
    $installerProcess = Start-Process -FilePath $Installer -ArgumentList '/S' -Wait -PassThru
    if ($installerProcess.ExitCode -ne 0) {
        throw "NSIS installer exited with $($installerProcess.ExitCode)"
    }
    $ownsInstall = $true

    $executable = Join-Path $installRoot 'ArcheAxis.exe'
    $python = Join-Path $installRoot 'runtime\python\python.exe'
    $doubleNestedPython = Join-Path $installRoot 'runtime\runtime\python\python.exe'
    if (-not (Test-Path $executable -PathType Leaf)) {
        throw 'installed desktop executable is missing'
    }
    if (-not (Test-Path $python -PathType Leaf)) {
        throw 'installed bundled Python is missing'
    }
    if (Test-Path $doubleNestedPython) {
        throw 'installed Runtime contains an invalid double runtime directory'
    }

    $pycBefore = @(Get-ChildItem (Join-Path $installRoot 'runtime') -Filter '*.pyc' -File -Recurse).Count
    $activeShell = Start-Process -FilePath $executable -PassThru
    $normal = Wait-ArcheAxisBackend -Shell $activeShell
    if ($normal.Child.ExecutablePath -ne $python) {
        throw "desktop used an unexpected Python: $($normal.Child.ExecutablePath)"
    }
    if ($normal.Child.CommandLine -notmatch ' -B -I -m app\.runtime_entrypoint core$') {
        throw "desktop Python isolation arguments are invalid: $($normal.Child.CommandLine)"
    }
    $base = "http://127.0.0.1:$($normal.Listener.LocalPort)"
    $workspaceStatus = (Invoke-WebRequest "$base/workspace" -UseBasicParsing).StatusCode
    $status = Invoke-RestMethod "$base/workspace/api/status"
    if ($workspaceStatus -ne 200 -or $status.release.version -ne '0.6.0') {
        throw 'installed Workspace returned an invalid product response'
    }
    if ($RequireReleaseIdentity) {
        $version = Invoke-RestMethod "$base/version"
        if (
            $version.release.status -ne 'released' -or
            $version.release.tag -ne 'v0.6.0' -or
            $version.capabilities.public_installer -ne 'available'
        ) {
            throw 'installed runtime did not expose the verified public release identity'
        }
    }
    $windowHandle = Wait-ArcheAxisWindow -Shell $activeShell
    $closeSent = $activeShell.CloseMainWindow()
    if (-not $closeSent) {
        throw "desktop shell rejected WM_CLOSE; pid=$($activeShell.Id) handle=$windowHandle"
    }
    if (-not $activeShell.WaitForExit(30000)) {
        $activeShell.Refresh()
        throw "desktop shell did not exit after WM_CLOSE; pid=$($activeShell.Id) handle=$windowHandle main_window=$($activeShell.MainWindowHandle)"
    }
    Start-Sleep -Seconds 1
    if (Get-Process -Id $normal.Child.ProcessId -ErrorAction SilentlyContinue) {
        throw 'owned Python survived normal desktop shutdown'
    }
    $pycAfter = @(Get-ChildItem (Join-Path $installRoot 'runtime') -Filter '*.pyc' -File -Recurse).Count
    if ($pycAfter -ne $pycBefore) {
        throw "installed Runtime wrote bytecode: before=$pycBefore after=$pycAfter"
    }

    # The same package must be able to replace the installed program without
    # replacing user state.  A release run cannot manufacture a prior signed
    # version, so this is deliberately named an in-place upgrade rather than
    # claiming cross-version migration coverage.
    # ARCHEAXIS_DATA_DIR is the runtime root.  resolve_runtime_path strips the
    # leading `data` component from the configured relative database path, so
    # the installed database lives directly below the app-local data root.
    $persistedDatabase = Join-Path $appData 'archeaxis.sqlite'
    if (-not (Test-Path -LiteralPath $persistedDatabase -PathType Leaf)) {
        throw "first launch did not create the expected user database: $persistedDatabase"
    }
    $persistenceSentinel = Join-Path $appData 'release-lifecycle-sentinel.txt'
    Set-Content -LiteralPath $persistenceSentinel -Value 'retain-this-user-state' -Encoding utf8 -NoNewline

    $upgradeProcess = Start-Process -FilePath $Installer -ArgumentList '/S' -Wait -PassThru
    if ($upgradeProcess.ExitCode -ne 0) {
        throw "NSIS in-place upgrade exited with $($upgradeProcess.ExitCode)"
    }
    if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
        throw 'NSIS in-place upgrade did not restore the desktop executable'
    }
    if (-not (Test-Path -LiteralPath $persistenceSentinel -PathType Leaf)) {
        throw 'NSIS in-place upgrade removed user state'
    }
    $activeShell = Start-Process -FilePath $executable -PassThru
    $upgraded = Wait-ArcheAxisBackend -Shell $activeShell
    $upgradedBase = "http://127.0.0.1:$($upgraded.Listener.LocalPort)"
    $upgradedStatus = Invoke-RestMethod "$upgradedBase/workspace/api/status"
    if ($upgradedStatus.release.version -ne '0.6.0') {
        throw 'in-place upgraded Workspace returned an invalid product response'
    }
    $upgradeCloseSent = $activeShell.CloseMainWindow()
    if (-not $upgradeCloseSent -or -not $activeShell.WaitForExit(30000)) {
        throw 'desktop shell did not close after in-place upgrade readback'
    }
    $activeShell = $null

    $activeShell = Start-Process -FilePath $executable -PassThru
    $forced = Wait-ArcheAxisBackend -Shell $activeShell
    $forcedChildId = $forced.Child.ProcessId
    $forcedPort = $forced.Listener.LocalPort
    Stop-Process -Id $activeShell.Id -Force
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        Start-Sleep -Milliseconds 250
        if (-not (Get-Process -Id $forcedChildId -ErrorAction SilentlyContinue)) {
            break
        }
    }
    if (Get-Process -Id $forcedChildId -ErrorAction SilentlyContinue) {
        throw 'owned Python survived forced desktop termination'
    }
    if (Get-NetTCPConnection -LocalPort $forcedPort -State Listen -ErrorAction SilentlyContinue) {
        throw 'desktop port survived forced desktop termination'
    }
    $activeShell = $null

    Stop-ArcheAxisInstallation
    $ownsInstall = $false
    if (Test-Path $installRoot) {
        throw 'NSIS uninstall left files in the installation directory'
    }
    if ((Get-ArcheAxisRegistryEntries).Count -ne 0) {
        throw 'NSIS uninstall left an uninstall registry entry'
    }
    if (-not (Test-Path -LiteralPath $persistedDatabase -PathType Leaf) -or
        -not (Test-Path -LiteralPath $persistenceSentinel -PathType Leaf)) {
        throw 'NSIS uninstall removed user data instead of retaining it'
    }

    $reinstallProcess = Start-Process -FilePath $Installer -ArgumentList '/S' -Wait -PassThru
    if ($reinstallProcess.ExitCode -ne 0) {
        throw "NSIS reinstall exited with $($reinstallProcess.ExitCode)"
    }
    $activeShell = Start-Process -FilePath $executable -PassThru
    $reinstalled = Wait-ArcheAxisBackend -Shell $activeShell
    $reinstalledBase = "http://127.0.0.1:$($reinstalled.Listener.LocalPort)"
    $reinstalledStatus = Invoke-RestMethod "$reinstalledBase/workspace/api/status"
    if ($reinstalledStatus.release.version -ne '0.6.0' -or
        -not (Test-Path -LiteralPath $persistenceSentinel -PathType Leaf)) {
        throw 'reinstalled Workspace did not read back retained user state'
    }
    $reinstallCloseSent = $activeShell.CloseMainWindow()
    if (-not $reinstallCloseSent -or -not $activeShell.WaitForExit(30000)) {
        throw 'desktop shell did not close after reinstall readback'
    }
    $activeShell = $null

    Stop-ArcheAxisInstallation
    $ownsInstall = $false
    if ((Test-Path -LiteralPath $installRoot) -or (Get-ArcheAxisRegistryEntries).Count -ne 0) {
        throw 'NSIS final uninstall did not clean the installation state'
    }
    if (-not (Test-Path -LiteralPath $persistedDatabase -PathType Leaf) -or
        -not (Test-Path -LiteralPath $persistenceSentinel -PathType Leaf)) {
        throw 'NSIS final uninstall removed retained user data'
    }

    [pscustomobject]@{
        Version = $status.release.version
        WorkspaceStatus = $workspaceStatus
        PycGrowth = $pycAfter - $pycBefore
        GracefulShutdown = $true
        ForcedTreeCleanup = $true
        CleanUninstall = $true
        InPlaceUpgrade = $true
        UninstallRetainsData = $true
        ReinstallReadback = $true
    } | ConvertTo-Json -Compress
}
finally {
    if ($activeShell -and -not $activeShell.HasExited) {
        Stop-Process -Id $activeShell.Id -Force -ErrorAction SilentlyContinue
    }
    if ($ownsInstall) {
        Stop-ArcheAxisInstallation
    }
    if (-not $appDataExisted -and (Test-Path $appData)) {
        Remove-Item -LiteralPath $appData -Recurse -Force
    }
}
