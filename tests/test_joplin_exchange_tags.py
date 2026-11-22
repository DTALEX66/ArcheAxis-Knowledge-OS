import base64
import io
import json
import tarfile

import pytest

from scripts.ingest import joplin_exchange as jex


def test_shared_tag_edits_preserve_unselected_records_and_attachment(tmp_path, monkeypatch):
    first, second, tag, link1, link2, dangling = (digit * 32 for digit in "123456")
    records = {key + ".md": key.encode() for key in (first, second, tag, link1, link2, dangling)}
    records["resources/" + "a" * 32 + ".png"] = b"original resource bytes"
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name, content in records.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
    raw = buffer.getvalue()
    revision = jex._digest(raw)
    transform = {"source_id": "source", "raw_sha256": revision, "content": "#inline"}
    notes = [{"id": key, "title": key, "member": key + ".md", "tag_ids": [tag],
              "body_start": 0, "body_end": 7} for key in (first, second)]
    edges = [{"member": key + ".md", "note_id": n, "tag_id": t}
             for key, n, t in ((link1, first, tag), (link2, second, tag), (dangling, first, "unknown"))]
    graph = {"notes": notes, "tags": [{"id": tag, "title": "Review"}], "note_tags": edges}
    monkeypatch.setattr(jex, "read_job", lambda *_: (transform, {"params": {"structure": {"joplin": graph}}}))
    docs = {}
    for note in notes:
        props = jex._note_properties(note, {tag: "Review"})
        docs[note["id"]] = {"source_id": "source", "source_revision": revision, "title": note["title"],
                            "version": 2, "content_sha256": "document hash", "properties": props,
                            "editor_json": jex._note_editor(note, {tag: "Review"}, "#inline")}

    def read(_, path):
        if path.endswith("/original"):
            return {"content_base64": base64.b64encode(raw).decode()}
        return docs[path.rsplit("/", 1)[1]]

    def edit(key, labels):
        text_node = docs[key]["editor_json"]["content"][0]["content"][0]
        text_node["text"] = text_node["text"].split("\ntags:")[0] + "\ntags: " + json.dumps(labels, ensure_ascii=False) + "\n---"
        docs[key]["properties"]["tags"] = labels

    edit(first, ["review"])
    same = tmp_path / "same.jex"
    assert jex.export_notes(read, "job", [first], same)["changed_members"] == []
    assert same.read_bytes() == raw

    edit(first, ["资料 Review"])
    edit(second, ["Review", "资料 Review"])
    out = tmp_path / "shared.jex"
    result = jex.export_notes(read, "job", [first, second], out)
    assert result["changed_note_timestamp"] is None
    assert result["removed_members"] == [link1 + ".md"]
    assert len(result["added_members"]) == 3
    with tarfile.open(out) as archive:
        readback = {m.name: archive.extractfile(m).read() for m in archive}
    for name in records.keys() - set(result["removed_members"]):
        assert readback[name] == records[name]
    assert link1 + ".md" not in readback
    added = {name[:-3]: readback[name].decode() for name in result["added_members"]}
    new_tag, = (key for key, text in added.items() if text.startswith("资料 Review\n\n"))
    assert added[new_tag].endswith("type_: 5")
    assert all(text.endswith("type_: 6") for key, text in added.items() if key != new_tag)
    assert all(f"tag_id: {new_tag}\n" in text for key, text in added.items() if key != new_tag)
    assert {line for text in added.values() for line in text.splitlines() if line.startswith("note_id:")} == {
        f"note_id: {first}", f"note_id: {second}"}

    docs[second]["properties"]["joplin_id"] = first
    with pytest.raises(ValueError, match="only native tag relationships"):
        jex.export_notes(read, "job", [first, second], tmp_path / "invalid.jex")
    assert not (tmp_path / "invalid.jex").exists()
