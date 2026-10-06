"""The shared tool resolver workers must use instead of guessing PATH.

R6 A02 requires a tool resolver over *exact paths* and explicitly forbids PATH
guessing. `services/python-workers` never got one: OCR calls
`shutil.which("tesseract")` and derives a binary from `TESSDATA_PREFIX`, video calls
`shutil.which("ffmpeg")`, and ASR derives a model directory from the checkout's
parent. On this machine all three engines are installed and declared in
`config/environment/capability-requirements.yaml`, yet all three report "not found",
because nothing reads the declaration.

These tests pin the resolver's contract: an explicit override wins, a declared path
resolves relative to the declared external root, a path may never escape that root,
and a missing tool is a named failure rather than a fall back to PATH.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MODULE = (Path(__file__).resolve().parents[2]
          / "services" / "python-workers" / "tool_paths.py")


def load():
    spec = importlib.util.spec_from_file_location("worker_tool_paths", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MANIFEST = """
schema_version: '1.0'
capabilities:
  toolchains:
    - name: tesseract
      healthcheck_command: 'tesseract --version'
      external_paths: ["10-toolchains/scoop/apps/tesseract/current/tesseract.exe"]
    - name: escapee
      healthcheck_command: 'escapee --version'
      external_paths: ["../../outside/escapee.exe"]
  models:
    - name: faster-whisper-large-v3-turbo
      external_paths: ["Model library/whisper/faster-whisper-large-v3-turbo"]
"""


@pytest.fixture()
def declared(tmp_path, monkeypatch):
    """A declared registry plus a real external root holding the tools it names.

    The layout mirrors the real one: `{root}/10-toolchains/...` for executables and
    `{root}/Model library/...` for model assets, with the manifest at the root.
    """
    external = tmp_path
    tesseract = external / "10-toolchains" / "scoop" / "apps" / "tesseract" / "current" / "tesseract.exe"
    tesseract.parent.mkdir(parents=True)
    tesseract.write_bytes(b"stub")
    model = external / "Model library" / "whisper" / "faster-whisper-large-v3-turbo"
    model.mkdir(parents=True)
    (model / "model.bin").write_bytes(b"stub")
    manifest = external / "capability-requirements.yaml"
    manifest.write_text(MANIFEST, encoding="utf-8")
    monkeypatch.setenv("ARCHEAXIS_EXTERNAL_ROOT", str(external))
    monkeypatch.delenv("OS_EXTERNAL_CONFIG", raising=False)
    monkeypatch.setenv("ARCHEAXIS_CAPABILITY_MANIFEST", str(manifest))
    return {"module": load(), "external": external, "tesseract": tesseract, "model": model}


def test_resolves_a_declared_executable_without_consulting_path(declared, monkeypatch):
    module = declared["module"]
    monkeypatch.setattr(module.shutil, "which", lambda name: None)
    assert Path(module.tool_path("tesseract")).resolve() == declared["tesseract"].resolve()


def test_resolves_a_declared_model_directory(declared, monkeypatch):
    module = declared["module"]
    monkeypatch.setattr(module.shutil, "which", lambda name: None)
    resolved = Path(module.tool_path("faster-whisper-large-v3-turbo"))
    assert resolved.resolve() == declared["model"].resolve()


def test_explicit_override_wins_over_the_declaration(declared, monkeypatch):
    module = declared["module"]
    override = declared["external"] / "elsewhere" / "tesseract.exe"
    override.parent.mkdir(parents=True)
    override.write_bytes(b"stub")
    monkeypatch.setenv("TESSERACT_CMD", str(override))
    assert Path(module.tool_path("tesseract")).resolve() == override.resolve()


def test_a_declared_path_may_not_escape_the_external_root(declared):
    module = declared["module"]
    with pytest.raises(module.ToolNotFound) as error:
        module.tool_path("escapee")
    assert "escapee" in str(error.value)


def test_a_missing_tool_is_named_and_the_default_never_consults_path(declared, monkeypatch):
    module = declared["module"]
    calls: list[str] = []

    def which(name):
        calls.append(name)
        return "/usr/bin/something-unrelated"

    monkeypatch.setattr(module.shutil, "which", which)
    with pytest.raises(module.ToolNotFound) as error:
        module.tool_path("not-declared-anywhere")
    assert "not-declared-anywhere" in str(error.value)
    assert calls == [], "the default resolution path must not consult PATH at all"


def test_path_guessing_is_opt_in_and_never_substitutes_a_binary(declared, monkeypatch):
    """`guess_on_path` may only *report* what PATH offers; it must not return it."""
    module = declared["module"]
    monkeypatch.setattr(module.shutil, "which", lambda name: "/usr/bin/something-unrelated")
    with pytest.raises(module.ToolNotFound) as error:
        module.tool_path("not-declared-anywhere", guess_on_path=True)
    message = str(error.value)
    assert "something-unrelated" in message, "the report should say what PATH offers"
    assert "no declared path resolved" in message


def test_no_declared_root_is_a_named_failure_not_a_guess(tmp_path, monkeypatch):
    module = load()
    monkeypatch.delenv("ARCHEAXIS_EXTERNAL_ROOT", raising=False)
    monkeypatch.delenv("OS_EXTERNAL_CONFIG", raising=False)
    monkeypatch.setenv("ARCHEAXIS_CAPABILITY_MANIFEST", str(tmp_path / "absent.yaml"))
    with pytest.raises(module.ToolNotFound) as error:
        module.tool_path("tesseract")
    assert "tesseract" in str(error.value)
