"""R11: an independent unseen-example measurement of the machine loop.

What this measures, and what it refuses to claim:

* **unseen means unseen.** Every held-out document and query is authored here and then
  checked against the whole tracked tree: if any distinctive token of the example already
  appears in a tracked file, the probe refuses to run and says so. An example that is
  already in the repository is not an unseen example.
* **retrieval is measured, learning is not.** The receipt reports how many held-out
  queries found their expected document, and how many returned an unrelated one. It does
  not report accuracy, because a retrieval hit is a retrieval hit; there is no trained
  weight anywhere in this loop, and the receipt carries that as an explicit UNMEASURED
  field rather than a zero.
* **the correction is measured as a change of behaviour.** One item is corrected by a
  human `modified` review, and the same query is asked again: the superseded revision must
  leave the active results while its successor appears, and a *new* held-out query about
  the corrected content is asked for the first time.

The corpus is deliberately small and closed-form: five documents, one expected document
per query. A bigger corpus would measure the search engine; this measures the loop.
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# Whole alphanumeric tokens, the same unit the Core's FTS5 index compares.
_TOKENS = re.compile(r"[a-z0-9]+")

TOKEN = "e" * 64
SESSION = "f" * 32

# Held-out corpus: authored here, never used by a test or a fixture elsewhere.
DOCUMENTS = {
    "holdout/aurora.md": (
        "The auroral oval widens during a substorm. The observed expansion was "
        "3.5 degrees within eleven minutes. "
    ),
    "holdout/basalt.md": (
        "The basalt sample from the drill core was dated to 12.4 million years. "
        "The potassium argon method was used. "
    ),
    "holdout/reef.md": (
        "Coral cover on the transect fell to 18 percent after the bleaching event. "
        "The survey was repeated four times. "
    ),
    "holdout/glacier.md": (
        "The glacier terminus retreated 640 metres in a single melt season. "
        "The stakes were measured weekly. "
    ),
    "holdout/soil.md": (
        "Soil moisture at the ridge site measured 0.27 cubic metres per cubic metre. "
        "The probes were installed at three depths. "
    ),
}

# One closed-form query per held-out document, plus the token that must be unique to it.
QUERIES = [
    ("auroral oval expansion degrees", "3.5 degrees", "holdout/aurora.md"),
    ("basalt drill core dating", "12.4 million years", "holdout/basalt.md"),
    ("coral cover bleaching transect", "18 percent", "holdout/reef.md"),
    ("glacier terminus retreat distance", "640 metres", "holdout/glacier.md"),
    ("ridge site soil moisture", "0.27 cubic metres", "holdout/soil.md"),
]

CORRECTION_QUERY = ("glacier terminus revised retreat", "705 metres", "holdout/glacier.md")


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core = _load("core_client_unseen", REPO / "shared" / "core_client.py")


def tracked_text() -> str:
    """Every tracked file's text, so an example can be proven unseen."""
    listing = subprocess.run(["git", "ls-files", "-z"], cwd=str(REPO), capture_output=True)
    paths = [item for item in listing.stdout.decode("utf-8", "replace").split("\x00") if item]
    chunks: list[str] = []
    for relative in paths:
        target = REPO / relative
        with contextlib.suppress(OSError, UnicodeDecodeError):
            chunks.append(target.read_text(encoding="utf-8", errors="strict"))
    return "\n".join(chunks)


def unseen_problems(corpus: str) -> list[str]:
    """Tokens that must not already exist in the repository, checked, not assumed."""
    problems: list[str] = []
    for _, token, _ in QUERIES + [CORRECTION_QUERY]:
        if token in corpus:
            problems.append(f"the held-out token {token!r} already appears in a tracked file")
    for name, body in DOCUMENTS.items():
        distinctive = body.split(".")[0]
        if distinctive in corpus:
            problems.append(f"the held-out document {name!r} is already in the repository")
    return problems


def terms_present(query: str, body: str) -> dict:
    """Which query terms occur in the document as whole tokens.

    The Core's search is an FTS5 ``MATCH``, which compares tokens, not substrings: a document
    that says "retreated" does not hold the term "retreat". Comparing tokens here keeps the
    diagnosis aligned with the search it is explaining.
    """
    document_tokens = set(_TOKENS.findall(body.lower()))
    return {word: word in document_tokens for word in _TOKENS.findall(query.lower())}


def head_is_prefix_of(heads: list[str], body: str) -> bool:
    """Whether the expected document came back.

    The Core returns ``substr(body,1,60)`` as the head
    (``crates/archeaxis-domain/src/search.rs``), and the response carries no source name,
    so the document is identified by a returned head being a prefix of its body.
    """
    return any(head and body.startswith(head) for head in heads)


def score(results: list[tuple[str, str, list[str]]]) -> dict:
    """Per-query outcome for (query, document_name, returned_heads).

    Misses carry the literal presence of each query term, so a reader can see whether the
    search missed the document or the query was written with words the document does not use.
    """
    hits, misses = 0, []
    for query, name, heads in results:
        body = DOCUMENTS[name]
        if head_is_prefix_of(heads, body):
            hits += 1
        else:
            misses.append(
                {
                    "query": query,
                    "expected_document": name,
                    "returned_heads": heads[:3],
                    "query_terms_present_in_the_document": terms_present(query, body),
                }
            )
    return {
        "queries": len(results),
        "hits": hits,
        "misses": misses,
        "hit_rate": round(hits / len(results), 3) if results else None,
        "hit_rate_meaning": "retrieval on a five-document corpus, not a quality or accuracy figure",
        "measured_by": "a returned head being a prefix of the expected document's body",
        "terms_compared_by": "whole tokens, mirroring the FTS5 index the search runs against",
    }


def search_heads(base: str, query: str, launch: str) -> list[str]:
    """The heads a query returns, from the Core's own search endpoint."""
    status, body = core.call(base, "GET", core.search_path(query, active_only=True), launch)
    if status != 200 or not isinstance(body, dict):
        return []
    heads: list[str] = []
    for item in body.get("items") or []:
        heads.append(str(item.get("head") or ""))
    return heads


def unexplained_misses(block: dict) -> list[dict]:
    """Misses the document's own tokens do not account for: every query term occurs in it."""
    return [
        miss
        for miss in block["misses"]
        if all(miss["query_terms_present_in_the_document"].values())
    ]


def main() -> int:
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")
    binary = REPO / ".project-local" / "build" / "cargo" / "debug" / "archeaxis-api.exe"
    if not binary.is_file():
        print(json.dumps({"ok": False, "blocked": "core binary not built", "path": str(binary)}))
        return 2

    receipt: dict = {"corpus": sorted(DOCUMENTS), "queries": len(QUERIES)}
    problems = unseen_problems(tracked_text())
    receipt["unseen_check"] = {"problems": problems, "passed": not problems}
    if problems:
        receipt["ok"] = False
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 4

    run_root = REPO / ".project-local" / "runs" / "r11-unseen"
    run_root.mkdir(parents=True, exist_ok=True)
    db = run_root / f"evaluation-{int(time.time())}.sqlite"
    child = subprocess.Popen(
        [str(binary), str(db), "0"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        cwd=str(REPO),
    )
    try:
        child.stdin.write(json.dumps({"launch_token": TOKEN, "session_id": SESSION}) + "\n")
        child.stdin.flush()
        child.stdin.close()  # the Core reads its claim to EOF
        deadline = time.time() + 20
        base = ""
        while time.time() < deadline:
            line = child.stdout.readline()
            if "127.0.0.1:" in line:
                port = line.split("127.0.0.1:", 1)[1].split()[0].strip()
                base = f"http://127.0.0.1:{port}"
                break
        if not base:
            receipt.update({"ok": False, "reason": "the Core never reported readiness"})
            print(json.dumps(receipt, ensure_ascii=False, indent=2))
            return 3

        # import the held-out documents, then let a human accept one item per document
        items: dict[str, str] = {}
        for name, body in DOCUMENTS.items():
            status, imported = core.call(base, "POST", "/api/v1/imports", TOKEN, core.import_request(name, body.encode("utf-8")))
            if status not in (200, 201, 202):
                receipt.update({"ok": False, "reason": f"import failed for {name}", "status": status, "body": str(imported)[:200]})
                print(json.dumps(receipt, ensure_ascii=False, indent=2))
                return 5
            status, created = core.call(
                base,
                "POST",
                "/api/v1/knowledge-items",
                TOKEN,
                {"knowledge_type": "OBSERVATION", "body": body, "created_by": "machine"},
            )
            if status not in (200, 201) or not isinstance(created, dict):
                receipt.update({"ok": False, "reason": f"candidate creation failed for {name}", "status": status})
                print(json.dumps(receipt, ensure_ascii=False, indent=2))
                return 5
            item_id = created.get("knowledge_id") or created.get("id")
            status, reviewed = core.call(
                base,
                "POST",
                f"/api/v1/knowledge-items/{item_id}/review-decisions",
                TOKEN,
                core.review_request("accepted", "owner", note="human acceptance of a machine candidate"),
            )
            if status not in (200, 201):
                receipt.update(
                    {"ok": False, "reason": f"human acceptance failed for {name}", "status": status, "body": str(reviewed)[:200]}
                )
                print(json.dumps(receipt, ensure_ascii=False, indent=2))
                return 5
            items[name] = item_id

        def frozen() -> list[tuple[str, str, list[str]]]:
            """The frozen evaluation set: one authored query per held-out document."""
            return [(query, name, search_heads(base, query, TOKEN)) for query, _, name in QUERIES]

        # Diagnostic, deliberately outside the frozen set: every term of this query occurs in
        # the original document, and the measured value falls inside the first 60 characters
        # the head is made of, so the same query must change its head when the value changes.
        diagnostic_query = "glacier terminus retreated metres"

        first = frozen()
        receipt["baseline"] = score(first)
        receipt["diagnostic_before_correction"] = {
            "query": diagnostic_query,
            "returned_heads": search_heads(base, diagnostic_query, TOKEN),
            "note": "not part of the frozen evaluation set; it attributes a cause",
        }

        # a human corrects one item; the successor must appear and the old one must go
        corrected_body = DOCUMENTS["holdout/glacier.md"].replace("640 metres", "705 metres")
        status, corrected = core.call(
            base,
            "POST",
            f"/api/v1/knowledge-items/{items['holdout/glacier.md']}/review-decisions",
            TOKEN,
            core.review_request("modified", "owner", new_body=corrected_body, note="human correction of a measurement"),
        )
        receipt["correction"] = {"status": status, "new_knowledge_id": (corrected or {}).get("knowledge_id") if isinstance(corrected, dict) else None}
        if isinstance(corrected, dict) and corrected.get("knowledge_id"):
            core.call(
                base,
                "POST",
                f"/api/v1/knowledge-items/{corrected['knowledge_id']}/review-decisions",
                TOKEN,
                core.review_request("accepted", "owner", note="accepting the corrected revision"),
            )

        after = frozen()
        receipt["after_correction"] = score(after)

        new_query, new_token, expected = CORRECTION_QUERY
        superseded_token = "640 metres"
        new_heads = search_heads(base, new_query, TOKEN)
        diagnostic_heads = search_heads(base, diagnostic_query, TOKEN)
        receipt["new_query_after_correction"] = {
            "query": new_query,
            "expected_document": expected,
            "expected_token": new_token,
            "returned_heads": new_heads,
            "document_returned": head_is_prefix_of(new_heads, DOCUMENTS[expected]),
            "query_terms_present_in_the_document": terms_present(new_query, DOCUMENTS[expected]),
            "note": "asked for the first time after the correction, so it cannot have been fitted to it",
        }
        receipt["diagnostic_after_correction"] = {
            "query": diagnostic_query,
            "returned_heads": diagnostic_heads,
            "carries_corrected_value": any(new_token in head for head in diagnostic_heads),
            "carries_superseded_value": any(superseded_token in head for head in diagnostic_heads),
            "note": "the same query as before the correction, so the two heads are comparable",
        }

        unexplained = unexplained_misses(receipt["baseline"]) + unexplained_misses(receipt["after_correction"])
        receipt["retrieval"] = {
            "documents_asked": receipt["baseline"]["queries"],
            "documents_returned_in_baseline": receipt["baseline"]["hits"],
            "documents_returned_after_correction": receipt["after_correction"]["hits"],
            "misses_explained_by_query_vocabulary": len(receipt["baseline"]["misses"]) - len(unexplained_misses(receipt["baseline"])),
            "unexplained_misses": unexplained,
        }
        receipt["finding"] = {
            "observed": (
                "a query term the document does not carry as a token removes that document from the "
                "result set, so an inflected query returns nothing for a document the corpus does hold"
            ),
            "evidence": "query_terms_present_in_the_document in each miss, against the same document's head",
            "source": "crates/archeaxis-domain/src/search.rs uses knowledge_fts MATCH with no stemming, and returns substr(body,1,60) as the head",
            "severity": "a usability behaviour of the current search, not a crash or a data loss",
            "deciding_authority": "the owner decides whether literal-term retrieval is acceptable, an audit decides what it means",
        }
        receipt["unmeasured"] = {
            "weights_trained": "UNMEASURED: nothing in this loop trains a weight; a receipt is a measurement fact",
            "description_quality": "UNMEASURED: quality needs a human truth pair, and no model was called here",
            "corpus_scale": "UNMEASURED: five documents and five queries measure this loop, not the search engine at scale",
            "ranking_quality": "UNMEASURED: this probe asks whether a document comes back at all, never where it ranks",
        }
        receipt["probe_complete"] = True
        correction_reflected = (
            receipt["diagnostic_after_correction"]["carries_corrected_value"]
            and not receipt["diagnostic_after_correction"]["carries_superseded_value"]
        )
        receipt["ok"] = bool(correction_reflected and not unexplained)
        receipt["verdict"] = (
            "PROBE_COMPLETE: the loop ran end to end and its numbers are recorded; this probe signs no PASS for retrieval"
        )
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 0 if receipt["ok"] else 6
    finally:
        child.kill()
        child.wait()


if __name__ == "__main__":
    raise SystemExit(main())
