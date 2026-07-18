"""C-line schema validation tests — 10 fixtures + 2 project candidates."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATORS = ROOT / "shared-contracts" / "validators"


def test_validate_fixtures():
    """All 10 fixtures pass their schema checks."""
    r = subprocess.run(
        [sys.executable, str(VALIDATORS / "validate_fixtures.py")],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert r.returncode == 0, f"Fixtures failed:\n{r.stdout}\n{r.stderr}"
    assert "All fixtures passed" in r.stdout


def test_validate_project_candidates():
    """All project candidates pass schema check."""
    r = subprocess.run(
        [sys.executable, str(VALIDATORS / "validate_project_candidates.py")],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert r.returncode == 0, f"Candidates failed:\n{r.stdout}\n{r.stderr}"
    assert "All project candidates passed" in r.stdout
