"""Explicit public OCR profile wiring and truthful subprocess failures."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "services/python-workers/vision/worker_ocr.py"
spec = importlib.util.spec_from_file_location("worker_ocr", SCRIPT)
ocr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ocr)
TSV = ("level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
       "5\t1\t1\t1\t1\t1\t10\t20\t30\t40\t95\tANCHOR\n")


def completed(stdout="", returncode=0, stderr=""):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


class OCRProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ["ARCHEAXIS_RUN_ROOT"])
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.tessdata = self.root / "languages"
        self.tessdata.mkdir()
        self.profile = self.root / "public-profile.yaml"
        self.profile.write_text(yaml.safe_dump({"schema": "archeaxis.model-profile/v1",
                                               "ocr": {"tessdata_dir": str(self.tessdata)}}), encoding="utf-8")
        self.image = self.root / "fixture.png"
        self.image.write_bytes(b"controlled subprocess fixture")

    def call_main(self, args):
        stream = io.StringIO()
        with patch.object(sys, "argv", [str(SCRIPT), *args]), contextlib.redirect_stdout(stream):
            try:
                code = ocr.main()
            except SystemExit as exc:
                self.fail(f"CLI did not handle the requested arguments: {exc}")
            except Exception as exc:
                self.fail(f"CLI exception escaped JSON error boundary: {type(exc).__name__}: {exc}")
        return code, json.loads(stream.getvalue())

    def test_cli_profile_routes_same_tessdata_to_probe_text_and_tsv(self):
        commands = []

        def execute(command, **kwargs):
            commands.append(command)
            if os.name == "nt":
                self.assertEqual(kwargs.get("creationflags"), subprocess.CREATE_NO_WINDOW)
            if "--version" in command:
                return completed("tesseract test\n")
            if "--list-langs" in command:
                return completed("List of available languages (2):\neng\nchi_sim\n")
            return completed(TSV if "tessedit_create_tsv=1" in command else "ANCHOR\n")

        with patch.object(ocr.shutil, "which", return_value="tesseract"), patch.object(ocr.subprocess, "run", side_effect=execute):
            code, probe = self.call_main(["--probe", "--profile", str(self.profile), "--lang", "eng+chi_sim"])
            self.assertEqual(code, 0)
            self.assertTrue(probe["capability"])
            code, result = self.call_main([str(self.image), "--profile", str(self.profile)])
            self.assertEqual(code, 0)
            self.assertEqual(result["text"], "ANCHOR")
            self.assertEqual(result["words"][0]["x"], 10)
            self.assertEqual(result["loss_receipt"]["params"]["tessdata_dir"], str(self.tessdata))
        self.assertEqual(sum("--version" in command for command in commands), 1)
        for command in commands:
            if "--version" not in command:
                self.assertIn("--tessdata-dir", command)
                self.assertEqual(command[command.index("--tessdata-dir") + 1], str(self.tessdata))
        self.assertEqual(commands[-1][-2:], ["-c", "tessedit_create_tsv=1"])

    def test_probe_rejects_nonzero_empty_timeout_and_missing_language(self):
        failures = [completed("eng\n", 1, "language lookup failed"), completed(""),
                    completed("List of available languages (0):\n"), completed("chi_sim\n"),
                    subprocess.TimeoutExpired("tesseract", 30)]
        for failure in failures:
            with self.subTest(failure=str(failure)):
                def execute(command, **kwargs):
                    if "--version" in command:
                        return completed("tesseract test\n")
                    if isinstance(failure, Exception):
                        raise failure
                    return failure
                with patch.object(ocr.shutil, "which", return_value="tesseract"), patch.object(
                    ocr.subprocess, "run", side_effect=execute
                ):
                    code, result = self.call_main(["--probe"])
                self.assertFalse(result["capability"])
                self.assertTrue(result.get("reason") or result.get("error"))

    def test_probe_version_failure_and_missing_binary_still_emit_json(self):
        for response in (completed("tesseract test", 1), completed(""), OSError("cannot launch")):
            with self.subTest(response=str(response)):
                def execute(command, **kwargs):
                    if isinstance(response, Exception):
                        raise response
                    return response if "--version" in command else completed("eng\n")
                with patch.object(ocr.shutil, "which", return_value="tesseract"), patch.object(ocr.subprocess, "run", side_effect=execute):
                    _, result = self.call_main(["--probe"])
                self.assertFalse(result["capability"])
        with patch.object(ocr.shutil, "which", return_value=None):
            _, result = self.call_main(["--probe"])
        self.assertFalse(result["capability"])

    def test_probe_preserves_windows_script_language_names(self):
        with patch.object(ocr.shutil, "which", return_value="tesseract"), patch.object(
            ocr.subprocess, "run", side_effect=[completed("tesseract test\n"),
                                               completed("List of available languages (2):\neng\nscript\\Latin\n")]
        ):
            _, result = self.call_main(["--probe", "--lang", "script\\Latin"])
        self.assertTrue(result["capability"], result)
        self.assertEqual(result["languages"], ["eng", "script\\Latin"])

    def test_plain_success_with_failed_or_invalid_tsv_is_not_complete_success(self):
        for tsv in (completed("", 1, "TSV failed"), completed(""), completed("not TSV")):
            with self.subTest(tsv=tsv):
                with patch.object(ocr.shutil, "which", return_value="tesseract"), patch.object(
                    ocr.subprocess, "run", side_effect=[completed("ANCHOR\n"), tsv]
                ):
                    code, result = self.call_main([str(self.image)])
                self.assertNotEqual(code, 0)
                self.assertIn("error", result)
                self.assertNotIn("text", result)

    def test_bad_explicit_profile_fails_without_fallback_in_real_cli(self):
        for content in ("not: [valid yaml", "schema: wrong\nocr: {}", "schema: archeaxis.model-profile/v1\nocr: {}",
                        "schema: archeaxis.model-profile/v1\nocr:\n  tessdata_dir: missing"):
            with self.subTest(content=content):
                self.profile.write_text(content, encoding="utf-8")
                result = subprocess.run([sys.executable, "-B", str(SCRIPT), "--probe", "--profile", str(self.profile)],
                                        capture_output=True, text=True, encoding="utf-8", check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(result.stdout.strip(), "explicit bad profile must produce JSON, not argparse-only stderr")
                self.assertIn("error", json.loads(result.stdout))

    def test_successful_subprocess_warnings_are_preserved_in_loss_receipt(self):
        with patch.object(ocr.shutil, "which", return_value="tesseract"), patch.object(
            ocr.subprocess, "run", side_effect=[completed("ANCHOR\n", stderr="text warning"),
                                               completed(TSV, stderr="TSV warning")]
        ):
            code, result = self.call_main([str(self.image)])
        self.assertEqual(code, 0)
        self.assertEqual(result["loss_receipt"]["params"]["warnings"],
                         [{"stage": "text", "message": "text warning"}, {"stage": "tsv", "message": "TSV warning"}])
        self.assertIn("warnings", result["loss_receipt"]["loss_note"])

    def test_malformed_word_rows_cannot_be_silently_omitted(self):
        for row in ("5\t1\t1\t1\t1\t2\t-1\t20\t30\t40\t95\tSECOND\n",
                    "5\t1\t1\t1\t1\t2\t10\t20\t30\t40\tNaN\tSECOND\n",
                    "5\t1\t1\t1\t1\t2\t10\t20\t30\t40\tbad\tSECOND\n"):
            with self.subTest(row=row), patch.object(ocr.shutil, "which", return_value="tesseract"), patch.object(
                ocr.subprocess, "run", side_effect=[completed("ANCHOR SECOND\n"), completed(TSV + row)]
            ):
                code, result = self.call_main([str(self.image)])
            self.assertNotEqual(code, 0)
            self.assertIn("error", result)

    def test_real_tesseract_with_public_profile_and_generated_image(self):
        profile = ROOT / "config/model-profiles/local-2026-09-05.yaml"
        public = yaml.safe_load(profile.read_text(encoding="utf-8"))
        self.assertIn("tessdata_dir", public["ocr"])
        if not shutil.which("tesseract") or not Path(public["ocr"]["tessdata_dir"]).is_dir():
            self.skipTest("real Tesseract or public tessdata directory is unavailable")
        from PIL import Image, ImageDraw, ImageFont
        image = Image.new("RGB", (1200, 180), "white")
        ImageDraw.Draw(image).text((35, 55), "OCR PROFILE ANCHOR 123", fill="black", font=ImageFont.load_default(size=52))
        image.save(self.image)
        probe_run = subprocess.run([sys.executable, "-B", str(SCRIPT), "--probe", "--profile", str(profile), "--lang", "eng+chi_sim"],
                                   capture_output=True, text=True, encoding="utf-8", check=False, timeout=60)
        self.assertEqual(probe_run.returncode, 0, probe_run.stdout + probe_run.stderr)
        probe = json.loads(probe_run.stdout)
        self.assertTrue(probe["capability"], probe)
        result = subprocess.run([sys.executable, "-B", str(SCRIPT), str(self.image), "--profile", str(profile), "--lang", "eng"],
                                capture_output=True, text=True, encoding="utf-8", check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = json.loads(result.stdout)
        self.assertIn("OCR PROFILE ANCHOR 123", output["text"])
        self.assertGreaterEqual(len(output["words"]), 4)
        self.assertTrue(all(word["w"] > 0 and word["h"] > 0 for word in output["words"]))
        print(json.dumps({"real_ocr_text": output["text"], "word_boxes": len(output["words"]),
                          "probe_languages": len(probe["languages"]), "warnings": output["loss_receipt"]["params"]["warnings"]}, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
