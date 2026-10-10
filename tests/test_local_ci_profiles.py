"""Regressions for missing/empty diffs and fail-closed qualification."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_explicit_empty_diff_does_not_trigger_heavy_qualification():
    result = subprocess.run([sys.executable, "-B", "scripts/ci/classify.py", "--paths"],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0
    plan = json.loads(result.stdout)
    assert not plan["full_qualification"]
    assert plan["required_gates"] == ["ci-verdict"]
    assert "fallback_reason" not in plan


def test_real_identical_refs_are_a_known_empty_diff():
    result = subprocess.run([sys.executable, "-B", "scripts/ci/classify.py",
                             "--base", "HEAD", "--head", "HEAD"],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0
    assert not json.loads(result.stdout)["full_qualification"]


def test_full_plan_requires_all_heavy_jobs_including_installation():
    from scripts.ci.classify import classify_paths
    plan = classify_paths([], force_full=True)
    assert {"py-primary", "rust-vnext", "workers-vnext", "desktop-build",
            "installer-lifecycle", "wheel-smoke", "contracts-vnext"} <= set(plan["required_gates"])
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    aggregate = workflow.split("\n  a0-gates:", 1)[1]
    assert "needs.green-candidate-vnext.result" in aggregate
    assert 'require desktop-vnext "$GREEN_VNEXT_RESULT"' in aggregate
    assert '[ "$result" != "success" ]' in aggregate


def test_quota_policy_preserves_gate_but_reserves_lifecycle_for_candidate():
    import yaml
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    triggers = workflow.get("on", workflow.get(True))
    assert triggers["push"]["branches"] == ["main"]
    assert "workflow_dispatch" in triggers
    assert "workflow_dispatch" in workflow["jobs"]["installer-lifecycle"]["if"]
    for name, job in workflow["jobs"].items():
        if name not in {"gateplan", "lint", "a0-gates", "installer-lifecycle"}:
            assert "lint" in job["needs"], name
    assert "continue-on-error" not in (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
