"""The host inventory must bind to what is declared, and certify only what it ran.

These four checks are the shape of the two defects the registry used to have:

* `shutil.which()` was consulted **first**, so an ambient binary silently substituted for the
  project's declared binding and the report called that the project's answer;
* the healthcheck string was reduced to its first token and `--version` was run against it, so
  `uv run python -c "import faster_whisper"` certified four engines and the CI venv as
  ``uv 0.12.23`` — a fabricated RESULT_VERIFIED — and a `.bat` file's `[ERROR:vcvarsall.bat]
  Invalid argument found` was recorded as a version.

The contract now: a declared path wins; PATH is a labelled fallback; a directory can never
satisfy a version probe; and an entry that declares no probe is certified at FILE_EXISTS at
most, because existence is a measurement and a version is not.
"""
from pathlib import Path

import pytest

from scripts.workflow.environment_registry import resolve


def _manifest(tmp_path: Path, body: str, name: str = "capabilities.yaml") -> Path:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


def test_registry_resolves_declared_capabilities_without_installing(tmp_path: Path, monkeypatch):
    manifest = _manifest(tmp_path, """
schema_version: '1.0'
capabilities:
  toolchains:
    - name: demo
      version_range: '>=1'
      required_by: [tests]
      local_only: true
      source_url: vendored
      healthcheck_command: 'demo --version'
""")
    monkeypatch.setattr("scripts.workflow.environment_registry.shutil.which", lambda name: None)
    report = resolve(manifest)
    assert report["schema"] == "archeaxis.environment-registry/v2"
    assert report["summary"] == {"total": 1, "available": 0, "missing": 1}
    assert report["capabilities"][0]["id"] == "toolchains/demo"
    # Nothing declared, nothing found, nothing guessed: an explicit non-claim.
    assert report["capabilities"][0]["verification_level"] == "NOT_RUN"
    assert report["capabilities"][0]["binding"] is None
    assert report["install_performed"] is False
    assert report["private_state_opened"] is False


def test_a_path_hit_is_reported_as_an_unbound_fallback_never_as_the_binding(tmp_path: Path, monkeypatch):
    """A PATH answer is visible and labelled; it is not the project's declared binding."""
    manifest = _manifest(tmp_path, """
capabilities:
  toolchains:
    - name: demo
      healthcheck_command: 'demo --version'
      probe:
        kind: command
        args: ['--version']
""")
    monkeypatch.setattr("scripts.workflow.environment_registry.shutil.which", lambda name: "C:/demo.exe")
    monkeypatch.setattr(
        "scripts.workflow.environment_registry.subprocess.run",
        lambda *args, **kwargs: type("R", (), {"returncode": 0, "stdout": "demo 1.2\n", "stderr": ""})(),
    )
    item = resolve(manifest)["capabilities"][0]
    assert item["available"] is True
    assert item["version_observed"] == "demo 1.2"
    assert item["binding"] == "unbound_path_fallback"
    assert item["verification_level"] == "VERSION_PROBED"
    assert resolve(manifest)["unbound_path_fallback"] == ["toolchains/demo"]


def test_a_declared_path_beats_an_ambient_path_hit(tmp_path: Path, monkeypatch):
    """The defect this pins: silent substitution by whichever binary sat on PATH first."""
    external = tmp_path / "external"
    declared_binary = external / "10-toolchains" / "demo" / "demo.exe"
    declared_binary.parent.mkdir(parents=True)
    declared_binary.write_bytes(b"demo")
    manifest = _manifest(tmp_path, """
capabilities:
  toolchains:
    - name: demo
      healthcheck_command: 'demo --version'
      external_paths: ['10-toolchains/demo/demo.exe']
      probe:
        kind: command
        args: ['--version']
""")
    calls = []

    def fake_run(command, **kwargs):
        calls.append(list(command))
        label = "ambient 9.9" if command[0] != str(declared_binary) else "declared 1.2"
        return type("R", (), {"returncode": 0, "stdout": label + "\n", "stderr": ""})()

    monkeypatch.setattr("scripts.workflow.environment_registry.shutil.which", lambda name: "C:/ambient/demo.exe")
    monkeypatch.setattr("scripts.workflow.environment_registry.subprocess.run", fake_run)
    monkeypatch.setenv("ARCHEAXIS_EXTERNAL_ROOT", str(external))
    item = resolve(manifest)["capabilities"][0]
    assert item["binding"] == "declared"
    assert item["version_observed"] == "declared 1.2"
    assert calls == [[str(declared_binary), "--version"]], "the ambient hit must never be executed"
    # and the ambient answer is still reported, so a reader can see the disagreement
    assert item["path_also_offers"] == "demo.exe"


def test_a_declared_directory_is_never_version_probed(tmp_path: Path, monkeypatch):
    """A model directory exists; that is not a version, and it was being certified anyway."""
    manifest = _manifest(tmp_path, """
capabilities:
  models:
    - name: demo-model
      external_paths: ['models/demo']
      healthcheck_command: 'demo-model --version'
      probe:
        kind: command
        args: ['--version']
""")
    external = tmp_path / "external"
    (external / "models" / "demo").mkdir(parents=True)
    monkeypatch.setattr("scripts.workflow.environment_registry.shutil.which", lambda name: None)
    monkeypatch.setenv("ARCHEAXIS_EXTERNAL_ROOT", str(external))
    def failed_external_probe(command, **kwargs):
        raise AssertionError(f"a directory must never be executed: {command}")

    monkeypatch.setattr("scripts.workflow.environment_registry.subprocess.run", failed_external_probe)
    item = resolve(manifest)["capabilities"][0]
    assert item["available"] is True
    assert item["resolved_path"] == "external:demo"
    # The declared location exists, and that is the whole claim: no version, no certification.
    assert item["verification_level"] == "FILE_EXISTS"
    assert item["version_observed"] is None
    assert "directory" in item["probe_evidence"]["reason"]


def test_registry_accepts_external_directory_assets(tmp_path: Path, monkeypatch):
    manifest = _manifest(tmp_path, """
capabilities:
  models:
    - name: demo-model
      purpose: 'demo model asset'
      version_range: latest
      platform: any
      license: MIT
      source_url: vendored
      install_method: 内置
      healthcheck_command: 'demo-model --version'
      external_paths: ['models/demo']
      required_by: [file-detection]
      local_only: true
""")
    external = tmp_path / "external"
    asset_dir = external / "models" / "demo"
    asset_dir.mkdir(parents=True)
    monkeypatch.setattr("scripts.workflow.environment_registry.shutil.which", lambda name: None)
    monkeypatch.setenv("ARCHEAXIS_EXTERNAL_ROOT", str(external))
    item = resolve(manifest)["capabilities"][0]
    assert item["available"] is True
    assert item["resolved_path"] == "external:demo"
    # No probe declared, so existence is the whole claim.
    assert item["verification_level"] == "FILE_EXISTS"
    assert item["version_observed"] is None


def test_a_version_can_only_be_inherited_from_the_probe_that_ran(tmp_path: Path, monkeypatch):
    """The engine rows used to inherit `uv`'s version. A wrapper answer certifies nothing.

    The falsification is the module's own: an interpreter-import probe that cannot resolve its
    declared interpreter returns `unavailable` with a reason — it must never fall through to
    whatever `--version` a neighbouring binary would have printed.
    """
    manifest = _manifest(tmp_path, """
capabilities:
  engines:
    - name: some-engine
      external_paths: ['Lib/site-packages/some_engine']
      healthcheck_command: 'python -c "import some_engine"'
      probe:
        kind: interpreter_import
        interpreter: some-venv
        module: some_engine
""")
    external = tmp_path / "external"
    (external / "Lib" / "site-packages" / "some_engine").mkdir(parents=True)
    monkeypatch.setenv("ARCHEAXIS_EXTERNAL_ROOT", str(external))
    monkeypatch.setattr("scripts.workflow.environment_registry.shutil.which", lambda name: None)
    item = resolve(manifest)["capabilities"][0]
    assert item["verification_level"] == "unavailable"
    assert "interpreter" in item["probe_evidence"]["reason"]
    assert item["version_observed"] is None


def test_a_healthcheck_that_is_not_runnable_is_not_recorded_as_missing(tmp_path: Path, monkeypatch):
    """`Test-Path ...` and `Get-ItemProperty ...` could never run from Python.

    Recording those as "missing" hid an installed WebView2 runtime and claimed a desktop runtime
    that had simply been moved. A registry/path probe that runs and answers "not present" is an
    `unavailable` with a stated reason, which is a different fact.
    """
    manifest = _manifest(tmp_path, """
capabilities:
  runtimes:
    - name: desktop-runtime-v1
      external_paths: []
      healthcheck_command: 'Test-Path runtimes/desktop-runtime-v1'
      probe:
        kind: path_exists
        paths: ['20-runtimes/desktop-runtime-v1']
""")
    external = tmp_path / "external"
    (external / "20-runtimes").mkdir(parents=True)
    monkeypatch.setenv("ARCHEAXIS_EXTERNAL_ROOT", str(external))
    item = resolve(manifest)["capabilities"][0]
    assert item["verification_level"] == "unavailable"
    assert "not present" in item["probe_evidence"]["reason"]
    assert item["binding"] is None


def test_the_real_manifest_reports_no_probe_failure_and_no_silent_substitution() -> None:
    """The shipped declaration, on a host with the root present, must be self-consistent.

    A row claiming RESULT_VERIFIED has to be re-run for real: this is what stops a green suite
    from sitting on top of a false certification, which is exactly how the `uv 0.12.23` rows
    survived while `rustc` died and tesseract aborted.
    """
    import os

    root_env = ("ARCHEAXIS_EXTERNAL_ROOT", "OS_EXTERNAL_CONFIG")
    if not any(os.environ.get(name, "").strip() for name in root_env):
        pytest.skip("no external root in the environment; nothing can be re-run here")
    report = resolve(Path(__file__).resolve().parents[2] / "config" / "environment"
                     / "capability-requirements.yaml")
    rows = report["capabilities"]
    assert len(rows) == report["summary"]["total"]
    assert [row["id"] for row in rows if row["verification_level"] == "probe_failed"] == []
    # Every row's measured level must sit at or below the ceiling its own probe declared.
    assert [row["id"] for row in rows if not row["ceiling_respected"]] == []
    # A PATH answer is only ever allowed for a row that declares no path of its own.
    for row in report["unbound_path_fallback"]:
        entry = next(item for item in rows if item["id"] == row)
        assert entry["declared_location"] is None, f"{row} substituted PATH for a declared binding"
    required = [row["id"] for row in rows
                if {"ci", "tests"} & set(row["required_by"])
                and row["verification_level"] not in ("FILE_EXISTS", "VERSION_PROBED", "RESULT_VERIFIED")]
    assert required == [], f"rows the CI/tests depend on are not certified: {required}"
