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
