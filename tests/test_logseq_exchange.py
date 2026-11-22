"""Regression cases for Logseq's native block offsets and graph-local identity."""

import codecs
from copy import deepcopy

from scripts.ingest.logseq_exchange import relation_target
from scripts.ingest.logseq_outline import references, split_outline, write_outline


BLOCK = "60ab6f5b-4bdc-4ef0-a0f8-6cad9dcad2b2"


def test_utf8_positions_preserve_bom_drawer_hierarchy_and_crlf_on_edit():
    lines = ["- 资料\r\n", f"  id:: {BLOCK}\r\n", "\t- 子块\r\n"]
    raw = codecs.BOM_UTF8 + "".join(lines).encode()
    nodes = [["Heading", {"level": 1}], ["Property_Drawer", [["id", BLOCK, []]]], ["Heading", {"level": 2}]]
    ast, pos = [], 0
    for node, line in zip(nodes, lines):
        end = pos + len(line.encode())
        ast.append([node, {"start_pos": pos, "end_pos": end}])
        pos = end
    before, _, _ = split_outline(raw, ast, "Markdown")
    assert before[0]["attrs"]["block_id"] == BLOCK and before[1]["attrs"]["parent"] == BLOCK
    edited = deepcopy(before)
    edited[0]["content"][0]["text"] = edited[0]["content"][0]["text"].replace("资料", "已修改")
    assert write_outline(raw, before, edited) == raw.replace("资料".encode(), "已修改".encode())


def test_native_examples_do_not_bind_and_ambiguous_ids_are_unresolved():
    tree = [["Code", "((" + BLOCK + "))"], ["Macro", {"name": "embed", "arguments": ["((" + BLOCK + "))"]}]]
    assert list(references(tree)) == [("Block_ref", BLOCK, "((" + BLOCK + "))", True)]
    found, reason = relation_target("pages/a.md", "Block_ref", BLOCK, {}, {BLOCK: [("a", "1"), ("b", "2")]}, {})
    assert found is None and reason == "ambiguous target"
