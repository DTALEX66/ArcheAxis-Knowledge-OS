"""ArcheAxis vNext machine worker: a real local model answer over a supplied context (G4).

This is the machine half of the co-learning loop. It sends a context and a question to a local text
model and returns the answer **as a candidate**, never as knowledge: the whole point of G4 is that a
human then identifies a real error in it, and an answer promoted automatically would remove the step
the gate exists for.

Which runtime answers is resolved rather than assumed, the same way the caption worker resolves a
vision endpoint. Ollama's `/api/generate` is tried first, then any OpenAI-compatible server's
`/chat/completions` (LM Studio serves this way), and `ARCHEAXIS_MACHINE_ENDPOINT` / `_MODEL` /
`_PROTOCOL` override the search. The two protocols differ in both the request body and the response
field, so the resolved protocol is carried through to the receipt.

These are reasoning models: the chain of thought arrives in `reasoning_content` and the answer in
`content`, and a small token budget is consumed entirely by reasoning, leaving `content` empty. The
token budget is therefore reported back, because a truncated answer and a finished one must not look
alike.

Only a model that answers the capability probe is reported as usable.

Usage:
    python worker_machine_answer.py --context <file> --question "<text>" [--model NAME]
    python worker_machine_answer.py --probe [--model NAME]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ENGINE = "python-worker-machine-answer"
ENGINE_VERSION = "0.1.0"
# The identity advertised in the sidecar handshake for this route.
WORKER_IDENTITY = "python-worker-machine-answer-ndjson"

# Two local runtimes can serve a text model, and which one exists is a property of the machine rather
# than something to hardcode. Ollama is tried first because that is the native local port; any
# OpenAI-compatible server is accepted as well, which is what makes the route usable on a host that
# has one and not the other.
OLLAMA_BASE = "http://127.0.0.1:11434"
OLLAMA_MODEL = "qwen3.5:4b"
OPENAI_BASE = "http://127.0.0.1:1234/v1"
OPENAI_MODEL = "qwen3.5-4b"

# The model a caller gets when it names none. It is resolved from the endpoint rather than fixed,
# because the two local runtimes name the same model differently.
DEFAULT_MODEL = OLLAMA_MODEL

# A reasoning model spends tokens thinking before it answers, and the budget is shared between the
# two. Measured on this host: a simple question answered with `finish_reason: stop` inside 600 tokens
# and kept its reasoning in `reasoning_content`, while a grounded question over a real context was
# still truncated at 512 and produced a complete answer at 2048. The default is therefore set where a
# grounded answer fits, and the budget and finish reason are both reported either way so a truncated
# answer cannot be mistaken for a finished one.
DEFAULT_MAX_TOKENS = 2048

PROMPT_TEMPLATE = (
    "You are answering from the supplied context only.\n"
    "Rules:\n"
    "1. Use only the context. If the context does not answer the question, say so plainly.\n"
    "2. Answer in the language of the question.\n"
    "3. Be concise: at most 150 words.\n"
    "4. Do not add facts that are not in the context. Mark anything uncertain.\n\n"
    "Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
)
PROMPT_VERSION = "archeaxis.vnext/v1 2026-10-02"


def _declared_lanes() -> list[dict]:
    """The local runtime lanes the capability manifest declares, in declared order.

    Falls back to this module's own two addresses only when no declaration can be read (a staged
    runtime without a manifest beside it), and the model id is this route's own per protocol.
    """
    per_protocol_model = {"ollama": OLLAMA_MODEL, "openai": OPENAI_MODEL}
    module_path = Path(__file__).resolve().parent.parent / "tool_paths.py"
    lanes: list[dict] = []
    if module_path.is_file():
        import importlib.util

        spec = importlib.util.spec_from_file_location("machine_tool_paths", module_path)
        if spec is not None and spec.loader is not None:
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
                lanes = [{"protocol": lane["protocol"], "base": lane["base"],
                          "model": per_protocol_model.get(lane["protocol"], OLLAMA_MODEL),
                          "resource": lane.get("name")}
                         for lane in module.local_runtime_lanes()
                         if lane.get("protocol") in per_protocol_model]
            except Exception:  # noqa: BLE001 - an unread declaration must not look like an empty host
                lanes = []
    if lanes:
        return lanes
    return [{"protocol": "ollama", "base": OLLAMA_BASE, "model": OLLAMA_MODEL, "resource": None},
            {"protocol": "openai", "base": OPENAI_BASE, "model": OPENAI_MODEL, "resource": None}]


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


def _endpoint() -> dict:
    """Which text endpoint to use, and under which protocol.

    Explicit configuration wins; otherwise every local lane the capability declaration names is
    probed in declared order and the first that answers is used. The result carries the protocol
    because the request body and the response field differ between them. The addresses come from
    `config/environment/capability-requirements.yaml` (the `models/*` rows carrying an `endpoint`);
    the constants below are what this route asks each protocol for, since the model a text answer
    needs is this worker's own choice, not the lane's declared vision identity.
    """
    explicit = _env("ARCHEAXIS_MACHINE_ENDPOINT")
    if explicit:
        protocol = _env("ARCHEAXIS_MACHINE_PROTOCOL") or (
            "openai" if explicit.rstrip("/").endswith("/v1") else "ollama")
        return {
            "protocol": protocol,
            "base": explicit.rstrip("/"),
            "model": _env("ARCHEAXIS_MACHINE_MODEL")
            or (OPENAI_MODEL if protocol == "openai" else OLLAMA_MODEL),
            "discovered": False,
        }
    for candidate in _declared_lanes():
        try:
            with urllib.request.urlopen(
                    f"{candidate['base']}/{'models' if candidate['protocol'] == 'openai' else 'api/tags'}",
                    timeout=3):
                return {**candidate, "discovered": True}
        except Exception:  # noqa: BLE001 - a candidate that is not running is not an error
            continue
    # Nothing answered: report the first declared lane so the failure names a concrete endpoint.
    first = _declared_lanes()[0]
    return {**first, "discovered": False}


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
    """Whether a text model can answer here, named concretely when it cannot."""
    endpoint = _endpoint()
    model = model or endpoint["model"]
    installed = _installed_models(endpoint)
    if not installed:
        return {
            "capability": False,
            "reason": f"no text endpoint answered at {endpoint['base']}",
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "endpoint": endpoint["base"],
            "protocol": endpoint["protocol"],
            "prompt_version": PROMPT_VERSION,
            "note": "availability only; answer quality is measured separately",
        }
    if model not in installed:
        return {
            "capability": False,
            "reason": f"model {model} is not available",
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "available": installed,
            "endpoint": endpoint["base"],
            "protocol": endpoint["protocol"],
            "prompt_version": PROMPT_VERSION,
            "note": "availability only; answer quality is measured separately",
        }
    return {
        "capability": True,
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "model": model,
        "endpoint": endpoint["base"],
        "protocol": endpoint["protocol"],
        "discovered": endpoint["discovered"],
        "available": installed,
        "prompt_version": PROMPT_VERSION,
        "note": "availability only; answer quality is measured separately",
    }


def _call(endpoint: dict, model: str, prompt: str, timeout_s: int,
          max_tokens: int) -> tuple[str, str]:
    """One text request, in whichever protocol the endpoint speaks.

    Returns the text and the endpoint's own finish reason, because "the model stopped" and "the
    budget ran out" produce very different confidence in the answer.
    """
    if endpoint["protocol"] == "openai":
        url = f"{endpoint['base']}/chat/completions"
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
    else:
        url = f"{endpoint['base']}/api/generate"
        body = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
    request = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if endpoint["protocol"] == "openai":
        choice = (payload.get("choices") or [{}])[0]
        message = choice.get("message", {})
        # These are reasoning models: the chain of thought arrives in `reasoning_content` and the
        # answer in `content`, and a small budget is consumed entirely by reasoning, leaving `content`
        # empty. Prefer the answer and fall back rather than reporting nothing.
        text = str(message.get("content") or "").strip()
        if not text:
            text = str(message.get("reasoning_content") or "").strip()
        return text, str(choice.get("finish_reason") or "")
    text = str(payload.get("response", "")).strip()
    return text, str(payload.get("done_reason") or "")


def answer(context: str, question: str, model: str | None = None,
           timeout_s: int = 300, max_tokens: int = DEFAULT_MAX_TOKENS) -> dict:
    """Ask the local model one question about one context.

    The result is labelled a candidate throughout: an answer that has not been reviewed by a human is
    a proposal, and `loss_receipt` says so in the terms the rest of the pipeline reads.
    """
    context = (context or "").strip()
    question = (question or "").strip()
    if not question:
        raise ValueError("a question is required; an answer to nothing is not a task")
    if not context:
        raise ValueError("a context is required; answering without one is not grounded")

    endpoint = _endpoint()
    model = model or endpoint["model"]
    prompt = PROMPT_TEMPLATE.format(context=context, question=question)
    started = time.monotonic()
    try:
        text, finish_reason = _call(endpoint, model, prompt, timeout_s, max_tokens)
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"text model call failed at {endpoint['base']} ({endpoint['protocol']}): {exc}"
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"text model call failed: {exc}") from exc
    elapsed_s = round(time.monotonic() - started, 2)

    if not text:
        raise ValueError(
            f"model {model} returned no answer within {max_tokens} tokens "
            f"(finish_reason={finish_reason or 'unknown'}); raise the budget rather than reporting "
            "an empty answer")

    truncated = finish_reason == "length"
    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "answer": text,
        "model": model,
        "endpoint": endpoint["base"],
        "protocol": endpoint["protocol"],
        "prompt_version": PROMPT_VERSION,
        "finish_reason": finish_reason,
        "max_tokens": max_tokens,
        "truncated": truncated,
        "elapsed_s": elapsed_s,
        "loss_receipt": {
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "params": {
                "model": model,
                "endpoint": endpoint["base"],
                "protocol": endpoint["protocol"],
                "prompt_version": PROMPT_VERSION,
                "max_tokens": max_tokens,
                "finish_reason": finish_reason,
                # Stated so no reader mistakes this for accepted knowledge.
                "authority": "candidate",
            },
            "losses": [] if not truncated else [{
                "kind": "truncated_answer",
                "note": f"the model stopped on the token budget ({max_tokens}), so the answer may be "
                        "incomplete",
            }],
            "loss_note": "an answer is model output awaiting human review, not accepted knowledge",
        },
    }


def extract(path: str, question: str | None = None,
            model: str | None = None,
            max_tokens: int = DEFAULT_MAX_TOKENS) -> dict:
    """Route entry point: answer a question about the staged context file."""
    source = Path(path)
    if not source.is_file():
        raise ValueError(f"context file not found: {source}")
    if question is None:
        raise ValueError(
            "this route needs a question; a machine answer without one is not a task")
    context = source.read_text(encoding="utf-8", errors="replace")
    result = answer(context, question, model=model, max_tokens=max_tokens)
    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "text": result["answer"],
        "answer": result["answer"],
        "model": result["model"],
        "endpoint": result["endpoint"],
        "protocol": result["protocol"],
        "prompt_version": result["prompt_version"],
        "loss_receipt": result["loss_receipt"],
    }


def main() -> int:
    if sys.argv[1:] == ["--document-check"]:
        from document_check import main as document_check_main
        return document_check_main()
    # G4: the sidecar mode is this worker's wiring, with its own identity and capability.
    if "--staging-root" in sys.argv:
        import importlib.util

        # The shared transport sits beside this worker's own category directory, in a source checkout
        # (`services/python-workers/transport/`) and in a staged runtime (`workers/transport/`) alike,
        # so both are tried from this file's location.
        candidates = (
            Path(__file__).resolve().parent.parent / "transport" / "text_ndjson.py",
            Path(__file__).resolve().parents[2] / "services" / "python-workers" / "transport"
            / "text_ndjson.py",
        )
        transport_path = next((p for p in candidates if p.is_file()), candidates[0])
        spec = importlib.util.spec_from_file_location("machine_transport", transport_path)
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
            WORKER_IDENTITY, ["machine.answer"], args.staging_root, args.artifact_root
        )

    parser = argparse.ArgumentParser(description="ArcheAxis machine answer worker")
    parser.add_argument("context", nargs="?", help="file holding the context to answer from")
    parser.add_argument("--question", default=None, help="the question to answer")
    parser.add_argument("--model", default=None,
                        help="override the model; the endpoint's own default is used otherwise")
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS,
                        help="token budget shared by reasoning and answer")
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()

    if args.probe:
        print(json.dumps(probe(args.model), ensure_ascii=False))
        return 0
    if not args.context:
        print(json.dumps({"error": "usage: worker_machine_answer.py <context-file> "
                                   "--question \"...\" [--model NAME] [--max-tokens N]"}))
        return 2
    try:
        result = extract(args.context, args.question, args.model, args.max_tokens)
    except (ValueError, RuntimeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
