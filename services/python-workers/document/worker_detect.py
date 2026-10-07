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
import json
import sys
from hashlib import sha256
from pathlib import Path

ENGINE = "python-worker-detect"
ENGINE_VERSION = "0.1.0"
WORKER_IDENTITY = "python-worker-detect-ndjson"
MODEL_RELPATH = Path("shared") / "models" / "magika"


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
    root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[3]
    paths = model_paths(root)
    absent = sorted(str(name.relative_to(root)).replace("\\", "/")
                    for name in paths.values() if not name.is_file())
    if absent:
        return _unavailable("the vendored Magika model is not present", absent)
    if not target.is_file():
        return _unavailable(f"input is not a file: {target.name}", [])

    try:
        from shared.file_detection import detect as magika_detect
    except ImportError as exc:
        # The detector is vendored; what can be absent is the runtime that reads it. Name it, so a
        # missing dependency is never reported as "the file has no type".
        return _unavailable(f"the vendored detector cannot be loaded: {exc}",
                            ["python package onnxruntime"])

    blob = target.read_bytes()
    verdict = magika_detect(blob)
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
            "licence": "Apache-2.0",
            "form": "vendored ONNX",
            "model_sha256": sha256(paths["model"].read_bytes()).hexdigest(),
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
