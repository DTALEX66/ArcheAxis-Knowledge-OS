"""R15/F14: the legacy binary presentation is read through a declared sidecar pair, not assumed.

`.ppt` was recorded for rounds as "no legal reader here", and the reason was true: the only candidate
is a Java program and this host had no JVM. Both halves are now declared and placed under the external
tool root, so the tests split the same way the `.doc` lane does - the resolution and refusal cases
always run, and the projection case runs only where the sidecar actually resolves, saying plainly
when it did not.

Two facts measured on this host shape the assertions below. Tika writes its own startup notice to
stderr while the document text goes to stdout, so a projection that swallowed stderr would be noise.
And a JVM that exists as a file is not a JVM that works: the identity question is asked before a
document is handed over, exactly as with antiword.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
OFFICE = REPO / "services/python-workers/document/worker_office.py"
TRANSPORT = REPO / "services/python-workers/transport/text_ndjson.py"
FIXTURE = REPO / "tests/fixtures/golden/golden-ppt-anchor.ppt"

TIKA_TEXT = "\nSample Powerpoint Slide\nCreated with Microsoft \nPowerpoint X for Mac\nService Release 1\n\n"
NOTICE = (
    "INFO  [main] 08:22:44 org.apache.tika.cli.TikaCLI As a convenience, TikaCLI has turned on "
    "several non-default features as specified in tika-config-default-single-file.json.\n"
)


def load_worker():
    spec = importlib.util.spec_from_file_location("office_ppt_test", OFFICE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeRun:
    """Records the exact argv and return-code surface of every sidecar call."""

    def __init__(self, *, java_version='openjdk version "21.0.12.1" 2026-08-18 LTS\n',
                 java_code=0, tika_version="Apache Tika 4.1.0", text=TIKA_TEXT, text_code=0,
                 stderr_after_text=NOTICE):
        self.calls: list[list[str]] = []
        self.java_version = java_version
        self.java_code = java_code
        self.tika_version = tika_version
        self.text = text
        self.text_code = text_code
        self.stderr_after_text = stderr_after_text

    def __call__(self, command, **kwargs):
        self.calls.append(list(command))
        if command[1:] == ["-version"]:
            return self._done(self.java_version, "", self.java_code)
        if "--version" in command:
            return self._done(self.tika_version, "", 0 if self.tika_version.startswith("Apache Tika") else 1)
        if "--text" in command:
            # the document text is stdout; the engine's own log is stderr
            return self._done(self.text, self.stderr_after_text, self.text_code)
        raise AssertionError(f"unexpected invocation: {command}")

    def _done(self, stdout, stderr, code):
        return subprocess.CompletedProcess(args=[], returncode=code, stdout=stdout, stderr=stderr)


@pytest.fixture
def sidecar(monkeypatch, tmp_path):
    """Install a fake sidecar with real files at the ends of each resolution lane."""
    worker = load_worker()
    jvm = tmp_path / "java.exe"
    jvm.write_bytes(b"")
    jar = tmp_path / "tika-app-4.1.0.jar"
    jar.write_bytes(b"")

    def install(run: FakeRun, *, java=None, jar_path=None, on_path=None, declared=None):
        monkeypatch.setattr(worker, "_run", run)
        monkeypatch.delenv("ARCHEAXIS_JAVA_CMD", raising=False)
        monkeypatch.delenv("ARCHEAXIS_TIKA_JAR", raising=False)
        if java is not None:
            monkeypatch.setenv("ARCHEAXIS_JAVA_CMD", str(java))
        if jar_path is not None:
            monkeypatch.setenv("ARCHEAXIS_TIKA_JAR", str(jar_path))
        monkeypatch.setattr(worker.shutil, "which", lambda name: on_path)
        monkeypatch.setattr(worker, "_declared_path",
                            lambda name: (declared or {}).get(name))
        return run

    install.jvm = jvm
    install.jar = jar
    install.worker = worker
    return install


def test_the_configured_jvm_is_the_one_used_and_the_declared_pair_is_resolved(sidecar, tmp_path):
    run = sidecar(FakeRun(), java=sidecar.jvm, jar_path=sidecar.jar)
    result = sidecar.worker._ppt_text(Path("sample.ppt"))

    assert [call[0] for call in run.calls[:2]] == [str(sidecar.jvm), str(sidecar.jvm)]
    assert "--version" in run.calls[1]
    assert "--text" in run.calls[2] and run.calls[2][-1] == "sample.ppt"
    assert result["loss_receipt"]["params"]["engine_version_reported"] == "4.1.0"
    assert "21.0.12.1" in result["loss_receipt"]["params"]["jvm"]


def test_the_declared_lane_is_used_when_nothing_is_configured(sidecar):
    declared = {"zulu-jre": str(sidecar.jvm), "apache-tika": str(sidecar.jar)}
    run = sidecar(FakeRun(), declared=declared)

    result = sidecar.worker._ppt_text(Path("sample.ppt"))

    assert run.calls[0][0] == str(sidecar.jvm), "the manifest, not PATH, decided which JVM ran"
    assert result["loss_receipt"]["params"]["jar"] == str(sidecar.jar)


def test_a_configured_jvm_that_does_not_exist_is_reported_as_itself(sidecar, tmp_path):
    missing = tmp_path / "gone" / "java.exe"
    sidecar(FakeRun(), java=missing, jar_path=sidecar.jar)

    with pytest.raises(RuntimeError) as caught:
        sidecar.worker._ppt_text(Path("sample.ppt"))

    assert "configured JVM does not exist" in str(caught.value)


def test_a_jvm_that_does_not_answer_as_a_jvm_is_not_trusted(sidecar):
    run = sidecar(FakeRun(java_version="some other tool\n", java_code=1),
                  java=sidecar.jvm, jar_path=sidecar.jar)

    with pytest.raises(RuntimeError) as caught:
        sidecar.worker._ppt_text(Path("sample.ppt"))

    assert "did not identify itself" in str(caught.value)
    assert len(run.calls) == 1, "no document was handed to something that is not a JVM"


def test_no_jvm_anywhere_is_a_named_refusal_that_projects_nothing(sidecar):
    run = sidecar(FakeRun())

    with pytest.raises(RuntimeError) as caught:
        sidecar.worker._ppt_text(Path("sample.ppt"))

    message = str(caught.value)
    assert "no JVM resolved" in message
    assert "ARCHEAXIS_JAVA_CMD" in message and "capability manifest" in message
    assert run.calls == []


def test_a_jar_that_is_not_tika_is_refused_before_any_document_is_read(sidecar):
    run = sidecar(FakeRun(tika_version="not the extractor"), java=sidecar.jvm, jar_path=sidecar.jar)

    with pytest.raises(RuntimeError) as caught:
        sidecar.worker._ppt_text(Path("sample.ppt"))

    assert "did not answer as Apache Tika" in str(caught.value)
    assert all("--text" not in call for call in run.calls)


def test_the_engine_log_is_not_part_of_the_projection(sidecar):
    run = sidecar(FakeRun(stderr_after_text=NOTICE), java=sidecar.jvm, jar_path=sidecar.jar)

    result = sidecar.worker._ppt_text(Path("sample.ppt"))

    assert "TikaCLI" not in result["text"], "the projection is stdout alone"
    assert "Sample Powerpoint Slide" in result["text"]
    assert result["structure"][1]["kind"] == "line"


def test_a_failing_read_reports_the_engine_line_and_not_the_log_noise(sidecar):
    sidecar(FakeRun(text="", text_code=1, stderr_after_text=NOTICE + "ERROR missing parser\n"),
            java=sidecar.jvm, jar_path=sidecar.jar)

    with pytest.raises(ValueError) as caught:
        sidecar.worker._ppt_text(Path("sample.ppt"))

    assert "missing parser" in str(caught.value)
    assert "TikaCLI" not in str(caught.value)


def test_an_empty_projection_is_not_reported_as_success(sidecar):
    sidecar(FakeRun(text="\n  \n"), java=sidecar.jvm, jar_path=sidecar.jar)

    with pytest.raises(ValueError) as caught:
        sidecar.worker._ppt_text(Path("sample.ppt"))

    assert "no readable text" in str(caught.value)


def test_ppt_reaches_the_office_route_by_its_own_name():
    """The five layers a media type has to pass, checked for the legacy presentation."""
    transport = importlib.util.spec_from_file_location("transport_ppt_test", TRANSPORT)
    assert transport and transport.loader
    module = importlib.util.module_from_spec(transport)
    transport.loader.exec_module(module)

    routes = module.ROUTES["office.structure"]
    assert "application/vnd.ms-powerpoint" in routes["media_types"]
    assert routes["suffix_by_media"]["application/vnd.ms-powerpoint"] == ".ppt"


def test_the_probe_states_the_sidecar_state_without_raising(monkeypatch):
    worker = load_worker()

    def missing_jvm():
        raise RuntimeError("ppt engine missing: no JVM resolved")

    monkeypatch.setattr(worker, "_resolve_jvm", missing_jvm)
    report = worker.probe()

    assert report["engines"]["ppt"] is False
    assert "no JVM resolved" in report["versions"]["ppt"]


def test_the_declared_sidecar_reads_the_real_powerpoint_document():
    """The claim itself: a genuine PowerPoint 97 file, the real engine, the real JVM.

    Skipped with the resolver's own reason where this host cannot resolve the pair, and the skip is
    a fact about the host rather than a pass.
    """
    worker = load_worker()
    try:
        jvm = worker._resolve_jvm()
        engine = worker._resolve_tika(jvm)
    except (RuntimeError, OSError) as exc:
        pytest.skip(f"the Tika sidecar pair is not resolvable here: {exc}")

    result = worker._ppt_text(FIXTURE)

    assert engine["version"] == "4.1.0", engine
    assert "Sample Powerpoint Slide" in result["text"]
    assert "Created with Microsoft" in result["text"]
    assert "TikaCLI" not in result["text"]
    assert result["loss_receipt"]["params"]["lines_projected"] >= 4
