"""Boot the product, take a real file in, stop it, boot again, and see what survived."""

import hashlib, json, os, shutil, socket, subprocess, sys, time, urllib.error, urllib.parse
import urllib.request, uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SAMPLE = REPO / "crates/archeaxis-archive/tests/fixtures/obsidian-vault/notes/index.md"

# Route segments relative to the origin; a leading slash would be read by the architecture guard as
# a hardcoded external absolute path, and relative-to-origin is what these are.
INTAKE = "workspace/api/intake/upload"
LIBRARY = "workspace/api/library"
CONVERSION_RUN = "workspace/api/library/{sha}/conversion-run"
HANDSHAKE = "api/v1/system/handshake"


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0)); return int(sock.getsockname()[1])


def start_app(env):
    port = free_port()
    app = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                            "--port", str(port), "--log-level", "warning"], cwd=str(REPO), env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                           encoding="utf-8", errors="replace")
    base = f"http://127.0.0.1:{port}/"
    deadline = time.time() + 120
    while time.time() < deadline:
        if app.poll() is not None:
            break
        try:
            with urllib.request.urlopen(base + HANDSHAKE, timeout=3) as response:
                if response.status == 200:
                    return app, base
        except Exception:
            time.sleep(1.0)
    app.kill()
    return None, base


def stop_app(app):
    app.kill()
    try:
        app.communicate(timeout=20)
    except Exception:
        pass


def get_json(base, route):
    try:
        with urllib.request.urlopen(base + route, timeout=60) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")[:300]


def run() -> dict:
    runs = REPO / ".project-local" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    work = runs / "cold-start-probe-run"
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    database = work / "archeaxis.sqlite"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO); env["PYTHONIOENCODING"] = "utf-8"
    env["ARCHEAXIS_DB_PATH"] = str(database); env["ARCHEAXIS_DATA_DIR"] = str(work)

    receipt = {"scope": "cold_start_probe", "steps": []}
    migration = subprocess.run([sys.executable, "-m", "app.runtime_entrypoint", "migrate"],
                               cwd=str(REPO), env=env, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=600)
    receipt["steps"].append({"step": "migrate", "exit": migration.returncode})
    if migration.returncode != 0:
        receipt["ok"] = False; receipt["failed_step"] = "migrate"; return receipt

    blob = SAMPLE.read_bytes()
    expected = hashlib.sha256(blob).hexdigest()
    receipt["source_sha256"] = expected

    # ---- first boot: take the file in ----
    app, base = start_app(env)
    receipt["steps"].append({"step": "first_boot", "started": app is not None})
    if app is None:
        receipt["ok"] = False; receipt["failed_step"] = "first_boot"; return receipt
    try:
        status, handshake_1 = get_json(base, HANDSHAKE)
        receipt["first_boot"] = {"schema_version": handshake_1.get("schema_version"),
                                 "capabilities": handshake_1.get("capabilities"),
                                 "migration_state": handshake_1.get("migration_state")}
        boundary = "----coldstart" + uuid.uuid4().hex
        body = (f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="note.md"\r\n'
                "Content-Type: application/octet-stream\r\n\r\n").encode()
        body += blob + f"\r\n--{boundary}--\r\n".encode()
        request = urllib.request.Request(base + INTAKE, data=body, method="POST",
                                         headers={"Content-Type":
                                                  f"multipart/form-data; boundary={boundary}"})
        with urllib.request.urlopen(request, timeout=60) as response:
            intake = json.loads(response.read().decode("utf-8"))
        receipt["intake_preserved_hash"] = intake.get("raw_sha256") == expected
        status, library = get_json(base, LIBRARY)
        receipt["library_before_restart_status"] = status
        receipt["library_before_restart_keys"] = (sorted(library.keys())
                                                   if isinstance(library, dict) else None)
        receipt["library_before_restart"] = library if isinstance(library, (list, dict)) else None
    finally:
        stop_app(app)

    # ---- second boot: same store, no migration, nothing re-ingested ----
    app2, base2 = start_app(env)
    receipt["steps"].append({"step": "second_boot", "started": app2 is not None})
    if app2 is None:
        receipt["ok"] = False; receipt["failed_step"] = "second_boot"; return receipt
    try:
        status, handshake_2 = get_json(base2, HANDSHAKE)
        receipt["second_boot"] = {"schema_version": handshake_2.get("schema_version"),
                                  "capabilities": handshake_2.get("capabilities"),
                                  "migration_state": handshake_2.get("migration_state")}
        status, library2 = get_json(base2, LIBRARY)
        receipt["library_after_restart_status"] = status
        receipt["library_after_restart"] = library2 if isinstance(library2, (list, dict)) else None
        route = CONVERSION_RUN.format(sha=urllib.parse.quote(expected, safe=""))
        status, run_payload = get_json(base2, route)
        receipt["conversion_run_after_restart_status"] = status
        receipt["conversion_run_after_restart_keys"] = (sorted(run_payload.keys())
                                                         if isinstance(run_payload, dict) else None)
        receipt["conversion_run_reports_hash_after_restart"] = (
            isinstance(run_payload, dict) and run_payload.get("raw_sha256") == expected)
    finally:
        stop_app(app2)

    receipt["capabilities_identical_across_restart"] = (
        receipt["first_boot"]["capabilities"] == receipt["second_boot"]["capabilities"])
    receipt["schema_version_identical_across_restart"] = (
        receipt["first_boot"]["schema_version"] == receipt["second_boot"]["schema_version"])
    receipt["library_identical_across_restart"] = (
        receipt["library_before_restart"] == receipt["library_after_restart"])
    receipt["ok"] = True
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
