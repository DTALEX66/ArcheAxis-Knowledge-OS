"""Real local ASR against the registered shared model library.

`media/worker_transcribe.py` resolves its model directory from
`PROJECT_ROOT.parent / "Model library" / "whisper" / "faster-whisper-large-v3-turbo"`.
That is correct for the normal repository layout, but it is a *derived* path rather
than the registered one, so it silently misses in any other checkout shape (a
worktree resolves it to `.project-local/worktrees/Model library/...`).  The same
worker also honours `--model-dir` and `ARCHEAXIS_ASR_MODEL_DIR`, which is how this
probe reaches the real model.

This probe therefore does two things in one run:

1. reproduces the default-path miss (so the defect is demonstrated, not asserted);
2. transcribes one real audio file through the real engine with the model directory
   taken from the declared external resource, and reports the recognised text.

The model, the audio and the engine are all real; nothing here is a fixture and no
network call is made.  The audio origin is recorded with its sha256 so the receipt
names its source.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WORKER = REPO / "services" / "python-workers" / "media" / "worker_transcribe.py"

# Both the model directory and the audio root are external, Owner-supplied resources,
# so they are read from the environment rather than baked in - the same rule the
# product should follow (R6 A02: exact paths, no PATH guessing). The model path is
# the one declared in OS External Configuration/00-registry/project-tool-index.yaml
# and config/environment/capability-requirements.yaml.
MODEL_DIR_ENV = "ARCHEAXIS_ASR_MODEL_DIR"
AUDIO_ROOT_ENV = "ARCHEAXIS_ASR_AUDIO_ROOT"
_raw_model = os.environ.get(MODEL_DIR_ENV, "").strip()
_raw_audio = os.environ.get(AUDIO_ROOT_ENV, "").strip()
MODEL_DIR = Path(_raw_model) if _raw_model else None
AUDIO_ROOT = Path(_raw_audio) if _raw_audio else None
MAX_AUDIO_BYTES = int(os.environ.get("ARCHEAXIS_ASR_MAX_BYTES", str(32 * 1024 * 1024)))
LANGUAGE = os.environ.get("ARCHEAXIS_ASR_LANGUAGE", "zh")
TIMEOUT = float(os.environ.get("ARCHEAXIS_ASR_TIMEOUT", "900"))


def pick_audio() -> Path | None:
    """Smallest real audio file, so the run stays bounded."""
    best: tuple[int, Path] | None = None
    for ext in (".mp3", ".m4a", ".wav", ".flac"):
        for path in AUDIO_ROOT.rglob(f"*{ext}"):
            with contextlib.suppress(OSError):
                size = path.stat().st_size
                if size <= MAX_AUDIO_BYTES and (best is None or size < best[0]):
                    best = (size, path)
    return best[1] if best else None


def _child_env() -> dict:
    """Force UTF-8 on the worker's stdio.

    The worker prints recognised Chinese text.  On a Windows console the child's
    default stdio encoding is the ANSI code page (cp936 here), which is not UTF-8,
    so decoding its output as UTF-8 raises and the real result is lost.  Pinning the
    child rather than guessing afterwards keeps recognised text intact.
    """
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def _run(argv: list[str], timeout: float) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout, cwd=str(REPO),
                          env=_child_env())


def probe(model_dir: str | None) -> dict:
    argv = [sys.executable, "-B", str(WORKER), "--probe"]
    if model_dir:
        argv += ["--model-dir", model_dir]
    done = _run(argv, 300)
    with contextlib.suppress(json.JSONDecodeError):
        return json.loads((done.stdout or "").strip().splitlines()[-1])
    return {"raw": (done.stdout or "")[-300:], "error": (done.stderr or "")[-300:]}


def transcribe(audio: Path) -> dict:
    begin = time.monotonic()
    done = _run([sys.executable, "-B", str(WORKER), str(audio),
                 "--model-dir", str(MODEL_DIR), "--language", LANGUAGE], TIMEOUT)
    elapsed = time.monotonic() - begin
    payload: dict = {}
    for line in reversed((done.stdout or "").strip().splitlines()):
        with contextlib.suppress(json.JSONDecodeError):
            payload = json.loads(line)
            break
    result = {
        "returncode": done.returncode,
        "elapsed_s": round(elapsed, 1),
        "keys": sorted(payload.keys()),
    }
    if payload:
        text = str(payload.get("text") or "")
        result["text_chars"] = len(text)
        result["text_head"] = text[:200]
        for key in ("engine", "engine_version", "model", "segments", "loss_receipt"):
            if payload.get(key) is not None:
                value = payload[key]
                result[key] = (value if not isinstance(value, (list, dict))
                               else (len(value) if isinstance(value, list) else value))
    else:
        result["error"] = (done.stderr or "")[-400:]
    return result


def main() -> int:
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")
    if not WORKER.is_file():
        print(json.dumps({"ok": False, "blocked": "ASR worker missing", "path": str(WORKER)}))
        return 2
    if MODEL_DIR is None or not MODEL_DIR.is_dir():
        print(json.dumps({
            "ok": False,
            "blocked": "ASR model directory not configured or absent",
            "env": MODEL_DIR_ENV, "value": _raw_model,
            "note": "point this at the declared whisper model directory",
        }, ensure_ascii=False))
        return 2
    if AUDIO_ROOT is None or not AUDIO_ROOT.is_dir():
        print(json.dumps({
            "ok": False,
            "blocked": "audio root not configured or absent",
            "env": AUDIO_ROOT_ENV, "value": _raw_audio,
        }, ensure_ascii=False))
        return 2

    receipt: dict = {
        "ok": False,
        "worker": str(WORKER.relative_to(REPO)),
        "declared_model_dir": str(MODEL_DIR),
        "model_dir_present": MODEL_DIR.is_dir(),
        "language": LANGUAGE,
    }
    receipt["probe_default_path"] = probe(None)
    receipt["probe_declared_model_dir"] = probe(str(MODEL_DIR))

    audio = pick_audio()
    if audio is None:
        receipt["blocked"] = "no real audio under AUDIO_ROOT"
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 2
    payload = audio.read_bytes()
    receipt["audio"] = {
        "origin": str(audio),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
    receipt["transcription"] = transcribe(audio)
    receipt["ok"] = bool(receipt["transcription"].get("text_chars"))
    receipt["evidence_level"] = "REAL_MODEL_REAL_AUDIO"
    out = REPO / ".project-local" / "runs" / "asr" / "real-asr-receipt.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, default=str) + "\n",
                   encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2, default=str))
    print(f"\nreceipt: {out}")
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
