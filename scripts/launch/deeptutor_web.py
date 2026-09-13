"""Run the pinned DeepTutor Web sidecar from a project-owned runtime home.

The upstream package stays read-only.  This wrapper owns only its child process
and project-local runtime directory; it never copies the Web bundle or forwards
provider credentials into the sidecar.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SHARED = Path("D:/All projects/OS External Configuration/10-toolchains/deeptutor/1.5.17")
DEFAULT_PYTHON = SHARED / "venv/Scripts/python.exe"
DEFAULT_NODE = Path("D:/All projects/OS External Configuration/10-toolchains/scoop/apps/nodejs-lts/24.18.0/node.exe")
DEFAULT_SERVER = SHARED / "venv/Lib/site-packages/deeptutor_web/server.js"
PINNED_VERSION = "1.5.17"
START_SNIPPET = (
    "import sys; from deeptutor.runtime.launcher import start; "
    "start(home=sys.argv[1], dev=False)"
)


class LaunchError(RuntimeError):
    """A named preflight or launch contract failure."""


def _version_from_interpreter(python: Path) -> str:
    probe = subprocess.run(
        [str(python), "-c", "from importlib.metadata import version; print(version('deeptutor'))"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False,
    )
    if probe.returncode != 0:
        raise LaunchError(f"cannot inspect DeepTutor version: {probe.stderr.strip()[:240]}")
    return probe.stdout.strip()


def resolve_installation(*, python: Path, node: Path, server: Path,
                         version_reader=_version_from_interpreter) -> dict[str, Path]:
    for label, path in (("DeepTutor Python", python), ("Node.js", node), ("DeepTutor Web server", server)):
        if not path.is_file():
            raise LaunchError(f"{label} is missing: {path}")
    version = version_reader(python)
    if version != PINNED_VERSION:
        raise LaunchError(f"requires DeepTutor {PINNED_VERSION}, found {version or 'unknown'}")
    return {"python": python, "node": node, "server": server}


def _provider_key(name: str) -> bool:
    upper = name.upper()
    return any(token in upper for token in (
        "API_KEY", "ACCESS_TOKEN", "AUTH_TOKEN", "SECRET", "PASSWORD",
        "CREDENTIAL", "OAUTH", "CLAUDE", "OPENAI", "ANTHROPIC", "GEMINI",
        "DEEPSEEK", "CODEBUDDY",
    ))


def build_environment(base: dict[str, str], *, runtime_home: Path,
                      backend_port: int = 8001, frontend_port: int = 3782,
                      node: Path | None = None) -> dict[str, str]:
    env = {key: value for key, value in base.items() if not _provider_key(key)}
    env.update({
        "DEEPTUTOR_HOME": str(runtime_home),
        "BACKEND_PORT": str(backend_port),
        "FRONTEND_PORT": str(frontend_port),
        "PORT": str(frontend_port),
        "HOSTNAME": "127.0.0.1",
        "DEEPTUTOR_API_BASE_URL": f"http://127.0.0.1:{backend_port}",
        "NEXT_PUBLIC_API_BASE": f"http://127.0.0.1:{backend_port}",
        "NEXT_PUBLIC_AUTH_ENABLED": "false",
        "DEEPTUTOR_AUTH_ENABLED": "false",
        "PYTHONUNBUFFERED": "1",
    })
    if node is not None:
        env["PATH"] = str(node.parent) + os.pathsep + env.get("PATH", "")
    return env


def build_command(*, python: Path, node: Path, server: Path, runtime_home: Path) -> list[str]:
    # The fixed interpreter selects the fixed installed package and server.js;
    # node is pinned in PATH by build_environment, so no shell is involved.
    return [str(python), "-c", START_SNIPPET, str(runtime_home)]


def _ready(url: str, timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 500
    except (OSError, ValueError):
        return False


def launch(*, python: Path = DEFAULT_PYTHON, node: Path = DEFAULT_NODE,
           server: Path = DEFAULT_SERVER, runtime_home: Path,
           backend_port: int = 8001, frontend_port: int = 3782,
           open_browser: bool = False) -> int:
    installation = resolve_installation(python=python, node=node, server=server)
    runtime_home.mkdir(parents=True, exist_ok=True)
    env = build_environment(os.environ.copy(), runtime_home=runtime_home,
                            backend_port=backend_port, frontend_port=frontend_port,
                            node=installation["node"])
    command = build_command(**installation, runtime_home=runtime_home)
    receipt = runtime_home / "deeptutor-web-launch.json"
    child = subprocess.Popen(
        command, cwd=str(runtime_home), env=env,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        start_new_session=os.name != "nt",
    )
    payload = {"status": "STARTED", "pid": child.pid,
               "url": f"http://127.0.0.1:{frontend_port}",
               "backend_url": f"http://127.0.0.1:{backend_port}",
               "python": str(python), "node": str(node), "server": str(server),
               "version": PINNED_VERSION, "runtime_home": str(runtime_home)}
    receipt.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if child.poll() is not None:
                raise LaunchError(f"DeepTutor exited before Web was ready: {child.returncode}")
            if _ready(payload["url"]):
                payload["status"] = "READY"
                receipt.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                if open_browser:
                    import webbrowser
                    webbrowser.open(payload["url"])
                return child.wait()
            time.sleep(0.5)
        raise LaunchError(f"DeepTutor Web did not become ready: {payload['url']}")
    except BaseException:
        if child.poll() is None:
            if os.name == "nt":
                subprocess.run(["taskkill.exe", "/PID", str(child.pid), "/T", "/F"],
                               check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            else:
                child.terminate()
        child.wait(timeout=15)
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-home", type=Path, required=True)
    parser.add_argument("--python", type=Path, default=DEFAULT_PYTHON)
    parser.add_argument("--node", type=Path, default=DEFAULT_NODE)
    parser.add_argument("--server", type=Path, default=DEFAULT_SERVER)
    parser.add_argument("--backend-port", type=int, default=8001)
    parser.add_argument("--frontend-port", type=int, default=3782)
    parser.add_argument("--open-browser", action="store_true")
    args = parser.parse_args(argv)
    try:
        return launch(python=args.python, node=args.node, server=args.server,
                      runtime_home=args.runtime_home, backend_port=args.backend_port,
                      frontend_port=args.frontend_port, open_browser=args.open_browser)
    except (LaunchError, OSError, ValueError) as exc:
        print(f"deeptutor Web launch failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
