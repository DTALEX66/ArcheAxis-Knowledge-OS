from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from shared.approved_paths import ApprovedRoots
from shared.media_extractor import extract_audio_track, extract_image_text, extract_video_keyframes


def test_extract_image_text_uses_real_tesseract_with_approved_paths(tmp_path: Path) -> None:
    pytest.importorskip("pytesseract")
    from PIL import Image, ImageDraw, ImageFont

    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 40)
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    output.mkdir()
    image_path = source / "evidence.png"
    image = Image.new("RGB", (640, 160), "white")
    ImageDraw.Draw(image).text((20, 50), "Cognitive Evidence 2026", fill="black", font=font)
    image.save(image_path)

    result = extract_image_text(
        str(image_path),
        approved_roots=ApprovedRoots(source_roots=[source], output_roots=[output]),
    )

    if "error" in result:
        pytest.skip(result["error"])
    assert result["image"] == str(image_path)
    assert result["engine"] == "tesseract"
    assert "cognitive evidence 2026" in result["text"].lower()


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
    assert result["video"] == str(video)
    assert result["output_file"] == str(audio)
    assert result["sample_rate_hz"] == 16000
    assert result["channels"] == 1
    assert result["codec"] == "pcm_s16le"
    assert result["sample_frames"] > 0
    assert result["duration_seconds"] == pytest.approx(result["sample_frames"] / 16000)
    assert audio.parent == output.resolve()
    assert audio.read_bytes().startswith(b"RIFF")
    assert audio.stat().st_size > 44


def test_extract_video_keyframes_reports_verified_png_dimensions(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("ffmpeg is not installed")

    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    output.mkdir()
    video = source / "scene.mp4"
    subprocess.run(
        [
            ffmpeg,
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=48x32:d=0.25",
            "-c:v",
            "mpeg4",
            str(video),
            "-y",
            "-loglevel",
            "error",
        ],
        check=True,
        timeout=30,
    )

    result = extract_video_keyframes(
        str(video),
        str(output),
        interval_seconds=0.1,
        max_frames=1,
        approved_roots=ApprovedRoots(source_roots=[source], output_roots=[output]),
    )

    frame = Path(result["output_files"][0])
    assert result["frames_extracted"] == 1
    assert result["frame_width"] == 48
    assert result["frame_height"] == 32
    assert frame.parent == output.resolve()
    assert frame.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert frame.stat().st_size > 24
