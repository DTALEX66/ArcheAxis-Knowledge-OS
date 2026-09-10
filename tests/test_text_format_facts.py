"""R15/F01: the text route reports the structure it can really derive.

The projection stays canonical - text plus line anchors, coverage over lines -
and the format facts for markdown, CSV/TSV, JSON and XML ride in
`loss_receipt.params["format"]`. Two rules make this trustworthy rather than
decorative:

  * the facts must be true for a real sample (headings and links counted where they
    are, a ragged CSV reported as ragged, JSON depth and keys measured);
  * a document that does not parse is still projected as text and the fact says
    `parsed: false` with the reason, so nothing is guessed and nothing is silent.

The last test drives the transport's own route so the declared media type is proven
to reach the worker, not just the function.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
WORKER = REPO / "services" / "python-workers" / "document" / "worker_text.py"
TRANSPORT = REPO / "services" / "python-workers" / "transport" / "text_ndjson.py"

MARKDOWN = """---
tags: [roundtrip]
---

# Index

Read [[atomic]] and [the canvas](vault.canvas).
The diagram is embedded: ![[diagram.png]]

## Why this matters

```python
# not a heading: # still inside a fence
```

- one item
1. numbered item
"""

CSV = """name,qty,note
bolt,4,ok
nut,7,"has, comma"
washer,2
screw,9,extra,field
"""

JSON_DOC = '{"a": {"b": [1, 2, {"c": 3}]}, "d": true}'
XML_DOC = "<vault><note id='1'><title>t</title></note><canvas/></vault>"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


worker = _load("worker_text_facts", WORKER)
transport = _load("text_ndjson_facts", TRANSPORT)


def _facts(tmp_path: Path, text: str, media_type: str, suffix: str) -> tuple[dict, dict]:
    sample = tmp_path / f"sample{suffix}"
    sample.write_text(text, encoding="utf-8", newline="\n")
    result = worker.extract(str(sample), media_type)
    return result, result["loss_receipt"]["params"]["format"]


def test_the_projection_contract_is_unchanged_for_every_format(tmp_path):
    for media, suffix, body in [
        ("text/plain", ".txt", "just text\nsecond line\n"),
        ("text/markdown", ".md", MARKDOWN),
        ("text/csv", ".csv", CSV),
        ("text/tab-separated-values", ".tsv", "a\tb\n1\t2\n"),
        ("application/json", ".json", JSON_DOC),
        ("application/xml", ".xml", XML_DOC),
    ]:
        result, _ = _facts(tmp_path, body, media, suffix)
        assert result["engine"] == worker.ENGINE, media
        assert result["text"] == body, media
        structure = result["structure"]
        assert structure and structure[0]["kind"] == "line", media
        assert structure[-1]["char_end"] == len(result["text"]), media
        receipt = result["loss_receipt"]
        assert receipt["covered"] == receipt["total"] == len(structure), media
        assert receipt["coverage"] == 1.0, media
        assert receipt["params"]["media_type"] == media, media


def test_markdown_facts_match_the_document(tmp_path):
    _, facts = _facts(tmp_path, MARKDOWN, "text/markdown", ".md")
    assert facts["format"] == "markdown" and facts["parsed"] is True
    assert facts["frontmatter"] is True
    assert [heading["level"] for heading in facts["headings"]] == [1, 2]
    assert [heading["line"] for heading in facts["headings"]] == [5, 10]
    assert facts["headings"][1]["text"] == "Why this matters"
    # the "# still inside a fence" line is not a heading
    assert all("still inside a fence" not in heading["text"] for heading in facts["headings"])
    assert facts["heading_count"] == 2
    assert facts["wiki_link_count"] == 1
    assert facts["embed_count"] == 1
    assert facts["markdown_link_count"] == 1
    assert facts["code_fence_count"] == 2
    assert facts["list_item_count"] == 2


def test_markdown_reports_an_unclosed_fence_instead_of_guessing(tmp_path):
    _, facts = _facts(tmp_path, "# Title\n\n```\ncode\n", "text/markdown", ".md")
    assert facts["code_fence_count"] == 1
    assert "unclosed" in facts["note"]


def test_csv_facts_count_rows_columns_and_raggedness(tmp_path):
    _, facts = _facts(tmp_path, CSV, "text/csv", ".csv")
    assert facts["format"] == "csv" and facts["delimiter"] == ","
    assert facts["row_count"] == 5
    assert facts["column_count"] == 4
    assert facts["header"] == ["name", "qty", "note"]
    # row 4 is short and row 5 is long: both are reported, neither is squared off
    assert facts["ragged_rows"] == 2
    assert "ragged" in facts["note"]


def test_tsv_is_read_with_a_tab_delimiter(tmp_path):
    _, facts = _facts(tmp_path, "a\tb\n1\t2\n", "text/tab-separated-values", ".tsv")
    assert facts["format"] == "tsv" and facts["delimiter"] == "\t"
    assert facts["row_count"] == 2 and facts["column_count"] == 2
    assert facts["ragged_rows"] == 0


def test_json_facts_measure_depth_and_keys(tmp_path):
    _, facts = _facts(tmp_path, JSON_DOC, "application/json", ".json")
    assert facts["parsed"] is True and facts["top_level"] == "dict"
    # dict -> dict -> list -> dict: four nested containers, the outermost counting as one
    assert facts["max_depth"] == 4
    assert facts["depth_unit"].startswith("nested containers")
    assert facts["key_count"] == 4  # a, b, c, d
    assert facts["item_count"] == 2


def test_unparsable_json_is_projected_and_reported(tmp_path):
    broken = '{"a": 1,\n"b": }\n'
    result, facts = _facts(tmp_path, broken, "application/json", ".json")
    assert facts["parsed"] is False
    assert "line 2" in facts["error"]
    assert "not guessed at" in facts["note"]
    # the text is still projected and the loss is named
    assert result["text"] == broken
    assert result["structure"][-1]["char_end"] == len(broken)
    assert any("json structure could not be derived" in loss for loss in result["loss_receipt"]["losses"])


def test_xml_facts_report_root_elements_and_depth(tmp_path):
    _, facts = _facts(tmp_path, XML_DOC, "application/xml", ".xml")
    assert facts["parsed"] is True and facts["root"] == "vault"
    assert facts["element_count"] == 4
    assert facts["child_count"] == 2
    # vault -> note -> title: three nested containers
    assert facts["max_depth"] == 3

    _, broken = _facts(tmp_path, "<vault><note></vault>", "text/xml", ".xml")
    assert broken["parsed"] is False and broken["error"]


def test_plain_text_claims_no_format_structure(tmp_path):
    _, facts = _facts(tmp_path, "plain\n", "text/plain", ".txt")
    assert facts["format"] == "plain" and facts["parsed"] is True
    assert "no format-specific structure" in facts["note"]


def test_the_transport_hands_the_declared_media_type_to_the_text_worker(tmp_path):
    """The route must pass what the Core declared, not leave the worker guessing."""
    assert transport.ROUTES["text.extract"].get("media_type_arg") is True
    source = tmp_path / "input"
    source.write_text(CSV, encoding="utf-8", newline="\n")
    route = transport.ROUTES["text.extract"]
    result = transport._run_route(route, source, "text/csv")
    facts = result["loss_receipt"]["params"]["format"]
    assert facts["format"] == "csv" and facts["row_count"] == 5
    assert facts["ragged_rows"] == 2

    # and a route that does not declare the argument is not passed one
    assert "media_type_arg" not in transport.ROUTES["pdf.extract"]
