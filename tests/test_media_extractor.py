from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from shared.approved_paths import ApprovedRoots
from shared.media_extractor import extract_audio_track


def test_extract_audio_track_creates_asr_ready_wav_with_real_ffmpeg(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("ffmpeg is not installed")

    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    output.mkdir()
    video = source / "tone.mp4"
    subprocess.run(
        [
            ffmpeg,
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=32x32:d=0.25",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=0.25",
            "-shortest",
            "-c:v",
            "mpeg4",
            "-c:a",
            "aac",
            str(video),
            "-y",
            "-loglevel",
            "error",
        ],
        check=True,
        timeout=30,
    )

    result = extract_audio_track(
        str(video),
        str(output),
        approved_roots=ApprovedRoots(source_roots=[source], output_roots=[output]),
    )

    audio = Path(result["output_file"])
    assert result == {
        "video": str(video),
        "output_file": str(audio),
        "sample_rate_hz": 16000,
        "channels": 1,
        "codec": "pcm_s16le",
    }
    assert audio.parent == output.resolve()
    assert audio.read_bytes().startswith(b"RIFF")
    assert audio.stat().st_size > 44
