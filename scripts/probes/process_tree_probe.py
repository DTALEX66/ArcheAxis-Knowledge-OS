"""Record the process tree and watch for the isolated python worker the core spawns.

Two rounds of reading established that the worker is not resident: the core registers routes at
startup and creates the python process per call, inside the machine-answer path. A later round found
that the machine-answer route has no worker registered for it at all, while the capability surface
performs a real handshake - so one request to a capability is enough to provoke a spawn.

The sighting itself is timing dependent and is therefore recorded, not required. What the tests
assert is what must hold anywhere the core runs: the core is a child of the process that launched
it, the capability answers and names its transport, and the watcher actually ran.
"""

import json, os, shutil, subprocess, sys, threading, time, urllib.error, urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CORE = REPO / ".project-local" / "build" / "aaos01-core" / "debug" / "archeaxis-api.exe"
CAPABILITY = "api/v1/capabilities/text.extract"
WATCH_SECONDS = 40


def powershell():
    """Find a shell by name, never by a hardcoded location.

    The harness supplies pwsh, but it is not on the PATH of a process we start ourselves. The
    fallback is composed from the system root the environment already knows, because a literal
    absolute path in runtime code is exactly what this repository forbids.
    """
    for name in ("pwsh", "powershell"):
        found = shutil.which(name)
        if found:
            return found
    root = os.environ.get("SystemRoot") or os.environ.get("windir")
    if root:
        candidate = Path(root) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
        if candidate.is_file():
            return str(candidate)
    return None


def run() -> dict:
    import importlib.util
    import uuid
    spec = importlib.util.spec_from_file_location("owned_probe_launcher", REPO / "scripts/runtime/dev.py")
    launcher = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = launcher
    spec.loader.exec_module(launcher)
    paths = launcher.layout(REPO, "process-tree-probe-" + uuid.uuid4().hex[:12])
    launcher.prepare(paths)
    work = paths["tmp"]

    shell = powershell()
    receipt = {"scope": "process_tree_and_worker_probe", "core_present": CORE.is_file(),
               "powershell_used": shell, "watch_seconds": WATCH_SECONDS, "sightings": []}
    if not CORE.is_file():
        receipt["ok"] = False; receipt["failed_step"] = "core_binary_missing"; return receipt
    if shell is None:
        receipt["ok"] = False; receipt["failed_step"] = "no_powershell"; return receipt

    token = "c" * 64
    launch = {"launch_token": token, "session_id": "d" * 32, "actor": "human",
              "text_worker": {"python": sys.executable,
                              "script": str(REPO / "services/python-workers/transport/text_ndjson.py"),
                              "staging": str(work / "staging")}}
    core = subprocess.Popen([str(CORE), str(work / "archeaxis.sqlite"), "0"], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                            encoding="utf-8")
    receipt["core_pid"] = core.pid
    receipt["launched_by_python_pid"] = os.getpid()
    lines = []

    def collect(process):
        for line in process.stdout:
            line = line.strip()
            if line:
                lines.append(line)

    try:
        started = time.time()
        core.stdin.write(json.dumps(launch) + "\n")
        core.stdin.flush(); core.stdin.close()
        deadline = time.time() + 60
        line = ""
        while time.time() < deadline:
            line = core.stdout.readline()
            if "127.0.0.1:" in line: break
        receipt["seconds_to_ready"] = round(time.time() - started, 2)
        receipt["readiness_announced"] = "127.0.0.1:" in line
        if "127.0.0.1:" not in line:
            receipt["ok"] = False; receipt["failed_step"] = "readiness"; return receipt
        base = "http://127.0.0.1:" + line.split("127.0.0.1:", 1)[1].split()[0].strip() + "/"

        # One long-lived shell polling inside itself: a process that lives for milliseconds cannot be
        # caught by a shell started per sample, which is why two earlier attempts saw nothing.
        script = (
            "$end = (Get-Date).AddSeconds({seconds}); "
            "while ((Get-Date) -lt $end) {{ "
            "  Get-CimInstance Win32_Process -Filter \"ParentProcessId = {pid}\" | "
            "    Where-Object {{ $_.Name -like 'python*' }} | "
            "    ForEach-Object {{ Write-Output ($_.ProcessId.ToString() + '|' + $_.Name) }}; "
            "  Start-Sleep -Milliseconds 60 }}").format(seconds=WATCH_SECONDS, pid=core.pid)
        watch = subprocess.Popen([shell, "-NoProfile", "-Command", script], stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
                                 errors="replace")
        reader = threading.Thread(target=collect, args=(watch,), daemon=True)
        reader.start()
        time.sleep(1.0)

        request = urllib.request.Request(base + CAPABILITY, method="GET",
            headers={"x-archeaxis-launch-token": token, "x-archeaxis-actor": "machine"})
        asked = time.time()
        with urllib.request.urlopen(request, timeout=120) as response:
            receipt["capability_status"] = response.status
            record = json.loads(response.read().decode("utf-8", "replace"))
        receipt["capability_seconds"] = round(time.time() - asked, 2)
        entry = record.get("capability") or {}
        receipt["capability_name"] = entry.get("capability")
        receipt["capability_provider"] = str(entry.get("default_provider") or "")[-60:]
        receipt["capability_health"] = entry.get("health")

        # The parent of the core itself, so parentage comes from the record rather than from a
        # comparison of two pids that are different processes by definition.
        parent_script = (
            "(Get-CimInstance Win32_Process -Filter "
            "\"ProcessId = {pid}\").ParentProcessId"
        ).format(pid=core.pid)
        parented = subprocess.run([shell, "-NoProfile", "-Command", parent_script],
                                  capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=60)
        try:
            receipt["core_parent_pid"] = int((parented.stdout or "").strip())
        except ValueError:
            receipt["core_parent_pid"] = None

        time.sleep(6.0)
        watch.kill()
        try: watch.wait(timeout=10)
        except Exception: pass
        time.sleep(0.5)
        seen = {}
        for item in lines:
            parts = item.split("|", 1)
            if len(parts) == 2:
                seen[parts[0]] = {"pid": parts[0], "name": parts[1]}
        receipt["sightings"] = list(seen.values())
        receipt["worker_seen"] = bool(seen)
        receipt["watcher_lines"] = len(lines)
        receipt["ok"] = True
    finally:
        core.kill()
        try: core.wait(timeout=20)
        except Exception: pass
        shutil.rmtree(work, ignore_errors=True)
    return receipt


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json-out", type=Path)
    options = parser.parse_args()
    receipt = run()
    text = json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True)
    if options.json_out:
        options.json_out.parent.mkdir(parents=True, exist_ok=True)
        options.json_out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if receipt.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
