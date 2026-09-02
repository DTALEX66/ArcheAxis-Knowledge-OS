"""Regression tests for local ASR model discovery."""

from __future__ import annotations


def test_resolve_model_dir_discovers_standard_sibling_shared_library(tmp_path, monkeypatch) -> None:
    """Portable installs use the sibling Model library when no override is set."""
    from app.ingestion import asr_adapter

    project = tmp_path / "All projects" / "ArcheAxis-Knowledge-OS"
    module_file = project / "app" / "ingestion" / "asr_adapter.py"
    shared = project.parent / "Model library" / "whisper"
    shared.mkdir(parents=True)

    monkeypatch.delenv("ARCHEAXIS_ASR_MODEL_DIR", raising=False)
    monkeypatch.delenv("ARCHEAXIS_MODEL_LIBRARY_DIR", raising=False)
    monkeypatch.delenv("ARCHEAXIS_EXTERNAL_ROOT", raising=False)
    monkeypatch.delenv("OS_EXTERNAL_CONFIG", raising=False)
    monkeypatch.setattr(asr_adapter, "__file__", str(module_file))

    assert asr_adapter.resolve_model_dir() == shared


def test_resolve_model_dir_discovers_shared_library_from_packaged_runtime_depth(tmp_path, monkeypatch) -> None:
    """The Green site-packages layout must not change shared-model discovery."""
    from app.ingestion import asr_adapter

    all_projects = tmp_path / "All projects"
    module_file = (
        all_projects
        / "ArcheAxis.Knowledge.Green-x64"
        / "runtime"
        / "python"
        / "Lib"
        / "site-packages"
        / "app"
        / "ingestion"
        / "asr_adapter.py"
    )
    shared = all_projects / "Model library" / "whisper"
    shared.mkdir(parents=True)

    monkeypatch.delenv("ARCHEAXIS_ASR_MODEL_DIR", raising=False)
    monkeypatch.delenv("ARCHEAXIS_MODEL_LIBRARY_DIR", raising=False)
    monkeypatch.delenv("ARCHEAXIS_EXTERNAL_ROOT", raising=False)
    monkeypatch.delenv("OS_EXTERNAL_CONFIG", raising=False)
    monkeypatch.setattr(asr_adapter, "__file__", str(module_file))

    assert asr_adapter.resolve_model_dir() == shared


def test_resolve_model_dir_discovers_library_adjacent_to_configured_external_root(
    tmp_path, monkeypatch
) -> None:
    """The standard shared-tool environment must also locate its sibling model library."""
    from app.ingestion import asr_adapter
    from shared.config import config

    all_projects = tmp_path / "All projects"
    external_root = all_projects / "OS External Configuration"
    shared = all_projects / "Model library" / "whisper"
    shared.mkdir(parents=True)

    monkeypatch.delenv("ARCHEAXIS_ASR_MODEL_DIR", raising=False)
    monkeypatch.delenv("ARCHEAXIS_MODEL_LIBRARY_DIR", raising=False)
    monkeypatch.delenv("OS_EXTERNAL_CONFIG", raising=False)
    monkeypatch.setenv("ARCHEAXIS_EXTERNAL_ROOT", str(external_root))
    monkeypatch.setattr(asr_adapter, "__file__", str(tmp_path / "runtime" / "asr_adapter.py"))
    monkeypatch.setattr(config, "get", lambda _key, _default="": "")

    assert asr_adapter.resolve_model_dir() == shared
