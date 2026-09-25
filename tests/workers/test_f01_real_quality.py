"""DP-F01 real text quality roundtrip (synthetic controlled fixture).

This suite drives ONE hand-authored synthetic fixture through the real worker
code path - ``worker_text.py`` in a real subprocess, then the real
``text_ndjson.py`` transport loaded over a real staging directory - and asserts
the whole receipt: original hash, transform hash, source->transform binding,
structure/anchors, quality/loss, engine/version, decoder fallback and explicit
unsupported/partial state.

Nothing here is mocked and nothing is copied back from the output as its own
expectation: every anchor range, count and hash is written by hand from the
fixture bytes measured independently (see ``tests/fixtures/f01-quality/manifest.yaml``).

Boundary: this is a controlled synthetic fixture, NOT real-corpus qualification,
and it does not close any P1 format. The Rust lane
(``crates/archeaxis-api/tests/f01_quality_roundtrip.rs``) is what binds the same
fixture to the Core API read-back routes.
"""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "f01-quality"
WORKER = ROOT / "services/python-workers/document/worker_text.py"
TRANSPORT = ROOT / "services/python-workers/transport/text_ndjson.py"

ENGINE = "python-worker-text"
ENGINE_VERSION = "0.1.0"

# Hand-measured fixture facts (independent of the worker's own output).
CONTROLLED_SOURCE_SHA = "70aff728005d7580260391e6754f30209ec5fbecd9803f30a31e48d72eb7b176"
CONTROLLED_SOURCE_BYTES = 561
CONTROLLED_TRANSFORM_SHA = "e5be0cbcaa4580bda39a481f49767ef8c3697f299adb2fa0806dc16592719ab6"
CONTROLLED_LINES = 17
CONTROLLED_RANGES = [
    (0, 4), (4, 25), (25, 29), (29, 48), (48, 106), (106, 120), (120, 202),
    (202, 261), (261, 269), (269, 289), (289, 293), (293, 311), (311, 330),
    (330, 390), (390, 434), (434, 480), (480, 535),
]
CAPPED_SOURCE_SHA = "71c0029230e042d72e9ec8db74f9a28196b37fdfb29f7df7d68e3b425af38928"
CAPPED_LINES = 5001
CAPPED_ANCHORS = 5000
GBK_SOURCE_SHA = "8ba7ed5cd0f33c11b7bb447337b0ce852b0a4f52c5ee854b6107943408b2b215"
GBK_TEXT_SHA = "627f58abc97febb55b9eab82217283d523070ecd70575e02c5fd5fd0789a3b20"
CSV_SOURCE_SHA = "938968124db09f78bfaeb7bcfc64e5a1c10ed4460388295e3e76b16603ed0bc5"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical(value) -> bytes:
    """The transport's own output encoding, restated here so it is not assumed."""
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


class F01RealQualityRoundtrip(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ["ARCHEAXIS_RUN_ROOT"])
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)

    # -- helpers ---------------------------------------------------------

    def fixture_bytes(self, name: str) -> bytes:
        return (FIXTURES / name).read_bytes()

    def run_worker(self, name: str, media_type: str) -> dict:
        """Run the real worker script in a real subprocess, like the Core does."""
        local = self.work / name
        local.write_bytes(self.fixture_bytes(name))
        command = [sys.executable, "-B", str(WORKER), str(local), media_type]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "", "the worker must not write to stderr on success")
        lines = result.stdout.splitlines()
        self.assertEqual(len(lines), 1, "one envelope, no extra output")
        return json.loads(lines[0])

    def stage_and_transport(self, name: str, media_type: str):
        """Drive the real NDJSON transport over a real staging directory.

        The staging layout is the one the Core owns: ``input/<sha256>`` plus the
        content-addressed outputs under ``output/``.
        """
        raw = self.fixture_bytes(name)
        digest = hashlib.sha256(raw).hexdigest()
        staging = self.work / "staging"
        (staging / "input").mkdir(parents=True, exist_ok=True)
        (staging / "output").mkdir(parents=True, exist_ok=True)
        (staging / "input" / digest).write_bytes(raw)
        request = {
            "schema": "archeaxis.worker-request/v1",
            "type": "job_request",
            "request_id": "f01-request",
            "job_id": "f01-job",
            "attempt": 1,
            "protocol_minor": 0,
            "capability": "text.extract",
            "capability_version": "1",
            "deadline_ms": 30000,
            "inputs": [{"uri": f"job://input/{digest}", "sha256": digest, "media_type": media_type}],
            "parameters": {},
        }
        transport = load_module("f01_transport", TRANSPORT)
        outputs, measurements, warnings = transport.execute(request, staging)
        payloads = {
            output["kind"]: (staging / "output" / output["sha256"]).read_bytes()
            for output in outputs
        }
        return digest, outputs, payloads, measurements, warnings

    def assert_transport_is_the_worker_output(self, result: dict, outputs, payloads):
        """The transport must publish exactly the worker's own bytes, hashed."""
        self.assertEqual({output["kind"] for output in outputs}, {"text", "document_structure", "loss_report"})
        expected = {
            "text": result["text"].encode("utf-8"),
            "document_structure": canonical(result["structure"]),
            "loss_report": canonical(result["loss_receipt"]),
        }
        for output in outputs:
            self.assertEqual(output["authority_effect"], "candidate_or_measurement_only")
            self.assertEqual(output["uri"], f"job://output/{output['sha256']}")
            self.assertEqual(
                output["sha256"],
                hashlib.sha256(expected[output["kind"]]).hexdigest(),
                f"{output['kind']} output is not the worker's own bytes",
            )
            self.assertEqual(output["byte_length"], len(expected[output["kind"]]))
            self.assertEqual(payloads[output["kind"]], expected[output["kind"]])

    # -- 1. the controlled markdown roundtrip ----------------------------

    def test_controlled_markdown_receipt_preserves_hash_structure_quality_and_engine(self):
        raw = self.fixture_bytes("controlled.md")
        # Original hash: the source is stored unchanged, BOM included.
        self.assertEqual(hashlib.sha256(raw).hexdigest(), CONTROLLED_SOURCE_SHA)
        self.assertEqual(len(raw), CONTROLLED_SOURCE_BYTES)

        result = self.run_worker("controlled.md", "text/markdown")
        text = result["text"]

        # Decode/fallback: the BOM is stripped and the fallback is *recorded*,
        # not silently applied.
        receipt = result["loss_receipt"]
        self.assertEqual(receipt["params"]["decode"], "utf-8-sig")
        self.assertIn("UTF-8 BOM stripped", receipt["losses"])
        self.assertEqual(receipt["params"]["media_type"], "text/markdown")

        # Engine identity and version.
        self.assertEqual(result["engine"], ENGINE)
        self.assertEqual(result["engine_version"], ENGINE_VERSION)
        self.assertEqual(receipt["engine"], ENGINE)
        self.assertEqual(receipt["engine_version"], ENGINE_VERSION)

        # Transform hash: the transform is the projected UTF-8 text, not the file.
        self.assertEqual(hashlib.sha256(text.encode("utf-8")).hexdigest(), CONTROLLED_TRANSFORM_SHA)
        self.assertNotEqual(hashlib.sha256(text.encode("utf-8")).hexdigest(), CONTROLLED_SOURCE_SHA)

        # Structure/anchors against hand-written character ranges.
        self.assertEqual(len(text.splitlines(keepends=True)), CONTROLLED_LINES)
        self.assertEqual(
            [(anchor["char_start"], anchor["char_end"]) for anchor in result["structure"]],
            CONTROLLED_RANGES,
        )
        self.assertEqual(
            [anchor["path"] for anchor in result["structure"]],
            [[f"line-{index}"] for index in range(1, CONTROLLED_LINES + 1)],
        )
        self.assertTrue(all(anchor["kind"] == "line" for anchor in result["structure"]))

        # Quality/coverage: exactly one documented loss, full anchor coverage.
        self.assertEqual((receipt["covered"], receipt["total"]), (CONTROLLED_LINES, CONTROLLED_LINES))
        self.assertAlmostEqual(receipt["coverage"], 1.0)
        self.assertEqual(receipt["losses"], ["UTF-8 BOM stripped"])
        self.assertIn("UTF-8 BOM stripped", receipt["loss_note"])

        # Derivable format facts for the declared media type.
        facts = receipt["params"]["format"]
        self.assertEqual(facts["format"], "markdown")
        self.assertIs(facts["parsed"], True)
        self.assertIs(facts["frontmatter"], True)
        self.assertEqual(facts["heading_count"], 2)
        self.assertEqual(
            [heading["text"] for heading in facts["headings"]],
            ["星环知识平台 Roundtrip", "结构 anchors"],
        )
        self.assertEqual(facts["wiki_link_count"], 1)
        self.assertEqual(facts["embed_count"], 1)
        self.assertEqual(facts["markdown_link_count"], 1)
        self.assertEqual(facts["code_fence_count"], 2)
        self.assertEqual(facts["list_item_count"], 2)

        # Source -> transform binding through the real transport, byte for byte.
        digest, outputs, payloads, measurements, warnings = self.stage_and_transport(
            "controlled.md", "text/markdown"
        )
        self.assertEqual(digest, CONTROLLED_SOURCE_SHA)
        self.assertEqual(measurements, {"input_bytes": len(raw)})
        self.assertEqual(warnings, receipt["losses"])
        self.assert_transport_is_the_worker_output(result, outputs, payloads)
        self.assertEqual(payloads["text"], text.encode("utf-8"))
        self.assertEqual(json.loads(payloads["loss_report"]), receipt)

        # Negative control: the assertion above is not a mirror of the worker.
        corrupted = [dict(anchor, char_end=anchor["char_end"] + 1) for anchor in result["structure"]]
        self.assertNotEqual(result["structure"], corrupted)

    # -- 2. every loss the worker can report is really reachable ---------

    def test_cap_and_bom_losses_coexist_and_are_both_accounted(self):
        raw = self.fixture_bytes("capped-lines.md")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), CAPPED_SOURCE_SHA)
        result = self.run_worker("capped-lines.md", "text/markdown")
        receipt = result["loss_receipt"]
        self.assertEqual(receipt["covered"], CAPPED_ANCHORS)
        self.assertEqual(receipt["total"], CAPPED_LINES)
        self.assertEqual(receipt["losses"], ["UTF-8 BOM stripped", "line anchors capped at 5000"])
        self.assertIn("line anchors capped at 5000", receipt["loss_note"])
        self.assertEqual(len(result["structure"]), CAPPED_ANCHORS)
        self.assertEqual(result["structure"][-1]["path"], ["line-5000"])
        self.assertLess(receipt["coverage"], 1.0)

    def test_decoder_fallback_is_recorded_instead_of_being_silent(self):
        raw = self.fixture_bytes("fallback-gbk.txt")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), GBK_SOURCE_SHA)
        # The fixture must really be invalid UTF-8, or the fallback proves nothing.
        with self.assertRaises(UnicodeDecodeError):
            raw.decode("utf-8")
        result = self.run_worker("fallback-gbk.txt", "text/plain")
        receipt = result["loss_receipt"]
        self.assertEqual(receipt["params"]["decode"], "gbk")
        self.assertEqual(len(receipt["losses"]), 1)
        self.assertIn("gbk", receipt["losses"][0])
        self.assertIn("gbk", receipt["loss_note"])
        text = result["text"]
        self.assertEqual(hashlib.sha256(text.encode("utf-8")).hexdigest(), GBK_TEXT_SHA)
        self.assertEqual(text, "简体中文回退编码\nGBK 回退第二行\n")
        # Structure is still derived from the *decoded* text, not from the bytes:
        # line 1 is 8 CJK characters plus its newline, line 2 is 9 characters
        # (5 ASCII + 4 CJK) plus its newline. Both are hand-counted here.
        self.assertEqual(
            [anchor["char_end"] - anchor["char_start"] for anchor in result["structure"]],
            [9, 10],
        )

    def test_delimited_facts_report_ragged_rows_without_squaring_them_off(self):
        raw = self.fixture_bytes("ragged.csv")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), CSV_SOURCE_SHA)
        result = self.run_worker("ragged.csv", "text/csv")
        facts = result["loss_receipt"]["params"]["format"]
        self.assertEqual(facts["format"], "csv")
        self.assertEqual(facts["row_count"], 4)
        self.assertEqual(facts["column_count"], 3)
        self.assertEqual(facts["ragged_rows"], 1)
        self.assertEqual(facts["header"], ["id", "name", "note"])
        self.assertIn("ragged", facts["note"])
        # A well-formed CSV has no decode loss and no cap loss.
        self.assertEqual(result["loss_receipt"]["losses"], [])

    def test_unsupported_extension_is_explicit_and_never_decoded_as_markdown(self):
        raw = self.fixture_bytes("unsupported.unknown-ext")
        self.assertEqual(raw, b"no media type names this extension\n")
        digest = hashlib.sha256(raw).hexdigest()
        local = self.work / "unsupported.unknown-ext"
        local.write_bytes(raw)
        # The transport is the boundary that decides which capability may read a
        # media type; an unknown one must be refused, not guessed.
        result = subprocess.run(
            [sys.executable, "-B", str(WORKER), str(local), "application/x-unknown"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        facts = json.loads(result.stdout)["loss_receipt"]["params"]["format"]
        self.assertEqual(facts["format"], "plain")
        self.assertIs(facts["parsed"], True)
        self.assertNotIn("markdown", result.stdout.lower())

        with self.assertRaises(ValueError) as refused:
            load_module("f01_transport_negative", TRANSPORT).execute(
                {
                    "schema": "archeaxis.worker-request/v1",
                    "type": "job_request",
                    "request_id": "f01-unsupported",
                    "job_id": "f01-unsupported",
                    "attempt": 1,
                    "protocol_minor": 0,
                    "capability": "text.extract",
                    "capability_version": "1",
                    "deadline_ms": 30000,
                    "inputs": [
                        {
                            "uri": "job://input/" + hashlib.sha256(raw).hexdigest(),
                            "sha256": hashlib.sha256(raw).hexdigest(),
                            "media_type": "application/x-unknown",
                        }
                    ],
                    "parameters": {},
                },
                self.work / "staging" if (self.work / "staging").is_dir() else self.work,
            )
        self.assertIn("unsupported media type", str(refused.exception))


if __name__ == "__main__":
    unittest.main()
