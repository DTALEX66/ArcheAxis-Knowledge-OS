"""The video and ASR workers must resolve engines and models from the declaration.

Same axis as the OCR fix: R6 A02 requires a tool/model resolver over exact paths and
forbids PATH guessing, but `worker_video.py` used bare `shutil.which("ffmpeg")` and
`worker_transcribe.py` derived its model directory from the checkout's parent. Both
therefore failed on a machine where ffmpeg is installed and the whisper model is on
disk, simply because nothing read the declaration.

These tests exercise the real worker modules (loaded by path, as the Core launches
them) with a synthetic external registry, so they do not depend on this machine.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VIDEO = ROOT / "services" / "python-workers" / "media" / "worker_video.py"
TRANSCRIBE = ROOT / "services" / "python-workers" / "media" / "worker_transcribe.py"

MANIFEST = """
capabilities:
  toolchains:
    - name: ffmpeg
      external_paths: ["10-toolchains/scoop/apps/ffmpeg/current/bin/ffmpeg.exe"]
"""


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def external(tmp_path, monkeypatch):
    """A declared external root holding ffmpeg, plus its sibling model library.

    Mirrors the real layout: the shared `Model library` sits *beside* the external
    configuration root, not inside it.
    """
    root = tmp_path / "OS External Configuration"
    binary = root / "10-toolchains" / "scoop" / "apps" / "ffmpeg" / "current" / "bin" / "ffmpeg.exe"
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"stub")
    model = tmp_path / "Model library" / "whisper" / "faster-whisper-large-v3-turbo"
    model.mkdir(parents=True)
    (model / "model.bin").write_bytes(b"stub")
    manifest = root / "capability-requirements.yaml"
    manifest.write_text(MANIFEST, encoding="utf-8")
    monkeypatch.setenv("ARCHEAXIS_EXTERNAL_ROOT", str(root))
    monkeypatch.delenv("OS_EXTERNAL_CONFIG", raising=False)
    monkeypatch.setenv("ARCHEAXIS_CAPABILITY_MANIFEST", str(manifest))
    monkeypatch.delenv("FFMPEG_CMD", raising=False)
    monkeypatch.delenv("ARCHEAXIS_FFMPEG_CMD", raising=False)
    monkeypatch.delenv("ARCHEAXIS_ASR_MODEL_DIR", raising=False)
    return {"root": root, "binary": binary, "model": model}


def test_video_resolves_ffmpeg_from_the_declaration_without_path(external, monkeypatch):
    module = load("worker_video_t", VIDEO)
    monkeypatch.setattr(module.shutil, "which", lambda name: None)
    assert Path(module._ffmpeg()).resolve() == external["binary"].resolve()


def test_video_probe_reports_the_declared_engine(external, monkeypatch):
    module = load("worker_video_t2", VIDEO)
    monkeypatch.setattr(module.shutil, "which", lambda name: None)
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **k: type(
        "R", (), {"returncode": 0, "stdout": "ffmpeg version 8.1.2\n", "stderr": ""})())
    report = module.probe()
    assert report["capability"] is True
    assert Path(report["ffmpeg"]).resolve() == external["binary"].resolve()


def test_video_override_still_wins(external, monkeypatch):
    module = load("worker_video_t3", VIDEO)
    override = external["root"] / "custom" / "ffmpeg.exe"
    override.parent.mkdir(parents=True)
    override.write_bytes(b"stub")
    monkeypatch.setenv("FFMPEG_CMD", str(override))
    assert Path(module._ffmpeg()).resolve() == override.resolve()


def test_transcribe_resolves_the_declared_model_directory(external, monkeypatch):
    """The declared sibling of the external root holds the model the worker needs."""
    module = load("worker_transcribe_t", TRANSCRIBE)
    monkeypatch.setattr(module, "DEFAULT_MODEL_DIR",
                        external["root"] / "Model library" / "whisper" / "faster-whisper-large-v3-turbo")
    assert module._model_dir(None).resolve() == external["model"].resolve()


def test_transcribe_explicit_path_wins_over_the_declaration(external, monkeypatch):
    module = load("worker_transcribe_t2", TRANSCRIBE)
    other = external["root"] / "other-model"
    other.mkdir()
    (other / "model.bin").write_bytes(b"stub")
    assert module._model_dir(str(other)).resolve() == other.resolve()


def test_transcribe_names_a_missing_model_instead_of_guessing(tmp_path, monkeypatch):
    """With no explicit path, no override, no declaration and no declared root, the
    failure names the model instead of falling back to another location on disk."""
    module = load("worker_transcribe_t3", TRANSCRIBE)
    monkeypatch.delenv("ARCHEAXIS_ASR_MODEL_DIR", raising=False)
    monkeypatch.delenv("ARCHEAXIS_EXTERNAL_ROOT", raising=False)
    monkeypatch.delenv("OS_EXTERNAL_CONFIG", raising=False)
    monkeypatch.setenv("ARCHEAXIS_CAPABILITY_MANIFEST", str(tmp_path / "absent.yaml"))
    monkeypatch.setattr(module, "DEFAULT_MODEL_DIR", tmp_path / "absent-model")
    with pytest.raises(ValueError) as error:
        module._model_dir(None)
    assert "ASR model directory not found" in str(error.value)


def test_transcribe_derives_the_model_from_the_declared_root(external, monkeypatch):
    """A worktree layout must not hide a model that the declared root can locate.

    `DEFAULT_MODEL_DIR` is derived from the checkout's parent, which points at an
    absent sibling in a worktree. The declared external root is the authoritative
    base, so it supplies the model even when the layout-derived path does not exist.
    """
    module = load("worker_transcribe_t4", TRANSCRIBE)
    monkeypatch.setattr(module, "DEFAULT_MODEL_DIR", external["root"] / "absent-sibling")
    assert module._model_dir(None).resolve() == external["model"].resolve()
