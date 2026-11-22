import base64

import pytest

from scripts.ingest import obsidian_sync as sync
from scripts.ingest import obsidian_vault as vault


@pytest.mark.parametrize("racing_writer", [False, True], ids=["resume-staged-write", "retain-intervening-edit"])
def test_resume_after_the_original_was_moved_aside(tmp_path, racing_writer):
    directory = tmp_path / ".aaos-sync"
    directory.mkdir()
    expected, wanted, intervening = b"original", b"from AAOS", b"edited in Vault"
    (directory / "previous").write_bytes(intervening if racing_writer else expected)
    (directory / "next").write_bytes(wanted)
    sync.write_json(directory / "pending.json", {"path": "Note.md", "previous": vault.digest(expected),
                                                 "next": vault.digest(wanted)})
    captured = []

    def capture(method, path, body):
        assert (method, path) == ("POST", "/api/v1/imports")
        data = base64.b64decode(body["content_base64"], validate=True)
        captured.append(data)
        return {"source_id": "captured", "sha256": vault.digest(data)}

    result = sync.finish_write(capture, tmp_path, directory, "batch")
    assert result["installed"] == (not racing_writer)
    assert (tmp_path / "Note.md").read_bytes() == (intervening if racing_writer else wanted)
    assert captured == ([intervening] if racing_writer else [])
    assert list(directory.iterdir()) == []


def test_two_external_edits_preserve_the_intervening_cited_heading():
    def block(kind, text, **attrs):
        return {"type": kind, "attrs": attrs, "content": [{"type": "text", "text": text}]}

    heading = block("heading", "历史引文", level=2, block_id="cited")
    editor = {"type": "doc", "attrs": {"title": "资料"}, "content": [
        block("paragraph", "first"), heading, block("paragraph", "last"),
    ]}
    change = "replacement\n\n## 历史引文\n\nnew ending"
    source = {"source_id": "latest", "sha256": vault.digest(change.encode())}
    updated = sync.updated_editor(editor, change, source)
    assert updated["content"][1] == heading
    assert updated["attrs"] == {"title": "资料", "obsidian_sync_source": source}
    assert vault._markdown(updated) == change


def test_move_with_an_identical_surviving_note_keeps_the_existing_bindings():
    digest = vault.digest(b"same text")
    files = {"First.md": {"common": digest, "doc": "first"}, "Second.md": {"common": digest, "doc": "second"}}
    actions = []
    sync.bind_moves(files, {"Second.md": digest, "New.md": digest}, set(), actions)
    assert not actions
    assert {p: row["doc"] for p, row in files.items()} == {"First.md": "first", "Second.md": "second"}
