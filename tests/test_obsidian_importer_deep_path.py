"""The Obsidian importer must walk, read and hash a Vault that sits deep in the run tree.

Windows refuses a plain create above total length ~252 and a plain open above ~260, and - the part
that hides the defect - `rglob`, `Path.exists()` and `Path.is_file()` answer *nothing at all* for
such a path instead of raising. An importer that is not verbatim-path aware therefore reports an
empty Vault, and "no notes" is indistinguishable from a Vault that genuinely has none.

A CI runner may have long paths enabled, where the plain name works and the failure cannot be
observed. So these tests assert the seam itself - the importer enumerated and opened the verbatim
form - on every host, and assert the returned facts too.
"""

from __future__ import annotations

import json
import os
from hashlib import sha256
from pathlib import Path

import pytest

from shared.obsidian_importer import _attachment_facts, _build_target_index, import_file, scan_vault
from shared.paths import native_path

VERBATIM = "\\\\?\\"
TARGET_DIRECTORY = 248
PNG = b"\x89PNG\r\n\x1a\n deep bytes"
DEEP_FOLDER = "50_领域知识/deep_ffffffffffff"
NOTE_REL = f"{DEEP_FOLDER}/note.md"
ASSET_REL = f"{DEEP_FOLDER}/attach/shot.png"


def _mkdir(path: Path) -> Path:
    Path(native_path(path)).mkdir(parents=True, exist_ok=True)
    return path


def _spy(monkeypatch) -> list[str]:
    """Record every path the importer passed to an enumeration or an existence check."""
    seen: list[str] = []
    for name in ("rglob", "glob", "is_file", "exists"):
        original = getattr(Path, name)
        takes_pattern = name in ("rglob", "glob")

        def spy(self, *args, _original=original, _seen=seen, _pattern=takes_pattern, **kwargs):
            _seen.append(str(self))
            return _original(self, *args, **kwargs) if _pattern else _original(self)

        monkeypatch.setattr(Path, name, spy)
    return seen


def _vault(tmp_path: Path) -> Path:
    """A Vault whose notes and assets sit past the plain-open limit of a normal Windows host."""
    node = tmp_path / "vault"
    if len(str(node)) > TARGET_DIRECTORY:
        pytest.skip(f"the temporary base is already {len(str(node))} characters deep")
    _mkdir(node)
    while len(str(node / ("d" * 24))) <= TARGET_DIRECTORY - 26:
        node = _mkdir(node / ("d" * 24))
    remainder = TARGET_DIRECTORY - len(str(node)) - 1
    if remainder > 1:
        node = _mkdir(node / ("c" * (remainder - 1)))
    assert len(str(node)) <= 251, "the Vault root itself must be plain-creatable"

    folder = _mkdir(_mkdir(node / DEEP_FOLDER.split("/")[0]) / DEEP_FOLDER.split("/")[1])
    attach = _mkdir(folder / "attach")
    Path(native_path(folder / "note.md")).write_text(
        "---\ntitle: 深路径笔记\n---\n\n正文见 ![图](attach/shot.png)\n", encoding="utf-8")
    Path(native_path(attach / "shot.png")).write_bytes(PNG)
    assert len(str(folder)) > 260 and len(str(attach / "shot.png")) > 260, (
        "the notes must live past the limit the seam exists for")
    return node


def _walked_verbatim(seen: list[str]) -> bool:
    """True wherever the verbatim form is not a thing this platform needs.

    `native_path` is a no-op off Windows by design, so on a Linux runner the ordinary root IS the
    correct root; asserting a prefix there would test the mechanism's spelling, not its purpose.
    """
    return True if os.name != "nt" else any(entry.startswith(VERBATIM) for entry in seen)


def test_scan_vault_enumerates_verbatim_and_returns_the_deep_notes(tmp_path: Path, monkeypatch) -> None:
    root = _vault(tmp_path)
    seen = _spy(monkeypatch)
    inventory = scan_vault(str(root))
    recorded = [info["path"] for group in inventory.values() if isinstance(group, list) for info in group]
    assert inventory["total_files"] >= 1, inventory
    assert any("note.md" in path for path in recorded), recorded
    assert _walked_verbatim(seen), "the importer walked the ordinary root: at depth that answers 'no notes'"
    assert VERBATIM not in json.dumps(inventory, ensure_ascii=False), (
        "the enumeration prefix leaked into stored paths")


def test_a_deep_note_is_read_through_the_verbatim_name(tmp_path: Path, monkeypatch) -> None:
    root = _vault(tmp_path)
    seen = _spy(monkeypatch)
    result = import_file(str(root), NOTE_REL, dry_run=True)
    assert "error" not in result, result
    assert result["status"] == "dry_run"
    assert _walked_verbatim(seen), "the existence check ran on an ordinary name"
    assert VERBATIM not in json.dumps(result, ensure_ascii=False)


def test_attachment_bytes_are_hashed_through_the_verbatim_name(tmp_path: Path, monkeypatch) -> None:
    root = _vault(tmp_path)
    seen = _spy(monkeypatch)
    facts = _attachment_facts(str(root), [{"target": ASSET_REL}])
    assert len(facts) == 1, "a deep attachment must not vanish from the facts"
    assert facts[0]["sha256"] == sha256(PNG).hexdigest()
    assert facts[0]["path"] == ASSET_REL
    assert _walked_verbatim(seen), "is_file() on an ordinary name answers False at depth, silently"


def test_the_wikilink_index_is_built_from_the_deep_vault(tmp_path: Path, monkeypatch) -> None:
    root = _vault(tmp_path)
    seen = _spy(monkeypatch)
    index = _build_target_index(str(root))
    assert any("note" in key for key in index), sorted(index)
    assert _walked_verbatim(seen)
    assert VERBATIM not in json.dumps(sorted(index), ensure_ascii=False)
