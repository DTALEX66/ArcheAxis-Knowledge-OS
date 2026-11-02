#!/usr/bin/env python3
"""ArcheAxis vNext content-detection worker (F04): name the bytes by evidence, never by guess.

F04's stated gap is that a file whose extension the Core cannot name is refused rather than named.
Refusing is right when the only signal is a name; it is wrong when the repository already carries a
content-type model. `shared/file_detection.py` is the vendored Magika ONNX (Apache-2.0, upstream
`google/magika` standard_v3_0) with committed tests, and nothing in the product path used it - so the
absorbed donor sat in the pool while the product kept refusing.

This worker reports **the model's judgement about these bytes**: label, group and the model's own
score, plus which model produced them. It deliberately does NOT translate a label into a media type:
the vendored config carries no mime table, and inventing one here would be exactly the guess the
requirement refuses. The original file's own name and bytes stay the authority; this is a fact about
what a model read.

Usage:
    python worker_detect.py <input-file>
Output: {"engine","engine_version","text","structure","loss_receipt"}
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from hashlib import sha256
from pathlib import Path
from threading import Lock
from types import ModuleType

ENGINE = "python-worker-detect"
ENGINE_VERSION = "0.1.0"
WORKER_IDENTITY = "python-worker-detect-ndjson"
MODEL_RELPATH = Path("shared") / "models" / "magika"
# The repository's preserved Apache-2.0 model. A configured alternate model
# is not assumed to have the same licence merely because it has the same name.
VENDORED_MODEL_SHA256 = "0c9bf7255c5a68e8e74c878005989b5ea7682c15d46f42fbb0198cfe5eeea38c"
_detector: ModuleType | None = None
_detector_lock = Lock()


def _installation_root() -> Path:
    """Resolve the same checkout or portable-worker root as the transport."""
    worker_root = Path(__file__).resolve().parents[1]
    if worker_root.name == "workers":
        return worker_root.parent
    return worker_root.parent.parent


def _load_detector() -> ModuleType:
    """Load executable code only from this worker's own installation."""
    global _detector
    with _detector_lock:
        if _detector is None:
            path = _installation_root() / "shared" / "file_detection.py"
            if not path.is_file():
                raise FileNotFoundError("shared/file_detection.py")
            spec = importlib.util.spec_from_file_location("archeaxis_owned_file_detection", path)
            if spec is None or spec.loader is None:
                raise ImportError("installed detector code cannot be loaded")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            _detector = module
        return _detector


def _unavailable(reason: str, missing: list[str]) -> dict:
    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "text": "",
        "structure": {"capability": "document.detection", "state": "unavailable", "candidates": []},
        # The job contract accepts a fixed receipt shape, so what is missing and what is claimed
        # travel inside `params` - a refusal that loses its reason reads as an empty success.
        "loss_receipt": {
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "params": {"state": "unavailable", "reason": reason, "missing_artifacts": missing,
                       "claim": "no content judgement was produced, so none is asserted"},
        },
    }


def model_paths(root: Path) -> dict[str, Path]:
    """The vendored model and config this capability consumes, under the repository root."""
    directory = root / MODEL_RELPATH
    return {"model": directory / "model.onnx", "config": directory / "config.min.json"}


def detect(path: str, repo_root: str | None = None) -> dict:
    target = Path(path)
    root = Path(repo_root) if repo_root else _installation_root()
    if not target.is_file():
        return _unavailable(f"input is not a file: {target.name}", [])

    try:
        detector = _load_detector()
    except FileNotFoundError:
        return _unavailable("the vendored detector code is not present", ["shared/file_detection.py"])
    except ModuleNotFoundError as exc:
        missing = [f"python package {exc.name}"] if exc.name else []
        return _unavailable(f"the vendored detector cannot be loaded: {exc}", missing)
    except ImportError as exc:
        return _unavailable(f"the vendored detector cannot be loaded: {exc}", [])

    blob = target.read_bytes()
    # A caller's root selects model data only, never executable code.
    selected = model_paths(root) if repo_root else dict(zip(("model", "config"), detector._model_paths()))
    absent = sorted(str(name.relative_to(root)).replace("\\", "/")
                    if name.is_relative_to(root) else str(name)
                    for name in selected.values() if not name.is_file())
    if absent:
        return _unavailable("the vendored Magika model is not present", absent)
    verdict = detector.detect(blob, model_paths=(selected["model"], selected["config"]))
    model_identity = verdict["model_identity"]
    label = str(verdict["label"])
    group = str(verdict["group"])
    score = float(verdict["confidence"])
    structure = {
        "capability": "document.detection",
        "state": "detected",
        "label": label,
        "group": group,
        "model_score": score,
        "input_sha256": sha256(blob).hexdigest(),
        "input_bytes": len(blob),
        "model": {
            "name": "magika",
            "revision": "standard_v3_0",
            "revision_status": "declared_profile_not_publisher_verified",
            "licence": "Apache-2.0" if model_identity["model_sha256"] == VENDORED_MODEL_SHA256 else "unverified",
            "form": "local ONNX",
            "model_sha256": model_identity["model_sha256"],
            "config_sha256": model_identity["config_sha256"],
        },
        "basis": "a model judgement over the bytes, derived without the file's extension",
        "candidates": [],
    }
    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "text": f"{label}\t{group}\t{score:.4f}\n",
        "structure": structure,
        "loss_receipt": {
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "params": {
                "state": "detected",
                "model_identity": dict(model_identity),
                "claim": "the type is what the vendored Magika model read from these bytes; it is "
                         "not the file's declared extension, and the model score is not an accuracy "
                         "measure",
            },
        },
    }


def extract(path: str) -> dict:
    """The transport's entry-point shape: one input path, one contract envelope.

    A refusal is raised, not returned: a job that answers with empty text and no reason is the
    shape this repository refuses, because nothing downstream can tell it from a real result.
    """
    result = detect(path)
    if result["structure"]["state"] != "detected":
        params = result["loss_receipt"]["params"]
        missing = ", ".join(params.get("missing_artifacts") or [])
        raise RuntimeError(f"{params['reason']}" + (f" (missing: {missing})" if missing else ""))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input", nargs="?")
    parser.add_argument("--repo-root", default=None, help="repository root holding shared/models/magika")
    parser.add_argument("--staging-root", type=Path, default=None)
    parser.add_argument("--artifact-root", type=Path, default=None)
    arguments = parser.parse_args(argv)
    if arguments.staging_root is not None:
        # Launched by the Core: the request arrives on stdin and the job loop is the shared one,
        # so a detection reaches the product through the same machinery as every other route.
        import importlib.util

        transport_path = Path(__file__).resolve().parent.parent / "transport" / "text_ndjson.py"
        spec = importlib.util.spec_from_file_location("detect_transport", transport_path)
        if spec is None or spec.loader is None:
            print(json.dumps({"error": "transport module is missing", "engine": ENGINE}))
            return 1
        transport = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(transport)
        return transport.serve_stdio(
            WORKER_IDENTITY, ["document.detect"], arguments.staging_root, arguments.artifact_root)
    if not arguments.input:
        parser.error("input is required outside a Core launch")
    print(json.dumps(detect(arguments.input, arguments.repo_root), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
