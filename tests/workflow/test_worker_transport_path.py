"""Standalone workers must find the shared transport wherever the tree is rooted.

Every format worker that can be launched as a sidecar re-enters the shared NDJSON
transport in `main()`. The workers located it as
`<repo>/services/python-workers/transport/text_ndjson.py` with `<repo>` taken from a
fixed `parents[3]`. That is right for the source layout and wrong for a staged runtime,
where the workers sit at `<root>/workers/...`: `parents[3]` resolved above the runtime
root, so the worker died with `FileNotFoundError` before it could serve a job - which is
exactly what a staged run of the canvas route produced.

These tests pin the depth-independent derivation and the failure mode.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE = (Path(__file__).resolve().parents[2]
          / "services" / "python-workers" / "tool_paths.py")


def load():
    spec = importlib.util.spec_from_file_location("worker_tool_paths_transport", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_source_layout_resolves_the_real_transport():
    module = load()
    worker = MODULE.parent / "document" / "worker_canvas.py"
    resolved = module.transport_path(str(worker))
    assert resolved == (MODULE.parent / "transport" / "text_ndjson.py").resolve()
    assert resolved.is_file(), "the repository's own transport must resolve"


def test_a_staged_layout_resolves_inside_the_runtime_root(tmp_path):
    """In a staged tree the transport is the worker category's sibling directory."""
    module = load()
    worker = tmp_path / "workers" / "document" / "worker_canvas.py"
    transport = tmp_path / "workers" / "transport" / "text_ndjson.py"
    transport.parent.mkdir(parents=True)
    transport.write_bytes(b"stub")
    worker.parent.mkdir(parents=True)
    worker.write_bytes(b"stub")

    resolved = module.transport_path(str(worker))
    assert resolved == transport.resolve()
    assert resolved.is_file()


def test_a_deeper_staged_root_still_resolves(tmp_path):
    """The staged derivation must not depend on how deep the runtime root sits."""
    module = load()
    root = tmp_path / "a" / "b" / "c"
    worker = root / "workers" / "vision" / "worker_ocr.py"
    transport = root / "workers" / "transport" / "text_ndjson.py"
    transport.parent.mkdir(parents=True)
    transport.write_bytes(b"stub")
    worker.parent.mkdir(parents=True)
    worker.write_bytes(b"stub")
    assert module.transport_path(str(worker)) == transport.resolve()


def test_no_worker_still_uses_a_fixed_parent_depth_for_the_transport():
    """A regression guard: the fixed-index derivation must be gone everywhere.

    Matches the code form `.parents[3]`, not the explanatory comment that names the
    old derivation.
    """
    offenders = []
    for path in MODULE.parent.rglob("worker_*.py"):
        text = path.read_text(encoding="utf-8")
        if ".parents[3]" in text and "text_ndjson" in text:
            offenders.append(path.name)
    assert offenders == [], f"workers still locating the transport by fixed depth: {offenders}"


def test_every_standalone_worker_resolves_a_real_transport():
    """Each worker that has a sidecar mode must find the transport from the source tree."""
    module = load()
    workers = [
        path for path in MODULE.parent.rglob("worker_*.py")
        if "--staging-root" in path.read_text(encoding="utf-8")
    ]
    assert workers, "expected at least one sidecar-capable worker"
    for path in workers:
        resolved = module.transport_path(str(path))
        assert resolved.is_file(), f"{path.name} cannot find the transport at {resolved}"

