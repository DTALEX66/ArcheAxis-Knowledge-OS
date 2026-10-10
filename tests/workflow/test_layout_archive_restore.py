"""The layout archive must actually restore, and must say so when it cannot.

The archive is the preservation point that made moving 197 unreferenced development entries
acceptable. It was unusable as written: the undo read a per-entry absolute path recorded *before*
the archive was relocated, skipped every entry when that path was absent, and still exited 0 — so a
later operator would read success while nothing had been restored. These tests pin the two halves of
the fix: deriving each entry's location from its own source, and failing loudly on a missing copy.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
UNDO = REPO / "scripts" / "runtime" / "undo_layout_realign.py"


def load_undo():
    spec = importlib.util.spec_from_file_location("undo_layout_realign", UNDO)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_archive(root: Path, entries: dict[str, str], *, stale_recorded: bool = True) -> Path:
    """A fake repository with one archive, laid out the way `realign_dev_layout` writes it."""
    scratch = root / ".project-local" / "legacy-scratch-20261006"
    moved = []
    for source, content in entries.items():
        if source.startswith(".project-local/"):
            archived = scratch / "project-local" / source.split("/", 1)[1]
        else:
            archived = scratch / "repo-root" / source
        archived.parent.mkdir(parents=True, exist_ok=True)
        archived.write_text(content, encoding="utf-8")
        moved.append({
            "source": source,
            # The old absolute location, as it really is in the shipped manifest.
            "scratch_path": (".project-local/task-runtime/legacy-scratch-20261006/" + str(archived.relative_to(scratch))).replace("\\", "/")
            if stale_recorded else str(archived),
        })
    scratch.mkdir(parents=True, exist_ok=True)
    (scratch / "manifest.json").write_text(json.dumps({
        "schema": "archeaxis/layout-scratch/v1",
        "scratch": str(root / ".project-local" / "task-runtime" / "legacy-scratch-20261006"),
        "moved": moved, "skipped": [], "note": "test",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return scratch


def wire(monkeypatch, root: Path, scratch: Path):
    undo = load_undo()
    monkeypatch.setattr(undo, "REPO", root)
    monkeypatch.setattr(undo, "SCRATCH_CANDIDATES", (scratch,))
    return undo


def test_the_audit_finds_the_relocated_archive_and_reports_complete(monkeypatch, tmp_path):
    scratch = build_archive(tmp_path, {".project-local/gone": "bytes"})
    undo = wire(monkeypatch, tmp_path, scratch)
    assert undo.archive_root() == scratch
    assert undo.main() == 0


def test_a_recorded_stale_path_does_not_hide_the_archived_copy(monkeypatch, tmp_path):
    """The shipped manifest records the pre-relocation path; the entry is still found."""
    scratch = build_archive(tmp_path, {".project-local/gone": "bytes", "temp/loose.txt": "other"})
    undo = wire(monkeypatch, tmp_path, scratch)
    manifest = json.loads((scratch / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["moved"]:
        assert not Path(entry["scratch_path"]).is_absolute(), entry
        assert undo.archived_copy(scratch, entry).exists(), entry


def test_restore_puts_the_bytes_back(monkeypatch, tmp_path):
    scratch = build_archive(tmp_path, {".project-local/gone": "bytes", "temp/loose.txt": "other"})
    undo = wire(monkeypatch, tmp_path, scratch)
    assert undo.restore() == 0
    assert (tmp_path / ".project-local" / "gone").read_text(encoding="utf-8") == "bytes"
    assert (tmp_path / "temp" / "loose.txt").read_text(encoding="utf-8") == "other"


def test_a_missing_archived_copy_fails_instead_of_reporting_success(monkeypatch, tmp_path, capsys):
    scratch = build_archive(tmp_path, {".project-local/gone": "bytes"})
    # Remove the archived copy: this is the case that used to exit 0 having restored nothing.
    (scratch / "project-local" / "gone").unlink()
    undo = wire(monkeypatch, tmp_path, scratch)
    assert undo.main() == 1
    assert "MISSING" in capsys.readouterr().out
    assert undo.restore() == 1
    out = capsys.readouterr().out
    assert "incomplete" in out and "1 missing" in out


def test_an_absent_archive_is_a_named_failure(monkeypatch, tmp_path):
    undo = load_undo()
    monkeypatch.setattr(undo, "REPO", tmp_path)
    monkeypatch.setattr(undo, "SCRATCH_CANDIDATES", (tmp_path / "nowhere",))
    try:
        undo.archive_root()
    except SystemExit as exit_code:
        assert "no layout archive found" in str(exit_code)
    else:
        raise AssertionError("an archive that does not exist must not be returned as if it did")


def test_permission_denied_restore_preserves_the_only_copy(monkeypatch, tmp_path):
    scratch = build_archive(tmp_path, {".project-local/gone": "unique evidence"})
    undo = wire(monkeypatch, tmp_path, scratch)
    def deny(source, target):
        raise PermissionError("locked")
    monkeypatch.setattr(undo.os, "rename", deny)
    assert undo.restore() == 1
    assert (scratch / "project-local/gone").read_text(encoding="utf-8") == "unique evidence"
    assert not (tmp_path / ".project-local/gone").exists()


def load_realign():
    path = REPO / "scripts/runtime/realign_dev_layout.py"
    spec = importlib.util.spec_from_file_location("realign_for_restore_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_incomplete_measurement_cannot_become_a_move_plan(monkeypatch, tmp_path):
    import pytest
    realign = load_realign()
    monkeypatch.setattr(realign.storage_report, 'measure', lambda repo: {
        'measurement_status': 'PARTIAL', 'dev_strays': ['.project-local/only-copy'],
        'out_of_layout': []})
    monkeypatch.setattr(realign, 'referenced_exactly', lambda *args: pytest.fail('incomplete plan searched references'))
    with pytest.raises(RuntimeError, match='incomplete ownership'):
        realign.plan_moves(tmp_path, tmp_path / '.project-local/legacy-scratch-20990101')


def test_private_assets_inside_a_stray_directory_refuse_migration(monkeypatch, tmp_path):
    import pytest
    realign = load_realign()
    private = tmp_path / '.project-local/stray/.codex'
    private.mkdir(parents=True)
    monkeypatch.setattr(realign.storage_report, 'measure', lambda repo: {
        'measurement_status': 'PASS', 'dev_strays': ['.project-local/stray'], 'out_of_layout': []})
    with pytest.raises(RuntimeError, match='candidate'):
        realign.plan_moves(tmp_path, tmp_path / '.project-local/legacy-scratch-20990101')
    assert private.exists()


def test_nested_sensitive_file_refuses_whole_directory_migration(monkeypatch, tmp_path):
    import pytest
    realign=load_realign()
    secret=tmp_path/'.project-local/stray/nested/.env.local'
    secret.parent.mkdir(parents=True)
    secret.write_bytes(b'fixture-only')
    monkeypatch.setattr(realign.storage_report,'measure',lambda repo:{
        'measurement_status':'PASS','dev_strays':['.project-local/stray'],'out_of_layout':[]})
    with pytest.raises(RuntimeError,match='candidate'):
        realign.plan_moves(tmp_path,tmp_path/'.project-local/legacy-scratch-20990101')
    assert secret.exists()


def test_linked_scratch_is_refused_before_any_write(monkeypatch, tmp_path):
    import os
    import subprocess
    import pytest
    if os.name != 'nt':
        pytest.skip('Windows junction regression')
    realign = load_realign()
    outside = tmp_path / 'outside'
    outside.mkdir()
    repo = tmp_path / 'repo'
    (repo / '.project-local').mkdir(parents=True)
    scratch = repo / '.project-local/legacy-scratch-20990101'
    result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(scratch), str(outside)],capture_output=True)
    assert result.returncode == 0
    monkeypatch.setattr(sys, 'argv', ['realign', '--repo', str(repo), '--stamp', '20990101'])
    monkeypatch.setattr(realign, 'plan_moves', lambda *args: pytest.fail('linked scratch reached planner'))
    assert realign.main() == 1
    assert list(outside.iterdir()) == []


def test_failed_second_move_keeps_first_move_recoverable(monkeypatch, tmp_path):
    realign = load_realign()
    first, second = tmp_path / 'first', tmp_path / 'second'
    first.write_text('first evidence', encoding='utf-8')
    second.write_text('second evidence', encoding='utf-8')
    scratch = tmp_path / '.project-local/legacy-scratch-20990101'
    monkeypatch.setattr(sys, 'argv', ['realign', '--repo', str(tmp_path), '--stamp', '20990101'])
    monkeypatch.setattr(realign, 'plan_moves', lambda repo, destination: (
        [(first, scratch / 'repo-root/first'), (second, scratch / 'repo-root/second')], []))
    rename = realign.os.rename
    def deny_second(source, target):
        if source == second:
            raise PermissionError('locked')
        return rename(source, target)
    monkeypatch.setattr(realign.os, 'rename', deny_second)
    assert realign.main() == 1
    receipt = json.loads((scratch / 'manifest-20990101.json').read_text(encoding='utf-8'))
    assert [entry['source'] for entry in receipt['moved']] == ['first']
    assert (scratch / 'repo-root/first').read_text(encoding='utf-8') == 'first evidence'
    assert second.read_text(encoding='utf-8') == 'second evidence'
    assert not (scratch / 'repo-root/second').exists()


def test_registered_private_clone_is_filtered_before_filesystem_probe(monkeypatch, tmp_path):
    from types import SimpleNamespace
    realign = load_realign()
    allowed = tmp_path / '.project-local/worktrees/known'
    allowed.mkdir(parents=True)
    private = tmp_path / '.ui-task-tree/private'
    def command(argv, **kwargs):
        if 'rev-parse' in argv:
            return SimpleNamespace(stdout=str(tmp_path / '.git'))
        return SimpleNamespace(stdout=f'worktree {allowed}\nworktree {private}\n', returncode=0)
    monkeypatch.setattr(realign.subprocess, 'run', command)
    is_dir = Path.is_dir
    def probe(path):
        assert '.ui-task-tree' not in path.parts, 'private clone was probed'
        return is_dir(path)
    monkeypatch.setattr(Path, 'is_dir', probe)
    assert realign.worktree_roots(tmp_path) == [tmp_path, allowed]
    assert realign.referenced_exactly('.project-local/unique-evidence', tmp_path), (
        'excluded private checkout must leave reference status unknown and protect assets')


def test_new_dated_manifest_restores_with_explicit_owner(monkeypatch, tmp_path):
    scratch = build_archive(tmp_path, {'.project-local/gone': 'preserved'})
    new = scratch.with_name('legacy-scratch-20990101')
    scratch.rename(new)
    (new / 'manifest.json').rename(new / 'manifest-20990101.json')
    undo = load_undo()
    monkeypatch.setattr(sys, 'argv', ['undo', '--repo', str(tmp_path), '--stamp', '20990101', '--restore'])
    assert undo.cli() == 0
    assert (tmp_path / '.project-local/gone').read_text(encoding='utf-8') == 'preserved'


def test_manifest_path_traversal_cannot_restore_outside_owner(monkeypatch, tmp_path):
    import pytest
    scratch = build_archive(tmp_path, {'.project-local/gone': 'preserved'})
    undo = wire(monkeypatch, tmp_path, scratch)
    manifest = json.loads((scratch / 'manifest.json').read_text(encoding='utf-8'))
    manifest['moved'][0]['source'] = '../escaped'
    (scratch / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ValueError, match='traversing'):
        undo.restore()
    assert (scratch / 'project-local/gone').read_text(encoding='utf-8') == 'preserved'
    assert not (tmp_path.parent / 'escaped').exists()


def test_reparse_root_is_refused_before_reading_an_empty_manifest(monkeypatch, tmp_path):
    from types import SimpleNamespace
    undo = load_undo()
    scratch = build_archive(tmp_path, {})
    monkeypatch.setattr(sys, 'argv', ['undo', '--repo', str(tmp_path), '--restore'])
    lstat = Path.lstat
    def linked(path):
        return SimpleNamespace(st_file_attributes=0x400, st_mode=0) if path == tmp_path else lstat(path)
    monkeypatch.setattr(Path, 'lstat', linked)
    read_text = Path.read_text
    def no_manifest(path, *args, **kwargs):
        assert path != scratch / 'manifest.json', 'manifest was read before checking the owner'
        return read_text(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'read_text', no_manifest)
    assert undo.cli() == 1
