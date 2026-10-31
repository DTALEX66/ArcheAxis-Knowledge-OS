param(
    [Parameter(Mandatory = $true)]
    [string]$Installer,
    [switch]$RequireReleaseIdentity,
    [switch]$RequireCandidateIdentity,
    [switch]$RequireLocalPinnedIdentity,
    [string]$LocalPinnedIdentityReceipt,
    [ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedLocalPinnedIdentitySha256,
    [ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedInstallerSha256,
    [string]$NativeToolsReceipt,
    [string]$EvidenceRoot,
    [ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedHostSha256,
    [ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedCoreSha256,
    [ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedRuntimeManifestSha256,
    [switch]$GroupedOwnerLoop,
    [switch]$GroupedRunAi,
    [switch]$GroupedAuthoredIntervention,
    [switch]$RequireActualAiLoop
)

$ErrorActionPreference = 'Stop'
if (($GroupedRunAi -or $GroupedAuthoredIntervention -or $RequireActualAiLoop) -and -not $GroupedOwnerLoop) {
    throw 'AI qualification switches require GroupedOwnerLoop'
}
if (($GroupedAuthoredIntervention -or $RequireActualAiLoop) -and -not $GroupedRunAi) {
    throw 'authored intervention or required AI qualification requires explicit GroupedRunAi'
}
if ($RequireActualAiLoop -and -not $GroupedAuthoredIntervention) {
    throw 'required AI qualification requires explicit GroupedAuthoredIntervention'
}
$installRoot = Join-Path $env:LOCALAPPDATA 'ArcheAxis Knowledge'
$appData = Join-Path $env:LOCALAPPDATA 'com.archeaxis.workspace'
$uninstallKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*'
$appDataExisted = Test-Path $appData
$ownsInstall = $false
$ownsAppData = $false
$dataOwnerId = [Guid]::NewGuid().ToString('N')
$dataOwnerMarker = Join-Path $appData '.aaos-lifecycle-owner'
$activeShell = $null
$evidenceDirectory = $null

function New-LifecycleEvidenceDirectory {
    param([string]$Root)
    if (-not [IO.Path]::IsPathFullyQualified($Root)) {
        throw 'lifecycle evidence root must be an absolute directory'
    }
    $directory = [IO.Path]::GetFullPath($Root)
    $ancestor = $directory
    while ($ancestor) {
        if (Test-Path -LiteralPath $ancestor) {
            $item = Get-Item -LiteralPath $ancestor -Force
            if (-not $item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
                throw 'lifecycle evidence root must not traverse a file or reparse point'
            }
        }
        $ancestor = [IO.Path]::GetDirectoryName($ancestor)
    }
    # Never overwrite prior evidence. The supplied root may be a mapped output
    # folder in a disposable Windows Sandbox; it does not imply host isolation.
    $owned = Join-Path $directory ([Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $owned -ErrorAction Stop | Out-Null
    return $owned
}

function Assert-LifecycleOwnedData {
    $expected = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'com.archeaxis.workspace'))
    $resolved = (Resolve-Path -LiteralPath $appData -ErrorAction Stop).ProviderPath
    if ($appDataExisted -or -not $ownsAppData -or
        -not [string]::Equals($resolved, $expected, [StringComparison]::OrdinalIgnoreCase) -or
        -not (Test-Path -LiteralPath $dataOwnerMarker -PathType Leaf) -or
        (Get-Content -LiteralPath $dataOwnerMarker -Raw) -ne $dataOwnerId) {
        throw 'refusing to remove data not created by this lifecycle run'
    }
    foreach ($item in @((Get-Item -LiteralPath $appData -Force)) + @(Get-ChildItem -LiteralPath $appData -Force -Recurse)) {
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw 'refusing lifecycle cleanup through a reparse point'
        }
    }
}

# Proposed insertion only. No installation occurs when defining these functions.
function Assert-LocalIdentityMode {
    param([switch]$Release, [switch]$Candidate, [switch]$Local,
          [string]$Receipt, [string]$ReceiptSha, [string]$InstallerSha)
    if ((@($Release, $Candidate, $Local) | Where-Object { $_ }).Count -gt 1) {
        throw 'release, CI candidate and local pinned identity requirements are mutually exclusive'
    }
    if (-not $Local -and ($Receipt -or $ReceiptSha -or $InstallerSha)) {
        throw 'local pinned identity inputs require RequireLocalPinnedIdentity'
    }
}
function Assert-LocalPinnedFile {
    param([string]$Path, [string]$Sha256, [Nullable[long]]$Bytes)
    if (-not [IO.Path]::IsPathFullyQualified($Path) -or $Sha256 -notmatch '^[a-fA-F0-9]{64}$') {
        throw 'local pinned file requires an absolute path and sha256'
    }
    $full = [IO.Path]::GetFullPath($Path)
    $ancestor = $full
    while ($ancestor) {
        $attributes = [IO.File]::GetAttributes($ancestor)
        if ($attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'local identity path traverses a reparse point' }
        $ancestor = [IO.Path]::GetDirectoryName($ancestor)
    }
    $file = Get-Item -LiteralPath $full -Force -ErrorAction Stop
    if ($file.PSIsContainer -or $file.LinkType -eq 'HardLink') { throw 'local identity requires an independent regular file' }
    if ($null -ne $Bytes -and $file.Length -ne $Bytes) { throw 'local pinned file byte count differs' }
    if ((Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash -ine $Sha256) { throw 'local pinned file sha256 differs' }
    return $full
}

function Read-LocalPinnedJson {
    param([string]$Path, [string]$Sha256, [Nullable[long]]$Bytes)
    function Assert-UniqueLocalJson {
        param([System.Text.Json.JsonElement]$Element)
        if ($Element.ValueKind -eq [System.Text.Json.JsonValueKind]::Object) {
            $names = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
            foreach ($property in $Element.EnumerateObject()) {
                if (-not $names.Add($property.Name)) { throw 'duplicate or case-aliased local identity JSON key' }
                Assert-UniqueLocalJson -Element $property.Value
            }
        } elseif ($Element.ValueKind -eq [System.Text.Json.JsonValueKind]::Array) {
            foreach ($child in $Element.EnumerateArray()) { Assert-UniqueLocalJson -Element $child }
        }
    }
    $full = Assert-LocalPinnedFile -Path $Path -Sha256 $Sha256 -Bytes $Bytes
    $raw = [IO.File]::ReadAllText($full)
    $document = [System.Text.Json.JsonDocument]::Parse($raw)
    try { Assert-UniqueLocalJson -Element $document.RootElement } finally { $document.Dispose() }
    return ($raw | ConvertFrom-Json -AsHashtable -Depth 100)
}

function Assert-LocalPinnedMemberName {
    param([string]$Name)
    if (-not $Name -or $Name.Contains('\') -or $Name.Contains(':') -or $Name.StartsWith('/') -or
        $Name -match '[\p{Cc}]') { throw 'unsafe local pinned member name' }
    foreach ($part in $Name.Split('/')) {
        if (-not $part -or $part -in @('.', '..') -or $part.EndsWith(' ') -or $part.EndsWith('.')) {
            throw 'noncanonical local pinned member name'
        }
    }
}

function Read-LocalPinnedPackaging {
    foreach ($value in @($ExpectedLocalPinnedIdentitySha256, $ExpectedInstallerSha256,
                         $ExpectedHostSha256, $ExpectedCoreSha256, $ExpectedRuntimeManifestSha256)) {
        if ($value -notmatch '^[a-fA-F0-9]{64}$') { throw 'all local identity/installer/Host/Core/manifest digests are mandatory' }
    }
    $receipt = Read-LocalPinnedJson -Path $LocalPinnedIdentityReceipt -Sha256 $ExpectedLocalPinnedIdentitySha256
    if ($receipt.schema -ne 'local-pinned-packaging/v1' -or $receipt.status -ne 'LOCAL_PACKAGING_PASS' -or
        $receipt.stage -ne 'COMPLETE' -or $receipt.exit_code -ne 0 -or
        $receipt.installed_qualification -ne 'NOT_RUN' -or $receipt.installer.sha256 -ine $ExpectedInstallerSha256) {
        throw 'local packaging receipt is incomplete or differs from the installer binding'
    }
    $identityPath = Join-Path ([IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($LocalPinnedIdentityReceipt))) 'local-pinned-identity.json'
    $identity = Read-LocalPinnedJson -Path $identityPath -Sha256 $receipt.identity.sha256 -Bytes $receipt.identity.bytes
    if ($identity.schema -ne 'local-pinned-packaging/v1' -or $identity.status -ne 'PINNED_INPUTS_VERIFIED' -or
        $identity.public -isnot [bool] -or $identity.public -ne $false -or $identity.release_status -ne 'unreleased' -or
        $identity.ci_qualification -ne 'NOT_CLAIMED' -or $identity.installed_qualification -ne 'NOT_RUN' -or
        $identity.data_restore -ne 'NOT_RUN' -or $identity.rollback -ne 'NOT_RUN' -or
        $identity.build_source.source_commit -notmatch '^[a-f0-9]{40}$' -or
        $identity.build_source.source_tree -notmatch '^[a-f0-9]{40}$' -or
        $identity.build_source.source_patch_sha256 -notmatch '^[a-f0-9]{64}$' -or
        $identity.payload.schema -ne 'archeaxis.tauri-portable-candidate/v1' -or $identity.payload.status -ne 'ASSEMBLED' -or
        $identity.payload.installed -ne $false -or $identity.payload.published -ne $false -or
        $identity.payload.source_patch_sha256 -ne $identity.build_source.source_patch_sha256) {
        throw 'invalid non-public local pinned identity/source'
    }
    foreach ($field in @('verification_ci_run_id', 'verification_ci_url', 'release_run_id', 'release_run_url')) {
        if ($identity.Contains($field) -or $identity.build_source.Contains($field) -or $identity.packaging_source.Contains($field)) {
            throw 'CI identity fields are forbidden in the local identity branch'
        }
    }
    if ($identity.inputs.snapshot.sha256 -notmatch '^[a-f0-9]{64}$' -or
        $identity.inputs.host_receipt.sha256 -notmatch '^[a-f0-9]{64}$' -or
        $identity.inputs.candidate_manifest -notmatch '^[a-f0-9]{64}$') { throw 'missing original qualification evidence pins' }
    $members = [Collections.Generic.Dictionary[string,object]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($entry in $identity.payload.files.GetEnumerator()) {
        $name, $row = $entry.Key, $entry.Value
        Assert-LocalPinnedMemberName -Name $name
        if ($row.Count -ne 2 -or -not $row.Contains('bytes') -or -not $row.Contains('sha256') -or
            ($row.bytes -isnot [int] -and $row.bytes -isnot [long]) -or $row.bytes -lt 0 -or
            $row.sha256 -notmatch '^[a-f0-9]{64}$' -or $name -match '(^|/)release-identity\.json$') {
            throw 'invalid payload row or artifact identity forbidden in a local candidate'
        }
        if (-not $members.TryAdd($name, $row)) { throw 'case-aliased payload target' }
    }
    foreach ($binding in @(@('ArcheAxis.exe', $ExpectedHostSha256), @('core/archeaxis-api.exe', $ExpectedCoreSha256),
                            @('backend-runtime-manifest.json', $ExpectedRuntimeManifestSha256))) {
        if (-not $members.ContainsKey($binding[0]) -or $members[$binding[0]].sha256 -ine $binding[1]) {
            throw 'local expected Host/Core/manifest differs from the pinned payload'
        }
    }
    if ($identity.payload.host_sha256 -ine $ExpectedHostSha256 -or $identity.payload.core_sha256 -ine $ExpectedCoreSha256 -or
        -not $members.ContainsKey('runtime/Lib/site-packages/app/release-manifest.json') -or
        -not $members.ContainsKey('portable.flag') -or $members['portable.flag'].bytes -ne 0 -or
        $members['portable.flag'].sha256 -ne 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855') {
        throw 'missing release-manifest or invalid portable-only exclusion'
    }
    $null = $members.Remove('portable.flag')
    return @{ receipt = $receipt; identity = $identity; identity_path = $identityPath; members = $members }
}

function Assert-LocalInstallerBinding {
    if ($RequireLocalPinnedIdentity) {
        $null = Assert-LocalPinnedFile -Path $Installer -Sha256 $ExpectedInstallerSha256 -Bytes $localPinned.receipt.installer.bytes
        $null = Assert-LocalPinnedFile -Path $LocalPinnedIdentityReceipt -Sha256 $ExpectedLocalPinnedIdentitySha256
        $null = Assert-LocalPinnedFile -Path $localPinned.identity_path -Sha256 $localPinned.receipt.identity.sha256 -Bytes $localPinned.receipt.identity.bytes
    }
}

function Read-InstalledLocalPinnedPayload {
    Assert-LocalInstallerBinding
    $root = [IO.Path]::GetFullPath($installRoot).TrimEnd('\')
    $seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($item in @((Get-Item -LiteralPath $root -Force)) + @(Get-ChildItem -LiteralPath $root -Force -Recurse -ErrorAction Stop)) {
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'installed tree contains a reparse point' }
        if ($item.PSIsContainer) { continue }
        if ($item.LinkType -eq 'HardLink') { throw 'installed tree contains a hardlinked file' }
        $name = [IO.Path]::GetRelativePath($root, $item.FullName).Replace('\', '/')
        Assert-LocalPinnedMemberName -Name $name
        if (-not $seen.Add($name)) { throw 'installed target alias' }
        if ($localPinned.members.ContainsKey($name)) {
            $row = $localPinned.members[$name]
            $null = Assert-LocalPinnedFile -Path $item.FullName -Sha256 $row.sha256 -Bytes $row.bytes
        } elseif ($name -cne 'uninstall.exe') {
            throw "unmanifested installed member: $name"
        }
    }
    foreach ($name in $localPinned.members.Keys) {
        if (-not $seen.Contains($name)) { throw "missing installed member: $name" }
    }
    if (-not $seen.Contains('uninstall.exe')) { throw 'missing NSIS-generated uninstaller' }
    return @{ manifest_sha256 = $localPinned.receipt.identity.sha256; member_count = $localPinned.members.Count;
              excluded = @('portable.flag'); generated = @('uninstall.exe') }
}

function Read-InstalledCandidateIdentity {
    $identity = [ordered]@{}
    foreach ($binding in @(
        @('host_sha256', 'ArcheAxis.exe', $ExpectedHostSha256),
        @('core_sha256', 'core\archeaxis-api.exe', $ExpectedCoreSha256),
        @('runtime_manifest_sha256', 'backend-runtime-manifest.json', $ExpectedRuntimeManifestSha256)
    )) {
        $actual = (Get-FileHash -LiteralPath (Join-Path $installRoot $binding[1]) -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($binding[2] -and $actual -ne $binding[2].ToLowerInvariant()) {
            throw "installed candidate identity mismatch: $($binding[0])"
        }
        $identity[$binding[0]] = $actual
    }
    if ($RequireLocalPinnedIdentity) {
        $payload = Read-InstalledLocalPinnedPayload
        $identity['local_pinned_identity_sha256'] = $payload.manifest_sha256
        $identity['local_pinned_member_count'] = $payload.member_count
    }
    return [pscustomobject]$identity
}

if ($EvidenceRoot) {
    $evidenceDirectory = New-LifecycleEvidenceDirectory -Root $EvidenceRoot
}

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

    # A cold first launch on a loaded CI runner (WebView2 start plus a large bundled
    # Python runtime) can exceed 40 s; the ceiling is raised so a slow start is not
    # reported as a broken install, while a backend that never listens still fails.
    for ($attempt = 0; $attempt -lt 320; $attempt++) {
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
    throw "installed desktop backend did not become ready; shell children: [$(@(Get-CimInstance Win32_Process -Filter "ParentProcessId=$($Shell.Id)" -ErrorAction SilentlyContinue | ForEach-Object { "$($_.Name)=$($_.ExecutablePath)" }) -join '; ')]; app data: [$(@(Get-ChildItem -LiteralPath $appData -ErrorAction SilentlyContinue | Select-Object -First 12 -ExpandProperty Name) -join ', ')]"
}

function New-ArcheAxisStartupPort {
    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
    try {
        $listener.Start()
        return ([Net.IPEndPoint]$listener.LocalEndpoint).Port
    } finally { $listener.Stop() }
}

function Start-ArcheAxisObservedShell {
    param([string]$Executable, [int]$Port, [string[]]$Arguments = @())
    if ($Port -lt 1024 -or $Port -gt 65535) { throw 'invalid owned startup port' }
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $Executable
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    # Child environment only; the existing Host opt-in binds CDP to loopback.
    $start.Environment['ARCHEAXIS_WEBDRIVER_CDP_PORT'] = [string]$Port
    foreach ($argument in $Arguments) { $start.ArgumentList.Add($argument) }
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $start
    if (-not $process.Start()) { throw 'installed desktop did not start' }
    return $process
}

function Wait-ArcheAxisFrontend {
    param([Diagnostics.Process]$Shell, [int]$Port, [string]$Executable, [string]$Receipt)
    $observerPython = if ($env:ARCHEAXIS_PYTHON) { $env:ARCHEAXIS_PYTHON } else { (Get-Command python -ErrorAction Stop).Source }
    $created = $Shell.StartTime.ToUniversalTime().ToFileTimeUtc().ToString()
    & $observerPython -B scripts/probes/installed_frontend_ready.py --host-pid $Shell.Id --host-created $created --host-path $Executable --port $Port --receipt $Receipt
    if ($LASTEXITCODE -ne 0) {
        $Shell.Refresh()
        throw "installed frontend readiness was not confirmed; pid=$($Shell.Id) responding=$($Shell.Responding) window=$($Shell.MainWindowHandle) receipt=$Receipt"
    }
}

function Invoke-LifecyclePythonProbe {
    param([string]$Executable, [string]$Code, [string[]]$Arguments,
          [ValidateSet('seed', 'readback')][string]$Mode)
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $Executable
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $start.StandardOutputEncoding = [Text.UTF8Encoding]::new($false)
    $start.StandardErrorEncoding = [Text.UTF8Encoding]::new($false)
    foreach ($argument in (@('-B', '-I', '-X', 'utf8', '-c', $Code) + $Arguments)) {
        $start.ArgumentList.Add($argument)
    }
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $start
    try {
        if (-not $process.Start()) { throw 'installed Python probe did not start' }
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        $process.WaitForExit()
        $stdout = $stdoutTask.GetAwaiter().GetResult()
        $stderr = $stderrTask.GetAwaiter().GetResult()
        $result = [ordered]@{ exit_code=$process.ExitCode; stdout=$stdout; stderr=$stderr }
        if ($evidenceDirectory) {
            $prefix = Join-Path $evidenceDirectory ("core-$Mode-" + [Guid]::NewGuid().ToString('N'))
            $result.stdout_path = "$prefix.stdout.txt"
            $result.stderr_path = "$prefix.stderr.txt"
            [IO.File]::WriteAllText($result.stdout_path, $stdout, [Text.UTF8Encoding]::new($false))
            [IO.File]::WriteAllText($result.stderr_path, $stderr, [Text.UTF8Encoding]::new($false))
            @{ mode=$Mode; exit_code=$result.exit_code; stdout_path=$result.stdout_path; stderr_path=$result.stderr_path } |
                ConvertTo-Json | Set-Content -LiteralPath "$prefix.exit.json" -Encoding utf8
        }
        return [pscustomobject]$result
    } finally {
        $process.Dispose()
    }
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
if requirement == "local-pinned":
    identity_path, expected_identity_sha = Path(sys.argv[5]), sys.argv[6]
    raw = identity_path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected_identity_sha, "local identity changed"
    identity = json.loads(raw)
    assert release.load_artifact_release_identity() is None, "local payload has an artifact CI/release identity"
    release_path = Path(release.__file__).with_name("release-manifest.json")
    relative = release_path.resolve().relative_to(root.resolve()).as_posix()
    row = identity["payload"]["files"][relative]
    original = release_path.read_bytes()
    assert len(original) == row["bytes"] and hashlib.sha256(original).hexdigest() == row["sha256"]
    frozen = json.loads(original)
    expected_summary = {"status": frozen["release"]["status"], "version": frozen["product"]["version"],
                        "channel": frozen["release"]["channel"], "public": frozen["release"]["public"],
                        "source_commit": frozen["source"]["commit"]}
    assert summary == expected_summary and summary["public"] is False, "local runtime summary changed"
    assert capabilities == frozen["capabilities"] and capabilities["public_installer"] != "available"
elif requirement == "candidate":
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
    $requirement = if ($RequireLocalPinnedIdentity) { 'local-pinned' } elseif ($RequireCandidateIdentity) { 'candidate' } elseif ($RequireReleaseIdentity) { 'release' } else { 'none' }
    $proofArguments = @($installRoot, $appData, $Mode, $requirement)
    if ($RequireLocalPinnedIdentity) { $proofArguments += @($localPinned.identity_path, $localPinned.receipt.identity.sha256) }
    $proof = Invoke-LifecyclePythonProbe -Executable $python -Code $probe -Arguments $proofArguments -Mode $Mode
    if ($proof.exit_code -ne 0) {
        throw "installed canonical Core $Mode probe failed; exit=$($proof.exit_code); stderr=$($proof.stderr_path)"
    }
    return ($proof.stdout | ConvertFrom-Json)
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
if ($appDataExisted) {
    throw 'refusing to use existing ArcheAxis workspace data; run in a fresh isolated Windows profile'
}
Assert-LocalIdentityMode -Release:$RequireReleaseIdentity -Candidate:$RequireCandidateIdentity -Local:$RequireLocalPinnedIdentity `
    -Receipt $LocalPinnedIdentityReceipt -ReceiptSha $ExpectedLocalPinnedIdentitySha256 -InstallerSha $ExpectedInstallerSha256
$localPinned = $null
if ($RequireLocalPinnedIdentity) {
    $localPinned = Read-LocalPinnedPackaging
    Assert-LocalInstallerBinding
} elseif ($LocalPinnedIdentityReceipt -or $ExpectedLocalPinnedIdentitySha256 -or $ExpectedInstallerSha256) {
    throw 'local pinned identity inputs require RequireLocalPinnedIdentity'
}

try {
    Assert-LocalInstallerBinding
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
    $initialIdentity = Read-InstalledCandidateIdentity

    $pycBefore = @(Get-ChildItem (Join-Path $installRoot 'runtime') -Filter '*.pyc' -File -Recurse).Count
    if (-not $evidenceDirectory) {
        $evidenceDirectory = New-LifecycleEvidenceDirectory -Root ([IO.Path]::GetFullPath('.project-local/task-runtime/aaos01-webdriver'))
    }
    $startupPort = New-ArcheAxisStartupPort
    $activeShell = Start-ArcheAxisObservedShell -Executable $executable -Port $startupPort
    $normal = Wait-ArcheAxisBackend -Shell $activeShell
    $windowHandle = Wait-ArcheAxisWindow -Shell $activeShell
    Wait-ArcheAxisFrontend -Shell $activeShell -Port $startupPort -Executable $executable -Receipt (Join-Path $evidenceDirectory 'frontend-startup/receipt.json')
    Close-ArcheAxisShell -Shell $activeShell -WindowHandle $windowHandle -Context 'initial readback'
    Start-Sleep -Seconds 1
    if (Get-Process -Id $normal.Child.ProcessId -ErrorAction SilentlyContinue) {
        throw 'owned Core survived normal desktop shutdown'
    }
    if (-not (Test-Path -LiteralPath $persistedDatabase -PathType Leaf)) {
        throw 'installed host did not create its canonical user database'
    }
    Set-Content -LiteralPath $dataOwnerMarker -Value $dataOwnerId -Encoding utf8 -NoNewline
    $ownsAppData = $true
    if ($NativeToolsReceipt) {
        $nativeTools = Get-Content -LiteralPath $NativeToolsReceipt -Raw | ConvertFrom-Json
        if ($nativeTools.ok -ne $true) { throw 'native driver preparation did not succeed' }
        # Persist completed preflight facts before the independent WebDriver session.
        # A failed session must not erase which installed lifecycle assertions ran.
        $preflightDirectory = if ($evidenceDirectory) { $evidenceDirectory } else { Join-Path ([IO.Path]::GetFullPath('.project-local/task-runtime/aaos01-webdriver')) ([Guid]::NewGuid().ToString('N')) }
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
        # Required independent installed conflict/dual-draft qualification.
        # Each invocation owns fresh portable data, separate from source/AI fixtures.
        python -B scripts/probes/aaos01_tauri_webdriver_loop.py --host $executable --driver $nativeTools.driver --native-driver $nativeTools.native_driver --installer $Installer --installed-draft-conflict-loop
        if ($LASTEXITCODE -ne 0) { throw 'actual installed document conflict recovery journey failed' }
        if ($GroupedOwnerLoop) {
            # A separate fresh owned data root exercises the current grouped UI.
            # The probe retains explicit missing AI/Owner qualification; no bridge writes.
            $groupedAiArguments = @()
            if ($GroupedRunAi) { $groupedAiArguments += '--actual-model' }
            if ($GroupedAuthoredIntervention) { $groupedAiArguments += '--grouped-authored-intervention' }
            if ($RequireActualAiLoop) { $groupedAiArguments += '--require-actual-ai-loop' }
            python -B scripts/probes/aaos01_tauri_webdriver_loop.py --host $executable --driver $nativeTools.driver --native-driver $nativeTools.native_driver --installer $Installer --grouped-common-owner-loop @groupedAiArguments
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

    Assert-LocalInstallerBinding
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
    $upgradeIdentity = Read-InstalledCandidateIdentity
    if (($upgradeIdentity | ConvertTo-Json -Compress) -ne ($initialIdentity | ConvertTo-Json -Compress)) {
        throw 'in-place upgrade changed the qualified candidate identity'
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

    Assert-LocalInstallerBinding
    $reinstallProcess = Start-Process -FilePath $Installer -ArgumentList '/S' -WindowStyle Hidden -Wait -PassThru
    if ($reinstallProcess.ExitCode -ne 0) {
        throw "NSIS reinstall exited with $($reinstallProcess.ExitCode)"
    }
    $reinstallIdentity = Read-InstalledCandidateIdentity
    if (($reinstallIdentity | ConvertTo-Json -Compress) -ne ($initialIdentity | ConvertTo-Json -Compress)) {
        throw 'reinstall changed the qualified candidate identity'
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
        same_installer_scope = if ($RequireLocalPinnedIdentity) { 'SAME_INSTALLER_SAME_VERSION_REINSTALL_DATA_PRESERVATION' } else { $null }
        cross_version_upgrade = if ($RequireLocalPinnedIdentity) { 'NOT_TESTED' } else { $null }
        rollback = if ($RequireLocalPinnedIdentity) { 'NOT_TESTED' } else { $null }
        qualification_scope = if ($RequireLocalPinnedIdentity) { 'LOCAL_PINNED_INSTALLED_LIFECYCLE' } else { 'EXISTING_CI_OR_RELEASE_LIFECYCLE' }
        local_packaging_receipt_sha256 = if ($RequireLocalPinnedIdentity) { $ExpectedLocalPinnedIdentitySha256 } else { $null }
        local_build_source = if ($RequireLocalPinnedIdentity) { $localPinned.identity.build_source } else { $null }
        local_packaging_source = if ($RequireLocalPinnedIdentity) { $localPinned.identity.packaging_source } else { $null }
        head_sha = if ($RequireLocalPinnedIdentity) { $null } else { $env:GITHUB_SHA }
        run_id = if ($RequireLocalPinnedIdentity) { $null } else { $env:GITHUB_RUN_ID }
        run_attempt = if ($RequireLocalPinnedIdentity) { $null } else { $env:GITHUB_RUN_ATTEMPT }
        installer_sha256 = (Get-FileHash -LiteralPath $Installer -Algorithm SHA256).Hash.ToLowerInvariant()
        host_sha256 = $initialIdentity.host_sha256
        core_sha256 = $initialIdentity.core_sha256
        runtime_manifest_sha256 = $initialIdentity.runtime_manifest_sha256
        product_version = $initialProof.product_version
        core_schema_version = $initialProof.schema_version
        persisted_job = $initialProof.job_id
        graceful_shutdown = $true
        in_place_upgrade = if ($RequireLocalPinnedIdentity) { 'SAME_VERSION_REINSTALL' } else { $true }
        forced_tree_cleanup = $true
        clean_uninstall = $true
        uninstall_retains_data = $true
        reinstall_readback = $true
        installed_document_conflict_loop = if ($NativeToolsReceipt) { 'PASS' } else { 'NOT_EXECUTED' }
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
        InPlaceUpgrade = if ($RequireLocalPinnedIdentity) { 'SAME_VERSION_REINSTALL' } else { $true }
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
    if ($ownsAppData -and (Test-Path -LiteralPath $appData)) {
        Assert-LifecycleOwnedData
        Remove-Item -LiteralPath $appData -Recurse -Force
    }
}
