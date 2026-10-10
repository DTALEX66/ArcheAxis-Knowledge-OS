"""A manifest that cannot be read must be a named failure, not "tool not found".

The resolver read `config/environment/capability-requirements.yaml` with a bare
`import yaml` inside a `try/except ImportError: return []`, and the same for a parse or
read error. On this machine a runtime interpreter without PyYAML therefore made every
declared path resolve to nothing, and the OCR worker reported

    tesseract binary not found on PATH (OCR engine unavailable)

for an engine that is installed and declared - a missing parser reported as a missing
engine. The project's rule is to fail closed with the failing component named, so these
tests pin that an unreadable manifest is loud.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MODULE = (Path(__file__).resolve().parents[2]
          / "services" / "python-workers" / "tool_paths.py")


def load():
    spec = importlib.util.spec_from_file_location("worker_tool_paths_manifest", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MANIFEST = """
capabilities:
  toolchains:
    - name: tesseract
      external_paths: ["10-toolchains/scoop/apps/tesseract/current/tesseract.exe"]
"""


@pytest.fixture()
def declared(tmp_path, monkeypatch):
    root = tmp_path
    binary = root / "10-toolchains" / "scoop" / "apps" / "tesseract" / "current" / "tesseract.exe"
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"stub")
    manifest = root / "capability-requirements.yaml"
    manifest.write_text(MANIFEST, encoding="utf-8")
    monkeypatch.setenv("ARCHEAXIS_EXTERNAL_ROOT", str(root))
    monkeypatch.delenv("OS_EXTERNAL_CONFIG", raising=False)
    monkeypatch.setenv("ARCHEAXIS_CAPABILITY_MANIFEST", str(manifest))
    return {"module": load(), "root": root, "binary": binary, "manifest": manifest}


def test_a_readable_manifest_still_resolves(declared):
    module = declared["module"]
    assert Path(module.tool_path("tesseract")).resolve() == declared["binary"].resolve()


def test_a_missing_yaml_parser_is_a_named_failure_not_a_silent_miss(declared, monkeypatch):
    """The parser is a dependency: its absence must not read as "not declared"."""
    module = declared["module"]

    real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

    def fake_import(name, *args, **kwargs):
        if name == "yaml":
            raise ImportError("no module named yaml")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    with pytest.raises(module.ManifestUnreadable) as error:
        module.tool_path("tesseract")
    message = str(error.value)
    assert "yaml" in message.lower() or "parser" in message.lower()
    assert str(declared["manifest"]) in message


def test_an_unparseable_manifest_is_a_named_failure(declared, monkeypatch):
    declared["manifest"].write_text("capabilities: [this: is: not: valid", encoding="utf-8")
    module = declared["module"]
    with pytest.raises(module.ManifestUnreadable) as error:
        module.tool_path("tesseract")
    assert str(declared["manifest"]) in str(error.value)


def test_an_absent_manifest_is_still_reported_as_no_declaration(tmp_path, monkeypatch):
    """No manifest at all is a legitimate "nothing declared", not an unreadable one."""
    module = load()
    monkeypatch.setenv("ARCHEAXIS_EXTERNAL_ROOT", str(tmp_path))
    monkeypatch.delenv("OS_EXTERNAL_CONFIG", raising=False)
    monkeypatch.setenv("ARCHEAXIS_CAPABILITY_MANIFEST", str(tmp_path / "absent.yaml"))
    with pytest.raises(module.ToolNotFound):
        module.tool_path("tesseract")


def test_declared_path_still_reports_unresolved_as_none(declared, monkeypatch):
    """A worker's fallback path keeps getting None, but the loud case stays loud."""
    module = declared["module"]
    monkeypatch.setenv("ARCHEAXIS_CAPABILITY_MANIFEST", str(declared["root"] / "absent.yaml"))
    assert module.declared_path("tesseract") is None
