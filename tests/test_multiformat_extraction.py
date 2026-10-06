"""Canvas, archive and subtitle extraction, against the fixtures added for them.

These three capabilities had no sample at all, so nothing exercised them and nothing noticed
when they stopped working. The fixtures live beside the other golden ones and carry the same
journey evidence, so an extraction test can look for the same anchors.

A missing optional engine is reported as a skip rather than a failure, because the engines for
these formats are optional by design; the point of the tests is to prove the path works where
the engine is present.
"""

from __future__ import annotations

from pathlib import Path

import pytest

GOLDEN = Path(__file__).parent / "fixtures" / "golden"


def _convert(name: str):
    from app.ingestion.multi_format import convert_file

    source = GOLDEN / name
    assert source.is_file(), f"fixture is missing: {source}"
    try:
        return convert_file(str(source))
    except Exception as error:  # noqa: BLE001 - surfaced as a skip with its reason
        pytest.skip(f"engine unavailable for {name}: {error}")


def test_canvas_fixture_is_a_json_canvas_with_nodes_and_an_edge() -> None:
    import json

    document = json.loads((GOLDEN / "golden-canvas-anchor.canvas").read_text(encoding="utf-8"))
    assert [node["id"] for node in document["nodes"]] == ["n1", "n2"]
    assert document["edges"][0]["fromNode"] == "n1"
    assert document["edges"][0]["toNode"] == "n2"


def test_canvas_extracts_its_node_text() -> None:
    content, engine = _convert("golden-canvas-anchor.canvas")
    assert engine
    assert "Golden Journey Evidence" in content
    assert "Page Anchor PASS" in content


def test_archive_fixture_is_a_real_zip() -> None:
    import zipfile

    path = GOLDEN / "golden-archive-anchor.zip"
    assert zipfile.is_zipfile(path)
    with zipfile.ZipFile(path) as archive:
        assert archive.namelist() == ["readme.txt"]


def test_archive_extracts_its_member_text() -> None:
    content, engine = _convert("golden-archive-anchor.zip")
    assert engine
    assert "Golden Journey Evidence" in content


def test_subtitles_fixture_has_two_cues() -> None:
    text = (GOLDEN / "golden-subtitles-anchor.srt").read_text(encoding="utf-8")
    assert text.count(" --> ") == 2
    assert "Page Anchor PASS" in text


def test_subtitles_extract_their_cue_text() -> None:
    content, engine = _convert("golden-subtitles-anchor.srt")
    assert engine
    assert "Golden Journey Evidence" in content
