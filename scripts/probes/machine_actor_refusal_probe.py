"""Start a machine-actor session and record whether the human-review route refuses it.

The rule being measured is that a human review may only be recorded by a human session. Two rounds
of reading showed the actor is taken from the matched launch credential and stamped onto the request,
overwriting whatever the client sent. This probe drives the machine half of that: it launches a Core
whose launch document declares the machine actor, then asks that Core to record a human review.

It declares itself machine, truthfully, and never sends a human declaration - a false human claim is
not needed to obtain the refusal, and not something this probe will emit even to test one.
"""

import json, os, shutil, socket, subprocess, sys, time, urllib.error, urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CORE = REPO / ".project-local" / "build" / "aaos01-core" / "debug" / "archeaxis-api.exe"
REVIEWS = "api/v1/learning/reviews"
VERSION = "api/v1/system/version"


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0)); return int(sock.getsockname()[1])


def run() -> dict:
    import importlib.util
    import uuid
    spec = importlib.util.spec_from_file_location("owned_probe_launcher", REPO / "scripts/runtime/dev.py")
    launcher = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = launcher
    spec.loader.exec_module(launcher)
    paths = launcher.layout(REPO, "machine-actor-probe-" + uuid.uuid4().hex[:12])
    launcher.prepare(paths)
    work = paths["tmp"]
    database = work / "archeaxis.sqlite"
    token = "c" * 64

    receipt = {"scope": "machine_actor_refusal_probe", "launch_declared_actor": "machine",
               "sent_human_declaration": False, "core_present": CORE.is_file()}
    if not CORE.is_file():
        receipt["ok"] = False; receipt["failed_step"] = "core_binary_missing"; return receipt

    launch = {"launch_token": token, "session_id": "d" * 32, "actor": "machine",
              "text_worker": {"python": sys.executable,
                              "script": str(REPO / "services/python-workers/transport/text_ndjson.py"),
                              "staging": str(work / "staging")}}
    core = subprocess.Popen([str(CORE), str(database), "0"], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                            encoding="utf-8")
    try:
        core.stdin.write(json.dumps(launch) + "\n")
        core.stdin.flush(); core.stdin.close()
        deadline = time.time() + 40
        line = ""
        while time.time() < deadline:
            line = core.stdout.readline()
            if "127.0.0.1:" in line: break
        if "127.0.0.1:" not in line:
            receipt["ok"] = False; receipt["failed_step"] = "readiness"; return receipt
        port = line.split("127.0.0.1:", 1)[1].split()[0].strip()
        base = "http://127.0.0.1:" + port + "/"
        receipt["ok"] = True

        version_request = urllib.request.Request(base + VERSION, method="GET",
            headers={"x-archeaxis-launch-token": token})
        with urllib.request.urlopen(version_request, timeout=10) as response:
            receipt["version_status"] = response.status

        body = {"item_key": "probe-item", "client_event_id": "probe-machine-event", "correct": True}
        request = urllib.request.Request(base + REVIEWS, data=json.dumps(body).encode(),
            method="POST",
            headers={"content-type": "application/json",
                     "x-archeaxis-launch-token": token,
                     "x-archeaxis-actor": "machine"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                receipt["review_status"] = response.status
                receipt["review_body"] = response.read().decode("utf-8", "replace")[:200]
        except urllib.error.HTTPError as error:
            receipt["review_status"] = error.code
            try:
                receipt["review_body"] = error.read().decode("utf-8", "replace")[:200]
            except Exception as read_error:
                receipt["review_body"] = f"<unreadable: {type(read_error).__name__}>"
        receipt["refused_with_403"] = receipt.get("review_status") == 403
        receipt["refusal_names_the_reason"] = "machine principal" in (receipt.get("review_body") or "")
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
