from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCTOR = ROOT / "scripts" / "doctor_windows.ps1"


def _pwsh_available() -> bool:
    return shutil.which("pwsh") is not None


def _run_doctor(project_root: Path | None = None) -> subprocess.CompletedProcess:
    cmd = ["pwsh", "-NoProfile", "-File", str(DOCTOR)]
    if project_root is not None:
        cmd += ["-ProjectRoot", str(project_root)]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120)


def test_doctor_script_present() -> None:
    assert DOCTOR.exists()
    assert DOCTOR.read_text(encoding="utf-8").startswith("#requires -Version 7.0")


def test_doctor_output_is_structured_json() -> None:
    if not _pwsh_available():
        return
    result = _run_doctor()
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "axw.007a.v1"
    assert "toolchain" in payload
    assert "paths" in payload
    assert "ports" in payload
    assert "encoding" in payload
    assert "writable" in payload
    assert "healthy" in payload


def test_doctor_never_emits_absolute_private_path() -> None:
    """AXW-007A: output must not leak absolute project or home paths; only the
    sanitized leaf and facts are allowed.
    """
    if not _pwsh_available():
        return
    result = _run_doctor()
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    raw = result.stdout

    # project_root and writable paths must be leaf-only, never an absolute drive
    # path that could reveal the local checkout location.
    assert ":" not in payload["paths"]["project_root_sanitized"]
    for entry in payload["writable"]:
        assert ":" not in entry["path"], f"leaked absolute path: {entry['path']}"
    # No Windows drive letters should appear anywhere in the JSON output.
    assert "C:\\" not in raw and "D:\\" not in raw


def test_doctor_detects_python_presence() -> None:
    if not _pwsh_available():
        return
    result = _run_doctor()
    payload = json.loads(result.stdout)
    # On a dev machine python is expected; the contract is that the field exists
    # and is a boolean, regardless of the actual value.
    assert isinstance(payload["toolchain"]["python"]["present"], bool)
    assert isinstance(payload["healthy"], bool)


def test_doctor_sanitizes_writable_probe() -> None:
    """The doctor must not leave probe files behind in the project root."""
    if not _pwsh_available():
        return
    before = {p.name for p in ROOT.glob(".doctor_probe_*.tmp")}
    _run_doctor(project_root=ROOT)
    after = {p.name for p in ROOT.glob(".doctor_probe_*.tmp")}
    assert after <= before


def test_doctor_accepts_custom_project_root_without_touching_source() -> None:
    if not _pwsh_available():
        return
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        result = _run_doctor(project_root=Path(tmp))
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["schema_version"] == "axw.007a.v1"
