"""Real subtitle-worker transport regression for mixed WebVTT timestamp forms."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "services/python-workers/document/worker_subtitles.py"


class WebVttIngestionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ["ARCHEAXIS_RUN_ROOT"])
        self.addCleanup(self.tmp.cleanup)
        self.staging = Path(self.tmp.name)
        (self.staging / "input").mkdir()
        (self.staging / "output").mkdir()

    def invoke(self, raw):
        digest = hashlib.sha256(raw).hexdigest()
        source = self.staging / "input" / digest
        source.write_bytes(raw)
        request = {
            "schema": "archeaxis.worker-request/v1", "type": "job_request",
            "request_id": "vtt-request", "job_id": "vtt-job", "attempt": 1,
            "protocol_minor": 0, "capability": "subtitles.structure",
            "capability_version": "1", "deadline_ms": 30000,
            "inputs": [{"uri": f"job://input/{digest}", "sha256": digest, "media_type": "text/vtt"}],
            "parameters": {},
        }
        # Keep the child local and do not inherit credentials or provider settings.
        env = {"SystemRoot": os.environ["SystemRoot"]} if os.name == "nt" else {}
        env.update(TEMP=str(self.staging), TMP=str(self.staging))
        process = subprocess.run(
            [sys.executable, "-B", "-S", str(WORKER), "--staging-root", str(self.staging)],
            input=json.dumps(request) + "\n", capture_output=True, text=True, encoding="utf-8",
            timeout=30, check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), env=env,
        )
        self.assertEqual(len(process.stdout.splitlines()), 2, process.stdout + process.stderr)
        hello, response = map(json.loads, process.stdout.splitlines())
        self.assertEqual(hello["capabilities"], ["subtitles.structure"])
        self.assertEqual(source.read_bytes(), raw)
        return process, response

    def test_mixed_hour_and_minute_timestamps_preserve_both_cues(self):
        raw = (b"WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nSYNTHETIC full\n\n"
               b"00:03.200 --> 00:04.500 align:start\nSYNTHETIC short\n\n")
        process, response = self.invoke(raw)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(response["status"], "succeeded")
        outputs = {item["kind"]: item for item in response["outputs"]}
        text = (self.staging / "output" / outputs["text"]["sha256"]).read_bytes()
        self.assertEqual(text, b"SYNTHETIC full\nSYNTHETIC short\n")
        receipt = json.loads((self.staging / "output" / outputs["loss_report"]["sha256"]).read_bytes())
        cues = receipt["params"]["worker_structure"]
        self.assertEqual([(cue["offset_ms"], cue["duration_ms"]) for cue in cues], [(1000, 1000), (3200, 1300)])
        self.assertEqual(receipt["params"]["cues"], 2)

    def test_short_long_and_mixed_timestamps_keep_millisecond_precision(self):
        raw = (b"WEBVTT\n\n00:00.008 --> 00:00.800\nA\n\n"
               b"00:01.08 --> 00:01.8\nB\n\n"
               b"00:00:02.5 --> 00:03.008\nC\n\n"
               b"0000000000100:00:00.005 --> 0000000000100:00:01.005\nD\n\n")
        process, response = self.invoke(raw)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(response["status"], "succeeded")
        outputs = {item["kind"]: item for item in response["outputs"]}
        self.assertEqual((self.staging / "output" / outputs["text"]["sha256"]).read_bytes(), b"A\nB\nC\nD\n")
        receipt = json.loads((self.staging / "output" / outputs["loss_report"]["sha256"]).read_bytes())
        cues = receipt["params"]["worker_structure"]
        self.assertEqual([(cue["offset_ms"], cue["duration_ms"]) for cue in cues],
                         [(8, 792), (1080, 720), (2500, 508), (360000005, 1000)])

    def test_malformed_timing_does_not_merge_or_silently_drop_a_cue(self):
        for invalid_timing in (
            b"00:60.000 --> 01:01.000",
            b"60:00.000 --> 01:00:01.000",
            b"00:03.000 --> broken",
            b"00:04.000 --> 00:03.000",
            b"00:03.000 --> 00:04.000 --> 00:05.000",
            b"9999999999:00:00.000 --> 9999999999:00:01.000",
        ):
            with self.subTest(invalid_timing=invalid_timing):
                raw = (b"WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nSYNTHETIC before\n\n"
                       + invalid_timing + b"\nSYNTHETIC invalid\n\n"
                       b"00:00:05.000 --> 00:00:06.000\nSYNTHETIC after\n\n")
                process, response = self.invoke(raw)
                self.assertEqual(process.returncode, 1)
                self.assertEqual(response["status"], "failed")
                self.assertEqual(response["outputs"], [])
                self.assertEqual(list((self.staging / "output").iterdir()), [])

    def test_cues_without_blank_separator_do_not_merge_the_identifier_into_text(self):
        raw = (b"WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nSYNTHETIC first\n"
               b"cue-identifier\n00:00:03.000 --> 00:00:04.000\nSYNTHETIC second\n\n")
        process, response = self.invoke(raw)
        self.assertEqual(process.returncode, 1)
        self.assertEqual(response["status"], "failed")
        self.assertEqual(response["outputs"], [])
        self.assertEqual(list((self.staging / "output").iterdir()), [])

    def test_malformed_block_without_arrow_is_not_silently_discarded(self):
        for malformed in (
            b"SYNTHETIC identifier without a timing line",
            b"SYNTHETIC cue id\n00:03.000 -> 00:04.000\nSYNTHETIC lost text",
        ):
            with self.subTest(malformed=malformed):
                raw = (b"WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nSYNTHETIC before\n\n"
                       + malformed + b"\n\n"
                       b"00:00:05.000 --> 00:00:06.000\nSYNTHETIC after\n\n")
                process, response = self.invoke(raw)
                self.assertEqual(process.returncode, 1)
                self.assertEqual(response["status"], "failed")
                self.assertEqual(response["outputs"], [])
                self.assertEqual(list((self.staging / "output").iterdir()), [])

    def test_empty_payload_cue_keeps_its_time_anchor(self):
        raw = (b"WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nSYNTHETIC before\n\n"
               b"empty-payload-id\n00:00:03.000 --> 00:00:04.000\n\n"
               b"00:00:05.000 --> 00:00:06.000\nSYNTHETIC after\n\n")
        process, response = self.invoke(raw)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(response["status"], "succeeded")
        outputs = {item["kind"]: item for item in response["outputs"]}
        self.assertEqual((self.staging / "output" / outputs["text"]["sha256"]).read_bytes(),
                         b"SYNTHETIC before\n\nSYNTHETIC after\n")
        receipt = json.loads((self.staging / "output" / outputs["loss_report"]["sha256"]).read_bytes())
        cues = receipt["params"]["worker_structure"]
        self.assertEqual([(cue["offset_ms"], cue["duration_ms"]) for cue in cues],
                         [(1000, 1000), (3000, 1000), (5000, 1000)])
        self.assertEqual(cues[1]["char_start"], cues[1]["char_end"])

    def test_header_without_cue_separator_is_rejected_without_partial_output(self):
        raw = (b"WEBVTT\n00:00:01.000 --> 00:00:02.000\nSYNTHETIC unseparated\n\n"
               b"00:00:03.000 --> 00:00:04.000\nSYNTHETIC after\n\n")
        process, response = self.invoke(raw)
        self.assertEqual(process.returncode, 1)
        self.assertEqual(response["status"], "failed")
        self.assertEqual(response["outputs"], [])
        self.assertEqual(list((self.staging / "output").iterdir()), [])

    def test_style_and_region_can_be_cue_identifiers(self):
        raw = (b"WEBVTT\n\nSTYLE\n00:00:01.000 --> 00:00:02.000\nSYNTHETIC one\n\n"
               b"REGION\n00:00:03.000 --> 00:00:04.000\nSYNTHETIC two\n\n")
        process, response = self.invoke(raw)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(response["status"], "succeeded")
        outputs = {item["kind"]: item for item in response["outputs"]}
        self.assertEqual((self.staging / "output" / outputs["text"]["sha256"]).read_bytes(),
                         b"SYNTHETIC one\nSYNTHETIC two\n")

    def test_note_blocks_are_dropped_but_cue_text_starting_with_note_is_kept(self):
        raw = (b"WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n"
               b"NOTE: this is cue text\nNOTE this is also cue text\nSYNTHETIC first\n\n"
               b"NOTE this whole block is commentary\nSYNTHETIC extra comment line\n"
               b"SYNTHETIC comment, not a cue\n\n"
               b"00:00:03.000 --> 00:00:04.000\nSYNTHETIC last\n\n")
        process, response = self.invoke(raw)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(response["status"], "succeeded")
        outputs = {item["kind"]: item for item in response["outputs"]}
        text = (self.staging / "output" / outputs["text"]["sha256"]).read_bytes()
        self.assertEqual(text, b"NOTE: this is cue text\nNOTE this is also cue text\nSYNTHETIC first\n"
                               b"SYNTHETIC last\n")
        receipt = json.loads((self.staging / "output" / outputs["loss_report"]["sha256"]).read_bytes())
        cues = receipt["params"]["worker_structure"]
        self.assertEqual([(cue["offset_ms"], cue["duration_ms"]) for cue in cues], [(1000, 1000), (3000, 1000)])
        self.assertEqual(receipt["params"]["cues"], 2)

    def test_note_and_named_note_can_be_cue_identifiers(self):
        raw = (b"WEBVTT\n\nNOTE\n00:00:01.000 --> 00:00:02.000\nSYNTHETIC one\n\n"
               b"NOTE cue id\n00:00:03.000 --> 00:00:04.000\nSYNTHETIC two\n\n")
        process, response = self.invoke(raw)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(response["status"], "succeeded")
        outputs = {item["kind"]: item for item in response["outputs"]}
        self.assertEqual((self.staging / "output" / outputs["text"]["sha256"]).read_bytes(),
                         b"SYNTHETIC one\nSYNTHETIC two\n")

    def test_whitespace_only_payload_line_does_not_end_a_cue(self):
        raw = (b"WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nSYNTHETIC before \n \n"
               b"NOTE payload\nSYNTHETIC same cue\n\n"
               b"00:00:03.000 --> 00:00:04.000\nSYNTHETIC after\n\n")
        process, response = self.invoke(raw)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(response["status"], "succeeded")
        outputs = {item["kind"]: item for item in response["outputs"]}
        self.assertEqual((self.staging / "output" / outputs["text"]["sha256"]).read_bytes(),
                         b"SYNTHETIC before \n \nNOTE payload\nSYNTHETIC same cue\nSYNTHETIC after\n")
        receipt = json.loads((self.staging / "output" / outputs["loss_report"]["sha256"]).read_bytes())
        self.assertEqual(receipt["params"]["cues"], 2)

    def test_noncue_block_with_late_arrow_is_rejected(self):
        for heading in (b"NOTE comment", b"STYLE", b"REGION"):
            with self.subTest(heading=heading):
                raw = (b"WEBVTT\n\n" + heading + b"\nSYNTHETIC noncue line\n"
                       b"00:00:01.000 --> 00:00:02.000\nSYNTHETIC cannot be discarded\n\n"
                       b"00:00:03.000 --> 00:00:04.000\nSYNTHETIC after\n\n")
                process, response = self.invoke(raw)
                self.assertEqual(process.returncode, 1)
                self.assertEqual(response["status"], "failed")
                self.assertEqual(response["outputs"], [])
                self.assertEqual(list((self.staging / "output").iterdir()), [])

    def test_header_signature_is_not_a_prefix_match(self):
        raw = b"WEBVTTX\n\n00:00:01.000 --> 00:00:02.000\nSYNTHETIC text\n\n"
        process, response = self.invoke(raw)
        self.assertEqual(process.returncode, 1)
        self.assertEqual(response["status"], "failed")
        self.assertEqual(response["outputs"], [])

    def test_note_heading_with_arrow_is_not_silently_discarded(self):
        raw = (b"WEBVTT\n\nNOTE comment --> 00:01.000\nSYNTHETIC ambiguous\n\n"
               b"00:00:03.000 --> 00:00:04.000\nSYNTHETIC after\n\n")
        process, response = self.invoke(raw)
        self.assertEqual(process.returncode, 1)
        self.assertEqual(response["status"], "failed")
        self.assertEqual(response["outputs"], [])
        self.assertEqual(list((self.staging / "output").iterdir()), [])

    def test_header_annotation_may_contain_arrow(self):
        raw = (b"WEBVTT synthetic --> header annotation\n\n"
               b"00:00:01.000 --> 00:00:02.000\nSYNTHETIC cue\n\n")
        process, response = self.invoke(raw)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(response["status"], "succeeded")
        outputs = {item["kind"]: item for item in response["outputs"]}
        self.assertEqual((self.staging / "output" / outputs["text"]["sha256"]).read_bytes(),
                         b"SYNTHETIC cue\n")

    def test_indented_noncues_are_not_silently_omitted(self):
        for heading in (b" NOTE comment", b" STYLE", b" REGION"):
            with self.subTest(heading=heading):
                raw = (b"WEBVTT\n\n" + heading + b"\nSYNTHETIC malformed block\n\n"
                       b"00:00:03.000 --> 00:00:04.000\nSYNTHETIC after\n\n")
                process, response = self.invoke(raw)
                self.assertEqual(process.returncode, 1)
                self.assertEqual(response["status"], "failed")
                self.assertEqual(response["outputs"], [])
                self.assertEqual(list((self.staging / "output").iterdir()), [])

    def test_vtt_receipt_reports_unpreserved_metadata_ids_and_timing_settings(self):
        raw = (b"WEBVTT - SYNTHETIC header\nLanguage: en\nKind: captions\n\n"
               b"STYLE\n::cue { color: red; }\n\n"
               b"REGION\nid:region-a\nwidth:50%\n\n"
               b"source-cue-id\n00:00:01.250 --> 00:00:02.500 line:10% position:20% align:start\n"
               b"SYNTHETIC caption\n\n")
        process, response = self.invoke(raw)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(response["status"], "succeeded")
        outputs = {item["kind"]: item for item in response["outputs"]}
        text = (self.staging / "output" / outputs["text"]["sha256"]).read_bytes()
        self.assertEqual(text, b"SYNTHETIC caption\n")
        receipt = json.loads((self.staging / "output" / outputs["loss_report"]["sha256"]).read_bytes())
        cues = receipt["params"]["worker_structure"]
        self.assertEqual(len(cues), 1)
        self.assertEqual((cues[0]["offset_ms"], cues[0]["duration_ms"]), (1250, 1250))
        self.assertEqual(cues[0]["path"], ["cue-1"])
        self.assertEqual((cues[0]["char_start"], cues[0]["char_end"]), (0, len("SYNTHETIC caption")))
        for detail in ("header metadata", "cue identifiers", "STYLE/REGION blocks", "cue timing settings",
                       "line", "position", "align", "not preserved", "character references remain encoded"):
            self.assertIn(detail, receipt["loss_note"])

    def test_vtt_character_references_are_retained_and_reported(self):
        raw = (b"WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n"
               b"SYNTHETIC A &amp; B &lt;C&gt;\n\n")
        process, response = self.invoke(raw)
        self.assertEqual(process.returncode, 0, process.stderr)
        outputs = {item["kind"]: item for item in response["outputs"]}
        self.assertEqual((self.staging / "output" / outputs["text"]["sha256"]).read_bytes(),
                         b"SYNTHETIC A &amp; B &lt;C&gt;\n")
        receipt = json.loads((self.staging / "output" / outputs["loss_report"]["sha256"]).read_bytes())
        self.assertIn("character references remain encoded", receipt["loss_note"])


if __name__ == "__main__":
    unittest.main()
