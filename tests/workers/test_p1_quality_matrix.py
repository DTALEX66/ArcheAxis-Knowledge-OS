"""DP-NF-03 P1 document format quality matrix through the real text worker path.

Every case drives the *real* ``worker_text.py`` in a real subprocess and the real
``text_ndjson.py`` transport over a real staging directory, and reads back the whole
receipt: source hash (transport-verified digest), transform hash, engine,
engine_version, decoder fallback, unsupported state and the loss fields
(``losses``/``loss_note``/``covered``/``total``/``coverage``).

What DP-F01 already covers in this same baseline
(``tests/workers/test_f01_real_quality.py`` + ``tests/fixtures/f01-quality/``) and is
therefore NOT repeated here:

* ``controlled.md`` - 17-line UTF-8-BOM markdown: BOM decode loss, 2 headings, wiki
  link/embed/markdown link/````` ``` ````` fence/list counts, transform hash and the
  transport byte binding.
* ``capped-lines.md`` - 5001 LF lines *with* a BOM -> 5000-anchor cap loss.
* ``fallback-gbk.txt`` - GBK decode fallback on an LF ``text/plain`` file.
* ``ragged.csv`` - a single short row: ``ragged_rows`` 1 with ``losses == []`` pinned.
* ``unsupported.unknown-ext`` - ``application/x-unknown`` refused by the transport.
* the fixture manifest itself.

This matrix is deliberately different, not larger:

1. lossless LF markdown with no BOM -> the transform is a byte identity
   (source sha == transform sha), a ``~~~`` fence pair, a ``#`` heading inside that
   fence that must not count, and a ``#notaheading`` line without a space;
2. declared-media-type precedence: markdown-looking bytes declared ``text/plain`` stay
   ``plain`` (nothing is sniffed from the name), and CSV bytes declared
   ``text/markdown`` stay ``markdown`` with no csv facts;
3. ragged CSV *field-count* accounting: one short AND one long row
   (``ragged_rows`` 2, ``column_count`` 5 > header width 4) with the loss list still
   empty, i.e. the raggedness is a fact and never a fabricated loss;
4. a 33-column header, where the worker reports only the first 32 header names - the
   one *silent* truncation in the format facts (see the RED note on that test);
5. GBK fallback *plus* CRLF inside a ``text/markdown`` document, so the markdown facts
   are derived from the decoded text and the CRLF survives in the anchors;
6. a UTF-8-BOM document whose payload is not UTF-8: the documented fallback chain is
   not reached, so the test pins the fail-closed invariant instead of a fake success;
7. caps: a 5001-line CRLF plain file (one cap loss, CRLF counted as one line) and a
   9000-character single line with ONE anchor (the anchor cap counts lines, not bytes);
8. the transport's own input byte cap versus a >1 MiB single line that is accepted;
9. an empty file through the transport: empty transform hash, zero-line coverage;
10. unsupported state: a real media type owned by another capability is refused with a
    named code rather than silently routed.

Nothing here is mocked and no expectation is copied back from the worker's own output:
every hash, byte length, character range and count is hand-measured from the authored
fixture bytes (``tests/fixtures/p1-quality/manifest.yaml``). The fixture directory
carries its own ``.gitattributes`` (``* -text``) because the repository root declares
``* text=auto eol=lf``, which would rewrite the CRLF fixtures on commit and change the
hashes these tests assert.

Boundary: this is a controlled synthetic matrix. It is NOT real-corpus qualification,
it does NOT close any P1 format, and it makes NO claim about common-format real quality.
The Rust read-back lane (``crates/archeaxis-api/tests/f01_quality_roundtrip.rs``) is
DP-F01's and is out of this card's scope.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "p1-quality"
WORKER = ROOT / "services/python-workers/document/worker_text.py"
TRANSPORT = ROOT / "services/python-workers/transport/text_ndjson.py"

ENGINE = "python-worker-text"
ENGINE_VERSION = "0.1.0"
# Restated, not imported: the transport's declared staging byte cap is part of the
# boundary this matrix measures.
MAX_INPUT_BYTES = 16 * 1024 * 1024

# -- hand-measured fixture facts (authored bytes, never worker output) ---------

CLEAN_MARKDOWN_SHA = "d1cffdcd99038a5bede95502efaf069df1f1724a1f774ac1e7b5f646fef39a19"
CLEAN_MARKDOWN_BYTES = 131
CLEAN_MARKDOWN_CHARS = 127
CLEAN_MARKDOWN_RANGES = [
    (0, 8), (8, 9), (9, 45), (45, 46), (46, 54), (54, 86),
    (86, 90), (90, 91), (91, 104), (104, 105), (105, 116), (116, 127),
]
CLEAN_MARKDOWN_HEADINGS = [{"level": 1, "line": 1, "text": "星环 P1"}]

DISGUISED_SHA = "513ecf128bed612f17d2518e279ef9c436f7b96471f150195d019f03cf05ccd4"
DISGUISED_BYTES = 79
DISGUISED_RANGES = [(0, 36), (36, 61), (61, 79)]

RAGGED_SHA = "e3d1c64ef3866d7ab75a47efe4a8a8d663a80578be8590dd44c7221d3305839c"
RAGGED_BYTES = 73
RAGGED_RANGES = [(0, 17), (17, 30), (30, 37), (37, 60), (60, 73)]
RAGGED_HEADER = ["id", "name", "note", "tag"]

WIDE_HEADER_SHA = "45fe9dd0bbfb4f29418a8c7c9606be1ffcff76b781bd5fe3e5ec22404eccccbd"
WIDE_HEADER_BYTES = 396
WIDE_HEADER_RANGES = [(0, 132), (132, 264), (264, 396)]
WIDE_HEADER_COLUMNS = 33
WIDE_HEADER_REPORTED = [f"c{index:02d}" for index in range(1, 33)]

GBK_SHA = "8b593c1ffc2e113962d12485f54b381af29c4ae029b8c2e98c762d686138e6b7"
GBK_BYTES = 24
GBK_TEXT = "# 编码回退\r\n\r\n正文行。\r\n"
GBK_TEXT_CHARS = 16
GBK_TRANSFORM_SHA = "4434cc617042d894d6bda4b2aaabfcc7cc84fb7488e70bf3528bfbfa17c26cfd"
GBK_RANGES = [(0, 8), (8, 10), (10, 16)]

BOM_NON_UTF8_SHA = "7b8e66f5da41888eb5cdd9ba9e142df708b548040f70aa7c6e417287ca4af188"
BOM_NON_UTF8_BYTES = 8

CAPPED_CRLF_SHA = "9a9af8502c625be793d85c664d7b2c728dc5052b4f60b73e059416118c6a310a"
CAPPED_CRLF_BYTES = 15003
CAPPED_CRLF_LINES = 5001
CAPPED_CRLF_ANCHORS = 5000
# "a\r\n" is one character plus a two-character CRLF terminator, so line 5000 covers
# characters 4999*3 .. 5000*3. (A first, wrong hand count assumed a one-character
# terminator and expected (9998, 10000); the worker's CRLF-preserving anchor was right.)
CAPPED_CRLF_LAST_ANCHOR = (14997, 15000)

ONE_LONG_LINE_SHA = "d9785ad494215a183ceaf55c11aeed1433227e88469f61159f2daf27e6929100"
ONE_LONG_LINE_BYTES = 9000
ONE_LONG_LINE_RANGES = [(0, 9000)]

EMPTY_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

CAP_LOSS = "line anchors capped at 5000"
GBK_LOSS = "non-UTF-8 bytes decoded as gbk (undecodable bytes reported, not silently replaced)"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical(value) -> bytes:
    """The transport's own artifact encoding, restated so it is not assumed."""
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def anchors_of(structure) -> list[tuple[int, int]]:
    return [(anchor["char_start"], anchor["char_end"]) for anchor in structure]


class P1QualityMatrix(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ["ARCHEAXIS_RUN_ROOT"])
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)

    # -- real worker process ---------------------------------------------

    def fixture_bytes(self, name: str) -> bytes:
        return (FIXTURES / name).read_bytes()

    def run_worker(self, raw: bytes, *, filename: str, media_type: str | None):
        """Run the real worker script exactly as the Core would, as a child process."""
        local = self.work / filename
        local.write_bytes(raw)
        command = [sys.executable, "-B", str(WORKER), str(local)]
        if media_type is not None:
            command.append(media_type)
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=180,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    def worker_envelope(self, raw: bytes, *, filename: str, media_type: str | None) -> dict:
        result = self.run_worker(raw, filename=filename, media_type=media_type)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "", "the worker must not write to stderr on success")
        lines = result.stdout.splitlines()
        self.assertEqual(len(lines), 1, "one envelope, no extra output")
        return json.loads(lines[0])

    def assert_envelope_shape(self, envelope: dict):
        self.assertEqual(
            set(envelope), {"engine", "engine_version", "text", "structure", "loss_receipt"}
        )
        self.assertEqual(envelope["engine"], ENGINE)
        self.assertEqual(envelope["engine_version"], ENGINE_VERSION)
        receipt = envelope["loss_receipt"]
        self.assertEqual(receipt["engine"], ENGINE)
        self.assertEqual(receipt["engine_version"], ENGINE_VERSION)
        self.assertEqual(
            set(receipt),
            {"engine", "engine_version", "params", "losses", "covered", "total", "coverage", "loss_note"},
        )
        return receipt

    # -- real transport over real staging --------------------------------

    def staging(self, raw: bytes, name: str = "staging") -> tuple[Path, str]:
        digest = hashlib.sha256(raw).hexdigest()
        staging = self.work / name
        (staging / "input").mkdir(parents=True, exist_ok=True)
        (staging / "input" / digest).write_bytes(raw)
        return staging, digest

    def request_for(self, raw: bytes, media_type: str, digest: str | None = None) -> dict:
        digest = digest or hashlib.sha256(raw).hexdigest()
        return {
            "schema": "archeaxis.worker-request/v1",
            "type": "job_request",
            "request_id": "p1-request",
            "job_id": "p1-job",
            "attempt": 1,
            "protocol_minor": 0,
            "capability": "text.extract",
            "capability_version": "1",
            "deadline_ms": 120000,
            "inputs": [{"uri": f"job://input/{digest}", "sha256": digest, "media_type": media_type}],
            "parameters": {},
        }

    def transport_execute(
        self, raw: bytes, media_type: str, *, module_name: str = "p1_transport", staging_name: str = "staging"
    ):
        transport = load_module(module_name, TRANSPORT)
        staging, digest = self.staging(raw, staging_name)
        (staging / "output").mkdir(parents=True, exist_ok=True)
        outputs, measurements, warnings = transport.execute(
            self.request_for(raw, media_type, digest), staging
        )
        payloads = {
            output["kind"]: (staging / "output" / output["sha256"]).read_bytes()
            for output in outputs
        }
        return transport, digest, staging, outputs, payloads, measurements, warnings

    def assert_transport_publishes_worker_bytes(self, envelope: dict, outputs, payloads):
        """The transport must publish exactly the worker's own bytes, hashed."""
        self.assertEqual(
            {output["kind"] for output in outputs}, {"text", "document_structure", "loss_report"}
        )
        expected = {
            "text": envelope["text"].encode("utf-8"),
            "document_structure": canonical(envelope["structure"]),
            "loss_report": canonical(envelope["loss_receipt"]),
        }
        for output in outputs:
            self.assertEqual(output["authority_effect"], "candidate_or_measurement_only")
            self.assertEqual(output["uri"], f"job://output/{output['sha256']}")
            self.assertEqual(
                output["sha256"],
                hashlib.sha256(expected[output["kind"]]).hexdigest(),
                f"{output['kind']} is not the worker's own bytes",
            )
            self.assertEqual(output["byte_length"], len(expected[output["kind"]]))
            self.assertEqual(payloads[output["kind"]], expected[output["kind"]])

    # -- 1. lossless markdown --------------------------------------------

    def test_lossless_markdown_is_a_byte_identity_transform(self):
        raw = self.fixture_bytes("clean-markdown.md")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), CLEAN_MARKDOWN_SHA)
        self.assertEqual(len(raw), CLEAN_MARKDOWN_BYTES)

        envelope = self.worker_envelope(raw, filename="clean-markdown.md", media_type="text/markdown")
        receipt = self.assert_envelope_shape(envelope)
        text = envelope["text"]

        # No BOM and no fallback: nothing was transformed, so the projected text is the
        # source byte for byte and the transform hash equals the source hash. (F01's
        # markdown always carries a BOM loss; this is the clean arm of the same pair.)
        self.assertEqual(receipt["params"]["decode"], "utf-8")
        self.assertEqual(receipt["losses"], [])
        self.assertEqual(receipt["loss_note"], "no transform applied")
        self.assertEqual(receipt["params"]["media_type"], "text/markdown")
        transform = hashlib.sha256(text.encode("utf-8")).hexdigest()
        self.assertEqual(transform, CLEAN_MARKDOWN_SHA)
        self.assertEqual(len(text), CLEAN_MARKDOWN_CHARS)
        self.assertEqual(text, raw.decode("utf-8"))

        # Anchors against hand-written character ranges, including the CR-free LF lines.
        self.assertEqual(anchors_of(envelope["structure"]), CLEAN_MARKDOWN_RANGES)
        self.assertEqual(
            [anchor["path"] for anchor in envelope["structure"]],
            [[f"line-{index}"] for index in range(1, len(CLEAN_MARKDOWN_RANGES) + 1)],
        )
        self.assertEqual(receipt["covered"], receipt["total"])
        self.assertEqual(receipt["total"], len(CLEAN_MARKDOWN_RANGES))
        self.assertAlmostEqual(receipt["coverage"], 1.0)

        # Derivable markdown facts: the "~~~" pair counts, the "#" heading inside that
        # fence and the "#notaheading" line (no space) do not.
        facts = receipt["params"]["format"]
        self.assertEqual(facts["format"], "markdown")
        self.assertIs(facts["parsed"], True)
        self.assertIs(facts["frontmatter"], False)
        self.assertEqual(facts["heading_count"], 1)
        self.assertEqual(facts["headings"], CLEAN_MARKDOWN_HEADINGS)
        self.assertEqual(facts["code_fence_count"], 2)
        self.assertEqual(facts["wiki_link_count"], 1)
        self.assertEqual(facts["markdown_link_count"], 1)
        self.assertEqual(facts["embed_count"], 0)
        self.assertEqual(facts["list_item_count"], 2)
        self.assertNotIn("note", facts, "a balanced fence pair must not report an unclosed fence")

        # Source -> transform binding through the real transport, byte for byte.
        _, digest, _, outputs, payloads, measurements, warnings = self.transport_execute(
            raw, "text/markdown"
        )
        self.assertEqual(digest, CLEAN_MARKDOWN_SHA)
        self.assertEqual(measurements, {"input_bytes": CLEAN_MARKDOWN_BYTES})
        self.assertEqual(warnings, [])
        self.assert_transport_publishes_worker_bytes(envelope, outputs, payloads)
        self.assertEqual(payloads["text"], raw)
        self.assertEqual(anchors_of(json.loads(payloads["document_structure"])), CLEAN_MARKDOWN_RANGES)

        # Negative control: the range assertion is not a mirror of the worker.
        corrupted = [
            dict(anchor, char_end=anchor["char_end"] + 1) for anchor in envelope["structure"]
        ]
        self.assertNotEqual(envelope["structure"], corrupted)

    # -- 2. declared media type decides, nothing is sniffed --------------

    def test_declared_media_type_decides_the_facts_not_the_name_or_content(self):
        raw = self.fixture_bytes("disguised-markdown.md")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), DISGUISED_SHA)
        self.assertEqual(len(raw), DISGUISED_BYTES)

        # Declared plain even though every line *looks* like markdown: the declaration wins
        # and no markdown fact is claimed. F01 only refuses an unsupported media type; it
        # never cross-declares one.
        envelope = self.worker_envelope(raw, filename="disguised-markdown.md", media_type="text/plain")
        receipt = self.assert_envelope_shape(envelope)
        facts = receipt["params"]["format"]
        self.assertEqual(facts["format"], "plain")
        self.assertIs(facts["parsed"], True)
        self.assertNotIn("heading_count", facts)
        self.assertNotIn("wiki_link_count", facts)
        self.assertNotIn("markdown_link_count", facts)
        self.assertIn("no format-specific structure", facts["note"])
        self.assertEqual(receipt["losses"], [])
        self.assertEqual(anchors_of(envelope["structure"]), DISGUISED_RANGES)
        self.assertEqual(receipt["covered"], receipt["total"])

        # The same bytes with the media type argument omitted: the worker default is
        # text/plain, so a ".md" name must not turn it into markdown either.
        defaulted = self.worker_envelope(raw, filename="disguised-markdown.md", media_type=None)
        self.assertEqual(defaulted["loss_receipt"]["params"]["media_type"], "text/plain")
        self.assertEqual(defaulted["loss_receipt"]["params"]["format"]["format"], "plain")
        self.assertEqual(defaulted["text"], envelope["text"])

        # And the transport carries the declaration through unchanged.
        _, digest, _, _, payloads, measurements, _ = self.transport_execute(raw, "text/plain")
        self.assertEqual(digest, DISGUISED_SHA)
        self.assertEqual(measurements, {"input_bytes": DISGUISED_BYTES})
        published = json.loads(payloads["loss_report"])
        self.assertEqual(published["params"]["media_type"], "text/plain")
        self.assertEqual(published["params"]["format"]["format"], "plain")

    def test_csv_bytes_declared_as_markdown_are_not_silently_upgraded(self):
        raw = self.fixture_bytes("ragged-fields.csv")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), RAGGED_SHA)

        envelope = self.worker_envelope(raw, filename="ragged-fields.csv", media_type="text/markdown")
        facts = envelope["loss_receipt"]["params"]["format"]
        # The declared type is what is measured; the bytes being CSV changes nothing.
        self.assertEqual(facts["format"], "markdown")
        self.assertIs(facts["parsed"], True)
        self.assertEqual(facts["heading_count"], 0)
        self.assertEqual(facts["headings"], [])
        for absent in ("row_count", "column_count", "ragged_rows", "header"):
            self.assertNotIn(absent, facts, "csv facts were derived from undeclared content")
        self.assertEqual(envelope["loss_receipt"]["losses"], [])

        # The same bytes declared as CSV do produce the csv facts (see the ragged test),
        # so the difference above is the declaration, not a capability gap.
        csv_envelope = self.worker_envelope(raw, filename="ragged-fields.csv", media_type="text/csv")
        self.assertEqual(csv_envelope["loss_receipt"]["params"]["format"]["row_count"], 5)

    # -- 3. ragged CSV field-count accounting ----------------------------

    def test_ragged_rows_are_counted_per_row_without_a_fabricated_loss(self):
        raw = self.fixture_bytes("ragged-fields.csv")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), RAGGED_SHA)
        self.assertEqual(len(raw), RAGGED_BYTES)

        envelope = self.worker_envelope(raw, filename="ragged-fields.csv", media_type="text/csv")
        receipt = self.assert_envelope_shape(envelope)
        # The projected text is the source bytes: raggedness is a measured shape, not a
        # transformation of the document.
        self.assertEqual(hashlib.sha256(envelope["text"].encode("utf-8")).hexdigest(), RAGGED_SHA)
        self.assertEqual(anchors_of(envelope["structure"]), RAGGED_RANGES)
        self.assertEqual(receipt["covered"], receipt["total"])
        self.assertEqual(receipt["total"], 5)
        self.assertAlmostEqual(receipt["coverage"], 1.0)

        facts = receipt["params"]["format"]
        self.assertEqual(facts["format"], "csv")
        self.assertEqual(facts["delimiter"], ",")
        self.assertEqual(facts["row_count"], 5)
        # Row widths are 4, 4, 2, 5, 4 against a 4-wide first row: two rows differ, and the
        # widest row (5 fields) is what column_count reports even though the header has 4.
        self.assertEqual(facts["ragged_rows"], 2)
        self.assertEqual(facts["column_count"], 5)
        self.assertEqual(facts["header"], RAGGED_HEADER)
        self.assertIn("ragged", facts["note"])
        self.assertIs(facts["rows_capped"], False)

        # Raggedness is a fact, never a loss: the loss list stays empty and the note does
        # not claim a transform happened. (F01's ragged.csv has one short row and equal
        # header/column width; this shape adds the long row and a wider column count.)
        self.assertEqual(receipt["losses"], [])
        self.assertEqual(receipt["loss_note"], "no transform applied")

    # -- 4. the one silent truncation in the facts -----------------------

    def test_a_header_past_the_reported_cap_is_flagged_not_silently_cut(self):
        raw = self.fixture_bytes("wide-header.csv")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), WIDE_HEADER_SHA)
        self.assertEqual(len(raw), WIDE_HEADER_BYTES)

        envelope = self.worker_envelope(raw, filename="wide-header.csv", media_type="text/csv")
        receipt = self.assert_envelope_shape(envelope)
        self.assertEqual(anchors_of(envelope["structure"]), WIDE_HEADER_RANGES)
        facts = receipt["params"]["format"]
        self.assertEqual(facts["row_count"], 3)
        self.assertEqual(facts["ragged_rows"], 0)
        self.assertEqual(facts["column_count"], WIDE_HEADER_COLUMNS)
        self.assertEqual(facts["header"], WIDE_HEADER_REPORTED)
        # The document really has 33 header fields and the reported header is 32 of them.
        self.assertEqual(len(raw.splitlines()[0].split(b",")), WIDE_HEADER_COLUMNS)
        self.assertEqual(len(facts["header"]), len(WIDE_HEADER_REPORTED))

        # RED note: before the DP-NF-03 fix the receipt carried no flag for this cut, so a
        # reader could not tell a 32-column document from a 33-column one whose header was
        # truncated -- the only cap in this worker's format facts without a `*_capped`
        # marker. The fact below is what the fix adds; the note must name it too.
        self.assertIs(facts["header_capped"], True)
        self.assertIn("header", facts["note"])
        self.assertIn(f"{len(WIDE_HEADER_REPORTED)} of {WIDE_HEADER_COLUMNS}", facts["note"])

        # The named cut survives the real transport publishing step.
        _, digest, _, outputs, payloads, measurements, warnings = self.transport_execute(
            raw, "text/csv"
        )
        self.assertEqual(digest, WIDE_HEADER_SHA)
        self.assertEqual(measurements, {"input_bytes": WIDE_HEADER_BYTES})
        self.assertEqual(warnings, [])
        published = json.loads(payloads["loss_report"])["params"]["format"]
        self.assertIs(published["header_capped"], True)
        self.assertEqual(published["column_count"], WIDE_HEADER_COLUMNS)
        self.assertEqual(published["header"], WIDE_HEADER_REPORTED)
        self.assertEqual(anchors_of(json.loads(payloads["document_structure"])), WIDE_HEADER_RANGES)

    # -- 5. GBK fallback with CRLF markdown ------------------------------

    def test_gbk_fallback_keeps_crlf_and_derives_markdown_from_decoded_text(self):
        raw = self.fixture_bytes("fallback-gbk-markdown.md")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), GBK_SHA)
        self.assertEqual(len(raw), GBK_BYTES)
        # The fixture must really be invalid UTF-8 or the fallback proves nothing.
        for encoding in ("utf-8", "utf-8-sig"):
            with self.assertRaises(UnicodeDecodeError):
                raw.decode(encoding)

        envelope = self.worker_envelope(
            raw, filename="fallback-gbk-markdown.md", media_type="text/markdown"
        )
        receipt = self.assert_envelope_shape(envelope)
        # The decoded text is the authored characters, CRLF included; the transform is
        # therefore *not* the source bytes and its hash is measured separately.
        self.assertEqual(envelope["text"], GBK_TEXT)
        self.assertEqual(len(envelope["text"]), GBK_TEXT_CHARS)
        self.assertEqual(
            hashlib.sha256(envelope["text"].encode("utf-8")).hexdigest(), GBK_TRANSFORM_SHA
        )
        self.assertNotEqual(GBK_TRANSFORM_SHA, GBK_SHA)
        self.assertEqual(anchors_of(envelope["structure"]), GBK_RANGES)
        self.assertEqual(receipt["covered"], receipt["total"])
        self.assertEqual(receipt["total"], 3)

        # The fallback is recorded, not silent, and it is the only loss this file has.
        self.assertEqual(receipt["params"]["decode"], "gbk")
        self.assertEqual(receipt["losses"], [GBK_LOSS])
        self.assertEqual(receipt["loss_note"], GBK_LOSS)

        # Markdown facts come from the decoded text, and CRLF is preserved so line 1 is
        # exactly "# " + 4 CJK characters + CRLF = 8 characters (hand-counted).
        facts = receipt["params"]["format"]
        self.assertEqual(facts["format"], "markdown")
        self.assertEqual(facts["heading_count"], 1)
        self.assertEqual(facts["headings"][0]["text"], "编码回退")
        self.assertEqual(facts["headings"][0]["line"], 1)
        self.assertEqual(envelope["text"][:8], "# 编码回退\r\n")

        # The transport republishes the decoded text (not the GBK bytes) and reports the
        # fallback as the job's warning list.
        _, digest, _, outputs, payloads, measurements, warnings = self.transport_execute(
            raw, "text/markdown"
        )
        self.assertEqual(digest, GBK_SHA)
        self.assertEqual(measurements, {"input_bytes": GBK_BYTES})
        self.assertEqual(warnings, [GBK_LOSS])
        self.assert_transport_publishes_worker_bytes(envelope, outputs, payloads)
        self.assertEqual(payloads["text"], GBK_TEXT.encode("utf-8"))

    # -- 6. the undecodable BOM boundary ---------------------------------

    def test_an_undecodable_bom_document_never_becomes_a_fabricated_success(self):
        raw = self.fixture_bytes("bom-then-non-utf8.txt")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), BOM_NON_UTF8_SHA)
        self.assertEqual(len(raw), BOM_NON_UTF8_BYTES)
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        with self.assertRaises(UnicodeDecodeError):
            raw.decode("utf-8-sig")

        result = self.run_worker(raw, filename="bom-then-non-utf8.txt", media_type="text/plain")
        if result.returncode == 0:
            envelope = json.loads(result.stdout)
            receipt = envelope["loss_receipt"]
            # A success is only honest if the decode fallback is named and recorded.
            self.assertNotIn(receipt["params"]["decode"], ("utf-8", "utf-8-sig"))
            self.assertTrue(receipt["losses"], "a fallback success must record its loss")
            self.assertIn(receipt["params"]["decode"], receipt["loss_note"])
        else:
            # Fail-closed arm: a named error envelope, no projected text and no outputs.
            # (Observed at the DP-NF-03 baseline: the BOM path calls raw.decode("utf-8-sig")
            # with no fallback handler, so a BOM'd non-UTF-8 document fails the whole job
            # instead of reaching the documented gbk fallback that the same bytes reach
            # without the BOM. Both arms are accepted here because a hard, named failure is
            # the module's documented failure contract; the asymmetry is reported, not fixed.)
            envelope = json.loads(result.stdout)
            self.assertEqual(set(envelope), {"error"})
            self.assertIn("codec can't decode", envelope["error"])
            self.assertEqual(result.stderr, "")

        # Through the real stdio boundary the same bytes must never yield a success
        # envelope without a recorded loss, and must publish no artifact at all.
        staging, digest = self.staging(raw)
        line = json.dumps(self.request_for(raw, "text/plain", digest)) + "\n"
        process = subprocess.run(
            [sys.executable, "-B", "-S", str(TRANSPORT), "--staging-root", str(staging)],
            input=line,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        hello, response = map(json.loads, process.stdout.splitlines())
        self.assertEqual(hello["type"], "hello")
        self.assertIn(response["status"], ("succeeded", "failed"))
        if response["status"] == "succeeded":
            receipt = json.loads(
                (staging / "output" / [
                    output["sha256"] for output in response["outputs"] if output["kind"] == "loss_report"
                ][0]).read_bytes()
            )
            self.assertNotIn(receipt["params"]["decode"], ("utf-8", "utf-8-sig"))
            self.assertTrue(receipt["losses"])
        else:
            self.assertEqual(response["error"]["code"], "AAK-WORKER-003")
            self.assertEqual(response["outputs"], [])
            output_dir = staging / "output"
            self.assertEqual(sorted(output_dir.iterdir()) if output_dir.exists() else [], [])
            self.assertNotEqual(process.returncode, 0, "a failed job must exit non-zero")

    # -- 7. line cap versus one very long line ---------------------------

    def test_the_anchor_cap_counts_lines_while_a_single_long_line_stays_one_anchor(self):
        capped = self.fixture_bytes("capped-crlf.txt")
        self.assertEqual(hashlib.sha256(capped).hexdigest(), CAPPED_CRLF_SHA)
        self.assertEqual(len(capped), CAPPED_CRLF_BYTES)

        envelope = self.worker_envelope(capped, filename="capped-crlf.txt", media_type="text/plain")
        receipt = self.assert_envelope_shape(envelope)
        # CRLF is preserved, so the text is the source byte for byte: 5001 lines of
        # "a" + CRLF, i.e. 15003 bytes and 15003 characters.
        self.assertEqual(hashlib.sha256(envelope["text"].encode("utf-8")).hexdigest(), CAPPED_CRLF_SHA)
        self.assertEqual(receipt["params"]["decode"], "utf-8")
        self.assertEqual(receipt["total"], CAPPED_CRLF_LINES)
        self.assertEqual(receipt["covered"], CAPPED_CRLF_ANCHORS)
        self.assertEqual(len(envelope["structure"]), CAPPED_CRLF_ANCHORS)
        self.assertAlmostEqual(receipt["coverage"], CAPPED_CRLF_ANCHORS / CAPPED_CRLF_LINES)
        self.assertEqual(receipt["losses"], [CAP_LOSS])
        self.assertEqual(receipt["loss_note"], CAP_LOSS)
        self.assertEqual(
            (envelope["structure"][-1]["char_start"], envelope["structure"][-1]["char_end"]),
            CAPPED_CRLF_LAST_ANCHOR,
        )
        self.assertEqual(envelope["structure"][-1]["path"], ["line-5000"])
        self.assertNotIn("BOM", receipt["loss_note"])

        # The same cap does not touch a single 9000-character line: the cap counts lines,
        # not characters, and the one anchor covers the whole text.
        long_line = self.fixture_bytes("one-long-line.txt")
        self.assertEqual(hashlib.sha256(long_line).hexdigest(), ONE_LONG_LINE_SHA)
        self.assertEqual(len(long_line), ONE_LONG_LINE_BYTES)
        long_envelope = self.worker_envelope(
            long_line, filename="one-long-line.txt", media_type="text/plain"
        )
        long_receipt = self.assert_envelope_shape(long_envelope)
        self.assertEqual(anchors_of(long_envelope["structure"]), ONE_LONG_LINE_RANGES)
        self.assertEqual(long_receipt["covered"], long_receipt["total"])
        self.assertEqual(long_receipt["total"], 1)
        self.assertAlmostEqual(long_receipt["coverage"], 1.0)
        self.assertEqual(long_receipt["losses"], [])
        self.assertEqual(long_receipt["loss_note"], "no transform applied")

    # -- 8. the transport's input byte cap -------------------------------

    def test_the_input_byte_cap_is_a_transport_boundary_above_the_line_cap(self):
        transport = load_module("p1_transport_input_cap", TRANSPORT)
        self.assertEqual(
            transport.MAX_INPUT_BYTES, MAX_INPUT_BYTES, "the transport input cap changed"
        )

        # One byte under a MiB is well past any line-length assumption and still a normal
        # document: one anchor covering every character, no loss.
        over_a_mib = b"L" * (1024 * 1024 + 1)
        _, digest, _, outputs, payloads, measurements, warnings = self.transport_execute(
            over_a_mib, "text/plain", module_name="p1_transport_input_cap_text", staging_name="staging-accepted"
        )
        self.assertEqual(digest, hashlib.sha256(over_a_mib).hexdigest())
        self.assertEqual(measurements, {"input_bytes": len(over_a_mib)})
        self.assertEqual(warnings, [])
        self.assertEqual(
            json.loads(payloads["document_structure"]),
            [{"kind": "line", "path": ["line-1"], "char_start": 0, "char_end": len(over_a_mib)}],
        )
        self.assertEqual(len(outputs), 3)

        # One byte over the transport's own cap is refused before anything is projected.
        too_big = b"L" * (MAX_INPUT_BYTES + 1)
        staging, _ = self.staging(too_big, "staging-refused")
        request = self.request_for(too_big, "text/plain")
        with self.assertRaises(Exception) as refused:
            transport.execute(request, staging)
        self.assertIsInstance(refused.exception, transport.Rejected)
        self.assertEqual(refused.exception.code, "AAK-VAL-003")
        self.assertIn("byte limit", str(refused.exception))
        self.assertFalse((staging / "output").exists(), "a refused job must publish nothing")

    # -- 9. the empty document -------------------------------------------

    def test_an_empty_file_publishes_the_empty_transform_with_explicit_zero_line_coverage(self):
        raw = self.fixture_bytes("empty.txt")
        self.assertEqual(raw, b"")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), EMPTY_SHA)

        envelope = self.worker_envelope(raw, filename="empty.txt", media_type="text/plain")
        receipt = self.assert_envelope_shape(envelope)
        self.assertEqual(envelope["text"], "")
        self.assertEqual(envelope["structure"], [])
        self.assertEqual((receipt["covered"], receipt["total"]), (0, 0))
        # Zero lines is defined as full coverage, and the receipt says that in words rather
        # than leaving a bare 1.0 to be misread as "nothing was lost".
        self.assertAlmostEqual(receipt["coverage"], 1.0)
        self.assertEqual(receipt["losses"], [])
        self.assertIn("zero-line coverage", receipt["loss_note"])
        self.assertEqual(receipt["params"]["format"]["format"], "plain")

        _, digest, _, outputs, payloads, measurements, warnings = self.transport_execute(
            raw, "text/plain"
        )
        self.assertEqual(digest, EMPTY_SHA)
        self.assertEqual(measurements, {"input_bytes": 0})
        self.assertEqual(warnings, [])
        self.assertEqual(payloads["text"], b"")
        self.assertEqual(json.loads(payloads["document_structure"]), [])
        for output in outputs:
            self.assertEqual(output["sha256"], hashlib.sha256(payloads[output["kind"]]).hexdigest())
        text_output = [output for output in outputs if output["kind"] == "text"][0]
        self.assertEqual(text_output["sha256"], EMPTY_SHA)
        self.assertEqual(text_output["byte_length"], 0)

    # -- 10. unsupported state -------------------------------------------

    def test_an_unsupported_media_type_is_refused_with_a_named_code(self):
        transport = load_module("p1_transport_unsupported", TRANSPORT)
        # text/html is a real media type that another capability owns, so this is not an
        # "unknown type" case: the text route must still refuse it explicitly.
        self.assertIn("text/html", transport.ROUTES["html.structure"]["media_types"])
        self.assertNotIn("text/html", transport.ROUTES["text.extract"]["media_types"])

        raw = self.fixture_bytes("clean-markdown.md")
        for media_type in ("text/html", "application/x-unknown"):
            with self.subTest(media_type=media_type):
                staging, digest = self.staging(raw)
                # The input is staged and hash-verified, so the refusal is about the
                # declaration only.
                self.assertEqual(digest, CLEAN_MARKDOWN_SHA)
                with self.assertRaises(Exception) as refused:
                    transport.execute(self.request_for(raw, media_type, digest), staging)
                self.assertIsInstance(refused.exception, transport.Rejected)
                self.assertEqual(refused.exception.code, "AAK-VAL-002")
                self.assertIn("unsupported media type", str(refused.exception))
                self.assertFalse((staging / "output").exists())

        # The stdio boundary turns the same refusal into a rejected envelope with no
        # outputs, so a reader never sees a partial artifact for a refused declaration.
        staging, digest = self.staging(raw)
        line = json.dumps(self.request_for(raw, "application/x-unknown", digest)) + "\n"
        process = subprocess.run(
            [sys.executable, "-B", "-S", str(TRANSPORT), "--staging-root", str(staging)],
            input=line,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        hello, response = map(json.loads, process.stdout.splitlines())
        self.assertEqual(hello["type"], "hello")
        self.assertEqual(hello["capabilities"], ["text.extract"])
        self.assertEqual(response["status"], "rejected")
        self.assertEqual(response["outputs"], [])
        self.assertEqual(response["error"]["code"], "AAK-VAL-002")
        self.assertFalse(response["error"]["retryable"])
        output_dir = staging / "output"
        self.assertEqual(sorted(output_dir.iterdir()) if output_dir.exists() else [], [])


if __name__ == "__main__":
    unittest.main()
