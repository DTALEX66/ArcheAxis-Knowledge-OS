"""Shared-input proposals must bind bytes and isolate each retry's output."""
import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET

from scripts.runtime import sandbox_inputs as subject


class SharedSandboxInputs(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sandbox-inputs-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "项目 & space"
        self.dev = self.root / ".project-local"
        self.stage = self.dev / "runs" / "retained" / "source"
        for folder in subject.ROOTS.values():
            (self.stage / folder).mkdir(parents=True)
        self.files = {
            r"C:\AAOSInput\guest-local-pinned-lifecycle.ps1": b"# synthetic guest; never executed\n",
            r"C:\AAOSInput\repo\.git\HEAD": b"fixture-source-identity\n",
            r"C:\AAOSInput\repo\source.py": b"fixture = True\n",
            r"C:\AAOSInstall\installer.exe": b"synthetic installer; not executable",
            r"C:\AAOSTools\pwsh.exe": b"synthetic PowerShell; not executable",
        }
        self.rows = []
        for path, data in self.files.items():
            folder, relative = subject.member(path)
            dest = self.stage / folder / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            self.rows.append({"path": path, "bytes": len(data),
                              "sha256": hashlib.sha256(data).hexdigest()})
        self.write_manifest()

    def write_manifest(self):
        self.manifest = self.stage / "input/inputs.json"
        self.manifest.write_text(json.dumps({"approval": "ROOT_REVIEWED_FOR_THIS_FRESH_RUN",
                                             "scope": "SYNTHETIC_ONLY", "files": self.rows}),
                                 encoding="utf-8")
        self.pin = hashlib.sha256(self.manifest.read_bytes()).hexdigest()

    def paths(self, name):
        identity = hashlib.sha256(str(self.root).casefold().encode()).hexdigest()[:10]
        run = self.dev / "runs" / identity / name
        (run / "artifacts").mkdir(parents=True)
        (run / "run-metadata.json").write_text(json.dumps({
            "owner": "ArcheAxis-Knowledge-OS", "worktree_root": str(self.root),
            "run_id": name}), encoding="utf-8")
        return {"root": self.root, "dev": self.dev, "run": run, "artifacts": run / "artifacts"}

    def test_two_retries_share_original_bytes_but_have_distinct_empty_outputs(self):
        before = {p: p.read_bytes() for p in self.stage.rglob("*") if p.is_file()}
        results = [subject.prepare(self.paths(name), self.stage, self.pin) for name in ("retry1", "retry2")]
        for result in results:
            self.assertEqual(result["status"], "SHARED_INPUT_PROPOSAL_ONLY", result)
            self.assertEqual(result["payload_bytes_copied"], 0)
            self.assertEqual(result["guest_write_isolation"], "NOT_EXECUTED")
            self.assertEqual(result["launcher"], "SHARED_MAPPING_LAUNCHER_NOT_QUALIFIED")
            xml = ET.parse(result["config"]).getroot()
            maps = xml.findall("./MappedFolders/MappedFolder")
            self.assertEqual(len(maps), 4)
            self.assertEqual([m.findtext("ReadOnly") for m in maps], ["true"] * 3 + ["false"])
            self.assertEqual({m.findtext("HostFolder") for m in maps[:3]},
                             {str(self.stage / folder) for folder in subject.ROOTS.values()})
            self.assertEqual(maps[3].findtext("HostFolder"), result["output"])
            self.assertEqual(list(Path(result["output"]).iterdir()), [])
            for name in ("Networking", "VGpu", "AudioInput", "VideoInput",
                         "PrinterRedirection", "ClipboardRedirection"):
                self.assertEqual(xml.findtext(name), "Disable")
            self.assertIn(self.pin, xml.findtext("./LogonCommand/Command"))
            self.assertFalse(list(Path(result["config"]).parent.rglob("*.exe")))
        self.assertNotEqual(results[0]["output"], results[1]["output"])
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_declared_private_state_rejected_before_any_payload_read(self):
        self.rows.append({"path": r"C:\AAOSInput\repo\.mimosa\session.json", "bytes": 1, "sha256": "a" * 64})
        self.write_manifest()
        original = subject.identity
        def guard(path):
            self.assertEqual(path, self.manifest, "No declared payload may be opened")
            return original(path)
        with patch.object(subject, "identity", side_effect=guard):
            result = subject.prepare(self.paths("private"), self.stage, self.pin)
        self.assertEqual(result["status"], "FAIL_CLOSED")
        self.assertIn("before access", result["error"])
        self.assertFalse((self.paths_for_result("private") / "lifecycle.wsb.proposed").exists())

    def paths_for_result(self, name):
        identity = hashlib.sha256(str(self.root).casefold().encode()).hexdigest()[:10]
        return self.dev / "runs" / identity / name / "artifacts"

    def test_undeclared_private_directory_not_entered(self):
        private = self.stage / "input/repo/.mimosa"
        private.mkdir()
        with patch.object(subject, "identity", side_effect=AssertionError("Must not hash payloads")):
            # Inventory itself rejects before it enumerates private contents.
            with self.assertRaisesRegex(ValueError, "before access"):
                subject.inventory(self.stage / "input", "AAOSInput")

    def test_tampering_is_not_a_cache_hit(self):
        target = self.stage / "package/installer.exe"
        target.write_bytes(b"X" * target.stat().st_size)
        result = subject.prepare(self.paths("changed"), self.stage, self.pin)
        self.assertEqual(result["status"], "FAIL_CLOSED")
        self.assertIn("bytes/hash", result["error"])
        self.assertFalse((self.paths_for_result("changed") / "sandbox-output").exists())

    def test_manifest_pin_extra_and_missing_members_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "Pinned"):
            subject.inspect_stage(self.stage, self.dev, "0" * 64)
        extra = self.stage / "tools/unlisted.exe"
        extra.write_bytes(b"fixture")
        with self.assertRaisesRegex(ValueError, "inventory"):
            subject.inspect_stage(self.stage, self.dev, self.pin)
        extra.unlink()
        (self.stage / "tools/pwsh.exe").unlink()
        with self.assertRaisesRegex(ValueError, "inventory"):
            subject.inspect_stage(self.stage, self.dev, self.pin)

    def test_duplicate_member_and_json_keys_rejected(self):
        self.rows.append(dict(self.rows[-1]))
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            subject.inspect_stage(self.stage, self.dev, self.pin)
        self.manifest.write_text('{"files": [], "files": []}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate JSON"):
            subject.read_manifest(self.manifest)

    def test_windows_aliases_and_private_names_rejected(self):
        for tail in (r"repo\..\outside", "repo/file", "repo\\file.", "repo\\file ",
                     "repo\\file:stream", "repo\\NUL", "repo\\.env.local", "repo\\.hermes\\state",
                     "repo\\.project-local\\old", "repo\\node_modules\\old", "repo\\.codex\\state"):
            with self.subTest(tail=tail), self.assertRaises(ValueError):
                subject.member("C:\\AAOSInput\\" + tail)

    def test_existing_evidence_and_output_are_never_reused(self):
        paths = self.paths("existing")
        result = subject.prepare(paths, self.stage, self.pin)
        saved = Path(result["config"]).read_bytes()
        with self.assertRaisesRegex(ValueError, "Fresh"):
            subject.prepare(paths, self.stage, self.pin)
        self.assertEqual(saved, Path(result["config"]).read_bytes())

    def test_external_source_and_overlapping_writable_run_rejected(self):
        with self.assertRaisesRegex(ValueError, "boundary"):
            subject.inspect_stage(self.root.parent, self.dev, self.pin)
        paths = self.paths("overlap")
        with self.assertRaisesRegex(ValueError, "overlaps"):
            subject.prepare(paths, paths["run"], self.pin)

    def test_private_source_stage_rejected_before_filesystem_access(self):
        with (patch.object(subject, "checked", side_effect=AssertionError("Must not inspect private ancestors")),
              self.assertRaisesRegex(ValueError, "before access")):
            subject.inspect_stage(self.dev / "runs/retained/.mimosa/source", self.dev, self.pin)

    def test_wrong_run_ownership_cannot_create_a_proposal(self):
        paths = self.paths("wrong-owner")
        (paths["run"] / "run-metadata.json").write_text('[]', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "ownership"):
            subject.prepare(paths, self.stage, self.pin)
        self.assertFalse((paths["artifacts"] / "lifecycle.wsb.proposed").exists())

    def test_hardlink_input_rejected(self):
        target = self.stage / "tools/pwsh.exe"
        os.link(target, self.stage / "tools/alias.exe")
        with self.assertRaisesRegex(ValueError, "independent"):
            subject.inspect_stage(self.stage, self.dev, self.pin)

    @unittest.skipUnless(os.name == "nt", "Windows junction regression")
    def test_junction_input_rejected_without_following(self):
        target = self.root / "outside-stage"
        target.mkdir()
        link = self.stage / "tools/linked"
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        try:
            with self.assertRaisesRegex(ValueError, "[Ll]inked"):
                subject.inspect_stage(self.stage, self.dev, self.pin)
        finally:
            link.rmdir()


if __name__ == "__main__":
    unittest.main()
