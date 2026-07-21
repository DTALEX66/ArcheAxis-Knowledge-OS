"""Start Core on a random loopback port and verify the packaged Workspace surface."""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

WORKSPACE_ROOT = "/" + "workspace"
WORKSPACE_STATUS_PATH = f"{WORKSPACE_ROOT}/api/status"
WORKSPACE_SCRIPT_PATH = f"{WORKSPACE_ROOT}/assets/app.js"
WORKSPACE_STYLE_PATH = f"{WORKSPACE_ROOT}/assets/styles.css"


def choose_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _direct_opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def wait_for_json(url: str, *, timeout: float = 20.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with _direct_opener().open(url, timeout=1.0) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # pragma: no cover - exercised only while process starts
            last_error = exc
            time.sleep(0.1)
    raise RuntimeError(f"Core did not become ready at {url}: {last_error}")


def read_text(url: str) -> str:
    with _direct_opener().open(url, timeout=5.0) as response:
        assert response.status == 200
        return response.read().decode("utf-8")


def terminate_process_tree(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            process.kill()
        else:
            os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)


@contextmanager
def running_core() -> Iterator[str]:
    port = choose_loopback_port()
    base_url = f"http://127.0.0.1:{port}"
    environment = os.environ.copy()
    environment.update(
        {
            "COGNITIVE_HOST": "127.0.0.1",
            "COGNITIVE_PORT": str(port),
            "NO_PROXY": "127.0.0.1",
            "no_proxy": "127.0.0.1",
        }
    )
    log_path = Path(tempfile.gettempdir()) / f"cognitive-core-smoke-{port}.log"
    with log_path.open("wb") as log:
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        process = subprocess.Popen(
            [sys.executable, "-m", "app.runtime_entrypoint", "core"],
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
            start_new_session=os.name != "nt",
        )
        try:
            wait_for_json(f"{base_url}/version")
        except Exception as exc:
            log.flush()
            output = log_path.read_text(encoding="utf-8", errors="replace")
            terminate_process_tree(process)
            raise RuntimeError(f"Core smoke failed; log follows:\n{output}") from exc
        try:
            yield base_url
        finally:
            terminate_process_tree(process)


def main() -> int:
    with running_core() as base_url:
        version = wait_for_json(f"{base_url}/version")
        status = wait_for_json(f"{base_url}{WORKSPACE_STATUS_PATH}")
        page = read_text(f"{base_url}{WORKSPACE_ROOT}")
        javascript = read_text(f"{base_url}{WORKSPACE_SCRIPT_PATH}")
        stylesheet = read_text(f"{base_url}{WORKSPACE_STYLE_PATH}")

        assert version["release"]["status"] == "unreleased"
        assert status["schema_version"] == "v1"
        assert status["components"]["api"] == "available"
        assert "元枢·观心" in page
        assert "validateStatus" in javascript
        assert "--accent" in stylesheet
        print(f"runtime HTTP smoke passed at {base_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
