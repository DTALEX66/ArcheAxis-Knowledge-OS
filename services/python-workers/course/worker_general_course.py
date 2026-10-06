"""One bounded JSON request; reuse course contracts/renderer without writing.

The returned path is a derived relative projection hint, never an IO target.
Core owns source/version validation, persistence and human review.
"""
from __future__ import annotations

from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import sys
import types

SCHEMA = "archeaxis.general-course-worker/v1"
ENGINE_VERSION = "0.1.0"
# The identity advertised in the sidecar handshake for this route.
WORKER_IDENTITY = "python-worker-general-course-ndjson"
MAX_INPUT = 256_000
MAX_OUTPUT = 1_000_000


def _donors():
    here = Path(__file__).resolve()
    root = here.parents[3] if here.parents[1].name == "python-workers" else here.parents[2]
    for package in ("app", "app.contracts", "app.adapters", "shared"):
        if package not in sys.modules:
            module = types.ModuleType(package)
            module.__path__ = [str(root / package.replace(".", "/"))]
            sys.modules[package] = module
    def load(name, relative):
        path = root / relative
        if not path.is_file():
            raise ImportError("required course donor is not bundled")
        if name not in sys.modules:
            spec = importlib.util.spec_from_file_location(name, path)
            if spec is None or spec.loader is None:
                raise ImportError("course donor cannot be loaded")
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
        return sys.modules[name]
    artifact = load("app.contracts.courseware_v1", "app/contracts/courseware_v1.py")
    manifest = load("app.contracts.general_learning_v1", "app/contracts/general_learning_v1.py")
    load("shared.approved_paths", "shared/approved_paths.py")
    load("shared.obsidian_projection", "shared/obsidian_projection.py")
    renderer = load("app.adapters.courseware_lesson", "app/adapters/courseware_lesson.py")
    return manifest.CourseManifestV1, artifact.CoursewareArtifactV1, renderer.render_general_lesson


def process(request: dict) -> dict:
    result = {"schema": SCHEMA, "engine_version": ENGINE_VERSION,
              "derived_only": True, "human_review_required": True,
              "canonical_bindings_verified": False}
    try:
        if not isinstance(request, dict) or request.get("schema") != SCHEMA:
            raise ValueError("invalid schema")
        if set(request) - {"schema", "operation", "manifest", "artifact"}:
            raise ValueError("unknown request fields")
        if len(json.dumps(request, allow_nan=False).encode()) > MAX_INPUT:
            raise ValueError("request exceeds bound")
        operation = request.get("operation")
        if operation not in ("validate", "render"):
            raise ValueError("operation must be validate or render")
        Manifest, Artifact, render = _donors()
        manifest = Manifest.model_validate(request.get("manifest"))
        if manifest.status != "candidate" or any(a.status != "candidate" for a in manifest.artifacts):
            raise ValueError("worker accepts candidate manifests/artifacts only")
        if any(not a.human_review_required for a in manifest.artifacts):
            raise ValueError("human review cannot be disabled")
        if len(manifest.knowledge_components) > 64 or len(manifest.artifacts) > 32:
            raise ValueError("course exceeds component/artifact bound")
        result.update(status="VALIDATED", manifest=manifest.model_dump(mode="json", by_alias=True),
                      donor="CourseManifestV1/CoursewareArtifactV1")
        if operation == "render":
            artifact = Artifact.model_validate(request.get("artifact"))
            if artifact.status != "candidate" or not artifact.human_review_required:
                raise ValueError("worker accepts candidates requiring human review only")
            projection = render(manifest, artifact)
            result.update(status="DERIVED", artifact=artifact.model_dump(mode="json", by_alias=True),
                          lesson=asdict(projection), renderer=artifact.renderer,
                          renderer_version=artifact.renderer_version)
        if len(json.dumps(result, allow_nan=False).encode()) > MAX_OUTPUT:
            raise ValueError("derived response exceeds bound")
    except (ImportError, ModuleNotFoundError):
        result = {**result, "status": "UNAVAILABLE", "reason": "required course donor/dependency unavailable"}
    except (ValueError, TypeError, RecursionError):
        # Validation diagnostics may echo source text; return only a safe category.
        result = {"schema": SCHEMA, "status": "INVALID_REQUEST", "reason": "course contract or boundary rejected",
                  "engine_version": ENGINE_VERSION, "derived_only": True, "human_review_required": True,
                  "canonical_bindings_verified": False}
    return result


def main() -> int:
    if sys.argv[1:] == ["--hello"]:
        print(json.dumps({"schema": "archeaxis.derived-worker-hello/v1",
                          "capability": "course.general", "version": 1}))
        return 0
    # Sidecar mode is this route's wiring, exactly as machine.answer does it: the launch declares
    # the capability, and the packaging readiness check starts the worker with --staging-root and
    # requires the transport hello. Without this branch the route is served (the Core reaches it
    # through its own derived route) but can never be reported ready, so a runtime that declares
    # it fails its own readiness check while the feature works.
    if "--staging-root" in sys.argv:
        import argparse
        import importlib.util
        from pathlib import Path

        candidates = (
            Path(__file__).resolve().parent.parent / "transport" / "text_ndjson.py",
            Path(__file__).resolve().parents[2] / "services" / "python-workers" / "transport"
            / "text_ndjson.py",
        )
        transport_path = next((p for p in candidates if p.is_file()), candidates[0])
        spec = importlib.util.spec_from_file_location("course.general_transport", transport_path)
        if spec is None or spec.loader is None:
            print(json.dumps({"error": "transport module is missing"}))
            return 1
        transport = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(transport)
        sidecar = argparse.ArgumentParser(description=__doc__)
        sidecar.add_argument("--staging-root", type=Path, required=True)
        sidecar.add_argument("--artifact-root", type=Path, default=None)
        args = sidecar.parse_args()
        return transport.serve_stdio(WORKER_IDENTITY, ["course.general"], args.staging_root,
                                     args.artifact_root)
    raw = sys.stdin.buffer.readline(MAX_INPUT + 1)
    try:
        if len(raw) > MAX_INPUT:
            raise ValueError("input bound")
        result = process(json.loads(raw))
    except (ValueError, TypeError, RecursionError):
        result = {"schema": SCHEMA, "status": "INVALID_REQUEST", "reason": "invalid bounded JSON request"}
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0 if result["status"] in ("VALIDATED", "DERIVED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
