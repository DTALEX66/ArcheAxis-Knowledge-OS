"""Static contract checks for every real Python worker route."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TRANSPORT = REPO / "services" / "python-workers" / "transport" / "text_ndjson.py"


def _load_transport():
    spec = importlib.util.spec_from_file_location("worker_route_contract_transport", TRANSPORT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _module_declarations(path: Path) -> tuple[set[str], set[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    assigned: set[str] = set()
    functions: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            assigned.update(
                target.id for target in targets if isinstance(target, ast.Name)
            )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.add(node.name)
    return assigned, functions


def _returned_dict_keys(path: Path) -> set[str]:
    """Top-level string keys of every dict this module returns, at any depth.

    Depth matters: `worker_office.py` returns its projection from per-format helpers rather
    than from `extract` itself, so a shallow look would call a routed worker unprojected.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    keys: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
            for key in node.value.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    keys.add(key.value)
    return keys


def test_every_routed_worker_projects_a_text():
    """The route contract is a projected text, so a routed worker must produce one.

    The Core derives canonical line anchors from the worker's `text` and refuses a receipt
    whose structure does not match that projection, so a worker without a projection cannot
    satisfy the contract however good its measurements are. This is the fact behind the one
    remaining unrouted capability: `media/worker_video.py` returns a duration, an extracted
    audio path and frame hashes - real, useful measurements - and no projection at all, so
    routing it needs an artifact-shaped contract rather than a parameters field, and the
    recorded reason for its exemption says so.
    """
    transport = _load_transport()
    missing = []
    for capability, route in transport.ROUTES.items():
        worker = (REPO / route["worker"]).resolve()
        if "text" not in _returned_dict_keys(worker):
            missing.append(f"{capability} -> {route['worker']}")
    assert missing == [], (
        "these routed workers return no projected text, so the Core cannot anchor them: "
        f"{missing}")


def test_the_routed_video_worker_has_real_projection_and_route():
    """Video is a declared route with raw text, time cues and sampled frames."""
    video = REPO / "services" / "python-workers" / "media" / "worker_video.py"
    keys = _returned_dict_keys(video)
    assert {"text", "cues", "raw_cues", "visual_results"} <= keys
    route = _load_transport().ROUTES["media.video"]
    assert route["worker"] == "services/python-workers/media/worker_video.py"
    assert route["call"] == "video_transcribe"
    assert {"frames", "duration_ms", "audio_wav"} <= keys, (
        f"worker_video projection fields missing. keys={sorted(keys)}")


def test_every_route_has_an_in_repo_worker_with_engine_and_extract():
    transport = _load_transport()

    assert transport.ROUTES
    for capability, route in transport.ROUTES.items():
        assert isinstance(capability, str) and capability.strip()
        assert isinstance(route.get("version"), str) and route["version"].strip()
        relative_worker = Path(route.get("worker", ""))
        assert relative_worker.parts and not relative_worker.is_absolute()
        worker = (REPO / relative_worker).resolve()
        assert worker.is_relative_to(REPO), f"{capability} escapes repository: {route['worker']}"
        assert worker.is_file(), f"{capability} points to missing worker: {route['worker']}"

        assigned, functions = _module_declarations(worker)
        assert "ENGINE" in assigned, f"{capability} worker lacks ENGINE: {worker}"
        assert "extract" in functions, f"{capability} worker lacks extract(): {worker}"

        media_types = route.get("media_types")
        assert isinstance(media_types, (set, frozenset)) and media_types
        assert all(isinstance(media_type, str) and media_type.strip() for media_type in media_types)
        # `transcribe` was added for the ASR route: it hands the worker a suffixed view of
        # the audio plus the configured model path, language and device, which `path` (one
        # positional argument) and `ocr` (language plus tessdata) cannot express.
        assert route.get("call") in {"path", "ocr", "transcribe", "video_transcribe"}
