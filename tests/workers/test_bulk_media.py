"""BULK-0907 P14: media lane asset generation / toolchain verification (no ASR model).

Verifies the local FFmpeg toolchain path used by the media workers by generating a
short silent WAV (<=30s) in the run root and reading its duration back with ffprobe.
Transcription/ASR execution requires a project model profile invocation and is not
performed here (execution group BLOCKED, recorded); subtitle/meta sample groups are
covered by P03/P09 fixtures. Media inputs stay <=30s; no daemon, no downloads.
"""

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


def _available(name: str) -> bool:
    return shutil.which(name) is not None


class MediaToolchainBulkTests(unittest.TestCase):
    def _run(self, command, cwd):
        return subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                              timeout=60, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                              cwd=cwd)

    def test_ffmpeg_and_ffprobe_are_available(self):
        if not (_available("ffmpeg") and _available("ffprobe")):
            self.skipTest("ffmpeg/ffprobe not on PATH")
        result = self._run(["ffmpeg", "-version"], ".")
        self.assertEqual(result.returncode, 0)
        self.assertIn("ffmpeg", result.stdout.splitlines()[0].lower())

    def test_short_silent_wav_is_generated_and_has_expected_duration(self):
        if not (_available("ffmpeg") and _available("ffprobe")):
            self.skipTest("ffmpeg/ffprobe not on PATH")
        with tempfile.TemporaryDirectory(dir=os.environ["ARCHEAXIS_RUN_ROOT"]) as tmp:
            wav = Path(tmp) / "silent-2s.wav"
            result = self._run(
                ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
                 "-t", "2", str(wav)], tmp)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(wav.is_file())
            self.assertGreater(wav.stat().st_size, 0)
            digest = hashlib.sha256(wav.read_bytes()).hexdigest()
            self.assertEqual(len(digest), 64)
            probe = self._run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                               "-of", "json", str(wav)], tmp)
            self.assertEqual(probe.returncode, 0, probe.stderr)
            duration = float(json.loads(probe.stdout)["format"]["duration"])
            self.assertAlmostEqual(duration, 2.0, delta=0.2)


if __name__ == "__main__":
    unittest.main()
