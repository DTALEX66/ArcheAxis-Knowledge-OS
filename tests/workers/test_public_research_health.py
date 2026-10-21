"""Input-free protocol health is not provider reachability or model execution."""
import importlib.util
import json
import shutil
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ENTRY = ROOT / "services/python-workers/machine/worker_machine_answer.py"
HELLO = {"schema": "archeaxis.public-research-worker-hello/v1", "version": 1,
         "worker": "python-worker-machine-answer-ndjson", "capability": "research.public",
         "protocol": "public-research-worker/v1", "task_executed": False,
         "network_performed": False, "model_executed": False}


def test_hello_loads_actual_modules_without_reading_input_or_using_network(monkeypatch, capsys):
    spec = importlib.util.spec_from_file_location("research_health_entry", ENTRY)
    entry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(entry)
    calls = []
    load = importlib.util.spec_from_file_location
    def observe(name, path, *args, **kwargs):
        calls.append(Path(path).name)
        return load(name, path, *args, **kwargs)
    def forbidden(*args, **kwargs):
        pytest.fail("health must not read query material, call providers or invoke a model")
    class NoInput:
        buffer = property(lambda self: self)
        read = forbidden
        readline = forbidden
    monkeypatch.setattr(importlib.util, "spec_from_file_location", observe)
    monkeypatch.setattr(sys, "argv", [str(ENTRY), "--public-research-hello"])
    monkeypatch.setattr(sys, "stdin", NoInput())
    monkeypatch.setattr(entry, "local_urlopen", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(urllib.request.OpenerDirector, "open", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    assert entry.main() == 0
    assert json.loads(capsys.readouterr().out) == HELLO
    assert {"public_research.py", "safe_http.py", "public_research_proxy.py"} <= set(calls)


def test_isolated_python_hello_imports_the_real_entrypoint():
    result = subprocess.run([sys.executable, "-I", "-B", str(ENTRY), "--public-research-hello"],
                            stdin=subprocess.DEVNULL, capture_output=True, timeout=5)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert json.loads(result.stdout) == HELLO
    assert result.stderr == b""


@pytest.mark.parametrize("missing", ["public_research.py", "safe_http.py", "public_research_proxy.py"])
def test_hello_refuses_missing_fixed_module_or_dependency(tmp_path, missing):
    machine = tmp_path / "sandbox/services/python-workers/machine"
    machine.mkdir(parents=True)
    entry = machine / ENTRY.name
    shutil.copyfile(ENTRY, entry)
    if missing != "public_research.py":
        shutil.copyfile(ENTRY.with_name("public_research.py"), machine / "public_research.py")
    if missing != "public_research_proxy.py":
        shutil.copyfile(ENTRY.with_name("public_research_proxy.py"), machine / "public_research_proxy.py")
    if missing != "safe_http.py":
        shared = tmp_path / "sandbox/shared"
        shared.mkdir()
        shutil.copyfile(ROOT / "shared/safe_http.py", shared / "safe_http.py")
    result = subprocess.run([sys.executable, "-I", "-B", str(entry), "--public-research-hello"],
                            stdin=subprocess.DEVNULL, capture_output=True, timeout=5)
    assert result.returncode != 0
    assert b'"capability": "research.public"' not in result.stdout


def test_existing_isolated_query_dispatch_keeps_fixed_importlib_loading(tmp_path):
    machine = tmp_path / "machine"
    machine.mkdir()
    entry = machine / ENTRY.name
    shutil.copyfile(ENTRY, entry)
    (machine / "public_research.py").write_text(
        "def main():\n print('{\"synthetic_query_dispatch\":true}')\n return 0\n", encoding="utf-8")
    result = subprocess.run([sys.executable, "-I", "-B", str(entry), "--public-research"],
                            stdin=subprocess.DEVNULL, capture_output=True, timeout=5)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert json.loads(result.stdout) == {"synthetic_query_dispatch": True}
