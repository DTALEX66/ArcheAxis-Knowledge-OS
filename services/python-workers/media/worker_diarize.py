#!/usr/bin/env python3
"""ArcheAxis vNext speaker-diarization worker (F10): who spoke when, or nothing at all.

The runtime is `sherpa-onnx`'s offline diarizer, which needs **two** ONNX assets - a pyannote
segmentation model and a speaker-embedding model. Neither is in the shared model library yet, and the
publishers that ship them in ONNX form are unreachable from this host (measured 2026-10-07, recorded in
`docs/integrations/AAOS_SPEAKER_MODEL_SUPPLY_20261007.md`). So the rule for this worker is that it
either reports a real diarization or reports exactly which artifact is missing. It never emits a
plausible segment: an invented `speaker 0` would be indistinguishable from a result downstream, and a
count of speakers nobody measured is the kind of claim this repository's rules forbid.

Input is 16-bit mono PCM WAV. Other containers are refused by name rather than decoded through a
guess: `media.probe` already states that a header is a claim by the file, not a measurement.

Usage:
    python worker_diarize.py <input.wav> [--models-dir DIR] [--num-speakers N]
Output: {"engine","engine_version","text","structure","loss_receipt"}
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import wave
from pathlib import Path

ENGINE = "python-worker-diarize"
ENGINE_VERSION = "0.1.0"
WORKER_IDENTITY = "python-worker-diarize-ndjson"
TARGET_SAMPLE_RATE = 16000
SEGMENTATION_FILE = "segmentation-3.0.onnx"
EMBEDDING_FILE = "speaker-embedding.onnx"
SUBDIRECTORY = "sherpa-onnx/speaker-diarization"


def _library_root(override: str | None) -> Path | None:
    """The model library, by explicit argument, then by the two environment names in use."""
    for candidate in (override, os.environ.get("ARCHEAXIS_DIARIZATION_MODEL_DIR", "").strip(),
                      os.environ.get("ARCHEAXIS_MODEL_LIBRARY_DIR", "").strip()):
        if candidate:
            return Path(candidate)
    return None


def model_paths(models_dir: str | None = None) -> dict[str, Path]:
    """The exact files this capability consumes, whether or not they exist."""
    root = _library_root(models_dir)
    if root is None:
        return {}
    directory = root / SUBDIRECTORY
    return {"segmentation": directory / SEGMENTATION_FILE, "embedding": directory / EMBEDDING_FILE}


def _unavailable(reason: str, missing: list[str]) -> dict:
    """The one shape a refusal may take: no text, no segments, and the named gap."""
    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "text": "",
        "structure": {"capability": "speaker_diarization", "state": "unavailable", "segments": []},
        # The job contract accepts a fixed receipt shape, so the reason and the exact missing
        # artefacts travel inside `params`; a refusal without them is indistinguishable from a
        # silent empty result.
        "loss_receipt": {
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "params": {"state": "unavailable", "reason": reason, "missing_artifacts": missing,
                       "claim": "no diarization was produced, so none is asserted"},
        },
    }


def probe(models_dir: str | None = None) -> dict:
    """Say what this host can actually do right now, by name and by path."""
    try:
        import sherpa_onnx  # noqa: F401
    except ImportError:
        return {"capability": False, "reason": "sherpa-onnx not installed", "engine": ENGINE,
                "missing_artifacts": ["python package sherpa-onnx"]}
    paths = model_paths(models_dir)
    if not paths:
        return {"capability": False, "engine": ENGINE,
                "reason": "no model library declared (pass --models-dir or set "
                          "ARCHEAXIS_DIARIZATION_MODEL_DIR / ARCHEAXIS_MODEL_LIBRARY_DIR)",
                "missing_artifacts": [f"{SUBDIRECTORY}/{SEGMENTATION_FILE}", f"{SUBDIRECTORY}/{EMBEDDING_FILE}"]}
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        return {"capability": False, "engine": ENGINE, "reason": "speaker models missing",
                "missing_artifacts": missing}
    return {"capability": True, "engine": ENGINE, "models": {name: str(path) for name, path in paths.items()}}


def _read_pcm(path: Path) -> tuple[list[float], int]:
    """16-bit mono PCM samples normalised to [-1, 1], or a refusal naming what the file is."""
    try:
        with wave.open(str(path), "rb") as source:
            channels, width, rate, frames = source.getnchannels(), source.getsampwidth(), \
                source.getframerate(), source.getnframes()
            raw = source.readframes(frames)
    except (wave.Error, EOFError) as exc:
        raise ValueError(f"not a readable WAV file: {exc}") from exc
    if width != 2:
        raise ValueError(f"only 16-bit PCM WAV is supported, this file is {width * 8}-bit")
    if channels != 1:
        raise ValueError(f"only mono WAV is supported, this file has {channels} channels")
    if rate != TARGET_SAMPLE_RATE:
        raise ValueError(f"the diarizer consumes {TARGET_SAMPLE_RATE} Hz, this file is {rate} Hz; "
                         "resampling is not done here because a resampled buffer is not the recorded audio")
    samples = [sample / 32768.0 for sample in _int16_le(raw)]
    return samples, rate


def _int16_le(raw: bytes) -> list[int]:
    import array
    values = array.array("h")
    values.frombytes(raw[: len(raw) - len(raw) % 2])
    if sys.byteorder == "big":  # pragma: no cover - the host this runs on is little-endian
        values.byteswap()
    return list(values)


def diarize(path: str, models_dir: str | None = None, num_speakers: int = -1) -> dict:
    """Run the real diarizer, or return the refusal that explains itself."""
    status = probe(models_dir)
    if not status.get("capability"):
        return _unavailable(status["reason"], status.get("missing_artifacts", []))
    audio = Path(path)
    try:
        samples, rate = _read_pcm(audio)
    except ValueError as exc:
        return _unavailable(str(exc), [])
    import sherpa_onnx
    paths = model_paths(models_dir)
    config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(
                model=str(paths["segmentation"])),
            num_threads=1, provider="cpu"),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(
            model=str(paths["embedding"]), num_threads=1, provider="cpu"),
        clustering=sherpa_onnx.FastClusteringConfig(num_clusters=num_speakers),
        min_duration_on=0.3, min_duration_off=0.5)
    try:
        result = sherpa_onnx.OfflineSpeakerDiarization(config).process(samples)
    except Exception as exc:  # a model that will not load is a supply fact, not a result
        return _unavailable(f"diarizer failed to run: {exc}", [])
    segments = [{"speaker": int(item.speaker), "start": float(item.start), "end": float(item.end),
                 "duration": float(item.end) - float(item.start)}
                for item in result.sort_by_start_time()]
    lines = [f"SPK{item['speaker']}\t{round(item['start'] * 1000)}-{round(item['end'] * 1000)}"
             for item in segments]
    text = "\n".join(lines) + ("\n" if lines else "")
    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "text": text,
        "structure": {
            "capability": "speaker_diarization",
            "state": "diarized",
            "sample_rate": rate,
            "audio_seconds": round(len(samples) / rate, 3),
            "num_speakers": int(result.num_speakers),
            "num_segments": int(result.num_segments),
            "segments": segments,
            "models": status["models"],
        },
        "loss_receipt": {
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "params": {
                "state": "diarized",
                "boundaries_only": True,
                "claim": "who spoke when, from the declared ONNX models; no words, no transcript, "
                         "no identity of who the speaker is",
            },
        },
    }


def extract(path: str) -> dict:
    """The transport's entry-point shape: one input path, one contract envelope.

    A refusal is raised, not returned: empty text with no reason is indistinguishable from a
    diarization of a silent recording, which is a claim this product does not get to make.
    """
    result = diarize(path)
    if result["structure"]["state"] != "diarized":
        params = result["loss_receipt"]["params"]
        missing = ", ".join(params.get("missing_artifacts") or [])
        raise RuntimeError(f"{params['reason']}" + (f" (missing: {missing})" if missing else ""))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input", nargs="?")
    parser.add_argument("--models-dir", default=None)
    parser.add_argument("--num-speakers", type=int, default=-1,
                        help="-1 lets the clusterer decide; a wrong fixed count is not a guess to make here")
    parser.add_argument("--staging-root", type=Path, default=None)
    parser.add_argument("--artifact-root", type=Path, default=None)
    arguments = parser.parse_args(argv)
    if arguments.staging_root is not None:
        # Launched by the Core: serve the shared job loop over stdin, so a registered route can
        # actually be reached by a job instead of only existing in the tables.
        import importlib.util

        transport_path = Path(__file__).resolve().parent.parent / "transport" / "text_ndjson.py"
        spec = importlib.util.spec_from_file_location("diarize_transport", transport_path)
        if spec is None or spec.loader is None:
            print(json.dumps({"error": "transport module is missing", "engine": ENGINE}))
            return 1
        transport = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(transport)
        return transport.serve_stdio(
            WORKER_IDENTITY, ["media.diarize"], arguments.staging_root, arguments.artifact_root)
    if not arguments.input:
        parser.error("input is required outside a Core launch")
    print(json.dumps(diarize(arguments.input, arguments.models_dir, arguments.num_speakers),
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
