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
# The revised value is taken from the probe, never quoted here: a held-out value written into a
# tracked test is no longer held out, which is what round 96's audit caught.
CORRECTED = GLACIER.replace(probe.QUERIES[3][1], probe.CORRECTION_QUERY[1])


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
    before = probe.QUERIES[3][1]
    after = probe.CORRECTION_QUERY[1]
    assert before in GLACIER[:60] and before not in CORRECTED[:60]
    assert after in CORRECTED[:60] and after not in GLACIER[:60]


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


def test_the_corpus_is_still_unseen():
    """The property the corpus exists for, enforced by the suite and not only by the probe.

    Round 96 found that a ledger row and a handoff section quoting two held-out values had
    destroyed it. Reading every tracked file (the probe's own source excluded, since that is
    where the corpus is authored) is what makes this a real check.
    """
    assert probe.unseen_problems(probe.tracked_text()) == []


def test_every_held_out_value_is_actually_in_its_document():
    """A rotation that misses one document would turn a query into a guaranteed miss.

    Only the five evaluation queries: the correction token is the *revised* value, so it must
    NOT be in the original document - that is what
    `test_the_correction_really_replaces_the_value_it_corrects` asserts.
    """
    for query, token, name in probe.QUERIES:
        assert token in probe.DOCUMENTS[name], f"{query!r} expects {token!r} in {name}"


def test_the_correction_really_replaces_the_value_it_corrects():
    """The round-96 no-op: hard-coded copies survived a rotation, so the correction changed nothing."""
    superseded, revised = probe.QUERIES[3][1], probe.CORRECTION_QUERY[1]
    assert superseded != revised
    assert revised not in probe.DOCUMENTS["holdout/glacier.md"]
    assert superseded in probe.DOCUMENTS["holdout/glacier.md"]
