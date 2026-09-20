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
        assert route.get("call") in {"path", "ocr"}
