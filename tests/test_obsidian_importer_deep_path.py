"""The Obsidian importer must walk, read and hash a Vault that sits deep in the run tree.

Windows refuses a plain create above total length ~252 and a plain open above ~260, and - the part
that hides the defect - `rglob` and `Path.is_file()` answer *nothing at all* for such a path instead
of raising. An importer that is not verbatim-path aware therefore reports an empty Vault, and "no
notes" is indistinguishable from a Vault that genuinely has none.
"""

from __future__ import annotations

import json
import pytest
from hashlib import sha256
from pathlib import Path

from shared.obsidian_importer import _attachment_facts, _build_target_index, import_file, scan_vault
from shared.paths import native_path

VERBATIM = "\\\\?\\"
TARGET_DIRECTORY = 248
PNG = b"\x89PNG\r\n\x1a\n deep bytes"


def _mkdir(path: Path) -> Path:
    Path(native_path(path)).mkdir(parents=True, exist_ok=True)
    return path


DEEP_FOLDER = "50_领域知识/deep_ffffffffffff"
NOTE_REL = f"{DEEP_FOLDER}/note.md"
ASSET_REL = f"{DEEP_FOLDER}/attach/shot.png"


def _vault(tmp_path: Path) -> Path:
    """A Vault root a plain call can still create, whose notes and assets plainly cannot be opened."""
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

    # One level deeper than a plain directory enumeration can open: a plain walk of the Vault
    # yields nothing below this point, which is exactly the failure that reads as "empty Vault".
    folder = _mkdir(_mkdir(node / DEEP_FOLDER.split("/")[0]) / DEEP_FOLDER.split("/")[1])
    attach = _mkdir(folder / "attach")
    note = folder / "note.md"
    Path(native_path(note)).write_text("---\ntitle: 深路径笔记\n---\n\n正文见 ![图](attach/shot.png)\n", encoding="utf-8")
    asset = attach / "shot.png"
    Path(native_path(asset)).write_bytes(PNG)
    assert len(str(folder)) > 260, "the notes must live past the plain-enumeration limit"
    assert len(str(asset)) > 260, "and the asset past the plain-open limit"
    assert not note.exists(), "the defect's precondition: a plain name reports nothing here"
    return node


def test_scan_vault_finds_the_notes_at_depth(tmp_path: Path) -> None:
    root = _vault(tmp_path)
    inventory = scan_vault(str(root))
    recorded = [info["path"] for group in inventory.values() if isinstance(group, list) for info in group]
    assert inventory["total_files"] >= 1, inventory
    assert any("note.md" in path for path in recorded), recorded
    assert VERBATIM not in json.dumps(inventory, ensure_ascii=False), (
        "the enumeration prefix leaked into stored paths")


def test_a_deep_note_reads_instead_of_answering_file_not_found(tmp_path: Path) -> None:
    root = _vault(tmp_path)
    result = import_file(str(root), NOTE_REL, dry_run=True)
    assert "error" not in result, result
    assert result["status"] == "dry_run"
    assert VERBATIM not in json.dumps(result, ensure_ascii=False)


def test_attachment_bytes_are_hashed_at_depth(tmp_path: Path) -> None:
    root = _vault(tmp_path)
    facts = _attachment_facts(str(root), [{"target": ASSET_REL}])
    assert len(facts) == 1, "a deep attachment must not vanish from the facts"
    assert facts[0]["sha256"] == sha256(PNG).hexdigest()
    assert facts[0]["path"] == ASSET_REL


def test_the_wikilink_index_is_built_from_the_deep_vault(tmp_path: Path) -> None:
    root = _vault(tmp_path)
    index = _build_target_index(str(root))
    assert any("note" in key for key in index), sorted(index)
    assert VERBATIM not in json.dumps(sorted(index), ensure_ascii=False)
