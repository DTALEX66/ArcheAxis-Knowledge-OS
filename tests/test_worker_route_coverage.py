"""Every worker must be reachable, or explicitly known to be unreachable.

The defect this guards against is not a crash: it is a worker that exists, works, and no
route ever names it. `media/worker_transcribe.py` is exactly that - a real engine with a
real model behind it, verified on real Chinese audio - and no Core job can reach it because
nothing declares the capability. Nothing failed; the capability was simply never wired, and
no test noticed.

So this test enumerates the worker scripts and requires each one to be either declared by
the runtime's route table or listed below with the mechanism that reaches it instead. A new
worker that is in neither place fails the suite, which is the point: an unrouted worker must
be a decision, not an oversight.

`media/worker_transcribe.py`, `media/worker_video.py` and `web/worker_webpage.py` are
recorded as real gaps rather than explained away - they have a usable engine and a `--probe`
but no sidecar mode, so no route can reach them. They are the remaining route work.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKERS = ROOT / "services" / "python-workers"
STAGER = ROOT / "scripts" / "release" / "stage_backend_runtime.py"

# worker path -> how a Core job reaches it, for workers not in ROUTE_SCRIPTS.
REACHED_OTHERWISE: dict[str, str] = {
    "document/worker_text.py":
        "the text route's handler: ROUTE_SCRIPTS names the transport, and the transport "
        "loads this worker as the route's handler",
    "learning/worker_schedule.py":
        "invoked as a bounded subprocess by crates/archeaxis-application/src/scheduler.rs, "
        "not as a capability route",
    "evaluation/worker_quality.py":
        "not routed: no route table names it and no caller outside the worker checker does",
    "worker_extract.py":
        "not routed: a legacy single-file extractor kept for compatibility; the route "
        "table's per-format workers supersede it",
    "web/worker_webpage.py":
        "GAP: a fetch worker with a --probe, but no sidecar mode and no declared "
        "capability, so no Core job can reach it. URL fetching is deliberately not part "
        "of the html route",
    "media/worker_transcribe.py":
        "GAP: a real ASR engine verified on real Chinese audio, but no --staging-root "
        "sidecar mode and no declared capability. The pack requires real audio before "
        "final closure, so this is the clearest remaining route gap",
    "media/worker_video.py":
        "GAP: decodes with a resolved ffmpeg path, but no sidecar mode and no declared "
        "capability, so no Core job can reach it",
}


def load_stager():
    spec = importlib.util.spec_from_file_location("stager_route_coverage", STAGER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def worker_scripts() -> list[str]:
    return sorted(
        str(path.relative_to(WORKERS)).replace("\\", "/")
        for path in WORKERS.rglob("worker_*.py")
        if "__pycache__" not in path.parts
    )


def declared_workers(stager) -> set[str]:
    return {
        Path(script).name
        for scripts in stager.ROUTE_SCRIPTS.values()
        for script in scripts
    }


def test_every_worker_is_declared_or_known(monkeypatch):
    stager = load_stager()
    declared = declared_workers(stager)
    unaccounted = []
    for relative in worker_scripts():
        name = Path(relative).name
        if name in declared or relative in REACHED_OTHERWISE:
            continue
        unaccounted.append(relative)
    assert not unaccounted, (
        "these workers are neither declared by ROUTE_SCRIPTS nor listed in "
        f"REACHED_OTHERWISE: {unaccounted}. Declare a route for them, or record how they "
        "are reached.")


def test_the_known_dispositions_are_still_accurate():
    """A disposition naming a mechanism must not outlive the mechanism."""
    stager = load_stager()
    declared = declared_workers(stager)
    for relative in REACHED_OTHERWISE:
        assert (WORKERS / relative).is_file(), f"{relative} no longer exists"
        assert Path(relative).name not in declared, (
            f"{relative} is now declared by ROUTE_SCRIPTS, so its REACHED_OTHERWISE entry "
            "is stale")


def test_the_declared_routes_all_resolve_to_an_existing_worker():
    stager = load_stager()
    for capability, scripts in stager.ROUTE_SCRIPTS.items():
        for script in scripts:
            relative = script.replace("workers/", "", 1)
            assert (WORKERS / relative).is_file(), f"{capability} names a missing worker: {script}"


def test_the_gap_workers_really_have_no_sidecar_mode():
    """The three recorded gaps must actually be gaps, not a stale note.

    If one of them grows a sidecar mode, this fails and the gap list gets revisited
    instead of silently under-reporting what is reachable.
    """
    gaps = [relative for relative, note in REACHED_OTHERWISE.items()
            if note.startswith("GAP:")]
    assert gaps, "the gap list is empty; if the gaps were closed, remove this test"
    for relative in gaps:
        text = (WORKERS / relative).read_text(encoding="utf-8")
        assert "serve_stdio" not in text, (
            f"{relative} now serves the sidecar protocol; move it out of the gap list")


@pytest.mark.parametrize("relative", sorted(REACHED_OTHERWISE))
def test_a_recorded_disposition_worker_exists(relative):
    assert (WORKERS / relative).is_file(), relative
