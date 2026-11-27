import base64
import json
import re
from copy import deepcopy
from types import SimpleNamespace

import pytest

from scripts.ingest import siyuan_exchange as sy

ROOT = "20200101230000-aaaaaaa"
BLOCK = "20200101230001-bbbbbbb"
MEDIA = "20200101230002-ccccccc"


def setup_note():
    tree = {"Type": "NodeDocument", "ID": ROOT, "Spec": "3",
            "Properties": {"title": "指南", "updated": "20200101230000"},
            "Children": [{"Type": "NodeParagraph", "ID": BLOCK, "Properties": {"updated": "20200101230001"},
                          "Children": [{"Type": "NodeText", "Data": "星环"}]},
                         {"Type": "NodeParagraph", "ID": MEDIA, "Children": [{"Type": "NodeImage", "Children": [
                             {"Type": "NodeLinkDest", "Data": "assets/x.png"}]}]}],
            "Future": {"unknown": ["星环", {}, 123], "Data": "星环"}}
    raw = b"\xef\xbb\xbf" + json.dumps(tree, indent=2).replace("\n", "\r\n").replace(" 123\r", " 1.2300e2\r").encode()
    revision = sy.digest(raw)
    node = {"type": "paragraph", "attrs": {"block_id": BLOCK}, "content": [{"type": "text", "text": "星环"}]}
    doc = {"document_id": "doc", "source_id": "source", "source_revision": revision, "version": 1,
           "editor_json": {"type": "doc", "content": [node]}}
    return raw, doc


def test_edit_existing_document_and_export_without_changing_other_bytes(tmp_path):
    raw, first = setup_note()
    current = deepcopy(first)
    current["editor_json"]["attrs"] = {"archeaxis_relations": {"kept": True}}

    def call(method, path, body=None):
        if method == "PUT":
            assert body["expected_version"] == current["version"]
            current.update(version=current["version"] + 1, editor_json=deepcopy(body["editor_json"]))
            return deepcopy(current)
        if path.endswith("/original"):
            return {"content_base64": base64.b64encode(raw), "sha256": sy.digest(raw)}
        return deepcopy(first if path.endswith("/versions/1") else current)

    args = SimpleNamespace(action="export", document="doc", output=tmp_path / (ROOT + ".sy"))
    sy.exchange(call, args)
    assert args.output.read_bytes() == raw
    with pytest.raises(FileExistsError):
        sy.exchange(call, args)
    args.action, args.block_id, args.text = "block", BLOCK, '修改"新"'
    assert sy.exchange(call, args)["version"] == 2
    assert sy.exchange(call, args)["version"] == 2
    assert current["editor_json"]["attrs"] == {"archeaxis_relations": {"kept": True}}
    (tmp_path / "new").mkdir()
    args.action, args.output = "export", tmp_path / "new" / (ROOT + ".sy")
    assert sy.exchange(call, args)["edited_blocks"] == [BLOCK]
    old = json.dumps("星环").encode()
    exported = args.output.read_bytes()
    expected = raw[3:].replace(old, json.dumps(args.text, ensure_ascii=False).encode(), 1)
    assert re.sub(rb'"updated": "\d{14}"', b'UPDATED', exported) == re.sub(rb'"updated": "\d{14}"', b'UPDATED', expected)
    assert b'1.2300e2' in exported
    assert json.loads(exported)["Properties"]["updated"] > "20200101230000"
    assert sy.native_blocks(args.output.read_bytes())[1][BLOCK]["Data"] == args.text


def test_refuses_structural_edits_and_unknown_native_blocks():
    raw, doc = setup_note()
    tree, leaves = sy.native_blocks(raw)
    assert MEDIA not in leaves
    for change in ("marks", "id", "extra"):
        edited = deepcopy(doc)
        node = edited["editor_json"]["content"][0]
        if change == "marks":
            node["content"][0]["marks"] = [{"type": "bold"}]
        elif change == "id":
            node["attrs"]["block_id"] = MEDIA
        else:
            edited["editor_json"]["content"].append(node)
        with pytest.raises(ValueError):
            sy.mapped_blocks(doc, edited, leaves)
    tree["Children"].append(tree["Children"][0])
    with pytest.raises(ValueError, match="duplicate"):
        sy.native_blocks(json.dumps(tree).encode())
    with pytest.raises(ValueError, match="duplicate JSON"):
        sy.native_blocks(b'{"Type":"NodeDocument","Type":"NodeParagraph"}')


def test_save_from_finished_job_keeps_native_ids_and_source_pin():
    raw, doc = setup_note()
    facts = {"format": "siyuan", "parsed": True, "spec": "3", "document_id": ROOT, "blocks": [
        {"id": ROOT, "node_type": "NodeDocument", "char_start": 0, "char_end": 2},
        {"id": BLOCK, "node_type": "NodeParagraph", "char_start": 3, "char_end": 5}]}
    receipt = json.dumps({"params": {"format": facts}})

    def call(method, path, body=None):
        if path.endswith("/jobs/j"):
            return {"state": "succeeded", "input_ref": "source"}
        if path.endswith("/transform"):
            return {"source_id": "source", "raw_sha256": sy.digest(raw), "content": "指南\n星环"}
        if path.endswith("/loss_report"):
            return {"content": receipt, "metadata": {"sha256": sy.digest(receipt.encode())}}
        if path.endswith("/original"):
            return {"content_base64": base64.b64encode(raw), "sha256": sy.digest(raw)}
        assert (method, path) == ("POST", sy.DOCUMENTS)
        assert body["source_revision"] == sy.digest(raw)
        assert body["editor_json"]["content"][1] == doc["editor_json"]["content"][0]
        return doc

    assert sy.save_conversion(call, "j")["document_id"] == "doc"


def test_native_heading_scopes_include_only_enclosing_sections_and_containers():
    def heading(ident, level):
        return {"Type": "NodeHeading", "ID": ident, "HeadingLevel": level}

    tree = {"Type": "NodeDocument", "ID": "root", "Children": [
        heading("outer", 1), heading("old", 2), heading("current", 2),
        {"Type": "NodeList", "ID": "list", "Children": [
            {"Type": "NodeListItem", "ID": "item", "Children": [
                heading("nested", 3), {"Type": "NodeParagraph", "ID": "edit"}]}]},
        heading("next", 1), {"Type": "NodeParagraph", "ID": "later"}]}
    assert {b["ID"] for b in sy.affected_blocks(tree, {"edit"})} == {
        "root", "outer", "current", "list", "item", "nested", "edit"}


def test_attachment_only_snapshot_and_missing_historical_timestamp(tmp_path):
    raw, doc = setup_note()
    tree = json.loads(raw)
    tree["Children"].pop(0)
    image_raw = json.dumps(tree).encode()
    doc["source_revision"] = sy.digest(image_raw)
    doc["editor_json"]["content"][0]["attrs"]["block_id"] = MEDIA

    def call(method, path, body=None):
        if path.endswith("/original"):
            return {"content_base64": base64.b64encode(image_raw), "sha256": sy.digest(image_raw)}
        return deepcopy(doc)

    args = SimpleNamespace(action="blocks", document="doc", output=tmp_path / (ROOT + ".sy"))
    assert sy.exchange(call, args)["blocks"] == []
    args.action = "export"
    assert sy.exchange(call, args)["edited_blocks"] == []
    assert args.output.read_bytes() == image_raw
    tree, leaves = sy.native_blocks(raw)
    del tree["Properties"]["updated"]
    with pytest.raises(ValueError, match="updated timestamp"):
        sy.timestamp_changes(tree, {BLOCK})


@pytest.mark.parametrize("issue", [None, "unbound", "asset_digest", "wrong_batch", "unsafe_name", "receipt_changed", "missing_loss_summary"])
def test_export_batch_note_and_verified_attachment_or_publish_nothing(tmp_path, issue):
    raw, first = setup_note()
    path = "assets/x.png"
    png = b"attachment fixture"
    asset_sha = sy.digest(png)
    note_name = ("../" if issue == "unsafe_name" else "parent/") + ROOT + ".sy"
    note = {"source_id": "source", "source_revision": first["source_revision"], "job_id": "job",
            "relative_path": note_name, "ordinal": 0}
    asset = {"source_id": "attachment", "source_revision": asset_sha,
             "relative_path": path, "ordinal": 1, "byte_length": len(png)}
    facts = {"format": "siyuan", "parsed": True, "document_id": ROOT, "omitted_subtrees": 0,
             "attachment_paths": [{"source_block_id": MEDIA, "relative_path": path}] * 2}
    if issue == "missing_loss_summary":
        del facts["omitted_subtrees"]
    loss = json.dumps({"params": {"format": facts}})
    loss_sha = sy.digest(loss.encode())
    original_requests = []

    def call(method, route):
        assert method == "GET"
        if route.startswith(sy.DOCUMENTS):
            doc = deepcopy(first)
            if not route.endswith("/versions/1"):
                doc["editor_json"]["content"][0]["content"][0]["text"] = "更新"
                doc["version"] = 2
            return doc
        if route.endswith("/original"):
            original_requests.append(route)
            data = raw if "/source/" in route else png
            return {"content_base64": base64.b64encode(data), "sha256": "changed" if data == png and issue == "asset_digest" else sy.digest(data)}
        if route.endswith("limit=200"):
            return {"complete": True, "workspace_id": "ws", "members": [asset] if issue == "wrong_batch" else [note, asset],
                    "next_ordinal": None}
        if route.endswith("/loss_report"):
            return {"content": loss, "metadata": {"sha256": loss_sha}}
        block = route.split("/")[-2]
        entry = {"relative_path": path, "status": "resolved_reference", "target_ordinal": 1,
                 "target": {"kind": "source", "source_id": asset["source_id"], "sha256": asset_sha}}
        if issue == "unbound":
            entry.update(status="unbound", reason="scoped_asset_path_unverified")
        return {"native_source_block": {"source_id": "source", "sha256": note["source_revision"], "block_id": block},
                "conversion": {"job_id": "job", "loss_sha256": "changed" if issue == "receipt_changed" else loss_sha},
                "assets": [entry, entry] if block == MEDIA else []}

    args = SimpleNamespace(action="export-folder", document="doc", batch="batch", output=tmp_path / "out")
    if issue:
        with pytest.raises(KeyError if issue == "missing_loss_summary" else ValueError):
            sy.exchange(call, args)
        assert list(tmp_path.iterdir()) == []
        return
    result = sy.exchange(call, args)
    assert result["version"] == 2 and result["edited_blocks"] == [BLOCK]
    assert sy.native_blocks((args.output / note_name).read_bytes())[1][BLOCK]["Data"] == "更新"
    assert (args.output / path).read_bytes() == png
    assert result["assets"] == [{"path": path, "bytes": len(png), "sha256": asset_sha}]
    assert len(original_requests) == 2
    with pytest.raises(FileExistsError):
        sy.exchange(call, args)
