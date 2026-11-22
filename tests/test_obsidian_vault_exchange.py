import codecs

from scripts.ingest.obsidian_vault import _edited_note


def test_edit_preserves_vault_bom_crlf_and_the_editors_bold_mark():
    raw = codecs.BOM_UTF8 + "标题\r\n\r\n原文\r\n".encode()
    original = {
        "source_id": "source", "source_revision": "rev", "version": 1, "content_sha256": "first",
        "editor_json": {"type": "doc", "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": raw.decode("utf-8-sig")}]},
        ]},
    }
    latest = {
        **original, "version": 2, "content_sha256": "second",
        "editor_json": {"type": "doc", "content": [
            *original["editor_json"]["content"],
            {"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": "批注"}]},
            {"type": "paragraph", "content": [
                {"type": "text", "text": "问题", "marks": [{"type": "bold"}]},
                {"type": "text", "text": "<&>", "marks": [{"type": "bold"}]},
                {"type": "hardBreak"}, {"type": "text", "text": "下一行"},
            ]},
        ]},
    }
    member = {"relative_path": "研究/笔记.md", "source_id": "source", "source_revision": "rev"}
    def read(_method, route):
        return original if route.endswith("/versions/1") else latest

    data, binding = _edited_note(read, "note", member, raw)
    assert data == raw + "\r\n\r\n### 批注\r\n\r\n<strong>问题&lt;&amp;&gt;</strong>  \r\n下一行".encode()
    assert binding == {"document_id": "note", "version": 2, "content_sha256": "second"}


def test_metadata_only_revision_keeps_the_original_mixed_line_endings():
    raw = b"---\r\ntags: [music]\n---\r\n"
    paragraph = {"type": "paragraph", "content": [{"type": "text", "text": raw.decode()}]}
    member = {"relative_path": "Music.md", "source_id": "source", "source_revision": "rev"}
    def read(_method, route):
        original = route.endswith("/versions/1")
        return {**member, "version": 1 if original else 2, "content_sha256": "doc",
                "editor_json": {"type": "doc", "attrs": {} if original else {"extra": "a reference"},
                                "content": [paragraph]}}

    data, binding = _edited_note(read, "note", member, raw)
    assert data == raw
    assert binding["version"] == 2
