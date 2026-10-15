"""Regressions for missing/empty diffs and fail-closed qualification."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('profile,preflight,route_failure', [
    ('quick', True, False), ('quick', True, True),
    ('quick', False, False), ('full', False, False),
])
def test_preflight_never_requires_owner_local_sources_but_local_profiles_do(
        tmp_path, monkeypatch, profile, preflight, route_failure):
    import io
    from types import SimpleNamespace
    from scripts.ci import local_verify as runner

    paths = {name: tmp_path / name for name in ('tmp', 'build', 'artifacts', 'logs', 'run')}
    for path in paths.values():
        path.mkdir()
    monkeypatch.setattr(runner.dev, 'layout', lambda *_: paths)
    monkeypatch.setattr(runner.dev, 'prepare', lambda *_: {})
    monkeypatch.setattr(runner, 'source_snapshot', lambda *_: {'head': 'synthetic'})
    monkeypatch.setattr(runner.subprocess, 'run', lambda *a, **k: SimpleNamespace(
        returncode=0, stdout='synthetic-version', stderr=''))

    class Child:
        def __init__(self, command, **kwargs):
            self.stdout = io.StringIO('')
            self.returncode = int('scripts/ci/check_h01_source_trace.py' in command or (
                route_failure and 'tests/maintenance/test_contract_route_inventory.py' in command))

        def wait(self):
            return self.returncode

        def poll(self):
            return self.returncode

    monkeypatch.setattr(runner.subprocess, 'Popen', Child)
    monkeypatch.setattr(sys, 'argv', ['local_verify.py', '--profile', profile] + (
        ['--preflight'] if preflight else []))
    result = runner.main()
    receipt = json.loads((paths['artifacts'] / 'local-ci.json').read_text(encoding='utf-8'))
    names = {check['name'] for check in receipt['checks']}
    assert result == (int(route_failure) if preflight else 1)
    assert ('h01-source-trace' in names) is not preflight
    assert {'route-inventory', 'contracts', 'vocabulary', 'ui-host-drift'} <= names
    if not preflight:
        assert next(check for check in receipt['checks'] if check['name'] == 'h01-source-trace')['status'] == 'FAIL'


def test_quick_profile_keeps_the_real_layout_gate_after_its_path_move():
    from scripts.ci.local_verify import QUICK_TEST_TARGETS
    assert "tests/workflow/test_workspace_layout_contract.py" in QUICK_TEST_TARGETS
    assert all((ROOT / target).is_file() for target in QUICK_TEST_TARGETS)


def test_direct_profile_cli_loads_timing_dependency_without_pythonpath(tmp_path):
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/ci/local_verify.py"), "--help"],
                            cwd=tmp_path, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "--preflight" in result.stdout


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
