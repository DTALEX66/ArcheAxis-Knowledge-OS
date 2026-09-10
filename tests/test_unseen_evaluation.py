"""R11: the unseen evaluation must measure the Core, not itself.

The probe scores retrieval on a closed corpus. Its first two runs reported a hit rate of
zero because it looked for a source name the search response does not carry, and then
because it looked for a fact token beyond the sixty characters the Core returns as a head.
Both were measurement bugs that read as product findings. These tests pin the two
properties that keep the measurement honest: a document is identified by the head prefix
the Core actually returns, and a query term is compared as a token, because the search runs
against an FTS5 index.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROBE = REPO / "scripts" / "probes" / "r11_unseen_evaluation.py"
SEARCH = REPO / "crates" / "archeaxis-domain" / "src" / "search.rs"


def _load():
    spec = importlib.util.spec_from_file_location("unseen_evaluation_under_test", PROBE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


probe = _load()

GLACIER = probe.DOCUMENTS["holdout/glacier.md"]
CORRECTED = GLACIER.replace("640 metres", "705 metres")


def test_query_terms_are_compared_as_tokens_not_substrings():
    """The search is an FTS5 MATCH: "retreat" is not a token of "retreated"."""
    presence = probe.terms_present("glacier terminus retreat distance", GLACIER)
    assert presence["retreat"] is False
    assert probe.terms_present("retreated", GLACIER)["retreated"] is True


def test_a_document_is_identified_by_the_head_the_core_returns():
    """The response carries no source name, so a hit is the returned head prefix."""
    heads = [GLACIER[:60]]
    assert probe.head_is_prefix_of(heads, GLACIER) is True
    assert probe.head_is_prefix_of(heads, CORRECTED) is False


def test_the_correction_diagnostic_can_tell_the_two_revisions_apart():
    """The measured value must fall inside the sixty characters the head is made of.

    If it did not, the same query would return the same head before and after a human
    correction and the probe could not observe the correction reaching the index.
    """
    assert "640 metres" in GLACIER[:60]
    assert "705 metres" in CORRECTED[:60]


def test_the_head_contract_the_probe_depends_on_is_still_in_the_source():
    """A pointer test: if the Core stops returning a sixty-character head, revisit the probe."""
    source = SEARCH.read_text(encoding="utf-8")
    assert "substr(body,1,60)" in source


def test_score_counts_a_miss_and_records_why():
    block = probe.score([("glacier terminus retreat distance", "holdout/glacier.md", [])])
    assert block["hits"] == 0
    assert block["hit_rate"] == 0.0
    miss = block["misses"][0]
    assert miss["expected_document"] == "holdout/glacier.md"
    assert miss["query_terms_present_in_the_document"]["distance"] is False


def test_score_counts_a_hit_when_the_expected_document_comes_back():
    block = probe.score([("glacier terminus retreated metres", "holdout/glacier.md", [GLACIER[:60]])])
    assert block["hits"] == 1
    assert block["misses"] == []


def test_a_vocabulary_miss_is_not_reported_as_unexplained():
    block = probe.score([("glacier terminus retreat distance", "holdout/glacier.md", [])])
    assert probe.unexplained_misses(block) == []


def test_a_miss_with_every_token_present_is_unexplained():
    """The point of the diagnosis: it must be able to fail."""
    block = {
        "misses": [
            {
                "query": "glacier terminus",
                "query_terms_present_in_the_document": {"glacier": True, "terminus": True},
            }
        ]
    }
    assert probe.unexplained_misses(block) == block["misses"]


def test_the_frozen_queries_name_documents_the_corpus_holds():
    names = {name for _, _, name in probe.QUERIES} | {probe.CORRECTION_QUERY[2]}
    assert names <= set(probe.DOCUMENTS)
    queries = [query for query, _, _ in probe.QUERIES]
    assert len(queries) == len(set(queries))
    assert len(probe.QUERIES) == len(probe.DOCUMENTS), "one query per held-out document"


def test_the_probe_signs_no_pass_for_retrieval():
    """A measurement records numbers; only an audit turns them into a verdict."""
    source = PROBE.read_text(encoding="utf-8")
    assert "signs no PASS for retrieval" in source
