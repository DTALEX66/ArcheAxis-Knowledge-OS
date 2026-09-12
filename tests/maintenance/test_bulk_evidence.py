"""BULK-0907 P02: tests for scripts/maintenance/bulk_evidence.py."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/maintenance/bulk_evidence.py"
SELF_HASH = hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
SELF_REL = "scripts/maintenance/bulk_evidence.py"


def _execution(exit_code: int = 0) -> dict:
    return {
        "source_commit": "2948b155db069d608e7ebd8acb7956079d8cf69f",
        "source_tree": "f" * 64,
        "dirty": True,
        "started_at": "2026-09-07T00:00:00+00:00",
        "ended_at": "2026-09-07T00:00:01+00:00",
        "exit_code": exit_code,
        "executable": sys.executable,
        "python": sys.version,
    }


def _make_run(root: Path, exit_code: int = 0, output_name: str = "output.bin") -> Path:
    run = root / "run"
    (run / "artifacts").mkdir(parents=True)
    (run / "artifacts" / "execution.json").write_text(
        json.dumps(_execution(exit_code)), encoding="utf-8"
    )
    (run / output_name).write_bytes(b"out-data")
    return run


def _write_spec(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _run_tool(run_root: Path, spec: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPT), "--run-root", str(run_root), "--spec", str(spec)],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def test_valid_run_produces_pass_receipt_with_correct_hashes(tmp_path):
    run = _make_run(tmp_path)
    out_hash = hashlib.sha256((run / "output.bin").read_bytes()).hexdigest()
    spec = _write_spec(tmp_path / "spec.json", {
        "title": "demo pass",
        "argv": [sys.executable, "-B", "sample_tool.py"],
        "repo_inputs": {SELF_REL: SELF_HASH},
        "run_outputs": {"output.bin": out_hash},
        "engine_versions": {"python": "3.13"},
    })
    result = _run_tool(run, spec)
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads((run / "artifacts" / "bulk-receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "PASS"
    assert receipt["exit_code"] == 0
    assert receipt["argv"] == [sys.executable, "-B", "sample_tool.py"]
    assert receipt["repo_input_sha256"][SELF_REL] == SELF_HASH
    assert receipt["run_output_sha256"]["output.bin"] == out_hash
    assert receipt["source_sha"] == "2948b155db069d608e7ebd8acb7956079d8cf69f"


def test_tampered_input_hash_is_rejected_with_failed_receipt(tmp_path):
    run = _make_run(tmp_path)
    spec = _write_spec(tmp_path / "spec.json", {
        "argv": ["python", "-B", "sample_tool.py"],
        "repo_inputs": {SELF_REL: "f" * 64},
    })
    result = _run_tool(run, spec)
    assert result.returncode == 1, result.stdout + result.stderr
    receipt = json.loads((run / "artifacts" / "bulk-receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "FAILED"
    assert any("tampered" in reason for reason in receipt["reason"])


def test_nonzero_exit_is_preserved_and_never_becomes_pass(tmp_path):
    run = _make_run(tmp_path, exit_code=7)
    spec = _write_spec(tmp_path / "spec.json", {"argv": ["python", "-B", "sample_tool.py"]})
    result = _run_tool(run, spec)
    assert result.returncode == 1
    receipt = json.loads((run / "artifacts" / "bulk-receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "FAILED"
    assert receipt["exit_code"] == 7
    assert any("non-zero" in reason for reason in receipt["reason"])


def test_expected_exit_mismatch_is_explicit(tmp_path):
    run = _make_run(tmp_path, exit_code=0)
    spec = _write_spec(tmp_path / "spec.json", {
        "argv": ["python", "-B", "sample_tool.py"], "expected_exit_code": 3,
    })
    result = _run_tool(run, spec)
    assert result.returncode == 1
    receipt = json.loads((run / "artifacts" / "bulk-receipt.json").read_text(encoding="utf-8"))
    assert any("exit mismatch" in reason for reason in receipt["reason"])


def test_missing_output_is_an_explicit_error(tmp_path):
    run = _make_run(tmp_path)
    spec = _write_spec(tmp_path / "spec.json", {
        "argv": ["python", "-B", "sample_tool.py"],
        "run_outputs": {"does-not-exist.bin": "f" * 64},
    })
    result = _run_tool(run, spec)
    assert result.returncode == 1
    receipt = json.loads((run / "artifacts" / "bulk-receipt.json").read_text(encoding="utf-8"))
    assert any("missing" in reason and "does-not-exist.bin" in reason for reason in receipt["reason"])


def test_invalid_run_root_writes_nothing(tmp_path):
    missing_run = tmp_path / "no-such-run"
    spec = _write_spec(tmp_path / "spec.json", {"argv": ["python", "-B", "sample_tool.py"]})
    result = _run_tool(missing_run, spec)
    assert result.returncode == 2
    assert not list(tmp_path.rglob("bulk-receipt*.json"))


def test_run_without_execution_json_writes_nothing(tmp_path):
    run = tmp_path / "run"
    (run / "artifacts").mkdir(parents=True)
    spec = _write_spec(tmp_path / "spec.json", {"argv": ["python", "-B", "sample_tool.py"]})
    result = _run_tool(run, spec)
    assert result.returncode == 2
    assert not list(tmp_path.rglob("bulk-receipt*.json"))


def test_parent_escape_output_is_rejected_without_writes(tmp_path):
    run = _make_run(tmp_path)
    spec = _write_spec(tmp_path / "spec.json", {
        "argv": ["python", "-B", "sample_tool.py"],
        "run_outputs": {"../escape.bin": "f" * 64},
    })
    result = _run_tool(run, spec)
    assert result.returncode == 2, result.stdout + result.stderr
    assert not list((run / "artifacts").glob("bulk-receipt*.json"))


def test_protected_drive_and_unc_outputs_are_rejected(tmp_path):
    run = _make_run(tmp_path)
    for bad in ("E:/escape.bin", "\\\\server\\share\\escape.bin"):
        spec = _write_spec(tmp_path / f"spec-{hash(bad) % 1000}.json", {
            "argv": ["python", "-B", "sample_tool.py"],
            "run_outputs": {bad: "f" * 64},
        })
        result = _run_tool(run, spec)
        assert result.returncode == 2, (bad, result.stdout, result.stderr)
        assert not list((run / "artifacts").glob("bulk-receipt*.json"))


def test_argv_that_is_not_a_string_list_is_rejected_without_writes(tmp_path):
    run = _make_run(tmp_path)
    spec = _write_spec(tmp_path / "spec.json", {"argv": "python -B sample_tool.py"})
    result = _run_tool(run, spec)
    assert result.returncode == 2
    assert not list((run / "artifacts").glob("bulk-receipt*.json"))
