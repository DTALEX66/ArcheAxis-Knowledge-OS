"""Run the OpenMAIC generation chain from a staged or installed backend runtime.

This probe starts the runtime's own `start-backend.py` launcher, so the Core
executable, the staged `workers/openmaic` closure, the staged Python capability
routes and the manifest-declared Node identity are exactly what an installation
would launch. It then creates one synthetic source document, generates an
outline through the declared local model, builds one slide scene and one quiz
scene (each with its narration stage), generates a second interactive outline
through the interactive-outlines adapter, builds diagram, game and code scenes through
the widget prompt/normalize adapters, restarts the same workspace and reads
every candidate back without rerunning a worker or the model.

The model is a loopback stub with a fixed reply queue; this is not real model
quality evidence and not Owner acceptance. The staged root is a candidate
directory; `--installed-runtime` names an installed package root instead.

Usage:
  python -B scripts/probes/aaos_openmaic_generation_staged_loop.py \
      --root .project-local/rt/staged-20261106-actions \
      --receipt .project-local/runs/<run>/artifacts/openmaic-staged.json
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import importlib.util
import json
from pathlib import Path
import secrets
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import time

MODEL = "synthetic-stub-model"
MODEL_REPLIES = [
    json.dumps({
        "languageDirective": "Use Simplified Chinese.",
        "courseTitle": "Synthetic course",
        "outlines": [
            {"id": "o1", "type": "slide", "title": "SYNTHETIC_SLIDE_TITLE",
             "description": "SYNTHETIC_SLIDE_DESCRIPTION", "keyPoints": ["SYNTHETIC_KEY_POINT"],
             "order": 1},
            {"id": "o2", "type": "quiz", "title": "SYNTHETIC_QUIZ_TITLE", "description": "",
             "keyPoints": [], "order": 2,
             "quizConfig": {"questionCount": 1, "difficulty": "easy",
                            "questionTypes": ["single"]}},
        ]}, ensure_ascii=False),
    json.dumps({
        "elements": [{"type": "text", "left": 60, "top": 50, "width": 880, "height": 76,
                      "rotate": 0, "content": "SYNTHETIC_SLIDE_TEXT",
                      "defaultFontName": "", "defaultColor": ""}],
        "background": {"type": "solid", "color": "#ffffff"}}, ensure_ascii=False),
    json.dumps([{"type": "action", "name": "spotlight", "params": {"elementId": "el_1"}},
                {"type": "text", "content": "SYNTHETIC_SLIDE_OPENING"}], ensure_ascii=False),
    json.dumps([{"id": "q1", "type": "single", "question": "SYNTHETIC_QUIZ_QUESTION",
                 "options": [{"label": "Alpha", "value": "A"}, {"label": "Beta", "value": "B"}],
                 "answer": ["A"], "analysis": "SYNTHETIC_ANALYSIS", "points": 5}],
               ensure_ascii=False),
    json.dumps([{"type": "text", "content": "SYNTHETIC_QUIZ_OPENING"}], ensure_ascii=False),
    json.dumps({
        "languageDirective": "Use Simplified Chinese.",
        "courseTitle": "Synthetic interactive course",
        "outlines": [
            {"id": "io1", "type": "interactive", "title": "SYNTHETIC_INTERACTIVE_TITLE",
             "description": "SYNTHETIC_INTERACTIVE_DESCRIPTION",
             "keyPoints": ["SYNTHETIC_INTERACTIVE_KEY_POINT"], "order": 1,
             "widgetType": "diagram",
             "widgetOutline": {"diagramType": "flowchart", "nodeCount": 4}},
            {"id": "io2", "type": "interactive", "title": "SYNTHETIC_GAME_TITLE",
             "description": "SYNTHETIC_GAME_DESCRIPTION", "keyPoints": ["SYNTHETIC_GAME_POINT"],
             "order": 2, "widgetType": "game",
             "widgetOutline": {"gameType": "action", "challenge": "SYNTHETIC_GAME_CHALLENGE",
                               "playerControls": ["SYNTHETIC_THRUST"], "physicsConcept": "SYNTHETIC_PHYSICS"}},
            {"id": "io3", "type": "interactive", "title": "SYNTHETIC_CODE_TITLE",
             "description": "SYNTHETIC_CODE_DESCRIPTION", "keyPoints": ["SYNTHETIC_CODE_POINT"],
             "order": 3, "widgetType": "code",
             "widgetOutline": {"language": "python", "challengeType": "SYNTHETIC_CODE_CHALLENGE"}},
        ]}, ensure_ascii=False),
    "<!DOCTYPE html><html><body><main>SYNTHETIC_INTERACTIVE_HTML</main>"
    "<script>const syntheticValue = 1;</script></body></html>",
    "<!DOCTYPE html><html><body><main>SYNTHETIC_GAME_HTML</main></body></html>",
    "<!DOCTYPE html><html><body><main>SYNTHETIC_CODE_HTML</main></body></html>",
]


class StubModel(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802 - stdlib handler name
        length = int(self.headers.get("content-length", "0") or 0)
        request_bytes = self.rfile.read(length) if length else b""
        server = self.server
        with server.lock:  # type: ignore[attr-defined]
            server.calls += 1  # type: ignore[attr-defined]
            server.markers.append({name: name.encode("ascii") in request_bytes for name in (  # type: ignore[attr-defined]
                "SYNTHETIC_GAME_CHALLENGE", "SYNTHETIC_THRUST", "SYNTHETIC_PHYSICS",
                "SYNTHETIC_CODE_CHALLENGE")})
            index = server.index  # type: ignore[attr-defined]
            if index >= len(server.replies):  # type: ignore[attr-defined]
                self.send_response(500)
                self.send_header("content-type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":"unexpected model call"}')
                return
            server.index = index + 1  # type: ignore[attr-defined]
            content = server.replies[index]  # type: ignore[attr-defined]
        payload = json.dumps({
            "model": MODEL,
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 7},
        }).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args) -> None:
        return


class StubServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, replies: list[str]) -> None:
        super().__init__(("127.0.0.1", 0), StubModel)
        self.replies = replies
        self.calls = 0
        self.index = 0
        self.markers = []
        self.lock = threading.Lock()


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


class Core:
    def __init__(self, launcher, data_root: Path) -> None:
        self.launcher = launcher
        self.data_root = data_root
        self.port = free_port()
        self.child = None
        self.base = ""
        self.token = ""

    def start(self) -> None:
        self.child, self.base, _receipt, tokens = self.launcher.start(self.data_root, self.port)
        self.token = tokens["human"]

    def stop(self) -> None:
        if self.child is None:
            return
        self.child.terminate()
        try:
            self.child.wait(timeout=15)
        except Exception:
            self.child.kill()
            self.child.wait(timeout=15)
        self.child = None

    def request(self, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=120)
        payload = None if body is None else json.dumps(body, separators=(",", ":"))
        connection.request(method, path, body=payload, headers={
            "content-type": "application/json",
            "x-archeaxis-launch-token": self.token,
        })
        response = connection.getresponse()
        raw = response.read()
        connection.close()
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"raw": raw.decode("utf-8", "replace")}
        return response.status, parsed


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expect(step: str, status: int, body: dict, expected: int) -> dict:
    if status != expected:
        raise RuntimeError(f"{step}: expected {expected}, got {status}: {json.dumps(body)[:800]}")
    return body


def snapshot(document: dict) -> dict:
    return {"document_id": document["document_id"], "version": document["version"],
            "content_sha256": document["content_sha256"]}


def scene_receipt(response: dict, route: str) -> dict:
    stored = response["document"]["editor_json"]["attrs"]["archeaxis_openmaic_scene_candidate"]
    scene = stored["worker_document"]["scene"]
    return {
        "scene_route": response["scene_route"],
        "document_id": response["document"]["document_id"],
        "generation_route": response["generation_route"],
        "model_call": response["model_call"],
        "actions_status": response.get("actions_stage", {}).get("status"),
        "action_count": response.get("actions_stage", {}).get("action_count"),
        "action_execution": response.get("actions_stage", {}).get("action_execution"),
        "rendering_authorized": response.get("actions_stage", {}).get("rendering_authorized"),
        "scene_actions": [{"type": a.get("type"), "elementId": a.get("elementId"),
                           "text": a.get("text")} for a in scene.get("actions", [])],
        "scene_type": scene.get("type"),
        "outline_id": stored["derived_metadata"]["outline_id"],
    }


def interactive_scene_receipt(response: dict) -> dict:
    stored = response["document"]["editor_json"]["attrs"]["archeaxis_openmaic_scene_candidate"]
    scene = stored["worker_document"]["scene"]
    normalize = response.get("normalize") or {}
    return {
        "scene_route": response["scene_route"],
        "document_id": response["document"]["document_id"],
        "generation_route": response["generation_route"],
        "model_call": response["model_call"],
        "widget_type": response["widget_type"],
        "html_execution": response["html_execution"],
        "rendering_authorized": response["rendering_authorized"],
        "normalize_status": normalize.get("status"),
        "extraction_strategy": normalize.get("extraction_strategy"),
        "katex_injected": normalize.get("katex_injected"),
        "render_playable": ((response.get("render") or {}).get("report") or {}).get("playable"),
        "scene_type": scene.get("type"),
        "scene_widget_type": (scene.get("content") or {}).get("widgetType"),
        "outline_id": stored["derived_metadata"]["outline_id"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--run-id", default=secrets.token_hex(6))
    parser.add_argument("--installed-runtime", action="store_true",
                        help="the root is an installed package, not a staged candidate")
    parser.add_argument("--data-root", type=Path,
                        help="workspace root for this probe; defaults to <root>/data, so name an "
                             "external directory to leave an installed package unchanged")
    args = parser.parse_args()

    root = args.root.resolve()
    manifest_path = root / "backend-runtime-manifest.json"
    launcher_path = root / "start-backend.py"
    for required in (manifest_path, launcher_path, root / "core/archeaxis-api.exe"):
        if not required.is_file():
            raise SystemExit(f"runtime member missing: {required}")

    manifest = json.loads(manifest_path.read_bytes())
    core_sha = digest(root / "core/archeaxis-api.exe")
    node_sha = manifest.get("openmaic_scene_build", {}).get("node_sha256")

    stub = StubServer(list(MODEL_REPLIES))
    thread = threading.Thread(target=stub.serve_forever, daemon=True)
    thread.start()
    import os
    os.environ["ARCHEAXIS_MACHINE_ENDPOINT"] = f"http://127.0.0.1:{stub.server_address[1]}/v1"
    os.environ["ARCHEAXIS_MACHINE_MODEL"] = MODEL
    os.environ["ARCHEAXIS_MACHINE_PROTOCOL"] = "openai"

    spec = importlib.util.spec_from_file_location("staged_backend_launcher", launcher_path)
    launcher = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(launcher)

    data_root = (args.data_root.resolve() if args.data_root
                 else root / "data" / f"probe-{args.run_id}")
    core = Core(launcher, data_root)
    installed = args.installed_runtime
    receipt: dict = {
        "schema": "archeaxis.probe/openmaic-generation-staged/v1",
        "run_id": args.run_id,
        "runtime_kind": "INSTALLED_PACKAGE" if installed else "STAGED_CANDIDATE",
        "evidence_level": ("INSTALLED_RUNTIME_REAL_CORE_REAL_NODE_SYNTHETIC_LOOPBACK_MODEL" if installed
                           else "STAGED_BACKEND_RUNTIME_REAL_CORE_REAL_NODE_WORKERS_SYNTHETIC_LOOPBACK_MODEL"),
        "runtime_root": str(root),
        "data_root": str(data_root),
        "manifest_sha256": digest(manifest_path),
        "manifest_version": manifest.get("version"),
        "core_sha256": core_sha,
        "node_sha256": node_sha,
        "openmaic_scene_build": manifest.get("openmaic_scene_build"),
        "model": MODEL,
        "boundary": ("Installed package runtime, synthetic material and a loopback stub model. "
                     "Not real model quality, not Owner acceptance, not release publication."
                     if installed else
                     "Staged backend runtime, synthetic material and a loopback stub model. "
                     "Not an installed package, not real model quality, not Owner acceptance."),
    }
    try:
        core.start()
        created = expect("create source document", *core.request(
            "POST", "/api/v1/documents",
            {"create_request_id": f"probe-src-{args.run_id}", "title": "Synthetic material",
             "editor_json": {"type": "doc", "content": []}}), 201)
        source = snapshot(created)
        outline = expect("generate outline", *core.request(
            "POST", "/api/v1/courses/openmaic/outlines/generate",
            {"create_request_id": f"probe-outline-{args.run_id}",
             "requirement": "Synthetic requirement",
             "source_text": "SYNTHETIC source material", "model": None}), 200)
        outline_id = outline["document"]["document_id"]
        receipt["outline"] = {
            "document_id": outline_id,
            "generation_route": outline.get("generation_route"),
            "model_call": outline.get("model_call"),
            "outline_count": outline.get("outline_count"),
            "types": [item.get("type") for item in outline.get("outlines", [])],
        }
        scenes: dict[str, dict] = {}
        for index, (label, route, count) in enumerate((
            ("slide", "slide", 2), ("quiz", "quiz", 1))):
            body = {"create_request_id": f"probe-{label}-{args.run_id}",
                    "outline_document_id": outline_id, "outline_index": index,
                    "source": source, "model": None}
            response = expect(f"{label} scene", *core.request(
                "POST", "/api/v1/courses/openmaic/scenes/generate", body), 200)
            scene = scene_receipt(response, route)
            if scene["scene_route"] != route:
                raise RuntimeError(f"{label} route mismatch: {scene}")
            if scene["actions_status"] != "CANDIDATE" or scene["action_count"] != count:
                raise RuntimeError(f"{label} narration was not admitted: {scene}")
            if scene["action_execution"] != "NOT_PERFORMED" or scene["rendering_authorized"] is not False:
                raise RuntimeError(f"{label} narration claims execution or rendering: {scene}")
            scenes[label] = scene
            receipt.setdefault("steps", []).append({"step": f"{label}_scene", **scene})
        receipt["scenes"] = scenes

        interactive_outline = expect("generate interactive outline", *core.request(
            "POST", "/api/v1/courses/openmaic/outlines/generate-interactive",
            {"create_request_id": f"probe-int-outline-{args.run_id}",
             "requirement": "Synthetic interactive requirement",
             "source_text": "SYNTHETIC interactive source material", "model": None}), 200)
        interactive_outline_id = interactive_outline["document"]["document_id"]
        receipt["interactive_outline"] = {
            "document_id": interactive_outline_id,
            "generation_route": interactive_outline.get("generation_route"),
            "model_call": interactive_outline.get("model_call"),
            "outline_count": interactive_outline.get("outline_count"),
            "types": [item.get("type") for item in interactive_outline.get("outlines", [])],
        }
        if interactive_outline.get("generation_route") != "local_model_interactive_outline":
            raise RuntimeError(f"interactive outline route mismatch: {interactive_outline}")
        if [item.get("type") for item in interactive_outline.get("outlines", [])] != ["interactive"] * 3:
            raise RuntimeError(f"interactive outline admission mismatch: {interactive_outline}")

        interactive_widgets, interactive_bodies = {}, {}
        for index, widget in enumerate(("diagram", "game", "code")):
            body = {"create_request_id": f"probe-interactive-{widget}-{args.run_id}",
                    "outline_document_id": interactive_outline_id, "outline_index": index,
                    "source": source, "model": None}
            interactive = interactive_scene_receipt(expect(f"{widget} scene", *core.request(
                "POST", "/api/v1/courses/openmaic/scenes/generate", body), 200))
            if interactive["scene_route"] != "interactive":
                raise RuntimeError(f"interactive route mismatch: {interactive}")
            if interactive["widget_type"] != widget or interactive["scene_widget_type"] != widget:
                raise RuntimeError(f"interactive widget was not carried through: {interactive}")
            if interactive["html_execution"] != "NOT_PERFORMED":
                raise RuntimeError(f"interactive chain claims HTML execution: {interactive}")
            if interactive["rendering_authorized"] is not False or interactive["render_playable"] is not False:
                raise RuntimeError(f"interactive chain claims rendering authorization: {interactive}")
            if interactive["normalize_status"] != "OBSERVED_CANDIDATE":
                raise RuntimeError(f"interactive normalize did not run: {interactive}")
            interactive_widgets[widget], interactive_bodies[widget] = interactive, body
            receipt["steps"].append({"step": f"interactive_{widget}_scene", **interactive})
        receipt["interactive"] = interactive_widgets["diagram"]
        receipt["interactive_widgets"] = interactive_widgets
        game_markers, code_markers = stub.markers[7], stub.markers[8]
        receipt["widget_prompt_details_observed"] = {
            "game_challenge": game_markers["SYNTHETIC_GAME_CHALLENGE"],
            "game_controls": game_markers["SYNTHETIC_THRUST"],
            "game_physics": game_markers["SYNTHETIC_PHYSICS"],
            "code_challenge": code_markers["SYNTHETIC_CODE_CHALLENGE"],
        }
        if not all(receipt["widget_prompt_details_observed"].values()):
            raise RuntimeError("admitted widget details did not reach the loopback model prompt")
        receipt["model_call_count"] = stub.calls

        core.stop()
        core.start()
        replay: dict[str, dict] = {}
        for index, label in enumerate(("slide", "quiz")):
            body = {"create_request_id": f"probe-{label}-{args.run_id}",
                    "outline_document_id": outline_id, "outline_index": index,
                    "source": source, "model": None}
            response = expect(f"{label} replay", *core.request(
                "POST", "/api/v1/courses/openmaic/scenes/generate", body), 200)
            if response.get("worker_invoked") is not False:
                raise RuntimeError(f"{label} replay reran work: {response}")
            if response["document"]["document_id"] != scenes[label]["document_id"]:
                raise RuntimeError(f"{label} replay returned a different candidate")
            replay[label] = {"worker_invoked": False,
                             "document_id": response["document"]["document_id"]}
        outline_replay = expect("interactive outline replay", *core.request(
            "POST", "/api/v1/courses/openmaic/outlines/generate-interactive",
            {"create_request_id": f"probe-int-outline-{args.run_id}",
             "requirement": "Synthetic interactive requirement",
             "source_text": "SYNTHETIC interactive source material", "model": None}), 200)
        if outline_replay.get("worker_invoked") is not False:
            raise RuntimeError(f"interactive outline replay reran work: {outline_replay}")
        if outline_replay["document"]["document_id"] != interactive_outline_id:
            raise RuntimeError("interactive outline replay returned a different candidate")
        replay["interactive_outline"] = {
            "worker_invoked": False, "document_id": outline_replay["document"]["document_id"]}
        for widget, body in interactive_bodies.items():
            scene_replay = expect(f"interactive {widget} replay", *core.request(
                "POST", "/api/v1/courses/openmaic/scenes/generate", body), 200)
            if scene_replay.get("worker_invoked") is not False:
                raise RuntimeError(f"interactive replay reran work: {scene_replay}")
            if scene_replay["document"]["document_id"] != interactive_widgets[widget]["document_id"]:
                raise RuntimeError("interactive replay returned a different candidate")
            replay[f"interactive_{widget}"] = {
                "worker_invoked": False, "document_id": scene_replay["document"]["document_id"]}
        receipt["restart_replay"] = replay
        receipt["model_call_after_restart"] = stub.calls
        receipt["ok"] = True
    except Exception as error:  # the receipt keeps the named failure
        receipt["ok"] = False
        receipt["error"] = str(error)
    finally:
        core.stop()
        stub.shutdown()

    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=1, ensure_ascii=False) + "\n",
                            encoding="utf-8", newline="\n")
    print(json.dumps({"ok": receipt["ok"], "receipt": str(args.receipt)}, ensure_ascii=False))
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
