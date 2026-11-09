"""Run a synthetic provider journey through a compiled host bridge and real Core.

Run under scripts/runtime/dev.py with a fresh run ID. The caller supplies the
actual Core and `core_bridge.rs` Rust test executable; this probe hashes those
files but does not establish which source produced either binary. The OpenMAIC
case additionally requires an explicitly hash-pinned Node executable. All
materials, answers, authorization and model replies are synthetic; the stub
listens only on loopback. No installed UI, real-model quality or Owner acceptance
is tested.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL = "synthetic-host-stub-model"
CASE_TESTS = {
    "deeptutor": "provider_real_core_deeptutor_synthetic_journey",
    "openmaic": "provider_real_core_openmaic_synthetic_generation_journey",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_core_class():
    path = ROOT / "scripts/ci/real_core_grading_journey.py"
    spec = importlib.util.spec_from_file_location("aaos_synthetic_core", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("synthetic Core launcher unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Core


class Stub(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802 - standard library handler name
        size = int(self.headers.get("content-length", "0"))
        if size < 0 or size > 1_000_000:
            self.send_error(413)
            return
        request = json.loads(self.rfile.read(size))
        self.server.calls += 1  # type: ignore[attr-defined]
        call = self.server.calls  # type: ignore[attr-defined]
        case = self.server.case  # type: ignore[attr-defined]
        if case == "deeptutor" and call == 1:
            self.server.schema_requested = (  # type: ignore[attr-defined]
                request.get("response_format", {}).get("type") == "json_schema"
            )
            content = json.dumps({"question_type": "choice", "question": "Synthetic sum?",
                "options": {"A": "3", "B": "4", "C": "5", "D": "6"},
                "correct_answer": "D", "explanation": "Synthetic model opinion."})
        elif case == "openmaic" and call == 1:
            content = json.dumps({"languageDirective": "使用简体中文", "courseTitle": "Synthetic",
                "outlines": [{"id": "interactive_1", "type": "interactive", "title": "Diagram",
                    "description": "Synthetic", "keyPoints": ["Synthetic point"], "order": 1,
                    "widgetType": "diagram", "widgetOutline": {"diagramType": "flowchart", "nodeCount": 4}}]})
        elif case == "openmaic" and call == 2:
            content = "<!DOCTYPE html><html><body><main>SYNTHETIC_HTML</main></body></html>"
        else:
            self.send_error(500)
            return
        data = json.dumps({"model": MODEL, "choices": [{"index": 0, "finish_reason": "stop",
            "message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 7}}).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_args: object) -> None:
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=sorted(CASE_TESTS), required=True)
    parser.add_argument("--core-exe", type=Path, required=True)
    parser.add_argument("--bridge-tests-exe", type=Path, required=True)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--node-exe", type=Path)
    parser.add_argument("--node-sha256")
    args = parser.parse_args(argv)
    core_exe = args.core_exe.resolve(strict=True)
    bridge_exe = args.bridge_tests_exe.resolve(strict=True)
    python = args.python.resolve(strict=True)
    run_value = os.environ.get("ARCHEAXIS_RUN_ROOT")
    if not run_value or not Path(run_value).is_dir():
        raise RuntimeError("a fresh scripts/runtime/dev.py run is required")
    run = Path(run_value).resolve(strict=True)
    artifacts = run / "artifacts" / f"host-provider-{args.case}"
    artifacts.mkdir(parents=True, exist_ok=False)
    node = None
    if args.case == "openmaic":
        if args.node_exe is None or args.node_sha256 is None:
            raise RuntimeError("OpenMAIC requires a Node executable and explicit SHA-256")
        node = args.node_exe.resolve(strict=True)
        if digest(node) != args.node_sha256.lower():
            raise RuntimeError("Node identity mismatch")

    core_class = load_core_class()

    class SyntheticCore(core_class):
        provider_enabled = True

        def _launch_document(self):
            launch = super()._launch_document()
            if self.provider_enabled:
                model_route = {"capability": "course.openmaic.outline-model",
                    "script": str(ROOT / "services/python-workers/course/worker_outline_local_model.py")}
                if args.case == "deeptutor":
                    launch["text_worker"]["routes"].append(model_route)
                else:
                    launch["text_worker"]["routes"] = [model_route]
                    launch["openmaic_node_worker"] = {"executable": str(node),
                        "executable_sha256": args.node_sha256.lower(),
                        "script": str(ROOT / "services/learning-providers/openmaic/scene-build-worker.mjs")}
            else:
                launch["text_worker"]["routes"] = []
            return launch

    server = ThreadingHTTPServer(("127.0.0.1", 0), Stub)
    server.case = args.case  # type: ignore[attr-defined]
    server.calls = 0  # type: ignore[attr-defined]
    server.schema_requested = False  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    workspace = artifacts / "workspace"
    workspace.mkdir()
    core = SyntheticCore(core_exe, workspace, python)
    phases: list[dict] = []
    temp_env = {"ARCHEAXIS_MACHINE_ENDPOINT": f"http://127.0.0.1:{server.server_port}/v1",
        "ARCHEAXIS_MACHINE_MODEL": MODEL, "ARCHEAXIS_MACHINE_PROTOCOL": "openai"}
    previous = {key: os.environ.get(key) for key in temp_env}
    os.environ.update(temp_env)

    def run_phase(phase: str) -> None:
        core.start()
        env = dict(os.environ, AAOS_SYNTHETIC_CORE_PORT=str(core.port),
            AAOS_SYNTHETIC_CORE_TOKEN=core.token, AAOS_SYNTHETIC_CORE_PHASE=phase,
            AAOS_SYNTHETIC_JOURNEY_STATE=str(artifacts / "synthetic-state.json"))
        result = subprocess.run([str(bridge_exe), CASE_TESTS[args.case], "--ignored", "--test-threads=1"],
            cwd=ROOT, env=env, check=False)
        phases.append({"phase": phase, "exit_code": result.returncode})
        core.stop()
        if result.returncode:
            raise RuntimeError(f"synthetic {phase} test failed")

    error = None
    try:
        run_phase("create")
        core.provider_enabled = False
        run_phase("reopen")
        if args.case == "deeptutor":
            state = json.loads((artifacts / "synthetic-state.json").read_text(encoding="utf-8"))
            filename = state["backup_filename"]
            if not isinstance(filename, str) or Path(filename).name != filename:
                raise RuntimeError("invalid synthetic backup filename")
            backup = workspace / "backups" / filename
            if digest(backup) != state["backup_sha256"]:
                raise RuntimeError("synthetic backup hash mismatch")
            restored_dir = artifacts / "restored-workspace"
            restored_dir.mkdir()
            restored = subprocess.run([str(core_exe), "--maintenance-restore",
                str(restored_dir / "workspace.sqlite"), str(backup)],
                capture_output=True, text=True, timeout=120, check=False)
            restored_receipt = json.loads(restored.stdout)
            if (restored.returncode != 0 or restored_receipt.get("ok") is not True
                    or restored_receipt.get("authorization_requires_new_grants") is not True):
                raise RuntimeError("synthetic restore or authorization fence failed")
            core = SyntheticCore(core_exe, restored_dir, python)
            core.provider_enabled = False
            run_phase("restore")
        expected_calls = 1 if args.case == "deeptutor" else 2
        if server.calls != expected_calls:  # type: ignore[attr-defined]
            raise RuntimeError("unexpected synthetic model request count")
        if args.case == "deeptutor" and not server.schema_requested:  # type: ignore[attr-defined]
            raise RuntimeError("structured schema was not requested")
    except Exception as exc:
        error = str(exc)
    finally:
        core.stop()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    receipt = {"schema": "aaos.host-provider-synthetic-journey/v1", "case": args.case,
        "ok": error is None, "error": error, "phases": phases,
        "core_sha256": digest(core_exe), "bridge_tests_sha256": digest(bridge_exe),
        "bridge_source_binding": "CALLER_SUPPLIED_NOT_INDEPENDENTLY_VERIFIED",
        "node_sha256": digest(node) if node else None,
        "synthetic_model_requests": server.calls,  # type: ignore[attr-defined]
        "structured_schema_requested": server.schema_requested if args.case == "deeptutor" else None,  # type: ignore[attr-defined]
        "ui_or_installed_runtime_tested": False, "html_executed": False}
    (artifacts / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": receipt["ok"], "receipt": str(artifacts / "receipt.json")}))
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
