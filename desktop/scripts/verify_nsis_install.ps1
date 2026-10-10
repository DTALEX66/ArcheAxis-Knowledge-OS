param(
    [Parameter(Mandatory = $true)]
    [string]$Installer,
    [switch]$RequireReleaseIdentity,
    [switch]$RequireCandidateIdentity,
    [string]$NativeToolsReceipt,
    [switch]$GroupedOwnerLoop
)

$ErrorActionPreference = 'Stop'
$installRoot = Join-Path $env:LOCALAPPDATA 'ArcheAxis Knowledge'
$appData = Join-Path $env:LOCALAPPDATA 'com.archeaxis.workspace'
$uninstallKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*'
$appDataExisted = Test-Path $appData
$ownsInstall = $false
$activeShell = $null
$evidenceDirectory = $null

if ($GroupedOwnerLoop -and -not $NativeToolsReceipt) {
    throw 'grouped native qualification requires a verified NativeToolsReceipt'
}

if (-not ('ArcheAxisWindow' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

public static class ArcheAxisWindow
{
    private const uint WmClose = 0x0010;
    private delegate bool EnumWindowsProc(IntPtr window, IntPtr parameter);

    [DllImport("user32.dll")]
    private static extern bool EnumWindows(EnumWindowsProc callback, IntPtr parameter);

    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(IntPtr window, out uint processId);

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool IsWindow(IntPtr window);

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool IsWindowVisible(IntPtr window);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowText(IntPtr window, StringBuilder text, int maximum);

    [DllImport("user32.dll")]
    private static extern int GetWindowTextLength(IntPtr window);

    [DllImport("user32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool PostMessage(IntPtr window, uint message, IntPtr wParam, IntPtr lParam);

    private static List<Tuple<IntPtr, string>> Candidates(uint processId)
    {
        var matches = new List<Tuple<IntPtr, string>>();
        EnumWindows((window, parameter) =>
        {
            uint owner;
            GetWindowThreadProcessId(window, out owner);
            var length = GetWindowTextLength(window);
            if (owner == processId && IsWindowVisible(window) && length > 0)
            {
                var title = new StringBuilder(length + 1);
                GetWindowText(window, title, title.Capacity);
                matches.Add(Tuple.Create(window, title.ToString()));
            }
            return true;
        }, IntPtr.Zero);
        return matches;
    }

    public static IntPtr FindVisibleTopLevelWindow(uint processId)
    {
        var matches = Candidates(processId);
        if (matches.Count == 1)
        {
            return matches[0].Item1;
        }

        IntPtr branded = IntPtr.Zero;
        foreach (var match in matches)
        {
            if (!match.Item2.StartsWith("ArcheAxis", StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }
            if (branded != IntPtr.Zero)
            {
                return IntPtr.Zero;
            }
            branded = match.Item1;
        }
        return branded;
    }

    public static string DescribeVisibleTopLevelWindows(uint processId)
    {
        var descriptions = new List<string>();
        foreach (var match in Candidates(processId))
        {
            descriptions.Add(match.Item1.ToInt64() + ":" + match.Item2);
        }
        return descriptions.Count == 0 ? "none" : string.Join(",", descriptions);
    }

    public static bool PostClose(IntPtr window, uint expectedProcessId)
    {
        uint owner;
        GetWindowThreadProcessId(window, out owner);
        return IsWindow(window) && owner == expectedProcessId &&
            PostMessage(window, WmClose, IntPtr.Zero, IntPtr.Zero);
    }
}
'@
}

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
            Where-Object { $_.ExecutablePath -eq $coreExecutable } |
            Select-Object -First 1
        if (-not $child) {
            continue
        }
        $listener = Get-NetTCPConnection -OwningProcess $child.ProcessId -State Listen -ErrorAction SilentlyContinue |
            Where-Object { $_.LocalAddress -eq '127.0.0.1' } |
            Select-Object -First 1
        if ($listener) {
            if ($child.CommandLine -notmatch [regex]::Escape($persistedDatabase)) {
                throw 'installed Core did not open the expected user workspace'
            }
            $response = Invoke-WebRequest "http://127.0.0.1:$($listener.LocalPort)/api/v1/system/version" -SkipHttpErrorCheck -TimeoutSec 5
            $failure = $response.Content | ConvertFrom-Json
            if ([int]$response.StatusCode -ne 401 -or $failure.code -ne 'AAK-AUTH-001') {
                throw 'installed Core did not enforce its launch-session authentication'
            }
            return [pscustomobject]@{ Child = $child; Listener = $listener }
        }
    }
    throw 'installed desktop backend did not become ready'
}

function Read-CoreCandidateProof {
    param([ValidateSet('seed', 'readback')][string]$Mode)

    # The shell's stdin credentials remain private. After it exits, the installed
    # authority launcher opens a separate authenticated v2 session on the SAME DB.
    $probe = @'
import base64, hashlib, importlib.util, json, os, sys, time
from pathlib import Path
root, data, mode, requirement = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
spec = importlib.util.spec_from_file_location("installed_launcher", root / "start-backend.py")
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)
profile = launcher.load_profile(root)
assert Path(sys.executable).resolve() == profile["python"].resolve(), "profile interpreter mismatch"
import app.release as release
import openpyxl, pptx
assert Path(release.__file__).resolve().is_relative_to(root.resolve()), "release module came from outside installation"
modules = [{"name": m.__name__, "path": m.__file__, "version": m.__version__} for m in (openpyxl, pptx)]
assert all(Path(m["path"]).resolve().is_relative_to(root.resolve()) for m in modules), "engines came from outside installation"
summary, capabilities = release.safe_release_summary(), release.effective_capabilities()
assert summary["version"] == "0.6.14", "installed product version mismatch"
if requirement == "candidate":
    assert summary["status"] == "qualified" and summary["tag"] == "v0.6.14" and summary["public"] is False
    assert capabilities["public_installer"] != "available"
    if os.environ.get("GITHUB_SHA"):
        assert summary["source_commit"] == os.environ["GITHUB_SHA"], "candidate source SHA mismatch"
elif requirement == "release":
    assert summary["status"] == "released" and summary["tag"] == "v0.6.14" and summary["public"] is True
    assert capabilities["public_installer"] == "available"
record_path = data / "installer-core-readback.json"
child = None
try:
    child, base, receipt, tokens = launcher.start(data, launcher.free_port(), workspace_name="archeaxis.sqlite")
    def call(method, path, body=None, headers=None):
        code, body = launcher.call(base, method, path, body, tokens=tokens, role="human", header_tokens=headers)
        assert 200 <= code < 300, f"installed Core request failed: {path}: {code}: {body}"
        return body
    version = call("GET", "/api/v1/system/version")
    assert version["runtime"] == "archeaxis-api" and version["contract"] == "0.1.0-outline"
    assert type(version["schema_version"]) is int and version["schema_version"] > 0
    assert version["launch_protocol"] == "archeaxis.desktop-launch/v2" and version["actor"] == "human"
    assert Path(version["workspace_db"]).samefile(data / "archeaxis.sqlite"), "Core version workspace_db does not identify the installed user database"
    info = call("GET", "/api/v1/workspaces/info")
    handshake = call("GET", "/api/v1/capabilities")
    text = b"Installed canonical Core lifecycle readback\n"
    if mode == "seed":
        imported = call("POST", "/api/v1/imports", {"name": "installer-lifecycle.txt", "content_base64": base64.b64encode(text).decode()})
        assert imported["sha256"] == hashlib.sha256(text).hexdigest()
        job = "installer-lifecycle-" + os.urandom(8).hex()
        call("POST", "/api/v1/jobs", {"job_id": job, "kind": "text", "input_ref": imported["source_id"]})
        call("POST", f"/api/v1/jobs/{job}/executions", {"deadline_ms": 30000}, {"idempotency-key": job})
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            state = call("GET", f"/api/v1/jobs/{job}")
            if state.get("state") in {"succeeded", "failed", "cancelled"}:
                break
            time.sleep(0.1)
        assert state["state"] == "succeeded", state
    else:
        saved = json.loads(record_path.read_text(encoding="utf-8"))
        job = saved["job_id"]
        state = call("GET", f"/api/v1/jobs/{job}")
        assert state["state"] == "succeeded", state
    output = call("GET", f"/api/v1/jobs/{job}/outputs/text")
    quality = call("GET", f"/api/v1/jobs/{job}/quality")
    assert text.decode() in json.dumps(output, ensure_ascii=False).replace("\\n", "\n")
    assert quality["engine"] == "python-worker-text" and quality["coverage"] == 1.0
    current = {"job_id": job, "output": output, "quality": quality}
    if mode == "seed":
        record_path.write_text(json.dumps(current, ensure_ascii=False), encoding="utf-8")
    else:
        assert current == saved, "installed Core persistent readback changed"
    result = {"product_version": summary["version"], "runtime": version["runtime"], "schema_version": version["schema_version"],
              "job_id": job, "mode": mode, "imports": modules, "profile_python": str(profile["python"]), "release": summary}
finally:
    if child is not None:
        launcher.stop(child)
print(json.dumps(result, ensure_ascii=False))
'@
    $requirement = if ($RequireCandidateIdentity) { 'candidate' } elseif ($RequireReleaseIdentity) { 'release' } else { 'none' }
    $proof = & $python -B -I -c $probe $installRoot $appData $Mode $requirement
    if ($LASTEXITCODE -ne 0) { throw "installed canonical Core $Mode probe failed" }
    return ($proof | ConvertFrom-Json)
}

function Wait-ArcheAxisWindow {
    param([System.Diagnostics.Process]$Shell)

    for ($attempt = 0; $attempt -lt 80; $attempt++) {
        Start-Sleep -Milliseconds 250
        $Shell.Refresh()
        if ($Shell.HasExited) {
            throw "desktop shell exited before its main window became ready with $($Shell.ExitCode)"
        }
        $window = [ArcheAxisWindow]::FindVisibleTopLevelWindow([uint32]$Shell.Id)
        if ($window -ne [IntPtr]::Zero) {
            return $window
        }
    }
    $candidates = [ArcheAxisWindow]::DescribeVisibleTopLevelWindows([uint32]$Shell.Id)
    throw "desktop shell main window was not ready; pid=$($Shell.Id) candidates=$candidates"
}

function Close-ArcheAxisShell {
    param(
        [System.Diagnostics.Process]$Shell,
        [IntPtr]$WindowHandle,
        [string]$Context
    )

    if (-not [ArcheAxisWindow]::PostClose($WindowHandle, [uint32]$Shell.Id)) {
        throw "desktop shell rejected WM_CLOSE; context=$Context pid=$($Shell.Id) handle=$WindowHandle"
    }
    if (-not $Shell.WaitForExit(30000)) {
        $candidates = [ArcheAxisWindow]::DescribeVisibleTopLevelWindows([uint32]$Shell.Id)
        throw "desktop shell did not exit after WM_CLOSE; context=$Context pid=$($Shell.Id) handle=$WindowHandle candidates=$candidates"
    }
}

function Stop-ArcheAxisInstallation {
    $uninstaller = Join-Path $installRoot 'uninstall.exe'
    if (Test-Path $uninstaller) {
        $process = Start-Process -FilePath $uninstaller -ArgumentList '/S' -WindowStyle Hidden -Wait -PassThru
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
if ($RequireReleaseIdentity -and $RequireCandidateIdentity) {
    throw 'release and candidate identity requirements are mutually exclusive'
}

try {
    $installerProcess = Start-Process -FilePath $Installer -ArgumentList '/S' -WindowStyle Hidden -Wait -PassThru
    if ($installerProcess.ExitCode -ne 0) {
        throw "NSIS installer exited with $($installerProcess.ExitCode)"
    }
    $ownsInstall = $true

    $executable = Join-Path $installRoot 'ArcheAxis.exe'
    $nestedPython = Join-Path $installRoot 'runtime\python\python.exe'
    $flatPython = Join-Path $installRoot 'runtime\python.exe'
    $python = if (Test-Path -LiteralPath $nestedPython -PathType Leaf) { $nestedPython } else { $flatPython }
    $coreExecutable = Join-Path $installRoot 'core\archeaxis-api.exe'
    $persistedDatabase = Join-Path $appData 'archeaxis.sqlite'
    $profile = Get-Content -LiteralPath (Join-Path $installRoot 'worker-profile.json') -Raw | ConvertFrom-Json
    if ($profile.schema -ne 'archeaxis.worker-profile/v1' -or
        [IO.Path]::GetFullPath((Join-Path $installRoot $profile.python)) -ne [IO.Path]::GetFullPath($python)) {
        throw 'installed worker profile disagrees with the desktop interpreter selection'
    }
    $doubleNestedPython = Join-Path $installRoot 'runtime\runtime\python\python.exe'
    if (-not (Test-Path $executable -PathType Leaf)) {
        throw 'installed desktop executable is missing'
    }
    if (-not (Test-Path $python -PathType Leaf)) {
        throw 'installed bundled Python is missing'
    }
    if (-not (Test-Path -LiteralPath $coreExecutable -PathType Leaf)) {
        throw 'installed canonical Core is missing'
    }
    if (Test-Path $doubleNestedPython) {
        throw 'installed Runtime contains an invalid double runtime directory'
    }

    $pycBefore = @(Get-ChildItem (Join-Path $installRoot 'runtime') -Filter '*.pyc' -File -Recurse).Count
    $activeShell = Start-Process -FilePath $executable -PassThru
    $normal = Wait-ArcheAxisBackend -Shell $activeShell
    $windowHandle = Wait-ArcheAxisWindow -Shell $activeShell
    Close-ArcheAxisShell -Shell $activeShell -WindowHandle $windowHandle -Context 'initial readback'
    Start-Sleep -Seconds 1
    if (Get-Process -Id $normal.Child.ProcessId -ErrorAction SilentlyContinue) {
        throw 'owned Core survived normal desktop shutdown'
    }
    if (-not (Test-Path -LiteralPath $persistedDatabase -PathType Leaf)) {
        throw 'installed host did not create its canonical user database'
    }
    if ($NativeToolsReceipt) {
        $nativeTools = Get-Content -LiteralPath $NativeToolsReceipt -Raw | ConvertFrom-Json
        if ($nativeTools.ok -ne $true) { throw 'native driver preparation did not succeed' }
        # Persist completed preflight facts before the independent WebDriver session.
        # A failed session must not erase which installed lifecycle assertions ran.
        $preflightDirectory = Join-Path ([IO.Path]::GetFullPath('.project-local/task-runtime/aaos01-webdriver')) ([Guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $preflightDirectory -Force | Out-Null
        $evidenceDirectory = $preflightDirectory
        [ordered]@{
            schema = 'archeaxis/installed-preflight/v1'
            complete_lifecycle_verified = $false
            head_sha = $env:GITHUB_SHA
            run_id = $env:GITHUB_RUN_ID
            run_attempt = $env:GITHUB_RUN_ATTEMPT
            installer_sha256 = (Get-FileHash -LiteralPath $Installer -Algorithm SHA256).Hash.ToLowerInvariant()
            host_sha256 = (Get-FileHash -LiteralPath $executable -Algorithm SHA256).Hash.ToLowerInvariant()
            core_sha256 = (Get-FileHash -LiteralPath $coreExecutable -Algorithm SHA256).Hash.ToLowerInvariant()
            profile_python = $profile.python
            installed_interpreter = $python
            normal_host_pid = $activeShell.Id
            normal_core_pid = $normal.Child.ProcessId
            initial_backend_ready = $true
            initial_visible_window = $true
            wm_close_completed = $true
            owned_core_absent_after_close = $true
            canonical_database_exists = $true
            next_operation = 'independent_webdriver_session'
        } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $preflightDirectory 'install-preflight.json') -Encoding utf8
        python -B scripts/probes/aaos01_tauri_webdriver_loop.py --host $executable --driver $nativeTools.driver --native-driver $nativeTools.native_driver --installer $Installer
        if ($LASTEXITCODE -ne 0) { throw 'actual installed Tauri WebDriver journey failed' }
        if ($GroupedOwnerLoop) {
            # A separate fresh owned data root exercises the current grouped UI.
            # The probe retains explicit missing AI/Owner qualification; no bridge writes.
            python -B scripts/probes/aaos01_tauri_webdriver_loop.py --host $executable --driver $nativeTools.driver --native-driver $nativeTools.native_driver --installer $Installer --grouped-common-owner-loop
            if ($LASTEXITCODE -ne 0) { throw 'actual installed grouped UI engineering journey failed' }
        }
    }
    $initialProof = Read-CoreCandidateProof -Mode seed
    $pycAfter = @(Get-ChildItem (Join-Path $installRoot 'runtime') -Filter '*.pyc' -File -Recurse).Count
    if ($pycAfter -ne $pycBefore) {
        throw "installed Runtime wrote bytecode: before=$pycBefore after=$pycAfter"
    }

    # The same package must be able to replace the installed program without
    # replacing user state.  A release run cannot manufacture a prior signed
    # version, so this is deliberately named an in-place upgrade rather than
    # claiming cross-version migration coverage.
    # CoreSpec::beside_runtime opens this canonical DB directly in app-local data.
    if (-not (Test-Path -LiteralPath $persistedDatabase -PathType Leaf)) {
        throw "first launch did not create the expected user database: $persistedDatabase"
    }
    $persistenceSentinel = Join-Path $appData 'release-lifecycle-sentinel.txt'
    Set-Content -LiteralPath $persistenceSentinel -Value 'retain-this-user-state' -Encoding utf8 -NoNewline

    $upgradeProcess = Start-Process -FilePath $Installer -ArgumentList '/S' -WindowStyle Hidden -Wait -PassThru
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
    $upgradeWindowHandle = Wait-ArcheAxisWindow -Shell $activeShell
    Close-ArcheAxisShell -Shell $activeShell -WindowHandle $upgradeWindowHandle -Context 'in-place upgrade readback'
    Start-Sleep -Seconds 1
    if (Get-Process -Id $upgraded.Child.ProcessId -ErrorAction SilentlyContinue) {
        throw 'owned Core survived upgraded desktop shutdown'
    }
    $upgradeProof = Read-CoreCandidateProof -Mode readback
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
        throw 'owned Core survived forced desktop termination'
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

    $reinstallProcess = Start-Process -FilePath $Installer -ArgumentList '/S' -WindowStyle Hidden -Wait -PassThru
    if ($reinstallProcess.ExitCode -ne 0) {
        throw "NSIS reinstall exited with $($reinstallProcess.ExitCode)"
    }
    $activeShell = Start-Process -FilePath $executable -PassThru
    $reinstalled = Wait-ArcheAxisBackend -Shell $activeShell
    if (-not (Test-Path -LiteralPath $persistenceSentinel -PathType Leaf)) {
        throw 'reinstalled Core lost retained user state'
    }
    $reinstallWindowHandle = Wait-ArcheAxisWindow -Shell $activeShell
    Close-ArcheAxisShell -Shell $activeShell -WindowHandle $reinstallWindowHandle -Context 'reinstall readback'
    Start-Sleep -Seconds 1
    if (Get-Process -Id $reinstalled.Child.ProcessId -ErrorAction SilentlyContinue) {
        throw 'owned Core survived reinstalled desktop shutdown'
    }
    $reinstallProof = Read-CoreCandidateProof -Mode readback
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

    # install-preflight.json above is a phase snapshot taken before the
    # independent WebDriver session and deliberately states
    # complete_lifecycle_verified = $false. The completion record below is
    # written only after every in-place upgrade, forced-kill, clean-uninstall,
    # uninstall-retains-data and reinstall-readback assertion above has passed,
    # so it is the durable evidence that the whole lifecycle ran in this job.
    if (-not $evidenceDirectory) {
        $evidenceDirectory = Join-Path ([IO.Path]::GetFullPath('.project-local/task-runtime/aaos01-installed-lifecycle')) ([Guid]::NewGuid().ToString('N'))
    }
    New-Item -ItemType Directory -Path $evidenceDirectory -Force | Out-Null
    [ordered]@{
        schema = 'archeaxis/installed-lifecycle-receipt/v1'
        complete_lifecycle_verified = $true
        head_sha = $env:GITHUB_SHA
        run_id = $env:GITHUB_RUN_ID
        run_attempt = $env:GITHUB_RUN_ATTEMPT
        installer_sha256 = (Get-FileHash -LiteralPath $Installer -Algorithm SHA256).Hash.ToLowerInvariant()
        product_version = $initialProof.product_version
        core_schema_version = $initialProof.schema_version
        persisted_job = $initialProof.job_id
        graceful_shutdown = $true
        in_place_upgrade = $true
        forced_tree_cleanup = $true
        clean_uninstall = $true
        uninstall_retains_data = $true
        reinstall_readback = $true
        pyc_growth = $pycAfter - $pycBefore
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $evidenceDirectory 'lifecycle-receipt.json') -Encoding utf8

    [pscustomobject]@{
        Version = $initialProof.product_version
        CoreRuntime = $initialProof.runtime
        CoreSchemaVersion = $initialProof.schema_version
        PersistedJob = $initialProof.job_id
        InstalledInterpreter = $initialProof.profile_python
        EngineImports = $initialProof.imports
        AuthenticatedUpgradeReadback = $upgradeProof.mode -eq 'readback'
        AuthenticatedReinstallReadback = $reinstallProof.mode -eq 'readback'
        PycGrowth = $pycAfter - $pycBefore
        GracefulShutdown = $true
        ForcedTreeCleanup = $true
        CleanUninstall = $true
        InPlaceUpgrade = $true
        UninstallRetainsData = $true
        ReinstallReadback = $true
    } | ConvertTo-Json -Depth 8 -Compress
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
