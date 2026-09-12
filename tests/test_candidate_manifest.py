"""R13: a candidate is only as good as its manifest's ability to fail.

The bundle's whole claim is "these bytes come from this commit". That claim is worth nothing
if a tampered file, a missing file, an unrecorded stowaway or an unknown commit can slip past
verification, so each of those is tested here, along with the manifest's duty to say what the
bundle does *not* contain.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "scripts" / "release" / "candidate.py"
BUILDER = REPO / "scripts" / "release" / "build_candidate.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


candidate = _load("candidate_under_test", MODULE)
builder = _load("build_candidate_under_test", BUILDER)

COMMIT = "a" * 40
COMMITS = {COMMIT, "b" * 40}


def _bundle(tmp_path: Path, *, name: str = "bundle") -> tuple[Path, dict]:
    root = tmp_path / name
    root.mkdir(parents=True)
    (root / "archeaxis-api.exe").write_bytes(b"MZ fake core binary")
    manifest = candidate.write_bundle(
        root,
        [root / "archeaxis-api.exe"],
        commit=COMMIT,
        commit_subject="a subject",
        kind="release-build",
        built_at="2026-09-12T00:00:00Z",
        tree_clean=True,
        untracked_present=False,
        python_hint="3.13",
    )
    return root, manifest


def test_a_faithful_bundle_verifies(tmp_path):
    root, manifest = _bundle(tmp_path)
    assert candidate.verify_manifest(root, manifest, known_commits=COMMITS) == []


def test_the_manifest_records_size_and_digest_for_every_file(tmp_path):
    root, manifest = _bundle(tmp_path)
    recorded = next(item for item in manifest["files"] if item["path"] == "archeaxis-api.exe")
    assert recorded["bytes"] == (root / "archeaxis-api.exe").stat().st_size
    assert len(recorded["sha256"]) == 64
    paths = [item["path"] for item in manifest["files"]]
    assert paths == sorted(paths), "a manifest that lists its files in a stable order is diffable"


def test_a_tampered_file_is_named(tmp_path):
    root, manifest = _bundle(tmp_path)
    (root / "archeaxis-api.exe").write_bytes(b"MZ fake core binary!")
    problems = candidate.verify_manifest(root, manifest, known_commits=COMMITS)
    assert any("archeaxis-api.exe" in line and "is" in line and "bytes" in line for line in problems)
    assert any("hashes to" in line for line in problems)


def test_a_missing_file_is_named(tmp_path):
    root, manifest = _bundle(tmp_path)
    (root / "archeaxis-api.exe").unlink()
    problems = candidate.verify_manifest(root, manifest, known_commits=COMMITS)
    assert any("recorded but missing" in line for line in problems)


def test_an_unrecorded_stowaway_is_refused(tmp_path):
    """A file nobody recorded is exactly how something rides along unnoticed."""
    root, manifest = _bundle(tmp_path)
    (root / "NOTES-THAT-NOBODY-RECORDED.txt").write_text("surprise", encoding="utf-8")
    problems = candidate.verify_manifest(root, manifest, known_commits=COMMITS)
    assert any("not recorded in the manifest" in line for line in problems)


def test_an_unknown_source_commit_is_refused(tmp_path):
    root, manifest = _bundle(tmp_path)
    manifest["source_commit"] = "c" * 40
    problems = candidate.verify_manifest(root, manifest, known_commits=COMMITS)
    assert any("not a commit in this repository" in line for line in problems)


def test_a_manifest_must_say_which_build_it_is(tmp_path):
    root, manifest = _bundle(tmp_path)
    manifest["build_kind"] = ""
    problems = candidate.verify_manifest(root, manifest, known_commits=COMMITS)
    assert any("which build" in line for line in problems)


def test_a_manifest_must_state_what_it_leaves_out(tmp_path):
    root, manifest = _bundle(tmp_path)
    manifest["not_included"] = []
    problems = candidate.verify_manifest(root, manifest, known_commits=COMMITS)
    assert any("leaves out" in line for line in problems)


def test_a_wrong_schema_is_refused(tmp_path):
    root, manifest = _bundle(tmp_path)
    manifest["schema"] = "archeaxis.candidate/v0"
    problems = candidate.verify_manifest(root, manifest, known_commits=COMMITS)
    assert any("schema" in line for line in problems)


def test_a_bundle_built_from_a_dirty_tree_is_labelled_but_not_rejected(tmp_path):
    """The label is a fact to record; only mismatched bytes are a failure."""
    root = tmp_path / "dirty"
    root.mkdir()
    (root / "archeaxis-api.exe").write_bytes(b"binary")
    manifest = candidate.build_manifest(
        root,
        [root / "archeaxis-api.exe"],
        commit=COMMIT,
        commit_subject="a subject",
        kind="debug-build",
        built_at="2026-09-12T00:00:00Z",
        tree_clean=False,
        untracked_present=True,
        python_hint="3.13",
    )
    assert manifest["tree_clean_when_built"] is False
    assert manifest["untracked_paths_present_when_built"] is True
    assert manifest["hash_meaning"].startswith("a digest binds")
    assert candidate.verify_manifest(root, manifest, known_commits=COMMITS) == []


def test_the_readme_is_generated_from_the_manifest(tmp_path):
    """The instructions cannot drift from the manifest, because the manifest writes them."""
    root, manifest = _bundle(tmp_path)
    text = candidate.readme_text(manifest)
    assert "archeaxis-api.exe" in text
    assert COMMIT[:12] in text
    assert "release-build" in text
    assert "verify_candidate.py" in text
    for item in manifest["not_included"]:
        assert item in text


def test_the_readme_and_manifest_record_each_other(tmp_path):
    """Both generated files are in the manifest, so neither can be edited unnoticed."""
    root, manifest = _bundle(tmp_path)
    recorded = {item["path"] for item in manifest["files"]}
    assert recorded == {"archeaxis-api.exe", "README.md"}
    (root / "README.md").write_text("do something else entirely", encoding="utf-8")
    problems = candidate.verify_manifest(root, manifest, known_commits=COMMITS)
    assert any("README.md" in line for line in problems)


def test_an_explicitly_given_binary_is_labelled_by_where_it_lives(tmp_path, monkeypatch):
    """A binary outside a release target directory is offered as a debug build, not as released."""
    monkeypatch.setattr(builder, "_tree_state", lambda: (True, False))  # the tree state under test
    binary = tmp_path / "archeaxis-api.exe"
    binary.write_bytes(b"debug")
    out = tmp_path / "out"
    assert builder.main(["--binary", str(binary), "--out", str(out)]) == 0
    manifest = json.loads((out / candidate.MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["build_kind"] == "debug-build"


def test_only_a_debug_binary_in_the_target_directory_is_refused_unless_allowed(tmp_path, monkeypatch, capsys):
    """The refusal R13 needs: a debug build must never be offered as the release candidate."""
    monkeypatch.setattr(builder, "_tree_state", lambda: (True, False))  # the tree state under test
    target = tmp_path / "cargo"
    (target / "debug").mkdir(parents=True)
    (target / "debug" / "archeaxis-api.exe").write_bytes(b"debug")
    monkeypatch.setattr(builder, "DEFAULT_TARGET", target)

    assert builder.main(["--out", str(tmp_path / "refused")]) == 2
    assert "--allow-debug" in capsys.readouterr().err
    assert not (tmp_path / "refused" / candidate.MANIFEST_NAME).exists()

    assert builder.main(["--out", str(tmp_path / "labelled"), "--allow-debug"]) == 0
    manifest = json.loads((tmp_path / "labelled" / candidate.MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["build_kind"] == "debug-build"


def test_a_bundle_from_a_dirty_tree_is_refused_unless_the_caller_insists(tmp_path, monkeypatch, capsys):
    """The rule core_launch.py --manifest already applies: a manifest describes a tested commit."""
    target = tmp_path / "cargo"
    (target / "release").mkdir(parents=True)
    (target / "release" / "archeaxis-api.exe").write_bytes(b"release")
    monkeypatch.setattr(builder, "DEFAULT_TARGET", target)
    monkeypatch.setattr(builder, "_tree_state", lambda: (False, True))

    assert builder.main(["--out", str(tmp_path / "refused")]) == 5
    assert "--allow-dirty" in capsys.readouterr().err
    assert not (tmp_path / "refused" / candidate.MANIFEST_NAME).exists()

    assert builder.main(["--out", str(tmp_path / "labelled"), "--allow-dirty"]) == 0
    manifest = json.loads((tmp_path / "labelled" / candidate.MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["tree_clean_when_built"] is False


def test_the_builder_refuses_a_commit_that_is_not_in_the_repository(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, "_tree_state", lambda: (True, False))  # the tree state under test
    binary = tmp_path / "archeaxis-api.exe"
    binary.write_bytes(b"debug")
    code = builder.main(["--binary", str(binary), "--out", str(tmp_path / "out"), "--commit", "0" * 40])
    assert code == 3
    assert not (tmp_path / "out" / candidate.MANIFEST_NAME).exists()


def test_existing_output_is_preserved(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, '_tree_state', lambda: (True, False))
    binary = tmp_path / 'archeaxis-api.exe'
    binary.write_bytes(b'fake')
    out = tmp_path / 'existing'
    out.mkdir()
    valuable = out / 'keep.txt'
    valuable.write_bytes(b'preserve')
    assert builder.main(['--binary', str(binary), '--out', str(out)]) != 0
    assert valuable.read_bytes() == b'preserve'


def test_dirty_refusal_creates_no_output(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, '_tree_state', lambda: (False, False))
    binary = tmp_path / 'archeaxis-api.exe'
    binary.write_bytes(b'fake')
    out = tmp_path / 'refused'
    assert builder.main(['--binary', str(binary), '--out', str(out)]) == 5
    assert not out.exists()


def test_existing_archive_is_preserved_before_bundle_creation(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, '_tree_state', lambda: (True, False))
    binary = tmp_path / 'archeaxis-api.exe'
    binary.write_bytes(b'fake')
    out = tmp_path / 'candidate'
    archive = out.with_suffix('.zip')
    archive.write_bytes(b'keep archive')
    assert builder.main(['--binary', str(binary), '--out', str(out), '--zip']) != 0
    assert archive.read_bytes() == b'keep archive'
    assert not out.exists()


def test_output_outside_governed_root_is_refused_without_creating_it(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, '_tree_state', lambda: (True, False))
    monkeypatch.setattr(builder.dev, 'layout', lambda root: {'dev': tmp_path / 'governed'})
    binary = tmp_path / 'archeaxis-api.exe'
    binary.write_bytes(b'fake')
    out = tmp_path / 'outside'
    assert builder.main(['--binary', str(binary), '--out', str(out)]) == 6
    assert not out.exists()


def test_zip_uses_recorded_whitelist_not_directory_walk(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, '_tree_state', lambda: (True, False))
    binary = tmp_path / 'archeaxis-api.exe'
    binary.write_bytes(b'fake')
    out = tmp_path / 'candidate'
    original = builder.candidate.verify_manifest

    def verify_then_create_unrecorded_file(root, manifest, **kwargs):
        result = original(root, manifest, **kwargs)
        (root / 'unrecorded-cache.bin').write_bytes(b'do not ship')
        return result

    monkeypatch.setattr(builder.candidate, 'verify_manifest', verify_then_create_unrecorded_file)
    assert builder.main(['--binary', str(binary), '--out', str(out), '--zip']) == 0
    with zipfile.ZipFile(out.with_suffix('.zip')) as archive:
        assert set(archive.namelist()) == {'archeaxis-api.exe', 'README.md', 'CANDIDATE.json'}
        assert archive.read('archeaxis-api.exe') == b'fake'


@pytest.mark.parametrize('name', ['../outside.bin', '/outside.bin', 'E:/forbidden',
                                  'C:\\outside.bin', 'file:stream', './README.md'])
def test_manifest_unsafe_paths_rejected_before_hashing(tmp_path, monkeypatch, name):
    root, manifest = _bundle(tmp_path)
    manifest['files'] = [{'path': name, 'bytes': 0, 'sha256': 'a' * 64}]
    monkeypatch.setattr(candidate, 'sha256_of', lambda path: pytest.fail('unsafe entry must not be hashed'))
    original = Path.is_file
    def guarded_is_file(path):
        if str(path).casefold().startswith('e:'):
            pytest.fail('protected drive metadata query')
        return original(path)
    with patch.object(Path, 'is_file', guarded_is_file):
        assert any('unsafe' in problem for problem in candidate.verify_manifest(root, manifest))


def test_duplicate_manifest_paths_and_unrecorded_digest_files_are_refused(tmp_path):
    root, manifest = _bundle(tmp_path)
    manifest['files'].append(dict(manifest['files'][0]))
    (root / 'unrecorded.sha256').write_text('not an allowed sidecar')
    problems = candidate.verify_manifest(root, manifest)
    assert any('duplicate' in problem for problem in problems)
    assert any('unrecorded.sha256' in problem for problem in problems)


def test_non_object_manifest_entry_is_a_named_failure(tmp_path):
    root, manifest = _bundle(tmp_path)
    manifest['files'] = [None]
    assert any('object' in problem for problem in candidate.verify_manifest(root, manifest))


def test_protected_root_rejected_before_any_metadata_or_content_read(monkeypatch):
    verifier = _load('candidate_verifier_boundary', REPO / 'scripts/release/verify_candidate.py')
    def forbidden(*args, **kwargs):
        pytest.fail('filesystem must not be accessed')
    monkeypatch.setattr(Path, 'lstat', forbidden)
    monkeypatch.setattr(Path, 'is_dir', forbidden)
    monkeypatch.setattr(Path, 'read_text', forbidden)
    assert candidate.verify_manifest(Path('E:/not-authorized'), {}) == ['unsafe bundle root']
    assert verifier.main(['--candidate', 'E:/not-authorized']) == 2


def test_linked_directory_is_never_enumerated_or_hashed(tmp_path, monkeypatch):
    root, manifest = _bundle(tmp_path)
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'payload').write_bytes(b'external fixture')
    link = root / 'redirect'
    if os.name == 'nt':
        result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(outside)],
                                capture_output=True)
        assert result.returncode == 0
    else:
        link.symlink_to(outside, target_is_directory=True)
    manifest['files'].append({'path': 'redirect/payload', 'bytes': 16, 'sha256': 'a' * 64})
    original_scan = os.scandir
    original_hash = candidate.sha256_of
    def guarded_scan(path):
        assert Path(path) != link
        return original_scan(path)
    def guarded_hash(path):
        assert 'redirect' not in path.parts
        return original_hash(path)
    try:
        monkeypatch.setattr(os, 'scandir', guarded_scan)
        monkeypatch.setattr(candidate, 'sha256_of', guarded_hash)
        problems = candidate.verify_manifest(root, manifest)
        assert 'unsafe manifest file path' in problems
        assert 'unsafe directory in bundle' in problems
        assert (outside / 'payload').read_bytes() == b'external fixture'
    finally:
        if os.name == 'nt':
            link.rmdir()
        else:
            link.unlink()


@pytest.mark.parametrize('mode,expected', [('silent', 4), ('ready', 0), ('exit', 4), ('port_only', 4)])
def test_candidate_wait_is_bounded_and_reaped_in_project_run(tmp_path, monkeypatch, mode, expected):
    verifier = _load('candidate_verifier_timeout', REPO / 'scripts/release/verify_candidate.py')
    root, manifest = _bundle(tmp_path)
    real_popen = subprocess.Popen
    children = []
    captured = []
    run_dir = verifier.dev.artifact_directory(REPO, 'candidate-timeout-test')
    monkeypatch.setattr(verifier.dev, 'artifact_directory', lambda *args: run_dir)

    def start_silent(command, **kwargs):
        if command[0] == 'taskkill.exe':
            return real_popen(command, **kwargs)
        captured.append((command, kwargs))
        payloads = {
            'silent': 'import sys,time; sys.stdin.read(); time.sleep(30)',
            'exit': 'import sys; sys.stdin.read()',
            'ready': 'import sys,time,pathlib; sys.stdin.read(); pathlib.Path(sys.argv[1]).touch(); print("127.0.0.1:12345",flush=True); time.sleep(30)',
            'port_only': 'import sys,time; sys.stdin.read(); print("127.0.0.1:12345",flush=True); time.sleep(30)',
        }
        child = real_popen([sys.executable, '-B', '-c', payloads[mode], command[1]], **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(verifier.subprocess, 'Popen', start_silent)
    receipt = {}
    started = time.monotonic()
    assert verifier.run_binary(root, manifest, receipt, timeout=0.5) == expected
    assert time.monotonic() - started < 5
    assert children[0].poll() is not None
    assert receipt['run']['stopped'] is True
    database = Path(captured[0][0][1])
    assert database.is_relative_to(Path(os.environ['ARCHEAXIS_RUN_ROOT']) / 'artifacts')
    if os.name == 'nt':
        assert captured[0][1]['creationflags'] & subprocess.CREATE_NO_WINDOW
