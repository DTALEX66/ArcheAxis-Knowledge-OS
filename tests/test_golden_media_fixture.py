"""G0: project-owned audio/video corpus entries retain bytes and transcript truth."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "fixtures" / "golden"
MANIFEST = GOLDEN / "manifest.json"


def test_golden_audio_and_video_fixtures_have_project_owned_bytes_and_time_anchor_truth() -> None:
    records = json.loads(MANIFEST.read_text(encoding="utf-8"))["fixtures"]

    for name, expected_format in (("golden-audio-anchor.wav", "audio/wav"), ("golden-video-anchor.mp4", "video/mp4")):
        fixture = GOLDEN / name
        record = records[name]
        assert record["format"] == expected_format
        assert record["rights_basis"] == "project-authored synthetic test fixture"
        assert record["privacy"] == "no personal data"
        assert record["expected"]["text"] == "Learning evidence anchor"
        assert record["expected"]["anchor"] == "time_range=start_s/end_s"
        assert hashlib.sha256(fixture.read_bytes()).hexdigest() == record["sha256"]
