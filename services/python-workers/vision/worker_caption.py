#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ArcheAxis vNext vision worker: diagram/scene description (F04 layer 2).

Sends the image to a local vision model over HTTP and returns a structured description separate
from OCR text. This lane NEVER claims OCR accuracy: text is handled by worker_ocr; descriptions are
model output labeled with model + prompt version for reproducibility.

Which local runtime answers is resolved rather than assumed. Ollama's `/api/generate` is tried
first, then any OpenAI-compatible server's `/chat/completions` (LM Studio serves this way), and
`ARCHEAXIS_CAPTION_ENDPOINT` / `_MODEL` / `_PROTOCOL` override the search. The two protocols differ
in both the request body and the response field, so the resolved protocol is carried through to the
receipt. The same model is named differently by each runtime (`qwen2.5vl:7b` against
`qwen2.5-vl-7b-instruct`), so the model is resolved with the endpoint.

Only models that pass the capability probe are reported as usable.

Usage:
    python worker_caption.py <image-file> [--model NAME]
    python worker_caption.py --probe [--model NAME]
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ENGINE = "python-worker-caption"
ENGINE_VERSION = "0.2.0"
# R15/F04: the identity advertised in the sidecar handshake for this route.
WORKER_IDENTITY = "python-worker-caption-ndjson"

# Two local runtimes can serve a vision model, and which one exists is a property of the machine
# rather than something to hardcode. Ollama is tried first because that is what this worker was
# written against; any OpenAI-compatible server (LM Studio, and others) is accepted as well, which
# is what makes the route usable on a host that has one and not the other.
OLLAMA_BASE = "http://127.0.0.1:11434"
OLLAMA_MODEL = "qwen2.5vl:7b"
OPENAI_BASE = "http://127.0.0.1:1234/v1"
OPENAI_MODEL = "qwen2.5-vl-7b-instruct"

# The model a caller gets when it names none. It is resolved from the endpoint rather than fixed,
# because the two local runtimes name the same model differently; this constant is what a caller
# that passes no model ends up with on a host that serves the default endpoint.
DEFAULT_MODEL = OLLAMA_MODEL

PROMPT_TEMPLATE = (
    "Describe this image for a knowledge workspace. "
    "State the dominant text layer briefly, then the structure/entities/diagram "
    "elements, then anything notable. Answer in the language of the dominant "
    "text when detectable, otherwise English. Keep under 200 words. "
    "Do not invent facts; mark uncertainty explicitly."
)
PROMPT_VERSION = "archeaxis.vnext/v1 2026-09-05"


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


def _endpoint() -> dict:
    """Which vision endpoint to use, and under which protocol.

    Explicit configuration wins; otherwise the two known local servers are probed in turn and the
    first that answers is used. The result carries the protocol because the request body and the
    response field differ between them, and a caller that assumed one shape would break on the
    other.
    """
    explicit = _env("ARCHEAXIS_CAPTION_ENDPOINT")
    if explicit:
        protocol = _env("ARCHEAXIS_CAPTION_PROTOCOL") or (
            "openai" if explicit.rstrip("/").endswith("/v1") else "ollama")
        return {
            "protocol": protocol,
            "base": explicit.rstrip("/"),
            "model": _env("ARCHEAXIS_CAPTION_MODEL")
            or (OPENAI_MODEL if protocol == "openai" else OLLAMA_MODEL),
            "discovered": False,
        }
    for candidate in (
        {"protocol": "ollama", "base": OLLAMA_BASE, "model": OLLAMA_MODEL},
        {"protocol": "openai", "base": OPENAI_BASE, "model": OPENAI_MODEL},
    ):
        try:
            with urllib.request.urlopen(
                    f"{candidate['base']}/{'models' if candidate['protocol'] == 'openai' else 'api/tags'}",
                    timeout=3):
                return {**candidate, "discovered": True}
        except Exception:  # noqa: BLE001 - a candidate that is not running is not an error
            continue
    # Nothing answered: report the first candidate so the failure names a concrete endpoint.
    return {"protocol": "ollama", "base": OLLAMA_BASE, "model": OLLAMA_MODEL, "discovered": False}


def _installed_models(endpoint: dict) -> list[str]:
    path = "/models" if endpoint["protocol"] == "openai" else "/api/tags"
    try:
        with urllib.request.urlopen(f"{endpoint['base']}{path}", timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        return []
    if endpoint["protocol"] == "openai":
        return sorted(item.get("id", "") for item in payload.get("data", []))
    return sorted(item.get("name", "") for item in payload.get("models", []))


def probe(model: str | None = None) -> dict:
    endpoint = _endpoint()
    model = model or endpoint["model"]
    installed = _installed_models(endpoint)
    if not installed:
        return {
            "capability": False,
            "reason": f"no vision endpoint answered at {endpoint['base']}",
            "engine": ENGINE,
            "endpoint": endpoint["base"],
            "protocol": endpoint["protocol"],
        }
    if model not in installed:
        return {
            "capability": False,
            "reason": f"model {model} not installed",
            "engine": ENGINE,
            "available": installed,
            "endpoint": endpoint["base"],
            "protocol": endpoint["protocol"],
        }
    return {
        "capability": True,
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "model": model,
        "endpoint": endpoint["base"],
        "protocol": endpoint["protocol"],
        "prompt_version": PROMPT_VERSION,
        "note": "model availability only; description quality is measured separately",
    }


def _call(endpoint: dict, model: str, encoded: str, timeout_s: int, *, receipt: dict | None = None) -> str:
    """One vision request, in whichever protocol the endpoint speaks."""
    if endpoint["protocol"] == "openai":
        url = f"{endpoint['base']}/chat/completions"
        body = {
            "model": model,
            "max_tokens": 400,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT_TEMPLATE},
                    {"type": "image_url",
                     "image_url": {"url": f"data:{receipt.get('mime', 'image/png') if receipt is not None else 'image/png'};base64,{encoded}"}},
                ],
            }],
        }
    else:
        url = f"{endpoint['base']}/api/generate"
        body = {
            "model": model,
            "prompt": PROMPT_TEMPLATE,
            "images": [encoded],
            "stream": False,
            "options": {"num_predict": 400},
        }
    request = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if endpoint["protocol"] == "openai":
        message = (payload.get("choices") or [{}])[0].get("message", {})
        # These are reasoning models: the chain of thought arrives in `reasoning_content` and the
        # answer in `content`, and a small budget is consumed entirely by reasoning, leaving
        # `content` empty. Prefer the answer and fall back rather than reporting nothing.
        text = str(message.get("content") or "").strip()
        if not text and receipt is None:
            text = str(message.get("reasoning_content") or "").strip()
    else:
        text = str(payload.get("response", "")).strip()
    if receipt is not None:
        receipt.update(actual_model=payload.get("model"), requested_model=model,
                       finish_reason=((payload.get("choices") or [{}])[0].get("finish_reason") if endpoint["protocol"] == "openai" else payload.get("done_reason")))
    return text


def describe(image: Path, model: str | None = None, timeout_s: int = 300, *, require_identity: bool = False, endpoint_override: dict | None = None) -> dict:
    if not image.is_file():
        raise ValueError(f"input image not found: {image}")
    supported = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}
    if image.suffix.lower() not in supported:
        raise ValueError(f"unsupported image extension: {image.suffix}")

    endpoint = endpoint_override if endpoint_override is not None else _endpoint()
    model = model or endpoint["model"]
    encoded = base64.b64encode(image.read_bytes()).decode("ascii")
    started = time.monotonic()
    trace = {"mime": "image/jpeg" if image.suffix.lower() in {".jpg", ".jpeg"} else "image/png"}
    try:
        description = _call(endpoint, model, encoded, timeout_s, receipt=trace) if require_identity else _call(endpoint, model, encoded, timeout_s)
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"vision model call failed at {endpoint['base']} ({endpoint['protocol']}): {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"vision model call failed: {exc}") from exc
    elapsed_s = round(time.monotonic() - started, 2)
    if not description:
        raise RuntimeError("vision model returned an empty description")
    if require_identity and (not isinstance(trace.get("actual_model"), str) or not trace["actual_model"].strip() or trace.get("finish_reason") not in {"stop", "length"}):
        raise RuntimeError("Vision actual model/finish identity unverified")
    if require_identity:
        trace["completion_state"] = "complete" if trace["finish_reason"] == "stop" else "partial"
    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "description": description,
        "engine_receipt": trace if require_identity else None,
        "model": model,
        "endpoint": endpoint["base"],
        "protocol": endpoint["protocol"],
        "prompt_version": PROMPT_VERSION,
        "elapsed_s": elapsed_s,
        "loss_receipt": {
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "params": {
                "model": model,
                "prompt_version": PROMPT_VERSION,
                "endpoint": endpoint["base"],
                "protocol": endpoint["protocol"],
            },
            "loss_note": (
                "description is model output, not OCR; text fidelity is owned by "
                "worker_ocr; uncertainty marked by the model is preserved verbatim"
            ),
        },
    }


def extract(path: str, model: str | None = None) -> dict:
    """R15/F04: the route-contract entry point for a figure description.

    A description is model output, so this is explicit about three things: the endpoint and model
    are resolved first and a missing one is a named failure rather than a raw HTTP error; the
    projection is the description itself, which the receipt labels as model output; and nothing here
    measures quality, because description quality needs a human truth pair rather than a second
    model call.
    """
    availability = probe(model)
    if not availability.get("capability"):
        raise ValueError(
            f"vision model {model or availability.get('model')} is not available: "
            f"{availability.get('reason')}"
            + (
                f" (installed: {', '.join(availability.get('available', [])[:8])})"
                if availability.get("available")
                else ""
            )
        )
    result = describe(Path(path), availability["model"])
    description = result["description"]
    receipt = dict(result["loss_receipt"])
    receipt["params"] = {
        **receipt.get("params", {}),
        "model": result["model"],
        "prompt_version": result["prompt_version"],
        "elapsed_s": result["elapsed_s"],
        "authority": "this text is a model description, not extracted content: it is a candidate",
    }
    receipt["loss_note"] = (
        receipt.get("loss_note", "")
        + "; the projection is model output and is labelled as such, so it is a candidate and not a fact about the image"
    ).strip("; ")
    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "text": description,
        "description": description,
        "model": result["model"],
        # An implementation that describes without naming its endpoint is still a valid answer; the
        # receipt simply does not claim one. Requiring the keys would make every stand-in carry
        # transport detail it has no opinion about.
        **({"endpoint": result["endpoint"]} if result.get("endpoint") else {}),
        **({"protocol": result["protocol"]} if result.get("protocol") else {}),
        "prompt_version": result["prompt_version"],
        "loss_receipt": receipt,
    }


def main() -> int:
    # R15/F04: this worker existed since an earlier slice with no route pointing at it.
    # The sidecar mode is that wiring, with this worker's own identity and capability.
    if "--staging-root" in sys.argv:
        import importlib.util

        # The shared transport sits beside this worker's own category directory, in a
        # source checkout (`services/python-workers/transport/`) and in a staged runtime
        # (`workers/transport/`) alike, so both are tried from this file's location. A
        # fixed parents[3] plus a `services/python-workers/` suffix was correct only for
        # the source layout and left a staged worker unable to start.
        _transport_candidates = (
            Path(__file__).resolve().parent.parent / "transport" / "text_ndjson.py",
            Path(__file__).resolve().parents[2] / "services" / "python-workers" / "transport" / "text_ndjson.py",
        )
        _transport = next((p for p in _transport_candidates if p.is_file()), _transport_candidates[0])
        spec = importlib.util.spec_from_file_location("caption_transport", _transport)
        if spec is None or spec.loader is None:
            print(json.dumps({"error": "transport module is missing", "engine": ENGINE}))
            return 1
        transport = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(transport)
        sidecar = argparse.ArgumentParser(description=__doc__)
        sidecar.add_argument("--staging-root", type=Path, required=True)
        sidecar.add_argument("--artifact-root", type=Path, default=None)
        args = sidecar.parse_args()
        return transport.serve_stdio(
            WORKER_IDENTITY, ["image.caption"], args.staging_root, args.artifact_root
        )

    parser = argparse.ArgumentParser(description="ArcheAxis vision description worker")
    parser.add_argument("input", nargs="?", help="image file")
    parser.add_argument("--model", default=None,
                        help="override the model; the endpoint's own default is used otherwise")
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    if args.probe:
        print(json.dumps(probe(args.model), ensure_ascii=False))
        return 0
    if not args.input:
        print(json.dumps({"error": "usage: worker_caption.py <image-file> [--model NAME]"}))
        return 2
    try:
        out = describe(Path(args.input), args.model)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
