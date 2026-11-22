"""R15/F15: a folder ingestion that resumes honestly, and never guesses a kind.

The driver's whole value is that a second run does not redo a first, and that a file it cannot
place is visible. So these tests hold three properties: only the latest attempt per path decides
(so a later failure is not hidden by an earlier success), a file with no known kind is imported
and recorded as carrying no job rather than skipped, and the Core's own refusals are recorded in
its own words. A last test checks the extension table against the Core's media-type table, so the
driver cannot invent an extension the Core has never heard of.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "scripts" / "ingest" / "directory_batch.py"
ATTEMPTS_RS = REPO / "crates" / "archeaxis-application" / "src" / "attempts.rs"


def _load():
    spec = importlib.util.spec_from_file_location("directory_batch_under_test", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


batch = _load()


def test_default_manifest_separates_source_roots_and_core_endpoints(tmp_path):
    left = tmp_path / 'left' / 'notes'
    right = tmp_path / 'right' / 'notes'
    left.mkdir(parents=True)
    right.mkdir(parents=True)
    first = batch.default_manifest(left, 'http://127.0.0.1:9000')
    assert first != batch.default_manifest(right, 'http://127.0.0.1:9000')
    assert first != batch.default_manifest(left, 'http://127.0.0.1:9001')
    assert first == batch.default_manifest(left, 'http://127.0.0.1:9000/')
    assert first.is_relative_to(batch._runtime().layout(REPO)['dev'] / 'state')
    assert not first.exists()


def test_default_manifest_is_independent_of_ephemeral_run_id(tmp_path, monkeypatch):
    first = batch.default_manifest(tmp_path, 'http://127.0.0.1:9000')
    monkeypatch.setenv('ARCHEAXIS_RUN_ROOT', str(tmp_path / 'another-run'))
    assert first == batch.default_manifest(tmp_path, 'http://127.0.0.1:9000')


def test_cli_dry_run_uses_managed_state_without_writing_it(tmp_path, capsys):
    root = _folder(tmp_path)
    base = 'http://127.0.0.1:9000'
    manifest = batch.default_manifest(root, base)
    before = manifest.parent.exists()
    assert batch.main(['--root', str(root), '--core', base, '--dry-run', '--json']) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt['manifest'] == str(manifest)
    assert receipt['dry_run'] is True
    assert not manifest.exists()
    assert manifest.parent.exists() == before


class FakeCore:
    """Records every call and answers with whatever the test decided per path."""

    def __init__(self, import_status: int = 202, job_status: int = 202) -> None:
        self.calls: list[tuple[str, str, dict]] = []
        self.import_status = import_status
        self.job_status = job_status
        self.counter = 0

    def __call__(self, method: str, path: str, body: dict | None = None):
        self.calls.append((method, path, body or {}))
        if path == "/api/v1/imports":
            self.counter += 1
            if self.import_status not in (200, 201, 202):
                return self.import_status, "the Core refused this name"
            return self.import_status, {"source_id": f"src_{self.counter:04d}"}
        return self.job_status, {"job_id": (body or {}).get("job_id")}

    def paths(self) -> list[str]:
        return [path for _, path, _ in self.calls]


def _folder(tmp_path: Path) -> Path:
    root = tmp_path / "documents"
    (root / "nested").mkdir(parents=True)
    (root / ".git").mkdir()
    (root / "notes.md").write_text("# Notes\n\nbody\n", encoding="utf-8")
    (root / "page.html").write_text("<html><body><p>hello</p></body></html>", encoding="utf-8")
    (root / "nested" / "deep.txt").write_text("deep\n", encoding="utf-8")
    (root / "mystery.xyz").write_text("nobody knows\n", encoding="utf-8")
    (root / ".git" / "config").write_text("ignored\n", encoding="utf-8")
    (root / ".hidden.md").write_text("hidden\n", encoding="utf-8")
    return root


def test_a_folder_is_walked_with_its_exclusions_reported(tmp_path):
    root = _folder(tmp_path)
    files, skipped = batch.iter_files(root)
    assert {path.relative_to(root).as_posix() for path in files} == {
        "mystery.xyz",
        "notes.md",
        "page.html",
        "nested/deep.txt",
    }
    assert any(".git" in item for item in skipped)
    assert any(".hidden.md" in item for item in skipped)


def test_excluded_directories_are_not_enumerated(tmp_path, monkeypatch):
    root = _folder(tmp_path)
    hidden = root / '.zcode'
    hidden.mkdir()
    (hidden / 'synthetic.txt').write_text('fixture only', encoding='utf-8')
    original = os.scandir

    def guarded(path):
        assert Path(path) != hidden, 'excluded private directory was entered'
        return original(path)

    monkeypatch.setattr(os, 'scandir', guarded)
    files, skipped = batch.iter_files(root)
    assert all('.zcode' not in path.parts for path in files)
    assert any('.zcode' in item for item in skipped)


def test_linked_directory_is_not_imported(tmp_path):
    root = _folder(tmp_path)
    target = tmp_path / 'outside'
    target.mkdir()
    (target / 'not-a-source.txt').write_text('fixture only', encoding='utf-8')
    link = root / 'linked'
    if os.name == 'nt':
        result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(target)], capture_output=True)
        assert result.returncode == 0, result.stderr
    else:
        link.symlink_to(target, target_is_directory=True)
    try:
        files, skipped = batch.iter_files(root)
        assert all('linked' not in path.parts for path in files)
        assert any('linked' in item and 'link' in item for item in skipped)
    finally:
        if os.name == 'nt':
            link.rmdir()
        else:
            link.unlink()


def test_the_limit_is_reported_rather_than_silently_dropping_files(tmp_path):
    files, skipped = batch.iter_files(_folder(tmp_path), limit=2)
    assert len(files) == 2
    assert any("over the limit" in item for item in skipped)


def test_each_file_is_imported_and_given_the_job_its_kind_calls_for(tmp_path):
    core = FakeCore()
    manifest = tmp_path / "manifest.jsonl"
    receipt = batch.run_batch(_folder(tmp_path), core_call=core, manifest_path=manifest, limit=4)
    assert receipt["counts"]["enqueued"] == 3, receipt["entries"]
    assert receipt["counts"]["imported_no_job"] == 1
    kinds = {call[2].get("kind") for call in core.calls if call[1] == "/api/v1/jobs"}
    assert kinds == {"text", "html"}
    job = next(call[2] for call in core.calls if call[1] == "/api/v1/jobs")
    assert job["input_ref"].startswith("src_"), "the job must reference the imported source"


def test_a_file_with_no_known_kind_is_imported_and_says_why_there_is_no_job(tmp_path):
    """Not skipped, not guessed: the content lands, and the missing job is named."""
    core = FakeCore()
    receipt = batch.run_batch(_folder(tmp_path), core_call=core, manifest_path=tmp_path / "m.jsonl", limit=1)
    entry = receipt["entries"][0]
    assert entry["path"] == "mystery.xyz"
    assert entry["kind"] is None
    assert entry["status"] == "imported_no_job"
    assert "no kind is mapped" in entry["detail"]
    assert entry["source_id"].startswith("src_")
    assert "/api/v1/jobs" not in core.paths()


def test_a_core_refusal_is_recorded_in_the_cores_own_words(tmp_path):
    core = FakeCore(import_status=400)
    receipt = batch.run_batch(_folder(tmp_path), core_call=core, manifest_path=tmp_path / "m.jsonl", limit=1)
    entry = receipt["entries"][0]
    assert entry["status"] == "refused"
    assert "the Core refused this name" in entry["detail"]
    assert receipt["counts"]["refused"] == 1
    assert batch.counts_ok(receipt["counts"]) is False, "a batch with a refusal is not a success"


@pytest.mark.parametrize("same_source", [True, False])
def test_a_conflicting_job_is_checked_before_marking_it_enqueued(tmp_path, same_source):
    core = FakeCore(job_status=409)
    def calls(method, path, body):
        if method == "GET" and path.startswith("/api/v1/jobs/"):
            wanted = core.calls[-1][2]
            return 200, {**wanted, "input_ref": wanted["input_ref"] if same_source else "other_source"}
        return core(method, path, body)
    receipt = batch.run_batch(_folder(tmp_path), core_call=calls, manifest_path=tmp_path / "m.jsonl", limit=3)
    assert receipt["counts"]["already_enqueued" if same_source else "failed"] == 2
    assert batch.counts_ok(receipt["counts"]) is same_source


def test_a_second_run_skips_what_did_not_change(tmp_path):
    root = _folder(tmp_path)
    manifest = tmp_path / "manifest.jsonl"
    first = batch.run_batch(root, core_call=FakeCore(), manifest_path=manifest)
    assert first["counts"]["enqueued"] == 3
    second_core = FakeCore()
    second = batch.run_batch(root, core_call=second_core, manifest_path=manifest)
    # All four, including the unmapped one: its reason is the extension, which will not change,
    # so retrying would only import the same file again and pile up duplicate sources.
    assert second["counts"]["skipped_unchanged"] == 4
    assert second_core.calls == [], "an unchanged folder must cost the Core nothing"


def test_a_third_run_still_skips(tmp_path):
    """Found by running it against a real Core: a skip record must not poison the next run.

    The second run's `skipped_unchanged` line overwrote the "job already enqueued" fact, so a
    third run re-processed the whole folder.
    """
    root = _folder(tmp_path)
    manifest = tmp_path / "manifest.jsonl"
    batch.run_batch(root, core_call=FakeCore(), manifest_path=manifest)
    batch.run_batch(root, core_call=FakeCore(), manifest_path=manifest)
    third_core = FakeCore()
    third = batch.run_batch(root, core_call=third_core, manifest_path=manifest)
    assert third["counts"]["skipped_unchanged"] == 4
    assert third_core.calls == [], "the third run must cost the Core nothing either"
    assert batch.latest_by_path(batch.read_manifest(manifest))["notes.md"]["status"] == "skipped_unchanged"
    decidable = batch.latest_decidable_by_path(batch.read_manifest(manifest))
    assert decidable["notes.md"]["status"] == "enqueued", "the decision must read the last real attempt"


@pytest.mark.parametrize("verify_first", [True, False])
def test_existing_siyuan_original_is_resumed_once_after_route_is_added(tmp_path, monkeypatch, verify_first):
    root = tmp_path / "folder"
    root.mkdir()
    source = root / "原件.SY"
    source.write_text("native fixture", encoding="utf-8")
    (root / "readme.md").write_text("# Existing job", encoding="utf-8")
    (root / "unknown.xyz").write_text("custody only", encoding="utf-8")
    manifest = tmp_path / "old.jsonl"
    with monkeypatch.context() as older:
        older.delitem(batch.KIND_BY_EXTENSION, "sy")
        before = batch.run_batch(root, core_call=FakeCore(), manifest_path=manifest)
    old = next(row for row in before["entries"] if row["path"] == source.name)
    assert old["status"] == "imported_no_job" and old["kind"] is None
    expected_job = f"batch-{old['sha256'][:12]}"
    source_route = "/api/v1/sources/" + old["source_id"]
    requests = []

    def run(verified):
        def call(method, route, body):
            requests.append((method, route, body))
            if (method, route) == ("GET", source_route):
                return 200, {"source_id": old["source_id"], "sha256": old["sha256"] if verified else "0" * 64,
                             "original_name": source.name}
            assert (method, route, body) == ("POST", "/api/v1/jobs",
                                            {"job_id": expected_job, "input_ref": old["source_id"], "kind": "text"})
            return 202, {"job_id": expected_job}
        return batch.run_batch(root, core_call=call, manifest_path=manifest)

    if not verify_first:
        refused = run(False)
        assert refused["counts"]["refused"] == 1
        assert "could not be confirmed" in next(row["detail"] for row in refused["entries"] if row["status"] == "refused")
        assert requests == [("GET", source_route, None)]
        requests.clear()
    accepted = run(True)
    assert accepted["counts"]["enqueued"] == 1 and accepted["counts"]["skipped_unchanged"] == 2
    entry = next(row for row in accepted["entries"] if row["status"] == "enqueued")
    assert entry["source_id"] == old["source_id"] and entry["job_id"] == expected_job
    assert [method for method, _, _ in requests] == ["GET", "POST"]
    requests.clear()
    assert run(True)["counts"]["skipped_unchanged"] == 3
    assert not requests


def test_changed_content_is_processed_again(tmp_path):
    root = _folder(tmp_path)
    manifest = tmp_path / "manifest.jsonl"
    batch.run_batch(root, core_call=FakeCore(), manifest_path=manifest)
    (root / "notes.md").write_text("# Notes\n\nbody changed\n", encoding="utf-8")
    core = FakeCore()
    receipt = batch.run_batch(root, core_call=core, manifest_path=manifest)
    assert [entry["path"] for entry in receipt["entries"] if entry["status"] == "enqueued"] == ["notes.md"]


def test_a_later_failure_is_not_hidden_by_an_earlier_success(tmp_path):
    """The rule the legacy processing ledger records, applied to this driver."""
    root = _folder(tmp_path)
    manifest = tmp_path / "manifest.jsonl"
    batch.run_batch(root, core_call=FakeCore(), manifest_path=manifest, limit=2)
    # The content changes, so the earlier success must not stop the driver trying again — and the
    # failure that follows is what speaks for that file from then on.
    (root / "nested" / "deep.txt").write_text("deep changed\n", encoding="utf-8")
    failing = batch.run_batch(root, core_call=FakeCore(job_status=400), manifest_path=manifest, limit=2)
    assert failing["counts"]["failed"] == 1
    latest = batch.latest_by_path(batch.read_manifest(manifest))
    assert latest["nested/deep.txt"]["status"] == "failed"
    assert latest["mystery.xyz"]["status"] == "skipped_unchanged"


def test_resume_off_reprocesses_everything(tmp_path):
    root = _folder(tmp_path)
    manifest = tmp_path / "manifest.jsonl"
    batch.run_batch(root, core_call=FakeCore(), manifest_path=manifest)
    core = FakeCore()
    receipt = batch.run_batch(root, core_call=core, manifest_path=manifest, resume=False)
    assert receipt["counts"]["skipped_unchanged"] == 0
    assert len(core.paths()) > 0


def test_a_dry_run_writes_nothing_and_calls_nothing(tmp_path):
    root = _folder(tmp_path)
    manifest = tmp_path / "manifest.jsonl"
    core = FakeCore()
    receipt = batch.run_batch(root, core_call=core, manifest_path=manifest, dry_run=True)
    assert receipt["counts"]["skipped_unchanged"] == 4
    assert core.calls == []
    assert not manifest.exists()


def test_interruption_preserves_each_finished_file_and_port_change(tmp_path):
    root = tmp_path / "input"
    root.mkdir()
    (root / "a.md").write_text("first", encoding="utf8")
    (root / "b.txt").write_text("second", encoding="utf8")
    manifest = tmp_path / "progress.jsonl"
    core = FakeCore()

    def interrupted(method, path, body):
        if path == "/api/v1/imports" and body["name"] == "b.txt":
            raise InterruptedError("controller stopped before second import")
        return core(method, path, body)

    with pytest.raises(InterruptedError):
        batch.run_batch(root, core_call=interrupted, manifest_path=manifest)
    assert [item["path"] for item in batch.read_manifest(manifest)] == ["a.md"]
    result = batch.run_batch(root, core_call=core, manifest_path=manifest)
    assert result["counts"]["skipped_unchanged"] == result["counts"]["enqueued"] == 1
    assert [body["name"] for _, path, body in core.calls if path.endswith("/imports")] == ["a.md", "b.txt"]

    def identify(*_):
        return 200, {"schema": "archeaxis.ingest-batches/v1", "workspace_id": "ws", "restore_epoch": "original"}

    with patch.object(batch, "default_manifest", side_effect=lambda _root, key: tmp_path / (batch.hashlib.sha256(key.encode()).hexdigest() + ".jsonl")):
        first = batch.resume_manifest(root, "http://127.0.0.1:21001", identify)
        assert batch.resume_manifest(root, "http://127.0.0.1:31001", identify) == first
        assert batch.resume_manifest(root, "http://127.0.0.1:31001", None) == first
        changed = lambda *_: (200, {**identify()[1], "restore_epoch": "restored"})
        assert batch.resume_manifest(root, "http://127.0.0.1:31001", changed) != first


def test_url_journal_adopts_only_completed_work_present_in_core(tmp_path, monkeypatch):
    monkeypatch.setattr(batch, "default_manifest", lambda root, key: tmp_path / (batch.hashlib.sha256(key.encode()).hexdigest() + ".jsonl"))
    base = "http://localhost:4000"
    old = batch.default_manifest(tmp_path, base)
    batch.append_records(old, [
        {"path": "kept.md", "source_id": "src1", "sha256": "sum", "kind": "text", "job_id": "job1", "status": "enqueued"},
        {"path": "gone.md", "source_id": "src2", "sha256": "sum2", "kind": "text", "job_id": "job2", "status": "enqueued"},
    ])

    def core(method, path, body):
        assert method == "GET"
        return {
            "/api/v1/ingest-batches?limit=1": (200, {"schema": "archeaxis.ingest-batches/v1", "workspace_id": "test", "restore_epoch": "one"}),
            "/api/v1/sources/src1": (200, {"sha256": "sum"}), "/api/v1/jobs/job1": (200, {"input_ref": "src1", "kind": "text"}),
            "/api/v1/sources/src2": (404, {}),
        }[path]

    original = old.read_bytes()
    journal = batch.resume_manifest(tmp_path, base, core)
    assert [entry["path"] for entry in batch.read_manifest(journal)] == ["kept.md"]
    assert old.read_bytes() == original


def test_the_manifest_is_one_json_line_per_attempt(tmp_path):
    root = _folder(tmp_path)
    manifest = tmp_path / "manifest.jsonl"
    batch.run_batch(root, core_call=FakeCore(), manifest_path=manifest, limit=2)
    lines = [line for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 2
    for line in lines:
        record = json.loads(line)
        assert record["schema"] == batch.MANIFEST_SCHEMA
        assert record["sha256"] and record["bytes"] > 0 and record["at"]


def test_every_extension_the_driver_maps_is_one_the_core_knows():
    """The driver may not invent an extension: it is checked against the Core's own table."""
    source = ATTEMPTS_RS.read_text(encoding="utf-8")
    body = source[source.index("fn media_type_for_name") : source.index("fn ", source.index("fn media_type_for_name") + 10)]
    known = set(re.findall(r'"([a-z0-9]+)"', body))
    unknown = sorted(extension for extension in batch.KIND_BY_EXTENSION if extension not in known)
    assert unknown == [], f"the driver maps extensions the Core's table does not name: {unknown}"


def test_every_mapped_kind_is_a_route_kind():
    source = ATTEMPTS_RS.read_text(encoding="utf-8")
    routes = source[source.index("const ROUTES") : source.index("];", source.index("const ROUTES"))]
    kinds = set(re.findall(r'\(\s*"([a-z]+)"\s*,', routes))
    assert kinds, "could not parse the route kinds out of the Core"
    assert set(batch.KIND_BY_EXTENSION.values()) <= kinds, set(batch.KIND_BY_EXTENSION.values()) - kinds


def test_siyuan_source_maps_to_the_same_text_route_as_the_core():
    source = ATTEMPTS_RS.read_text(encoding="utf-8")
    assert batch.KIND_BY_EXTENSION["sy"] == "text"
    assert '"sy" => "application/x-siyuan"' in source
    routes = source[source.index("pub const ROUTE_MEDIA_TYPES"):source.index('    ("pdf.extract",')]
    assert '"text.extract"' in routes and '"application/x-siyuan"' in routes


def test_legacy_office_mapping_uses_existing_core_media_and_office_route():
    """A request is mapped to the existing engine lane; this asserts no installed qualification."""
    source = ATTEMPTS_RS.read_text(encoding="utf-8")
    for extension, mime in [("doc", "application/msword"), ("xls", "application/vnd.ms-excel"), ("ppt", "application/vnd.ms-powerpoint")]:
        assert batch.KIND_BY_EXTENSION[extension] == "office"
        assert f'"{extension}" => "{mime}"' in source
        assert mime in source[source.index("pub const ROUTE_MEDIA_TYPES"):source.index("pub fn media_type_for_name")]
