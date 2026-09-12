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


def test_push_diff_refs_use_event_before_and_after() -> None:
    from scripts.ci.classify import resolve_diff_refs

    assert resolve_diff_refs(
        "push",
        push_before="1111111",
        push_after="2222222",
    ) == ("1111111", "2222222", True)


def test_pull_request_diff_refs_use_prospective_merge_inputs() -> None:
    from scripts.ci.classify import resolve_diff_refs

    assert resolve_diff_refs(
        "pull_request",
        pull_base="3333333",
        pull_head="4444444",
    ) == ("3333333", "4444444", True)


def test_missing_push_before_is_untrusted_and_fails_closed() -> None:
    from scripts.ci.classify import resolve_diff_refs

    assert resolve_diff_refs("push", push_after="2222222") == (
        "origin/main",
        "2222222",
        False,
    )


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


def test_root_level_markdown_classifies_as_docs() -> None:
    # AGENTS.md / README.md are root-level .md files that must match **/*.md
    # (docs-mechanical), not be treated as unknown.
    plan = _classify(["AGENTS.md", "README.md"])
    assert plan["full_qualification"] is False
    assert plan["unknown_paths"] == []
    assert {"static"} <= set(plan["required_gates"])


def test_tests_directory_classifies_as_ordinary_python() -> None:
    # tests/** must not be treated as unknown (which would force full).
    plan = _classify(["tests/test_truth_reset_contract.py", "tests/test_api.py"])
    assert {"py-primary", "lint", "static"} <= set(plan["required_gates"])
    assert plan["full_qualification"] is False
    assert plan["unknown_paths"] == []


def test_ui_requires_browser_smoke() -> None:
    for path in (
        "frontend/src/app/App.tsx",
        "frontend/src/components/RecoveryShell.tsx",
        "frontend/src/design-system/tokens.css",
    ):
        plan = _classify([path])
        assert "browser-smoke" in plan["required_gates"], path
        assert plan["unknown_paths"] == [], path
        assert "desktop-build" not in plan["required_gates"], path
        assert "installer-lifecycle" not in plan["required_gates"], path


def test_windows_runtime_requires_windows_smoke() -> None:
    plan = _classify(["windows/install.ps1", "windows/paths.ps1"])
    assert "windows-runtime" in plan["required_gates"]


def test_installer_requires_desktop_and_installer_gates() -> None:
    for path in (
        "desktop/scripts/verify_nsis_install.ps1",
        "frontend/vite.config.ts",
        "src-tauri/tauri.conf.json",
    ):
        plan = _classify([path])
        assert {"desktop-fast", "desktop-build", "installer-lifecycle"} <= set(
            plan["required_gates"]
        ), path


def test_tauri_rust_source_uses_fast_gate_without_rebuilding_installer() -> None:
    for path in ("src-tauri/src/main.rs", "src-tauri/src/recovery.rs"):
        plan = _classify([path])
        assert "desktop-fast" in plan["required_gates"], path
        assert "desktop-build" not in plan["required_gates"], path
        assert "installer-lifecycle" not in plan["required_gates"], path
        assert plan["unknown_paths"] == [], path


def test_wheel_packaging_requires_wheel_smoke() -> None:
    plan = _classify(["pyproject.toml"])
    assert "wheel-smoke" in plan["required_gates"]


def test_requirements_change_triggers_wheel_and_compat_not_full_scan() -> None:
    """AXW-003C: a requirements.txt change is a dependency change that must
    rebuild and smoke the wheel and the compat matrix. It must NOT degrade into
    a blanket full-qualification scan, and it must NOT be treated as unknown.
    """
    plan = _classify(["requirements.txt"])
    assert plan["full_qualification"] is False, plan
    assert "wheel-smoke" in plan["required_gates"]
    assert "py-compat" in plan["required_gates"]
    assert plan["unknown_paths"] == []


def test_parser_change_triggers_wheel_smoke() -> None:
    """AXW-003C: changing a format parser (pdf/multi-format) affects what the
    installed wheel can convert, so the wheel must be rebuilt and smoked.
    AXC-060: format adapters run lint + format-targeted + wheel-smoke
    (no py-primary full suite, no full-qualification).
    """
    for path in ("app/ingestion/pdf.py", "app/ingestion/multi_format.py"):
        plan = _classify([path])
        assert plan["full_qualification"] is False, (path, plan)
        assert {"format-targeted", "wheel-smoke"} <= set(plan["required_gates"]), (
            f"{path} missing format-targeted/wheel-smoke"
        )
        assert plan["unknown_paths"] == [], (path, plan["unknown_paths"])


def test_desktop_ci_policy_change_runs_desktop_gates_without_force_full() -> None:
    """The desktop workflow must test its own packaging path after it changes."""
    plan = _classify([".github/workflows/ci.yml"])
    assert plan["full_qualification"] is False
    assert "ci-verdict" in plan["required_gates"]
    assert {"static", "lint", "desktop-fast", "desktop-build", "installer-lifecycle"} <= set(
        plan["required_gates"]
    )
    assert "full-qualification" not in plan["required_gates"]  # logical profile


def test_classifier_self_change_does_not_force_full() -> None:
    """AXC-060: classifier self-change runs its own gates, not full."""
    plan = _classify(["scripts/ci/classify.py"])
    assert plan["full_qualification"] is False
    assert {"static", "lint"} <= set(plan["required_gates"])


def test_unknown_path_is_unclassified_block() -> None:
    """AXC-060: unknown paths run static+lint+primary and are marked
    unclassified (merge blocked until the profile gains a class); they no
    longer force full-qualification or NSIS/full matrix."""
    plan = _classify(["some/unknown/file.bin"])
    assert plan["full_qualification"] is False
    assert plan["unknown_paths"] == ["some/unknown/file.bin"]
    assert {"static", "lint", "py-primary"} <= set(plan["required_gates"])
    assert "desktop-build" not in plan["required_gates"]
    assert "installer-lifecycle" not in plan["required_gates"]


def test_mixed_change_takes_union() -> None:
    plan = _classify(["app/main.py", "frontend/src/app/App.tsx", "docs/README.md"])
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


def test_every_tracked_path_is_classified() -> None:
    """Full-coverage guard (T14): no tracked path may fall into
    unclassified-block; a new directory therefore fails until the profile
    gains a class, and an over-broad class cannot silently shadow specifics
    because first-match order is asserted by the existing gate tests."""
    from scripts.ci.classify import classify_paths

    out = subprocess.run(
        ["git", "-c", "core.quotePath=false", "ls-files", "-z"],
        capture_output=True,
        cwd=ROOT,
    )
    assert out.returncode == 0, "git ls-files failed"
    tracked = [
        p for p in out.stdout.decode("utf-8", errors="surrogateescape").split("\0") if p
    ]
    assert tracked, "expected tracked files in a git checkout"
    plan = classify_paths(tracked)
    unknown = plan["unknown_paths"]
    assert not unknown, f"tracked paths without a risk class: {unknown[:20]}"

    # The union of class paths must stay deterministic and complete: every
    # matched class must be one of the profile's registered classes.
    profile_classes = {
        cls["id"]
        for cls in classify_paths.__globals__["_load_yaml"](PROFILE)["risk_classes"]
    }
    assert set(plan["matched_classes"]) <= profile_classes


def test_vnext_lane_paths_trigger_their_own_gates() -> None:
    """T01 regression: C#/worker/contract changes each trigger their gate."""
    from scripts.ci.classify import classify_paths

    cases = {
        "apps/ArcheAxis.Desktop/MainWindow.axaml.cs": "desktop-vnext",
        "crates/archeaxis-domain/src/knowledge.rs": "rust-vnext",
        "packages/contracts/v1/quality-report.schema.json": "contracts-vnext",
        "services/python-workers/media/worker_transcribe.py": "workers-vnext",
        "config/model-profiles/local-2026-09-05.yaml": "workers-vnext",
    }
    for path, gate in cases.items():
        plan = classify_paths([path])
        assert gate in plan["required_gates"], f"{path} must require {gate}"

    plan = classify_paths(["apps/ArcheAxis.Desktop/MainWindow.axaml.cs"])
    assert "rust-vnext" not in plan["required_gates"], "C#-only change must not run rust-vnext"
    assert "desktop-vnext" in plan["required_gates"]


def test_vnext_policy_and_worker_regressions_cannot_be_shadowed() -> None:
    from scripts.ci.classify import classify_paths

    for path in (".github/workflows/vnext-ci.yml", "scripts/ci/check_vnext_scope.py",
                 "scripts/ci/check_vnext_workers.py"):
        gates = classify_paths([path])["required_gates"]
        assert {"rust-vnext", "desktop-vnext", "contracts-vnext", "workers-vnext"} <= set(gates)
    assert "workers-vnext" in classify_paths(["tests/workers/test_quality_regressions.py"])["required_gates"]


def test_shared_vocabulary_changes_verify_all_three_consumers_without_full_qualification():
    from scripts.ci.classify import classify_paths

    for path in ("scripts/contracts/generate_vocabulary.py",
                 "crates/archeaxis-contracts/src/generated/vocabulary.rs",
                 "apps/ArcheAxis.Desktop/Contracts/Generated/Vocabulary.g.cs",
                 "services/python-workers/contracts/generated/vocabulary.py",
                 "tests/contract/fixtures/vocabulary-cases.json"):
        gates = set(classify_paths([path])["required_gates"])
        assert {"rust-vnext", "desktop-vnext", "contracts-vnext"} <= gates
        assert "full-qualification" not in gates
    assert "desktop-vnext" in classify_paths(["tests/contract/Vocabulary.Tests/Program.cs"])["required_gates"]


def test_text_transport_changes_run_the_real_rust_consumer_without_desktop_build():
    from scripts.ci.classify import classify_paths

    for path in ("services/python-workers/transport/text_ndjson.py",
                 "services/python-workers/document/worker_text.py",
                 "tests/workers/test_text_ndjson.py"):
        gates = set(classify_paths([path])["required_gates"])
        assert {"rust-vnext", "workers-vnext"} <= gates
        assert "desktop-vnext" not in gates
