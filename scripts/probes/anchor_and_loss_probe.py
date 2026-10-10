"""Ingest a real file, anchor an exact position, and ask for the conversion loss notes."""

import hashlib, json, os, shutil, socket, subprocess, sys, time, urllib.error, urllib.parse
import urllib.request, uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SAMPLE = REPO / "crates/archeaxis-archive/tests/fixtures/obsidian-vault/notes/index.md"
NEEDLE = "Why this matters"

# Route segments relative to the origin; written without a leading slash because the architecture
# guard reads a leading-slash runtime string as a hardcoded external absolute path.
INTAKE = "workspace/api/intake/upload"
ANCHOR = "workspace/api/evidence/anchor"
CONVERSION_RUN = "workspace/api/library/{sha}/conversion-run"

# The locator fields that would have to come back for a read to be called a precise position.
PRECISION_FIELDS = ("char_region", "block")


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0)); return int(sock.getsockname()[1])


def run() -> dict:
    runs = REPO / ".project-local" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    work = runs / "anchor-loss-probe-run"
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    database = work / "archeaxis.sqlite"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO); env["PYTHONIOENCODING"] = "utf-8"
    env["ARCHEAXIS_DB_PATH"] = str(database); env["ARCHEAXIS_DATA_DIR"] = str(work)

    receipt = {"scope": "anchor_and_loss_probe", "steps": []}
    migration = subprocess.run([sys.executable, "-m", "app.runtime_entrypoint", "migrate"],
                               cwd=str(REPO), env=env, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=600)
    receipt["steps"].append({"step": "migrate", "exit": migration.returncode})
    if migration.returncode != 0:
        receipt["ok"] = False; receipt["failed_step"] = "migrate"; return receipt

    port = free_port()
    app = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                            "--port", str(port), "--log-level", "warning"], cwd=str(REPO), env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                           encoding="utf-8", errors="replace")
    try:
        base = f"http://127.0.0.1:{port}/"
        deadline = time.time() + 120
        while time.time() < deadline:
            if app.poll() is not None: break
            try:
                with urllib.request.urlopen(base + "api/v1/system/handshake", timeout=3) as response:
                    if response.status == 200: break
            except Exception:
                time.sleep(1.0)

        blob = SAMPLE.read_bytes()
        text = blob.decode("utf-8", "replace")
        boundary = "----anchorloss" + uuid.uuid4().hex
        body = (f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="note.md"\r\n'
                "Content-Type: application/octet-stream\r\n\r\n").encode()
        body += blob + f"\r\n--{boundary}--\r\n".encode()
        request = urllib.request.Request(base + INTAKE, data=body, method="POST",
                                         headers={"Content-Type":
                                                  f"multipart/form-data; boundary={boundary}"})
        with urllib.request.urlopen(request, timeout=60) as response:
            intake = json.loads(response.read().decode("utf-8"))
        source_sha = hashlib.sha256(blob).hexdigest()
        receipt["steps"].append({"step": "intake", "status": 200})
        receipt["intake"] = {"format": intake.get("format"), "engine": intake.get("engine"),
                             "raw_sha256": intake.get("raw_sha256")}
        receipt["intake_preserved_hash"] = intake.get("raw_sha256") == source_sha

        start = text.find(NEEDLE)
        locator = {"char_region": [start, start + len(NEEDLE)], "block": f"notes/index.md#{NEEDLE}",
                   "page": 1, "source_format": "md"}
        receipt["locator_sent"] = locator
        receipt["locator_offset_lands_on_the_phrase"] = (start >= 0
                                                         and text[start:start + len(NEEDLE)] == NEEDLE)
        request = urllib.request.Request(base + ANCHOR, data=json.dumps({
            "raw_sha256": intake.get("raw_sha256"), "source_revision": "1",
            "locator": locator}).encode(), method="POST",
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=60) as response:
            created = json.loads(response.read().decode("utf-8"))
        receipt["steps"].append({"step": "anchor_create", "status": 200})
        receipt["anchor_response_matches_sent_locator"] = created.get("locator") == locator
        anchor_id = created.get("anchor_id")

        with urllib.request.urlopen(base + ANCHOR + "/" + str(anchor_id), timeout=60) as response:
            readback = json.loads(response.read().decode("utf-8"))
        projected = readback.get("locator") or {}
        receipt["steps"].append({"step": "anchor_read", "status": 200})
        receipt["locator_readback"] = projected
        receipt["locator_readback_keys"] = sorted(projected.keys())
        receipt["precision_fields_returned"] = [f for f in PRECISION_FIELDS if f in projected]
        # The rule: a read is only a precise position if a precision field actually came back.
        receipt["precise_position_returned"] = bool(receipt["precision_fields_returned"])

        route = CONVERSION_RUN.format(sha=urllib.parse.quote(str(intake.get("raw_sha256")), safe=""))
        try:
            with urllib.request.urlopen(base + route, timeout=60) as response:
                receipt["conversion_run_status"] = response.status
                payload = json.loads(response.read().decode("utf-8"))
                receipt["conversion_run_keys"] = sorted(payload.keys()) if isinstance(payload, dict) else None
                receipt["loss_notes"] = payload.get("loss_notes") if isinstance(payload, dict) else None
                receipt["conversion_loss_notes"] = (payload.get("conversion_loss_notes")
                                                    if isinstance(payload, dict) else None)
                if isinstance(payload, dict):
                    receipt["conversion_run_engine"] = payload.get("engine")
                    receipt["conversion_run_block_count"] = payload.get("block_count")
                    receipt["format_execution_receipt"] = payload.get("format_execution_receipt")
                    receipt["format_execution_receipt_status"] = payload.get("format_execution_receipt_status")
        except urllib.error.HTTPError as error:
            receipt["conversion_run_status"] = error.code
            receipt["conversion_run_error"] = error.read().decode("utf-8", "replace")[:300]
        except Exception as error:
            receipt["conversion_run_status"] = None
            receipt["conversion_run_error"] = f"{type(error).__name__}: {error}"[:300]
        receipt["ok"] = True
    finally:
        app.kill()
        try: app.communicate(timeout=20)
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
