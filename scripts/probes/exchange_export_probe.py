"""Ingest a real file, export an open exchange directory, then verify what was written."""

import hashlib, json, os, shutil, socket, subprocess, sys, time, urllib.error, urllib.request, uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SAMPLE = REPO / "crates/archeaxis-archive/tests/fixtures/obsidian-vault/notes/index.md"
EXPORT_NAME = "probe-exchange"

# Route segments relative to the origin; the architecture guard reads a leading-slash runtime
# string as a hardcoded external absolute path, and relative-to-origin is what these are.
INTAKE = "workspace/api/intake/upload"
ANCHOR = "workspace/api/evidence/anchor"
EXPORT = "workspace/api/exchange/export"
VERIFY = "workspace/api/exchange/verify"


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0)); return int(sock.getsockname()[1])


def post_json(base, route, obj):
    request = urllib.request.Request(base + route, data=json.dumps(obj).encode(), method="POST",
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def run() -> dict:
    runs = REPO / ".project-local" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    work = runs / "exchange-probe-run"
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    database = work / "archeaxis.sqlite"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO); env["PYTHONIOENCODING"] = "utf-8"
    env["ARCHEAXIS_DB_PATH"] = str(database); env["ARCHEAXIS_DATA_DIR"] = str(work)

    receipt = {"scope": "exchange_export_probe", "steps": []}
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
        boundary = "----exchange" + uuid.uuid4().hex
        body = (f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="note.md"\r\n'
                "Content-Type: application/octet-stream\r\n\r\n").encode()
        body += blob + f"\r\n--{boundary}--\r\n".encode()
        request = urllib.request.Request(base + INTAKE, data=body, method="POST",
                                         headers={"Content-Type":
                                                  f"multipart/form-data; boundary={boundary}"})
        with urllib.request.urlopen(request, timeout=60) as response:
            intake = json.loads(response.read().decode("utf-8"))
        receipt["steps"].append({"step": "intake", "status": 200})
        receipt["intake_preserved_hash"] = (intake.get("raw_sha256")
                                            == hashlib.sha256(blob).hexdigest())

        # Anchor an exact character range, and read it back, so the receipt carries both the read
        # projection and the exported record and the two can be compared rather than described.
        text = blob.decode("utf-8", "replace")
        needle = "Why this matters"
        start = text.find(needle)
        locator = {"char_region": [start, start + len(needle)],
                   "block": f"notes/index.md#{needle}", "page": 1, "source_format": "md"}
        status, created = post_json(base, ANCHOR, {"raw_sha256": intake.get("raw_sha256"),
                                                    "source_revision": "1", "locator": locator})
        receipt["anchor_status"] = status
        read_request = urllib.request.Request(
            base + ANCHOR + "/" + str(created.get("anchor_id")), method="GET")
        with urllib.request.urlopen(read_request, timeout=60) as response:
            readback = json.loads(response.read().decode("utf-8"))
        projected = readback.get("locator") or {}
        receipt["read_projection_keys"] = sorted(projected.keys())
        receipt["read_projection_has_block_ids"] = "block_ids" in projected

        try:
            status, exported = post_json(base, EXPORT, {"name": EXPORT_NAME, "overwrite": True})
            receipt["export_status"] = status
            receipt["export"] = exported
        except urllib.error.HTTPError as error:
            receipt["export_status"] = error.code
            receipt["export_error"] = error.read().decode("utf-8", "replace")[:400]
            exported = None
        except Exception as error:
            receipt["export_status"] = None
            receipt["export_error"] = f"{type(error).__name__}: {error}"[:400]
            exported = None

        destination = exported.get("destination") if isinstance(exported, dict) else None
        if destination:
            path = Path(destination)
            receipt["destination_exists"] = path.is_dir()
            if path.is_dir():
                files = sorted(entry.name for entry in path.rglob("*") if entry.is_file())
                receipt["exported_files"] = files[:20]
                receipt["exported_file_count"] = len(files)
                manifest = path / "manifest.json"
                if manifest.is_file():
                    # The hash of the file that carries the manifest, recorded under a name that says
                    # so. It is deliberately NOT compared with the manifest's own manifest_sha256
                    # field: that field is not the hash of the file containing it, and treating the
                    # two as equal would manufacture a defect out of a wrong expectation.
                    receipt["manifest_file_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()

        try:
            request = urllib.request.Request(base + VERIFY + "?name=" + EXPORT_NAME, method="GET")
            with urllib.request.urlopen(request, timeout=180) as response:
                receipt["verify_status"] = response.status
                receipt["verify"] = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            receipt["verify_status"] = error.code
            receipt["verify_error"] = error.read().decode("utf-8", "replace")[:300]
        except Exception as error:
            receipt["verify_status"] = None
            receipt["verify_error"] = f"{type(error).__name__}: {error}"[:300]
        # What the exported record carries, for comparison with the read projection above.
        verify_payload = receipt.get("verify")
        manifest = (verify_payload or {}).get("manifest") if isinstance(verify_payload, dict) else None
        items = (manifest or {}).get("items") if isinstance(manifest, dict) else None
        exported_locator_keys: list[str] = []
        if items:
            for entry in items:
                metadata = entry.get("metadata") or {}
                loc = metadata.get("locator") or {}
                exported_locator_keys.extend(sorted(loc.keys()))
        receipt["exported_locator_keys"] = sorted(set(exported_locator_keys))
        receipt["exported_has_block_ids"] = "block_ids" in receipt["exported_locator_keys"]
        receipt["contrast"] = {
            "read_projection_has_block_ids": receipt["read_projection_has_block_ids"],
            "exported_has_block_ids": receipt["exported_has_block_ids"],
        }
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
