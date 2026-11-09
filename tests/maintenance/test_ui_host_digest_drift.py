"""UI host generated contracts must follow the exact Core response schema."""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_host_contract_check_detects_core_response_schema_drift(tmp_path):
    inputs = (
        "scripts/contracts/generate_ui_host.py",
        "packages/contracts/v2/ui-host.schema.json",
        "packages/contracts/v1/core-document.schema.json",
        "packages/contracts/v1/core-command.schema.json",
    )
    for name in inputs:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    script = tmp_path / inputs[0]

    def run(*args):
        return subprocess.run([sys.executable, "-B", str(script), *args], cwd=tmp_path,
                              capture_output=True, text=True, check=False)

    assert run().returncode == 0
    assert run("--check").returncode == 0
    response = tmp_path / "packages/contracts/v1/core-document.schema.json"
    response.write_bytes(response.read_bytes() + b"\n")
    mismatch = run("--check")
    assert mismatch.returncode == 1
    paths = mismatch.stdout.replace("\\", "/")
    assert "crates/archeaxis-contracts/src/generated/ui_host.rs" in paths
    assert "frontend/src/api/generated/ui-host-contract.ts" in paths
    assert run().returncode == 0
    assert run("--check").returncode == 0
