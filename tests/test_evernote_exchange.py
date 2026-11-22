from defusedxml import ElementTree

from scripts.ingest.evernote_exchange import append_paragraphs, enml_xml, paragraph


def test_annotating_preserves_source_markup_entities_and_cdata():
    original = "<en-note><div style='color:blue'>A&nbsp;B <![CDATA[keep &nbsp;]]></div></en-note>\n"
    updated = append_paragraphs(original, [paragraph("a", "复核 A&B <原件>")])
    assert updated == original.replace("</en-note>", "<div>复核 A&amp;B &lt;原件&gt;</div></en-note>")
    root = ElementTree.fromstring(enml_xml(updated))
    assert root[0].text == "A\u00a0B keep &nbsp;"
    assert root[1].text == "复核 A&B <原件>"


def test_appending_to_empty_enml_preserves_the_note_root_and_line_breaks():
    block = {"type": "paragraph", "content": [
        {"type": "text", "text": "before"}, {"type": "hardBreak"}, {"type": "text", "text": "after"}]}
    body = ElementTree.fromstring(append_paragraphs("<en-note/>", [block]))
    assert body.tag == "en-note"
    assert body[0].text == "before"
    assert body[0][0].tag == "br" and body[0][0].tail == "after"
