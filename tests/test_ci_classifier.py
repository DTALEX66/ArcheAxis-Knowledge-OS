from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLASSIFIER = ROOT / "scripts" / "ci" / "classify.py"
PROFILE = ROOT / ".worklab" / "project-validation.v1.yaml"
REGISTRY = ROOT / ".worklab" / "gate-registry.v1.yaml"

PYTHON = sys.executable


def _classify(paths: list[str], force_full: bool = False) -> dict:
    cmd = [PYTHON, str(CLASSIFIER), "--base", "a" * 40, "--head", "b" * 40, "--paths", *paths]
    if force_full:
        cmd.append("--force-full")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, f"classifier failed: {result.stderr}"
    return json.loads(result.stdout)


def test_docs_only_classifies_static() -> None:
    plan = _classify(["docs/PROJECT_STATUS.md", "README.md"])
    assert plan["required_gates"] == ["ci-verdict", "static"]
    assert "full-qualification" not in plan["required_gates"]
    assert plan["unknown_paths"] == []


def test_ordinary_python_requires_py_primary() -> None:
    plan = _classify(["app/main.py", "shared/config.py"])
    assert {"py-primary", "lint", "static"} <= set(plan["required_gates"])
    assert "full-qualification" not in plan["required_gates"]


def test_tests_directory_classifies_as_ordinary_python() -> None:
    # tests/** must not be treated as unknown (which would force full).
    plan = _classify(["tests/test_truth_reset_contract.py", "tests/test_api.py"])
    assert {"py-primary", "lint", "static"} <= set(plan["required_gates"])
    assert plan["full_qualification"] is False
    assert plan["unknown_paths"] == []


def test_ui_requires_browser_smoke() -> None:
    plan = _classify(["app/workspace/ui/assets/app.js"])
    assert "browser-smoke" in plan["required_gates"]


def test_windows_runtime_requires_windows_smoke() -> None:
    plan = _classify(["windows/install.ps1", "windows/paths.ps1"])
    assert "windows-runtime" in plan["required_gates"]


def test_installer_requires_desktop_and_installer_gates() -> None:
    plan = _classify(["desktop/scripts/verify_nsis_install.ps1"])
    assert {"desktop-fast", "desktop-build", "installer-lifecycle"} <= set(
        plan["required_gates"]
    )


def test_wheel_packaging_requires_wheel_smoke() -> None:
    plan = _classify(["pyproject.toml"])
    assert "wheel-smoke" in plan["required_gates"]


def test_ci_policy_change_forces_full() -> None:
    plan = _classify([".github/workflows/ci.yml"])
    assert "full-qualification" not in plan["required_gates"]  # logical profile
    assert "ci-verdict" in plan["required_gates"]
    # full-qualification collapses required gates to just the verdict aggregator
    assert plan["required_gates"] == ["ci-verdict"]


def test_classifier_self_change_forces_full() -> None:
    plan = _classify(["scripts/ci/classify.py"])
    assert plan["required_gates"] == ["ci-verdict"]


def test_unknown_path_forces_full() -> None:
    plan = _classify(["some/unknown/file.bin"])
    assert plan["required_gates"] == ["ci-verdict"]
    assert plan["unknown_paths"] == ["some/unknown/file.bin"]


def test_mixed_change_takes_union() -> None:
    plan = _classify(["app/main.py", "app/workspace/ui/assets/app.js", "docs/README.md"])
    assert {"py-primary", "browser-smoke", "static"} <= set(plan["required_gates"])


def test_rename_delete_are_classified() -> None:
    # delete / rename appear as paths too; they must still classify
    plan = _classify(["docs/old.md", "app/main.py"])
    assert "py-primary" in plan["required_gates"]
    assert "static" in plan["required_gates"]


def test_missing_base_diff_forces_full() -> None:
    # no --paths and no --diff -> full fallback
    result = subprocess.run(
        [PYTHON, str(CLASSIFIER), "--base", "a" * 40, "--head", "b" * 40],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert result.returncode == 0
    plan = json.loads(result.stdout)
    assert plan["fallback_reason"] == "no_diff_available"
    assert plan["required_gates"] == ["ci-verdict"]


def test_force_full_overrides_light_classification() -> None:
    plan = _classify(["docs/PROJECT_STATUS.md"], force_full=True)
    assert plan["required_gates"] == ["ci-verdict"]
    assert plan["force_full"] is True


def test_digest_is_stable_for_same_input() -> None:
    a = _classify(["app/main.py", "docs/x.md"])
    b = _classify(["app/main.py", "docs/x.md"])
    assert a["digest"] == b["digest"]
    assert len(a["digest"]) == 64


def test_worklab_registry_and_profile_parse() -> None:
    import yaml

    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    profile = yaml.safe_load(PROFILE.read_text(encoding="utf-8"))

    gate_ids = {g["id"] for g in registry["gates"]}
    assert "ci-verdict" in gate_ids
    assert "full-qualification" in gate_ids

    for cls in profile["risk_classes"]:
        for gate in cls["gates"]:
            if gate == "full-qualification":
                continue
            assert gate in gate_ids, f"gate {gate} not in registry"


def test_worklab_excluded_from_wheel_and_tauri_bundle() -> None:
    import tomllib

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    wheel_include = project["tool"]["setuptools"]["packages"]["find"]["include"]
    # .worklab must never be packaged into the wheel.
    assert ".worklab*" not in wheel_include
    assert not any("worklab" in item.lower() for item in wheel_include)

    tauri_conf = (ROOT / "desktop/src-tauri/tauri.conf.json").read_text(encoding="utf-8")
    # No .worklab resource or bundle entry in the Tauri config.
    assert "worklab" not in tauri_conf.lower()


def test_pr_concurrency_cancels_stale_runs_but_not_main() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "concurrency:" in workflow
    assert "cancel-in-progress" in workflow
    # PR-only cancellation: main/full pushes are NOT auto-cancelled.
    assert "github.event_name == 'pull_request'" in workflow
    # Per-PR group key so only the same PR's older runs cancel.
    assert "github.event.pull_request.number" in workflow


def test_ci_emits_gateplan_artifact() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "gateplan:" in workflow
    assert "Generate deterministic GatePlan" in workflow
    assert "scripts.ci.classify" in workflow
    assert "gateplan.json" in workflow
    assert "required_gates=" in workflow
    assert "GITHUB_OUTPUT" in workflow
