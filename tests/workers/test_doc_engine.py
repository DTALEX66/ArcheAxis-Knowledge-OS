"""R15/F14: a Word 97 binary document is read through a probed sidecar, not an assumed one.

The engine here is an external binary (`antiword`) that may or may not exist on a given host, and
the traps below are the ones that were measured rather than imagined: a stale shim that resolves
as a file but is not the engine; a batch invocation whose exit code cannot be trusted; an engine
that echoes the full input path back into its own error; and an output mode that silently flattens
typographic quotes when a character mapping is requested by path (antiword truncates that path).

So the tests split into two kinds. The resolver and refusal tests always run - they pin that an
absent engine is a named failure that projects nothing, which is what the product claims about
itself. The projection test runs only where the sidecar actually resolves, and says plainly when
it did not.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
OFFICE = REPO / "services" / "python-workers" / "document" / "worker_office.py"
TRANSPORT = REPO / "services" / "python-workers" / "transport" / "text_ndjson.py"
FIXTURE = REPO / "tests" / "fixtures" / "golden" / "golden-word-anchor.doc"

USAGE = (
    "\tName: antiword\n"
    "\tPurpose: Display MS-Word files\n"
    "\tAuthor: (C) 1998-2005 Adri van Os\n"
    "\tVersion: 0.37  (21 Oct 2005)\n"
    "\tStatus: GNU General Public License\n"
    "\tUsage: antiword [switches] wordfile1 [wordfile2 ...]\n"
)
TEXT = "\nSample Word Document Title\n\n\nAnd now for a subtitle\n\n\nMain Heading\n\n\n" \
       "This is a sample Microsoft Word Document.\n\n"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


worker = _load("doc_worker_office", OFFICE)


class FakeRun:
    """Stand in for the sidecar process, recording every command it was asked to run.

    The fake is asked the same two questions the real binary is: who are you (`-h`) and read this
    one file (`-t <path>`). Nothing else is answered, so a command that batches documents or
    requests a mapping file by path shows up as a failure of the product, not of the fake.
    """

    def __init__(self, stdout=TEXT, stderr="", returncode=0, not_word=False, honest=True):
        self.calls: list[list[str]] = []
        self.envs: list[dict | None] = []
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.not_word = not_word
        self.honest = honest

    def __call__(self, command, **kwargs):
        self.calls.append(list(command))
        self.envs.append(kwargs.get("env"))
        if len(command) == 2 and command[1] == "-h":
            return self._complete(USAGE if self.honest else "some other tool", "", 1)
        if "-t" not in command:
            raise AssertionError(f"unexpected invocation: {command}")
        if "antiword" not in Path(command[0]).name.lower():
            raise AssertionError(f"a document was handed to something else: {command}")
        if len([item for item in command[2:] if not item.startswith("-")]) != 1:
            raise AssertionError(f"one file per process: {command}")
        if self.not_word:
            # the engine names the file it rejected, in its own words
            return self._complete("", f"{command[-1]} is not a Word Document.", 1)
        return self._complete(self.stdout, self.stderr, self.returncode)

    def _complete(self, stdout, stderr, code):
        return subprocess.CompletedProcess(args=[], returncode=code, stdout=stdout, stderr=stderr)


@pytest.fixture
def fake_engine(monkeypatch, tmp_path):
    """Install a fake sidecar. A configured path has to exist, because a product that will not
    substitute a different binary for a missing one cannot be tested with a made-up path."""
    tool = tmp_path / "antiword.exe"
    tool.write_bytes(b"")
    other = tmp_path / "not-antiword.exe"
    other.write_bytes(b"")

    def install(run: FakeRun, *, on_path=None, declared=None, configured=str(tool)):
        monkeypatch.setenv("ARCHEAXIS_ANTIWORD_CMD", configured)
        monkeypatch.setattr(worker, "_run", run)
        monkeypatch.setattr(worker, "_declared_path", lambda name: declared)
        monkeypatch.setattr(worker.shutil, "which", lambda name: on_path)
        return run

    install.tool = str(tool)
    install.other = str(other)
    return install


def test_a_configured_engine_is_the_one_used_and_is_never_substituted(fake_engine):
    run = FakeRun()
    fake_engine(run, on_path=r"C:\elsewhere\antiword.exe")
    identity = worker._antiword()
    assert identity["path"] == fake_engine.tool
    assert run.calls[0][0] == fake_engine.tool


def test_a_configured_path_that_does_not_exist_is_reported_as_itself(fake_engine, tmp_path):
    gone = tmp_path / "gone.exe"
    fake_engine(FakeRun(), on_path=r"C:\elsewhere\antiword.exe", configured=str(gone))
    with pytest.raises(RuntimeError) as exc:
        worker._antiword()
    assert "does not exist" in str(exc.value) and str(gone) in str(exc.value)
    assert "C:\\elsewhere" not in str(exc.value), "a refused configuration must not be replaced"


def test_a_binary_that_does_not_answer_as_the_engine_is_not_trusted(fake_engine):
    fake_engine(FakeRun(honest=False), on_path=fake_engine.other, configured="")
    with pytest.raises(RuntimeError) as exc:
        worker._antiword()
    assert "no usable antiword sidecar" in str(exc.value)
    assert "PATH" in str(exc.value)


def test_the_declared_registry_is_consulted_before_path(fake_engine, tmp_path):
    declared_tool = tmp_path / "declared-antiword.exe"
    declared_tool.write_bytes(b"")
    run = FakeRun()
    fake_engine(run, declared=str(declared_tool), on_path=r"C:\path\antiword.exe", configured="")
    assert worker._antiword()["path"] == str(declared_tool)
    assert run.calls[0][0] == str(declared_tool)


def test_no_engine_anywhere_is_a_named_refusal_that_projects_nothing(fake_engine, tmp_path):
    run = FakeRun()
    fake_engine(run, configured="")
    copy = tmp_path / "letter.doc"
    copy.write_bytes(FIXTURE.read_bytes())
    with pytest.raises(RuntimeError) as exc:
        worker.extract(str(copy))
    assert "doc engine missing" in str(exc.value)
    assert "antiword" in str(exc.value) and "PATH" in str(exc.value)
    assert run.calls == [], "nothing was asked to read the document"


def test_the_document_is_read_one_file_per_process_without_a_mapping_path(fake_engine):
    run = FakeRun()
    fake_engine(run)
    worker._doc_text(FIXTURE)
    reading = [call for call in run.calls if "-t" in call]
    assert len(reading) == 1, run.calls
    assert reading[0][-1] == str(FIXTURE)
    assert "-m" not in reading[0], "a mapping asked for by path is truncated by the engine"


def test_the_projection_is_the_engines_own_text_with_line_addresses(fake_engine):
    fake_engine(FakeRun())
    result = worker._doc_text(FIXTURE)
    text = result["text"]
    assert text.startswith("\nSample Word Document Title")
    assert "This is a sample Microsoft Word Document." in text
    anchors = result["structure"]
    assert anchors, "a projection with no addresses is not an anchored one"
    previous = -1
    for anchor in anchors:
        assert anchor["kind"] == "line" and anchor["path"][0].startswith("line-")
        assert 0 <= anchor["char_start"] < anchor["char_end"] <= len(text)
        assert anchor["char_start"] > previous, "anchors ascend"
        previous = anchor["char_start"]
        assert text[anchor["char_start"]:anchor["char_end"]].strip(), anchor
    params = result["loss_receipt"]["params"]
    assert params["engine"] == "antiword"
    assert params["engine_version_reported"].startswith("0.37")
    assert "General Public License" in params["engine_licence_self_reported"]
    losses = " ".join(result["loss_receipt"]["losses"])
    assert "no heading level" in losses and "character grid" in losses


def test_a_file_that_only_claims_the_extension_keeps_the_engines_reason(fake_engine):
    fake_engine(FakeRun(not_word=True))
    with pytest.raises(ValueError) as exc:
        worker._doc_text(FIXTURE)
    reason = str(exc.value)
    assert "is not a Word Document." in reason
    assert str(FIXTURE) not in reason, "the receipt should not carry this host's path"


def test_an_empty_engine_output_is_not_reported_as_success(fake_engine):
    fake_engine(FakeRun(stdout="   \n\n"))
    with pytest.raises(ValueError) as exc:
        worker._doc_text(FIXTURE)
    assert "no readable text" in str(exc.value)


def test_the_word_name_is_reachable_in_the_first_match_table():
    """A first-match table makes a name a reachability question, not a preference.

    `.py` was once named in a branch that an earlier text/plain arm had already claimed, and
    every table still said it was supported. This guard reads the source the way the compiler
    does: the name must be mapped, and it must not appear in any arm before it.
    """
    attempts = (REPO / "crates" / "archeaxis-application" / "src" / "attempts.rs").read_text(
        encoding="utf-8"
    )
    statement = '"doc" => "application/msword"'
    assert statement in attempts, "the Word 97 binary must be named for the office route"
    body = attempts[attempts.index("fn media_type_for_name"):]
    earlier_arms = body[:body.index(statement)]
    assert '"doc"' not in earlier_arms, "an earlier arm would shadow the Word binary name"
    accepted = re.search(r'"office\.structure",\s*&\[(.*?)\]', attempts, re.S)
    assert accepted, "the office route's accepted media list was not found"
    assert "application/msword" in accepted.group(1), (
        "the office route must accept the media type its name table produces"
    )


def test_the_route_carries_the_document_end_to_end(tmp_path):
    """The projection travels the real transport, the way a Core job sends it.

    This is where two things get proven that a direct worker call cannot prove: the route accepts
    `application/msword` at all, and the transport keeps the engine's own structure rather than
    dropping it when it derives canonical line anchors.
    """
    try:
        worker._antiword()
    except (RuntimeError, OSError) as exc:
        pytest.skip(f"the antiword sidecar is not resolvable here: {exc}")
    transport = _load("doc_transport", TRANSPORT)
    digest = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    staging = tmp_path / "staging"
    (staging / "input").mkdir(parents=True)
    (staging / "input" / digest).write_bytes(FIXTURE.read_bytes())
    root = staging / "attempt-1"
    outputs, measurements, losses = transport.execute(
        {
            "schema": "archeaxis.worker-request/v1", "type": "job_request",
            "request_id": "req-doc", "job_id": "job-doc", "attempt": 1, "protocol_minor": 0,
            "capability": "office.structure", "capability_version": "1", "deadline_ms": 120_000,
            "inputs": [{"uri": f"job://input/{digest}", "sha256": digest,
                        "media_type": "application/msword"}],
            "parameters": {},
        },
        staging,
        artifact_root=root,
    )
    kinds = [item["kind"] for item in outputs]
    assert kinds == ["text", "document_structure", "loss_report"], kinds

    def payload(kind):
        item = next(o for o in outputs if o["kind"] == kind)
        raw = (staging / "output" / item["uri"].rsplit("/", 1)[-1]).read_bytes()
        return raw if kind == "text" else json.loads(raw)

    text = payload("text").decode("utf-8")
    structure = payload("document_structure")
    loss = payload("loss_report")
    assert "Sample Word Document Title" in text
    assert measurements["input_bytes"] == len(FIXTURE.read_bytes())
    assert loss["params"]["engine"] == "antiword"
    assert loss["params"]["worker_structure"], "the engine's own structure must survive the route"
    # canonical anchors cover every line, blank ones included, so they are not the same list as
    # the engine's non-blank structure - and the receipt says which one is which
    non_blank = sum(1 for item in structure if text[item["char_start"]:item["char_end"]].strip())
    assert non_blank == len(loss["params"]["worker_structure"]), (non_blank, structure[:2])
    assert any("params.worker_structure" in line for line in loss["losses"]), loss["losses"]


def test_the_probe_states_the_sidecar_state_without_raising(monkeypatch):
    def missing():
        raise RuntimeError("doc engine missing (nothing declared, PATH offers nothing)")

    monkeypatch.setattr(worker, "_antiword", missing)
    report = worker.probe()
    assert report["engines"]["doc"] is False
    assert "doc engine missing" in report["versions"]["doc"]
    assert "doc" not in report["formats"]


def test_xls_and_doc_are_both_reported_by_the_probe(monkeypatch):
    monkeypatch.setattr(
        worker, "_antiword",
        lambda: {"path": "x", "version": "0.37  (21 Oct 2005)", "author": "a",
                 "licence_status": "GPL"},
    )
    report = worker.probe()
    # the probe used to stay silent about xlrd, so an engine could be missing without anyone
    # being told; both legacy families are now stated
    assert "xls" in report["engines"] and "doc" in report["engines"]
    assert report["engines"]["doc"] is True
    assert report["versions"]["doc"].startswith("antiword 0.37")


def test_the_real_sidecar_reads_the_real_word_document():
    """The strongest form of this evidence needs the actual engine and an actual Word file.

    It is skipped with the resolver's own reason when this host cannot resolve the sidecar, and
    the skip is a fact about the host rather than a pass: the projection claim is only verified
    where this test actually ran.
    """
    try:
        identity = worker._antiword()
    except (RuntimeError, OSError) as exc:
        pytest.skip(f"the antiword sidecar is not resolvable here: {exc}")
    result = worker._doc_text(FIXTURE)
    assert identity["version"].startswith("0.37"), identity
    assert "Sample Word Document Title" in result["text"]
    assert "This is a sample Microsoft Word Document." in result["text"]
    assert "|This is a table" in result["text"], "the file's table arrives as a character grid"
    assert "’" in result["text"], "the default mapping keeps the typographic apostrophe"
    assert len(result["structure"]) >= 20, result["structure"]
    assert result["loss_receipt"]["params"]["engine_version_reported"] == identity["version"]


def _mapping_declaration(monkeypatch, mapping_dir):
    """Answer only the `antiword-mappings` query, the way the declared registry would."""
    monkeypatch.setattr(
        worker,
        "_declared_path",
        lambda name: str(mapping_dir) if name == "antiword-mappings" else None,
    )


def test_a_declared_mapping_directory_is_handed_to_the_engine_as_home(
    fake_engine, monkeypatch, tmp_path
):
    """A relocated antiword finds its tables only under $HOME/.antiword.

    The engine refuses a mapping requested by absolute path - the name is truncated and its
    default table is used instead - so the declaration has to become a HOME, not an argument.
    """
    run = fake_engine(FakeRun())
    mappings = tmp_path / ".antiword"
    mappings.mkdir()
    _mapping_declaration(monkeypatch, mappings)

    result = worker._doc_text(Path("sample.doc"))

    assert run.envs[0] is None, "the identity probe needs no mapping table"
    assert run.envs[1]["HOME"] == str(tmp_path)
    assert result["loss_receipt"]["params"]["mapping_home"] == str(tmp_path)


def test_no_mapping_declaration_leaves_the_engine_environment_alone(fake_engine, monkeypatch, tmp_path):
    """An in-place install resolves its own prefix, so nothing is overridden when undeclared."""
    run = fake_engine(FakeRun())
    monkeypatch.setattr(worker, "_declared_path", lambda name: None)

    result = worker._doc_text(Path("sample.doc"))

    assert run.envs[1] is None
    assert result["loss_receipt"]["params"]["mapping_home"] == "inherited from this process"


def test_a_mapping_declaration_that_is_not_named_dot_antiword_is_not_used_as_home(
    fake_engine, monkeypatch, tmp_path
):
    """The engine searches `$HOME/.antiword`, so any other directory name would miss.

    A declaration that does not carry that name is not turned into a HOME by guessing: the
    environment stays untouched and the engine's own refusal is what the run reports.
    """
    run = fake_engine(FakeRun())
    mappings = tmp_path / "antiword-maps"
    mappings.mkdir()
    _mapping_declaration(monkeypatch, mappings)

    worker._doc_text(Path("sample.doc"))

    assert run.envs[1] is None


def test_the_declared_sidecar_and_its_tables_are_a_working_pair():
    """Where the engine is bound by declaration, the bound copy is the thing that reads the file.

    Resolution by PATH alone proves nothing about the declaration, so this test asks the registry
    for both entries and runs the declared binary with the declared tables - the layout the
    capability manifest promises, checked rather than assumed. It is skipped with the resolver's
    own reason where nothing is declared, and that skip is a fact about the host.
    """
    declared_binary = worker._declared_path("antiword")
    declared_mappings = worker._declared_path("antiword-mappings")
    if not declared_binary or not declared_mappings:
        pytest.skip(
            "no declared antiword binding on this host "
            f"(binary={declared_binary!r} mappings={declared_mappings!r})"
        )
    mappings = Path(declared_mappings)
    assert mappings.name == ".antiword", mappings
    home = mappings.parent
    assert (home / "antiword.exe").is_file() or Path(declared_binary).parent == home, (
        "the declared binary must sit with the directory that becomes its HOME"
    )
    identity = worker._antiword_identity(declared_binary)
    if identity is None:
        pytest.skip(f"the declared binary did not identify itself as antiword: {declared_binary}")

    run = subprocess.run(
        [declared_binary, "-t", str(FIXTURE)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        env={**os.environ, "HOME": str(home)},
    )

    assert run.returncode == 0, (run.returncode, run.stderr)
    assert "Sample Word Document Title" in run.stdout
    assert (mappings / "UTF-8.txt").is_file(), "the default mapping has to be one of the tables"
