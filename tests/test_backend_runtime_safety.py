"""Regression coverage for staged-runtime trust and child lifetime boundaries."""
import importlib.util
import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest


def module(name):
    path = Path(__file__).resolve().parents[1] / "scripts" / "release" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


launcher = module("backend_launcher")
stager = module("stage_backend_runtime")


def directory_link(link, target):
    if os.name == "nt":
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True, capture_output=True)
    else:
        link.symlink_to(target, target_is_directory=True)


def profile(root, **updates):
    (root / "python.exe").touch()
    (root / "worker.py").touch()
    data = dict(schema=launcher.PROFILE_SCHEMA, python="python.exe", script="worker.py", staging="data")
    data.update(updates)
    (root / launcher.PROFILE_NAME).write_text(json.dumps(data), encoding="utf-8")


@pytest.mark.parametrize("value", ["../bad", "E:/never-read", "E:never-read", "//server/share", ".ssh/key", ".env.local", "sessions/file", ".project-local/agents/file"])
def test_profile_rejects_protected_paths(tmp_path, value):
    profile(tmp_path, staging=value)
    with pytest.raises(launcher.LaunchFailure):
        launcher.load_profile(tmp_path)


@pytest.mark.parametrize("document", ['[]', '{"schema":"archeaxis.worker-profile/v1","python":"p","script":"s","staging":"d","extra":"x"}', '{"schema":"archeaxis.worker-profile/v1","python":"p","script":"s","staging":"d","staging":"other"}'])
def test_profile_strict_object(tmp_path, document):
    (tmp_path / launcher.PROFILE_NAME).write_text(document, encoding="utf-8")
    with pytest.raises(launcher.LaunchFailure):
        launcher.load_profile(tmp_path)


def test_python_environment_is_clean(monkeypatch, tmp_path):
    monkeypatch.setenv("PYTHONPATH", "host-injection")
    monkeypatch.setenv("PYTHONHOME", "host-runtime")
    environment = launcher.build_environment(tmp_path)
    assert "PYTHONPATH" not in environment
    assert "PYTHONHOME" not in environment
    assert environment["PYTHONNOUSERSITE"] == "1"


def test_valid_profile_and_invalid_explicit_do_not_fallback(tmp_path):
    profile(tmp_path)
    assert launcher.load_profile(tmp_path)["staging"] == tmp_path / "data"
    with pytest.raises(launcher.LaunchFailure):
        launcher.load_profile(tmp_path, "missing.json")


@pytest.mark.parametrize("field", ["python", "script", "staging"])
def test_profile_empty_and_nonstring_fields(tmp_path, field):
    for value in ["", "  ", None, 1]:
        profile(tmp_path, **{field: value})
        with pytest.raises(launcher.LaunchFailure):
            launcher.load_profile(tmp_path)


def test_profile_size_limit(tmp_path):
    (tmp_path / launcher.PROFILE_NAME).write_text(" " * 16385)
    with pytest.raises(launcher.LaunchFailure, match="limit"):
        launcher.load_profile(tmp_path)


def dummy_core(monkeypatch, tmp_path, code):
    profile(tmp_path)
    (tmp_path / "core").mkdir()
    (tmp_path / launcher.CORE_RELATIVE).touch()
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    original = subprocess.Popen
    children = []

    def spawn(_args, **kwargs):
        child = original([sys.executable, "-u", "-c", code], **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(launcher.subprocess, "Popen", spawn)
    return children


def test_silent_child_timeout_is_bounded_and_reaped(monkeypatch, tmp_path):
    children = dummy_core(monkeypatch, tmp_path, "import sys,time;sys.stdin.readline();time.sleep(2)")
    monkeypatch.setattr(launcher, "STARTUP_TIMEOUT_SECONDS", 0.15)
    begin = time.monotonic()
    with pytest.raises(launcher.LaunchFailure):
        launcher.start(tmp_path / "data", 1234)
    assert time.monotonic() - begin < 1.5
    assert children[0].poll() is not None


def test_readiness_drains_stderr_and_receipt_has_no_secrets(monkeypatch, tmp_path):
    children = dummy_core(monkeypatch, tmp_path, "import sys,time;sys.stdin.readline();sys.stderr.write('x'*1000000);sys.stderr.flush();print('archeaxis-api ready on http://127.0.0.1:1234');time.sleep(2)")
    monkeypatch.setattr(launcher, "STARTUP_TIMEOUT_SECONDS", 0.5)
    try:
        child, base, receipt, tokens = launcher.start(tmp_path / "data", 1234)
        assert base == "http://127.0.0.1:1234"
        assert "launch_token" not in json.dumps(receipt)
        assert "machine_token" not in json.dumps(receipt)
        assert launcher.credential(tokens, "human")["x-archeaxis-launch-token"] not in json.dumps(receipt)
    finally:
        for child in children:
            launcher.stop(child)


def test_machine_credential_uses_the_header_the_core_reads(monkeypatch, tmp_path):
    """The Core authenticates every request from `x-archeaxis-launch-token` alone.

    `launch.rs::authenticate` reads that one header and matches it against either
    the launch token or the machine token, then derives the actor from which one
    matched.  The launcher used to publish the machine token under
    `x-archeaxis-machine-token`, a header the Core never reads, so a machine call
    made with those credentials was authenticated as the human actor instead of
    being refused - a silent identity downgrade rather than a visible error.
    """
    children = dummy_core(monkeypatch, tmp_path, "import sys,time;sys.stdin.readline();print('archeaxis-api ready on http://127.0.0.1:1234');time.sleep(2)")
    child, base, _, tokens = launcher.start(tmp_path / "data", 1234)
    try:
        human = launcher.credential(tokens, "human")
        machine = launcher.credential(tokens, "machine")
        assert set(human) == {"x-archeaxis-launch-token"}
        assert set(machine) == {"x-archeaxis-launch-token"}
        assert human != machine
        assert "x-archeaxis-machine-token" not in json.dumps(tokens)
    finally:
        for child in children:
            launcher.stop(child)


def test_non_smoke_main_waits_and_reaps_child(monkeypatch, tmp_path, capsys):
    children = dummy_core(monkeypatch, tmp_path, "import sys,time;sys.stdin.readline();print('archeaxis-api ready on http://127.0.0.1:1234');time.sleep(0.2);sys.exit(7)")
    monkeypatch.setattr(sys, "argv", ["start-backend.py", "--data-root", str(tmp_path / "data"), "--port", "1234"])
    assert launcher.main() == 7
    assert children[0].poll() == 7
    receipt = capsys.readouterr().out
    assert "launch_token" not in receipt and "machine_token" not in receipt


def test_invalid_readiness_reaps_child_without_echoing_output(monkeypatch, tmp_path):
    children = dummy_core(monkeypatch, tmp_path, "import sys,time;secret=sys.stdin.readline();print('127.0.0.1:1234 '+secret);time.sleep(2)")
    with pytest.raises(launcher.LaunchFailure, match="invalid readiness endpoint") as error:
        launcher.start(tmp_path / "data", 1234)
    assert "launch_token" not in str(error.value)
    assert children[0].poll() is not None


def test_ephemeral_port_and_stream_cleanup(monkeypatch, tmp_path):
    children = dummy_core(monkeypatch, tmp_path, "import sys,time;sys.stdin.readline();print('archeaxis-api ready on http://127.0.0.1:1234');time.sleep(2)")
    child, base, _, _ = launcher.start(tmp_path / "data", 0)
    try:
        assert base == "http://127.0.0.1:1234"
    finally:
        launcher.stop(child)
    assert children[0].poll() is not None
    assert all(stream.closed for stream in [child.stdin, child.stdout, child.stderr])


def test_early_exit_is_reaped_and_diagnostics_are_not_echoed(monkeypatch, tmp_path):
    children = dummy_core(monkeypatch, tmp_path, "import sys;sys.stderr.write(sys.stdin.readline());sys.exit(8)")
    with pytest.raises(launcher.LaunchFailure, match="exit 8") as error:
        launcher.start(tmp_path / "data", 1234)
    assert "launch_token" not in str(error.value)
    assert children[0].poll() == 8


def test_copy_tree_rejects_nested_link_before_output(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "plain").write_text("plain")
    target = tmp_path / "output"
    external = tmp_path / "external"
    external.mkdir()
    directory_link(source / "linked", external)
    with pytest.raises(ValueError):
        stager.copy_tree(source, target)
    assert not target.exists()


def test_profile_rejects_symlink_ancestor(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    directory_link(link, real)
    profile(tmp_path, staging="link/missing/data")
    with pytest.raises(launcher.LaunchFailure):
        launcher.load_profile(tmp_path)


@pytest.mark.parametrize("path", ["E:/never-read", "E:never-read", "//server/share", ".ssh/key"])
def test_stager_rejects_protected_paths_without_access(path, monkeypatch):
    def no_access(*args, **kwargs):
        pytest.fail("protected path must be rejected before filesystem access")
    monkeypatch.setattr(Path, "lstat", no_access)
    monkeypatch.setattr(Path, "exists", no_access)
    with pytest.raises(ValueError):
        stager.reject_reparse(Path(path))


def test_stager_main_preflights_nested_and_output_links(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "python.exe").touch()
    workers = tmp_path / "workers"
    (workers / "transport").mkdir(parents=True)
    (workers / "transport" / "text_ndjson.py").touch()
    core = tmp_path / "core.exe"
    core.touch()
    donor = tmp_path / "donor.py"
    donor.touch()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    directory_link(runtime / "nested", elsewhere)
    output = tmp_path / "output"
    argv = ["stage_backend_runtime.py", "--core", str(core), "--runtime", str(runtime), "--workers", str(workers), "--shared", str(donor), "--out", str(output), "--version", "test", "--source-commit", "test", "--source-tree", "test", "--packager-commit", "test"]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(ValueError, match="linked"):
        stager.main()
    assert not output.exists()
    # A linked output ancestor must be rejected before donor validation or writes.
    directory_link(tmp_path / "redirect", elsewhere)
    argv[argv.index("--out") + 1] = str(tmp_path / "redirect" / "output")
    with pytest.raises(ValueError, match="linked"):
        stager.main()
    assert not (elsewhere / "output").exists()


def test_packager_identity_includes_launcher_dirty_state(tmp_path, monkeypatch):
    tooling = tmp_path / "stage_backend_runtime.py"
    tooling.write_text("# stager fixture\n")
    launch = tmp_path / "backend_launcher.py"
    launch.write_text("# launcher fixture\n")

    def git(*args):
        return subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True, text=True).stdout.strip()

    git("init")
    git("add", "stage_backend_runtime.py", "backend_launcher.py")
    git("-c", "user.name=Test Fixture", "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false", "commit", "-m", "fixture baseline")
    monkeypatch.setattr(stager, "__file__", str(tooling))
    commit = git("rev-parse", "HEAD")
    assert stager.packager_identity() == commit
    launch.write_text("# uncommitted launcher fix\n")
    assert stager.packager_identity() == commit + "+dirty"


def test_manifest_distinguishes_asserted_sources_and_measured_tooling(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "python.exe").write_bytes(b"synthetic interpreter fixture")
    workers = tmp_path / "workers"
    (workers / "transport").mkdir(parents=True)
    (workers / "transport" / "text_ndjson.py").write_text("# fixture")
    core = tmp_path / "core.exe"
    core.write_bytes(b"synthetic core fixture")
    donor = tmp_path / "donor.py"
    donor.write_text("# fixture")
    output = tmp_path / "output"
    monkeypatch.setattr(sys, "argv", ["stage_backend_runtime.py", "--core", str(core), "--runtime", str(runtime), "--workers", str(workers), "--shared", str(donor), "--out", str(output), "--version", "test", "--source-commit", "claimed-source", "--source-tree", "claimed-tree", "--runtime-commit", "claimed-runtime", "--packager-commit", "claimed-packager"])
    monkeypatch.setattr(stager, "packager_identity", lambda: "actual-tooling+dirty")
    monkeypatch.setattr(stager.os, "popen", lambda *_: io.StringIO("fixture-version"))
    assert stager.main() == 0
    manifest = json.loads((output / "backend-runtime-manifest.json").read_text())
    assert manifest["runtime_source"]["evidence"] == "ASSERTED_NOT_VERIFIED"
    assert manifest["built_from"]["evidence"] == "ASSERTED_NOT_VERIFIED"
    assert manifest["packager_source"]["commit"] == "actual-tooling+dirty"
    assert manifest["packager_source"]["asserted_commit"] == "claimed-packager"
    assert manifest["packager_source"]["inputs_sha256"]["backend_launcher.py"] == stager.sha256(output / "start-backend.py")
