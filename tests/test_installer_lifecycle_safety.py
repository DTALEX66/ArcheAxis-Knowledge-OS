"""Run actual PowerShell path/ownership guards without starting an installer."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PWSH = shutil.which("pwsh")
pytestmark = pytest.mark.skipif(not PWSH, reason="PowerShell 7 unavailable")
DRIVER = r"""
param([string]$Source, [string]$Mode, [string]$Root, [string]$Python)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$tokens = $null; $errors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile($Source, [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw 'PowerShell source has syntax errors' }
$names = @('New-LifecycleEvidenceDirectory', 'Assert-LifecycleOwnedData', 'Read-InstalledCandidateIdentity', 'Invoke-LifecyclePythonProbe')
foreach ($function in $ast.FindAll({ param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -in $names }, $true)) {
    . ([scriptblock]::Create($function.Extent.Text))
}
if ($Mode -eq 'evidence') {
    $first = New-LifecycleEvidenceDirectory -Root $Root
    $second = New-LifecycleEvidenceDirectory -Root $Root
    @{ first=$first; second=$second } | ConvertTo-Json -Compress
    exit 0
}
if ($Mode -like 'probe-*') {
    $evidenceDirectory = New-LifecycleEvidenceDirectory -Root $Root
    $code = 'import sys;print("{\"ok\":true}");print("synthetic stderr 中文",file=sys.stderr)'
    if ($Mode -eq 'probe-failure') { $code += ';sys.exit(17)' }
    Invoke-LifecyclePythonProbe -Executable $Python -Code $code -Arguments @() -Mode seed | ConvertTo-Json -Compress
    exit 0
}
if ($Mode -like 'identity*') {
    $installRoot = Join-Path $Root 'program'
    New-Item -ItemType Directory -Path (Join-Path $installRoot 'core') -Force | Out-Null
    foreach ($name in @('ArcheAxis.exe', 'core\archeaxis-api.exe', 'backend-runtime-manifest.json')) {
        Set-Content -LiteralPath (Join-Path $installRoot $name) -Value 'synthetic-bytes' -NoNewline
    }
    $ExpectedHostSha256 = (Get-FileHash -LiteralPath (Join-Path $installRoot 'ArcheAxis.exe')).Hash
    $ExpectedCoreSha256 = $ExpectedHostSha256
    $ExpectedRuntimeManifestSha256 = $ExpectedHostSha256
    if ($Mode -eq 'identity-mismatch') { $ExpectedCoreSha256 = '0' * 64 }
    Read-InstalledCandidateIdentity | ConvertTo-Json -Compress
    exit 0
}
$env:LOCALAPPDATA = $Root
$appData = Join-Path $Root 'com.archeaxis.workspace'
New-Item -ItemType Directory -Path $appData -Force | Out-Null
$dataOwnerMarker = Join-Path $appData '.aaos-lifecycle-owner'
$dataOwnerId = 'synthetic-run-identity'
$appDataExisted = $Mode -eq 'preexisting'
$ownsAppData = $true
Set-Content -LiteralPath $dataOwnerMarker -Value $dataOwnerId -NoNewline
if ($Mode -eq 'wrong-marker') { Set-Content -LiteralPath $dataOwnerMarker -Value 'different-run' -NoNewline }
if ($Mode -eq 'reparse') {
    $target = Join-Path $Root 'preserved-target'
    New-Item -ItemType Directory -Path $target | Out-Null
    New-Item -ItemType Junction -Path (Join-Path $appData 'escape') -Target $target | Out-Null
}
Assert-LifecycleOwnedData
Write-Output 'OWNERSHIP_VERIFIED_NO_DELETE'
"""


def run_guard(tmp_path, mode, root):
    driver = tmp_path / "guard.ps1"
    driver.write_text(DRIVER, encoding="utf-8")
    return subprocess.run(
        [PWSH, "-NoLogo", "-NoProfile", "-NonInteractive", "-File", str(driver),
         "-Source", str(ROOT / "desktop/scripts/verify_nsis_install.ps1"),
         "-Mode", mode, "-Root", str(root), "-Python", sys.executable],
        capture_output=True, text=True, encoding="utf-8", timeout=30, check=False,
    )


def test_evidence_uses_fresh_directories_and_preserves_prior_files(tmp_path):
    root = tmp_path / "evidence"
    root.mkdir()
    prior = root / "prior.json"
    prior.write_bytes(b"preserve")
    result = run_guard(tmp_path, "evidence", root)
    assert result.returncode == 0, result.stderr
    paths = json.loads(result.stdout)
    assert paths["first"] != paths["second"]
    assert all(Path(p).parent == root and Path(p).is_dir() for p in paths.values())
    assert prior.read_bytes() == b"preserve"


@pytest.mark.parametrize("mode, exit_code", [("probe-success", 0), ("probe-failure", 17)])
def test_native_probe_preserves_separate_utf8_streams_and_original_exit(tmp_path, mode, exit_code):
    result = run_guard(tmp_path, mode, tmp_path / "evidence")
    assert result.returncode == 0, result.stderr
    proof = json.loads(result.stdout)
    assert proof["exit_code"] == exit_code
    assert json.loads(proof["stdout"]) == {"ok": True}
    assert proof["stderr"].strip() == "synthetic stderr 中文"
    # Evidence names deliberately include GUIDs; nested dev-run pytest paths can
    # exceed Windows MAX_PATH without requiring a machine-wide policy change.
    stderr_path = Path("\\\\?\\" + proof["stderr_path"])
    stdout_path = Path("\\\\?\\" + proof["stdout_path"])
    assert stderr_path.read_bytes().decode("utf-8") == proof["stderr"]
    assert stdout_path.read_bytes().decode("utf-8") == proof["stdout"]


def test_evidence_rejects_relative_destination(tmp_path):
    result = run_guard(tmp_path, "evidence", "relative-output")
    assert result.returncode != 0
    assert "must be an absolute directory" in result.stderr


def test_exact_owned_data_guard_accepts_without_deleting(tmp_path):
    result = run_guard(tmp_path, "owned", tmp_path / "profile")
    assert result.returncode == 0, result.stderr
    assert "OWNERSHIP_VERIFIED_NO_DELETE" in result.stdout
    assert (tmp_path / "profile/com.archeaxis.workspace/.aaos-lifecycle-owner").is_file()


def test_installed_identity_records_actual_bytes_and_rejects_other_candidate(tmp_path):
    result = run_guard(tmp_path, "identity", tmp_path / "matching")
    assert result.returncode == 0, result.stderr
    identity = json.loads(result.stdout)
    assert set(identity) == {"host_sha256", "core_sha256", "runtime_manifest_sha256"}
    assert len(set(identity.values())) == 1
    refused = run_guard(tmp_path, "identity-mismatch", tmp_path / "mismatch")
    assert refused.returncode != 0
    assert "installed candidate identity mismatch: core_sha256" in refused.stderr


@pytest.mark.parametrize("mode", ["wrong-marker", "preexisting", "reparse"])
def test_data_guard_refuses_foreign_or_escaping_state(tmp_path, mode):
    result = run_guard(tmp_path, mode, tmp_path / "profile")
    assert result.returncode != 0
    assert "refusing" in result.stderr
    assert (tmp_path / "profile/com.archeaxis.workspace/.aaos-lifecycle-owner").is_file()
    if mode == "reparse":
        assert (tmp_path / "profile/preserved-target").is_dir()
