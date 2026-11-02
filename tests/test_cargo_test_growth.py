"""Synthetic growth review only: no Cargo network, compiler or test is launched."""
import copy
import hashlib
import json
from types import SimpleNamespace

import pytest

from scripts.runtime import cargo_test_growth as cargo


ONE_TEST = "running 1 test\ntest result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n"


@pytest.fixture
def growth(tmp_path, monkeypatch):
    portable = cargo.portable
    monkeypatch.setattr(cargo, "REPO", tmp_path)
    monkeypatch.setattr(portable, "REPO", tmp_path)
    run = tmp_path / ".project-local/runs/0123456789/cargo-growth"
    artifacts = run / "artifacts"
    target = tmp_path / ".project-local/build/cargo"
    cache = tmp_path / ".project-local/cache"
    artifacts.mkdir(parents=True)
    target.mkdir(parents=True)
    (cache / "cargo/registry").mkdir(parents=True)
    paths = {"root": tmp_path, "run": run, "artifacts": artifacts,
             "cargo_build": target, "cache": cache}
    monkeypatch.setattr(portable.dev, "layout", lambda *args: paths)
    monkeypatch.setattr(portable.dev, "git", lambda *args: str(tmp_path / ".git"))
    monkeypatch.setattr(cargo, "_command_processor", lambda: tmp_path / "cmd.exe")
    report = {"schema": "aaos.storage-footprint/v2", "repository": str(tmp_path),
              "measured_at": "2026-11-01T00:00:00+00:00", "readable_bytes": 30 * 1024 ** 3,
              "measurement_status": "PARTIAL", "measurement_errors": [{"error": "synthetic denial"}],
              "excluded_private": ["private-preserved"], "excluded_checkouts": [], "out_of_layout": [],
              "dev_root": [
                  {"name": "build/", "bytes": 10 * 1024 ** 3, "budget_gb": 22.0, "over_budget": False,
                   "errors": [], "excluded_private": [], "links": []},
                  {"name": "runs/", "bytes": 3 * 1024 ** 3, "budget_gb": 2.0, "over_budget": True},
                  {"name": "cache/", "bytes": 1024 ** 3, "budget_gb": None, "over_budget": False,
                   "errors": [], "excluded_private": [], "links": []},
              ]}
    baseline = tmp_path / ".project-local/runs/0123456789/checkpoint/artifacts/storage.json"
    baseline.parent.mkdir(parents=True)
    raw = json.dumps(report).encode()
    baseline.write_bytes(raw)
    pointer = tmp_path / "docs/current/AAOS-ACTIVE-EXECUTION.json"
    pointer.parent.mkdir(parents=True)
    descriptor = {"schema": portable.CHECKPOINT_SCHEMA, "path": baseline.relative_to(tmp_path).as_posix(),
                  "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                  "report_schema": report["schema"], "recorded_by": "synthetic test",
                  "measurement_scope": "partial synthetic coverage"}
    pointer.write_text(json.dumps({"execution_control": {"owner_priority_20261030": {
        "operator_storage_checkpoint": descriptor}}}), encoding="utf-8")
    measures = []
    def measure(root):
        measures.append(root)
        return copy.deepcopy(report)
    monkeypatch.setattr(portable.storage_report, "measure", measure)
    context = {"paths": paths, "purpose": "synthetic finite tests", "sharing": "existing cache",
               "retention_reason": "local evidence"}
    return SimpleNamespace(paths=paths, report=report, measures=measures, baseline=baseline,
                           pointer=pointer, context=context)


def test_cargo_test_projects_build_and_preserves_existing_checkpoint(growth, monkeypatch):
    calls = []
    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout=ONE_TEST)
    monkeypatch.setattr(cargo.subprocess, "run", run)
    before = (growth.pointer.read_bytes(), growth.baseline.read_bytes())
    results = cargo.run(["archeaxis-domain:provider_learning"], 128, "synthetic fixture forecast", growth.context)
    assert results == [{"case": "archeaxis-domain:provider_learning", "exit_code": 0,
                        "tests_passed": 1, "tests_failed": 0, "tests_ignored": 0}]
    assert len(calls) == 1
    command, options = calls[0]
    assert command[-7:] == ["test", "--offline", "--locked", "-p", "archeaxis-domain", "--test", "provider_learning"]
    assert options["env"]["CARGO_TARGET_DIR"] == str(growth.paths["cargo_build"])
    assert options["env"]["ARCHEAXIS_CARGO_HOME"] == str(growth.paths["cache"] / "cargo")
    receipt = json.loads((growth.paths["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["projected_storage_class"] == "build/"
    assert receipt["planned_payload_bytes"] == 128
    assert receipt["command_mode"] == "test" and receipt["qualification"] == "TEST_COMMAND_EXECUTION"
    assert set(receipt["alternative_projected_reviews"]) == {"runs/", "cache/"}
    assert "not a hard quota" in receipt["projection_scope"]
    assert receipt["measurement_status"] == "PARTIAL"
    assert len(growth.measures) == 2 and before == (growth.pointer.read_bytes(), growth.baseline.read_bytes())
    with pytest.raises(ValueError, match="evidence already exists"):
        cargo.run(["archeaxis-domain:provider_learning"], 128, "synthetic forecast", growth.context)
    assert len(calls) == 1


def test_check_mode_is_offline_and_never_claims_test_execution(growth, monkeypatch):
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(cargo.subprocess, "run", run)
    cargo.run(["archeaxis-domain:provider_learning"], 128, "synthetic check forecast", growth.context, mode="check")
    assert calls[0][-7:] == ["check", "--offline", "--locked", "-p", "archeaxis-domain", "--test", "provider_learning"]
    receipt = json.loads((growth.paths["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["command_mode"] == "check"
    assert receipt["qualification"] == "COMPILE_CHECK_ONLY_NO_TEST_EXECUTION"


@pytest.mark.parametrize("case,crate,test_name", [
    ("archeaxis-domain:openmaic_scene_persistence", "archeaxis-domain", "openmaic_scene_persistence"),
    ("archeaxis-api:openmaic_scene_runtime", "archeaxis-api", "openmaic_scene_runtime"),
    ("archeaxis-api:deeptutor_practice_import", "archeaxis-api", "deeptutor_practice_import"),
])
def test_provider_integration_targets_use_the_existing_offline_growth_gate(growth, monkeypatch, case, crate, test_name):
    calls = []
    monkeypatch.setattr(cargo.subprocess, "run", lambda command, **kwargs: (
        calls.append(command) or SimpleNamespace(returncode=0, stdout=ONE_TEST)))
    cargo.run([case], 128, "synthetic provider test forecast", growth.context)
    assert calls[0][-7:] == ["test", "--offline", "--locked", "-p", crate, "--test", test_name]


@pytest.mark.parametrize("extra", [["--", "--release"], ["--target", "foreign"],
                                  ["--case", "archeaxis-domain:unknown"]])
def test_cli_rejects_arbitrary_options_and_unlisted_tests(growth, monkeypatch, extra):
    monkeypatch.setattr(cargo, "_owned_run", lambda: pytest.fail("invalid CLI must not allocate a run"))
    monkeypatch.setattr(cargo.sys, "argv", ["cargo_test_growth", "--mode", "check", "--case",
        "archeaxis-domain:provider_learning", "--storage-generated-bytes", "128",
        "--estimate-basis", "fixture", "--storage-purpose", "test", "--storage-sharing", "reuse",
        "--storage-retention-reason", "evidence", *extra])
    with pytest.raises(SystemExit) as error:
        cargo.main()
    assert error.value.code == 2 and not growth.measures


def test_unlisted_mode_fails_before_measurement(growth):
    with pytest.raises(ValueError, match="mode must be fetch, check or test"):
        cargo.run(["archeaxis-domain:provider_learning"], 128, "fixture", growth.context, mode="run")
    assert not growth.measures


@pytest.mark.parametrize("estimate", [None, 0, -1, True])
def test_unknown_or_invalid_forecast_fails_before_measurement(growth, estimate, monkeypatch):
    monkeypatch.setattr(cargo.subprocess, "run", lambda *args, **kwargs: pytest.fail("unexpected child"))
    with pytest.raises(ValueError, match="positive byte estimate"):
        cargo.run(["archeaxis-domain:provider_learning"], estimate, "fixture", growth.context)
    assert not growth.measures and not list(growth.paths["artifacts"].iterdir())


@pytest.mark.parametrize("basis", ["", "  ", "UNKNOWN", "unknown output", "bad\nline"])
def test_missing_estimate_basis_fails_before_measurement(growth, basis):
    with pytest.raises(ValueError, match="evidence basis"):
        cargo.run(["archeaxis-domain:provider_learning"], 128, basis, growth.context)
    assert not growth.measures


@pytest.mark.parametrize("cases", [[], ["archeaxis-domain:arbitrary"],
                                   ["archeaxis-domain:provider_learning"] * 2])
def test_non_allowlisted_or_duplicate_cases_do_not_execute(growth, cases):
    with pytest.raises(ValueError, match="allowlist"):
        cargo.run(cases, 128, "fixture forecast", growth.context)
    assert not growth.measures


def test_foreign_cache_and_target_fail_before_measurement(growth):
    for key in ("cache", "cargo_build"):
        paths = {**growth.paths, key: growth.paths["root"] / "foreign"}
        with pytest.raises(ValueError, match="foreign Cargo"):
            cargo.run(["archeaxis-domain:provider_learning"], 128, "fixture", {**growth.context, "paths": paths})
    assert not growth.measures


def test_linked_common_owner_cannot_borrow_primary_checkpoint(growth, monkeypatch):
    monkeypatch.setattr(cargo.dev, "git", lambda *args: str(growth.paths["root"] / ".git/worktrees/other"))
    with pytest.raises(ValueError, match="primary checkout"):
        cargo.run(["archeaxis-domain:provider_learning"], 128, "fixture", growth.context)
    assert not growth.measures


@pytest.mark.parametrize("field", ["errors", "excluded_private", "links"])
def test_unmeasured_or_redirected_target_never_starts_cargo(growth, monkeypatch, field):
    monkeypatch.setattr(cargo.subprocess, "run", lambda *args, **kwargs: pytest.fail("unexpected child"))
    member = str(growth.paths["cargo_build"] / "debug/unknown")
    value = member if field == "excluded_private" else {"link" if field == "links" else "path": member}
    growth.report["dev_root"][0][field].append(value)
    with pytest.raises(ValueError, match="skipped, private or redirected"):
        cargo.run(["archeaxis-domain:provider_learning"], 128, "fixture", growth.context)
    receipt = json.loads((growth.paths["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["copy_outcome"] == "NOT_STARTED"
    assert len(growth.measures) == 2


@pytest.mark.parametrize("field", ["errors", "excluded_private", "links"])
def test_unmeasured_or_redirected_cargo_registry_never_starts_cargo(growth, monkeypatch, field):
    monkeypatch.setattr(cargo.subprocess, "run", lambda *args, **kwargs: pytest.fail("unexpected child"))
    member = str(growth.paths["cache"] / "cargo/registry/unknown")
    value = member if field == "excluded_private" else {"link" if field == "links" else "path": member}
    growth.report["dev_root"][2][field].append(value)
    with pytest.raises(ValueError, match="skipped, private or redirected"):
        cargo.run(["archeaxis-domain:provider_learning"], 128, "fixture", growth.context)
    receipt = json.loads((growth.paths["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["copy_outcome"] == "NOT_STARTED"
    assert len(growth.measures) == 2


@pytest.mark.parametrize("kind", ["build", "runs"])
def test_projected_class_violation_stops_child_and_seals(growth, monkeypatch, kind):
    monkeypatch.setattr(cargo.subprocess, "run", lambda *args, **kwargs: pytest.fail("child must not start"))
    if kind == "build":
        growth.report["dev_root"][0]["bytes"] = 22 * 1024 ** 3 - 64
    else:
        growth.report["dev_root"][1]["bytes"] += 2 * 1024 ** 3 - 64
    with pytest.raises(cargo.portable.GrowthReviewRequiredError):
        cargo.run(["archeaxis-domain:provider_learning"], 128, "fixture", growth.context)
    receipt = json.loads((growth.paths["artifacts"] / "portable-storage-receipt.json").read_bytes())
    review = (receipt["projected_review"] if kind == "build"
              else receipt["alternative_projected_reviews"]["runs/"])
    assert review["status"] == "REVIEW_REQUIRED"
    assert receipt["copy_outcome"] == "NOT_STARTED" and len(growth.measures) == 2


def test_child_failure_is_preserved_when_post_measurement_also_fails(growth, monkeypatch):
    original = cargo.portable.storage_report.measure
    def measure(root):
        if growth.measures:
            raise OSError("synthetic post failure")
        return original(root)
    monkeypatch.setattr(cargo.portable.storage_report, "measure", measure)
    monkeypatch.setattr(cargo.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=7))
    with pytest.raises(cargo.CargoTestFailure) as caught:
        cargo.run(["archeaxis-domain:provider_learning"], 128, "fixture", growth.context)
    assert caught.value.exit_code == 7
    assert any("post measurement" in note for note in caught.value.__notes__)
    receipt = json.loads((growth.paths["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["child_results"][0]["exit_code"] == 7
    assert receipt["post_error"]["message"] == "synthetic post failure"
    assert receipt["original_error"]["type"] == "CargoTestFailure"


@pytest.fixture
def fetch_growth(growth, monkeypatch):
    root = growth.paths["root"]
    (root / "Cargo.toml").write_text('[workspace]\nmembers = ["crates/demo"]\n', encoding="utf-8")
    member = root / "crates/demo"
    member.mkdir(parents=True)
    (member / "Cargo.toml").write_text(
        '[package]\nname = "demo"\nversion = "0.1.0"\n'
        '[dependencies]\nserde = "1"\n', encoding="utf-8")
    (root / "Cargo.lock").write_text(
        'version = 4\n[[package]]\nname = "serde"\nversion = "1.0.0"\n'
        f'source = "{cargo.CRATES_IO_SOURCE}"\nchecksum = "' + "a" * 64 + '"\n', encoding="utf-8")
    config = root / ".cargo/config.toml"
    config.parent.mkdir()
    config.write_text('[build]\ntarget-dir = ".project-local/build/cargo"\n', encoding="utf-8")
    index = growth.paths["cache"] / "cargo/registry/index" / cargo.CRATES_IO_CACHE
    index.mkdir(parents=True)
    (index / "config.json").write_text(json.dumps({"dl": "https://static.crates.io/crates",
                                                  "api": "https://crates.io"}), encoding="utf-8")
    (growth.paths["run"] / "tmp").mkdir()
    windows = root / "windows"
    (windows / "System32").mkdir(parents=True)
    executable = root / "toolchain/bin/cargo.exe"
    executable.parent.mkdir(parents=True)
    executable.touch()
    monkeypatch.setattr(cargo, "_fetch_executable", lambda: executable)
    monkeypatch.setenv("SystemRoot", str(windows))
    # The synthetic repo itself is nested beneath the real repo's test-run
    # directory; exclude that outer repo's real config from this fixture.
    monkeypatch.setattr(cargo, "_config_ancestors", lambda cwd:
                        tuple(path for path in (cwd, *cwd.parents) if path == root or path.is_relative_to(root)))
    return growth


def test_fetch_is_fixed_official_windows_only_and_has_no_inherited_secrets(fetch_growth, monkeypatch):
    calls = []
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "CARGO_REGISTRIES_CRATES_IO_TOKEN", "GIT_CONFIG_GLOBAL",
                "RUSTUP_HOME", "OPENAI_API_KEY"):
        monkeypatch.setenv(key, "synthetic-secret")
    monkeypatch.setattr(cargo, "_fetch_child", lambda command, **kwargs:
                        (calls.append((command, kwargs)) or {"exit_code": 0, "timed_out": False}))
    result = cargo.run([], 128, "synthetic fetch forecast", fetch_growth.context, mode="fetch")
    assert result == [{"case": "workspace", "exit_code": 0, "timed_out": False}]
    command, options = calls[0]
    assert command[1:] == ["fetch", "--locked", "--target", "x86_64-pc-windows-msvc",
                           "--manifest-path", str(fetch_growth.paths["root"] / "Cargo.toml")]
    assert options["cwd"] == fetch_growth.paths["run"]
    env = options["env"]
    assert env["CARGO_HOME"] == str(fetch_growth.paths["cache"] / "cargo")
    assert env["CARGO_REGISTRIES_CRATES_IO_PROTOCOL"] == "sparse"
    assert env["HOME"] == str(fetch_growth.paths["run"] / "tmp/cargo-fetch-home")
    assert "synthetic-secret" not in env.values()
    assert not set(env).intersection({"HTTP_PROXY", "HTTPS_PROXY", "CARGO_REGISTRIES_CRATES_IO_TOKEN",
                                      "GIT_CONFIG_GLOBAL", "RUSTUP_HOME", "OPENAI_API_KEY"})
    receipt = json.loads((fetch_growth.paths["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["command_mode"] == "fetch"
    assert receipt["qualification"] == "DEPENDENCY_FETCH_ONLY_NO_BUILD_OR_TEST"
    assert receipt["fetch_target"] == "x86_64-pc-windows-msvc"
    assert receipt["cargo_lock_sha256"] == hashlib.sha256(
        (fetch_growth.paths["root"] / "Cargo.lock").read_bytes()).hexdigest()
    assert len(fetch_growth.measures) == 2


@pytest.mark.parametrize("kind", ["credentials", "cargo_config", "ancestor_config", "repo_config",
                                  "registry_download", "lock_source", "manifest_git", "manifest_registry",
                                  "manifest_unlocked", "external_path"])
def test_fetch_rejects_credential_or_alternative_source_before_storage(fetch_growth, monkeypatch, kind):
    root = fetch_growth.paths["root"]
    home = fetch_growth.paths["cache"] / "cargo"
    manifest = root / "crates/demo/Cargo.toml"
    if kind == "credentials":
        (home / "credentials.toml").write_text("do not read", encoding="utf-8")
    elif kind == "cargo_config":
        (home / "config.toml").write_text("do not read", encoding="utf-8")
    elif kind == "ancestor_config":
        path = fetch_growth.paths["run"] / ".cargo/config.toml"
        path.parent.mkdir()
        path.write_text("do not read", encoding="utf-8")
    elif kind == "repo_config":
        (root / ".cargo/config.toml").write_text('[source.crates-io]\nreplace-with = "mirror"\n', encoding="utf-8")
    elif kind == "registry_download":
        path = home / "registry/index" / cargo.CRATES_IO_CACHE / "config.json"
        path.write_text(json.dumps({"dl": "https://example.invalid", "api": "https://crates.io"}), encoding="utf-8")
    elif kind == "lock_source":
        lock = root / "Cargo.lock"
        lock.write_text(lock.read_text(encoding="utf-8").replace(cargo.CRATES_IO_SOURCE, "git+https://example.invalid"),
                        encoding="utf-8")
    elif kind == "manifest_git":
        manifest.write_text('[dependencies]\nserde = { git = "https://example.invalid" }\n', encoding="utf-8")
    elif kind == "manifest_registry":
        manifest.write_text('[dependencies]\nserde = { version = "1", registry = "mirror" }\n', encoding="utf-8")
    elif kind == "manifest_unlocked":
        manifest.write_text('[dependencies]\nnot_locked = "1"\n', encoding="utf-8")
    else:
        manifest.write_text('[dependencies]\nlocal = { path = "../../../outside" }\n', encoding="utf-8")
    monkeypatch.setattr(cargo, "_fetch_child", lambda *a, **k: pytest.fail("unexpected network child"))
    with pytest.raises(ValueError):
        cargo.run([], 128, "synthetic fetch forecast", fetch_growth.context, mode="fetch")
    assert not fetch_growth.measures and not list(fetch_growth.paths["artifacts"].iterdir())


@pytest.mark.parametrize("extra", [["--case", "archeaxis-domain:provider_learning"],
                                  ["--target", "foreign"], ["--source", "https://example.invalid"],
                                  ["--", "--all-features"]])
def test_fetch_cli_rejects_cases_sources_and_arbitrary_arguments(fetch_growth, monkeypatch, extra):
    monkeypatch.setattr(cargo, "_owned_run", lambda: pytest.fail("invalid CLI must not allocate a run"))
    monkeypatch.setattr(cargo.sys, "argv", ["cargo_test_growth", "--mode", "fetch",
        "--storage-generated-bytes", "128", "--estimate-basis", "fixture", "--storage-purpose", "fetch",
        "--storage-sharing", "reuse", "--storage-retention-reason", "evidence", *extra])
    with pytest.raises(SystemExit) as error:
        cargo.main()
    assert error.value.code == 2 and not fetch_growth.measures


def test_fetch_preserves_child_failure_and_post_review(fetch_growth, monkeypatch):
    monkeypatch.setattr(cargo, "_fetch_child", lambda *args, **kwargs: {"exit_code": 101, "timed_out": False})
    with pytest.raises(cargo.CargoTestFailure) as caught:
        cargo.run([], 128, "synthetic fetch forecast", fetch_growth.context, mode="fetch")
    assert caught.value.exit_code == 101
    receipt = json.loads((fetch_growth.paths["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["copy_outcome"] == "CHILD_FAILED"
    assert receipt["child_results"] == [{"case": "workspace", "exit_code": 101, "timed_out": False}]
    assert len(fetch_growth.measures) == 2


def test_fetch_review_required_stops_before_home_creation_or_network(fetch_growth, monkeypatch):
    fetch_growth.report["dev_root"][0]["bytes"] = 22 * 1024 ** 3 - 64
    monkeypatch.setattr(cargo, "_fetch_child", lambda *a, **k: pytest.fail("unexpected network child"))
    with pytest.raises(cargo.portable.GrowthReviewRequiredError):
        cargo.run([], 128, "synthetic fetch forecast", fetch_growth.context, mode="fetch")
    receipt = json.loads((fetch_growth.paths["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["copy_outcome"] == "NOT_STARTED"
    assert not (fetch_growth.paths["run"] / "tmp/cargo-fetch-home").exists()
    assert len(fetch_growth.measures) == 2


def test_fetch_detects_lock_change_before_claiming_success(fetch_growth, monkeypatch):
    lock = fetch_growth.paths["root"] / "Cargo.lock"
    def change_lock(*args, **kwargs):
        lock.write_text(lock.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")
        return {"exit_code": 0, "timed_out": False}
    monkeypatch.setattr(cargo, "_fetch_child", change_lock)
    with pytest.raises(ValueError, match="Cargo.lock changed"):
        cargo.run([], 128, "synthetic fetch forecast", fetch_growth.context, mode="fetch")
    receipt = json.loads((fetch_growth.paths["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["copy_outcome"] == "INTEGRITY_FAILED" and len(fetch_growth.measures) == 2


@pytest.mark.parametrize("case", ["archeaxis-domain:provider_question", "archeaxis-application:openmaic_node",
                                  "archeaxis-api:openmaic_capabilities", "archeaxis-api:openmaic_configuration_plans"])
def test_new_integration_targets_use_fixed_tests_and_record_ignored_count(growth, monkeypatch, case):
    calls = []
    output = "test result: ok. 3 passed; 0 failed; 1 ignored; 0 measured; 0 filtered out; finished in 0.00s\n"
    monkeypatch.setattr(cargo.subprocess, "run", lambda command, **options:
                        (calls.append(command) or SimpleNamespace(returncode=0, stdout=output)))
    result = cargo.run([case], 128, "fixture", growth.context)
    package, test = case.split(":")
    assert calls[0][-7:] == ["test", "--offline", "--locked", "-p", package, "--test", test]
    assert result[0]["tests_passed"] == 3 and result[0]["tests_ignored"] == 1


@pytest.mark.parametrize("case", sorted(cargo.LIB_CASES))
def test_lib_cases_use_fixed_exact_test_and_require_one_execution(growth, monkeypatch, case):
    calls = []
    monkeypatch.setattr(cargo.subprocess, "run", lambda command, **options:
                        (calls.append(command) or SimpleNamespace(returncode=0, stdout=ONE_TEST)))
    result = cargo.run([case], 128, "fixture", growth.context, mode="test")
    package, full_test_name = cargo.LIB_CASES[case]
    assert calls[0][-9:] == ["test", "--offline", "--locked", "-p", package, "--lib",
                             full_test_name, "--", "--exact"]
    assert result[0]["tests_passed"] == 1 and result[0]["tests_ignored"] == 0


@pytest.mark.parametrize("case", sorted(cargo.LIB_CASES))
def test_lib_check_never_claims_unit_test_compilation_or_execution(growth, monkeypatch, case):
    calls = []
    monkeypatch.setattr(cargo.subprocess, "run", lambda command, **options:
                        (calls.append(command) or SimpleNamespace(returncode=0)))
    result = cargo.run([case], 128, "fixture", growth.context, mode="check")
    package, _ = cargo.LIB_CASES[case]
    assert calls[0][-6:] == ["check", "--offline", "--locked", "-p", package, "--lib"]
    assert result[0]["qualification"] == "LIBRARY_CHECK_ONLY_NO_UNIT_TEST_CODE"
    receipt = json.loads((growth.paths["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["qualification"] == "LIBRARY_CHECK_ONLY_NO_UNIT_TEST_CODE"


@pytest.mark.parametrize("case,output", [
    ("archeaxis-domain:provider_question", "test result: ok. 0 passed; 0 failed; 0 ignored;"),
    ("archeaxis-domain:provider_question", "test result: ok. 0 passed; 0 failed; 2 ignored;"),
    ("archeaxis-domain:provider_question", "cargo succeeded without a test summary"),
    ("archeaxis-application:lib-openmaic-withdrawal", "test result: ok. 2 passed; 0 failed; 0 ignored;"),
    ("archeaxis-application:lib-openmaic-withdrawal", "test result: ok. 1 passed; 0 failed; 1 ignored;"),
])
def test_zero_ignored_missing_or_wrong_exact_test_count_is_not_a_pass(growth, monkeypatch, case, output):
    monkeypatch.setattr(cargo.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0, stdout=output))
    with pytest.raises(cargo.CargoCoverageFailure):
        cargo.run([case], 128, "fixture", growth.context, mode="test")
    receipt = json.loads((growth.paths["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["copy_outcome"] == "TEST_RESULT_UNVERIFIED"
    assert receipt["child_results"][0]["exit_code"] == 0
    assert len(growth.measures) == 2


def test_fetch_timeout_records_actual_termination_and_still_measures_post(fetch_growth, monkeypatch):
    timed_out = {"exit_code": 1, "timed_out": True, "timeout_seconds": cargo.FETCH_TIMEOUT_SECONDS,
                 "termination_confirmed": True}
    monkeypatch.setattr(cargo, "_fetch_child", lambda *a, **k: timed_out)
    with pytest.raises(cargo.CargoFetchTimeout):
        cargo.run([], 128, "fixture", fetch_growth.context, mode="fetch")
    receipt = json.loads((fetch_growth.paths["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["copy_outcome"] == "TIMED_OUT"
    assert receipt["child_results"] == [{"case": "workspace", **timed_out}]
    assert len(fetch_growth.measures) == 2


def test_fetch_timeout_is_preserved_if_post_measurement_also_fails(fetch_growth, monkeypatch):
    original = cargo.portable.storage_report.measure
    def measure(root):
        if fetch_growth.measures:
            raise OSError("synthetic post failure")
        return original(root)
    monkeypatch.setattr(cargo.portable.storage_report, "measure", measure)
    monkeypatch.setattr(cargo, "_fetch_child", lambda *a, **k:
                        {"exit_code": None, "timed_out": True, "timeout_seconds": cargo.FETCH_TIMEOUT_SECONDS,
                         "termination_confirmed": False})
    with pytest.raises(cargo.CargoFetchTimeout) as caught:
        cargo.run([], 128, "fixture", fetch_growth.context, mode="fetch")
    assert any("post measurement" in note for note in caught.value.__notes__)
    receipt = json.loads((fetch_growth.paths["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["child_results"][0]["exit_code"] is None
    assert receipt["child_results"][0]["termination_confirmed"] is False
    assert receipt["post_error"]["message"] == "synthetic post failure"
    assert receipt["original_error"]["type"] == "CargoFetchTimeout"


def test_fetch_timeout_wrapper_code_is_not_reported_as_a_cargo_exit(growth, monkeypatch):
    monkeypatch.setattr(cargo, "_owned_run", lambda: growth.paths)
    monkeypatch.setattr(cargo, "run", lambda *a, **k: (_ for _ in ()).throw(cargo.CargoFetchTimeout("timeout")))
    monkeypatch.setattr(cargo.sys, "argv", ["cargo_test_growth", "--mode", "fetch",
        "--storage-generated-bytes", "128", "--estimate-basis", "fixture", "--storage-purpose", "fetch",
        "--storage-sharing", "reuse", "--storage-retention-reason", "evidence"])
    assert cargo.main() == 124


@pytest.mark.parametrize("termination_confirmed", [True, False])
def test_fetch_timeout_targets_only_child_handle_and_reports_whether_it_exited(monkeypatch, termination_confirmed):
    calls = []
    class Child:
        def __init__(self):
            self.stopped = False
        def wait(self, *, timeout):
            calls.append(("wait", timeout))
            if self.stopped and termination_confirmed:
                return 1
            raise cargo.subprocess.TimeoutExpired("cargo", timeout)
        def poll(self):
            return 1 if self.stopped and termination_confirmed else None
        def terminate(self):
            calls.append(("terminate",))
            self.stopped = True
        def kill(self):
            calls.append(("kill",))
            self.stopped = True
    child = Child()
    monkeypatch.setattr(cargo.subprocess, "Popen", lambda *a, **k: child)
    result = cargo._fetch_child(["synthetic-cargo"], cwd=cargo.REPO, env={})
    assert result["timed_out"] is True and result["timeout_seconds"] == 1800
    assert result["termination_confirmed"] is termination_confirmed
    assert result["exit_code"] == (1 if termination_confirmed else None)
    assert ("terminate",) in calls
    assert (("kill",) in calls) is (not termination_confirmed)
