"""Ask the product what it can do, and ask it to search, and record both answers."""

import json, os, shutil, socket, subprocess, sys, time, urllib.error, urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# Route segments relative to the origin; a leading slash would be read by the architecture guard as
# a hardcoded external absolute path, and relative-to-origin is what these are.
HANDSHAKE = "api/v1/system/handshake"
SEARCH = "workspace/api/vault/search"


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0)); return int(sock.getsockname()[1])


def run() -> dict:
    runs = REPO / ".project-local" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    work = runs / "capability-search-probe-run"
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    database = work / "archeaxis.sqlite"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO); env["PYTHONIOENCODING"] = "utf-8"
    env["ARCHEAXIS_DB_PATH"] = str(database); env["ARCHEAXIS_DATA_DIR"] = str(work)

    receipt = {"scope": "capability_and_search_probe", "steps": []}
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
        handshake = None
        while time.time() < deadline:
            if app.poll() is not None: break
            try:
                with urllib.request.urlopen(base + HANDSHAKE, timeout=3) as response:
                    if response.status == 200:
                        handshake = json.loads(response.read().decode("utf-8")); break
            except Exception:
                time.sleep(1.0)
        if handshake is None:
            receipt["ok"] = False; receipt["failed_step"] = "handshake"; return receipt
        receipt["steps"].append({"step": "handshake", "status": 200})
        receipt["handshake_capabilities"] = handshake.get("capabilities")
        receipt["handshake_capabilities_is_empty_list"] = handshake.get("capabilities") == []

        # Search: the route takes {root, query} and the root must be an existing directory. An earlier
        # version pointed it at the working directory, which is full of the database and its sidecars,
        # and got a server error; a purpose-built vault avoids confusing the route with a store.
        import tempfile
        vault = Path(tempfile.mkdtemp(prefix="vault-"))
        (vault / "note.md").write_text(
            "# Index\n\nWhy this matters: a phrase to find.\n", encoding="utf-8")
        receipt["vault_root_has_space"] = " " in str(vault)
        for root in (str(vault), str(REPO / "crates/archeaxis-archive/tests/fixtures/obsidian-vault")):
            payload = {"root": root, "query": "Why this matters"}
            try:
                request = urllib.request.Request(base + SEARCH, data=json.dumps(payload).encode(),
                                                 method="POST",
                                                 headers={"Content-Type": "application/json"})
                # A short timeout on purpose: this call is expected not to answer, and waiting a
                # minute per attempt costs the suite two minutes for the same observation.
                with urllib.request.urlopen(request, timeout=10) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    receipt.setdefault("searches", []).append({
                        "root_kind": "purpose-built-vault" if root == str(vault) else "fixture-vault",
                        "status": response.status,
                        "keys": sorted(data.keys()) if isinstance(data, dict) else None,
                        "match_count": (len(data.get("results") or [])
                                        if isinstance(data, dict) else None),
                        "payload": json.dumps(data, ensure_ascii=False)[:320]})
            except urllib.error.HTTPError as error:
                # Reading an error body can itself hang, which is how an earlier run of this probe
                # crashed instead of reporting the status it had already received.
                try:
                    detail = error.read().decode("utf-8", "replace")[:300]
                except Exception as read_error:
                    detail = f"<error body unreadable: {type(read_error).__name__}>"
                receipt.setdefault("searches", []).append({
                    "root_kind": "temp-work" if root == str(work) else "fixture-vault",
                    "status": error.code,
                    "error": detail})
            except Exception as error:
                receipt.setdefault("searches", []).append({
                    "root_kind": "temp-work" if root == str(work) else "fixture-vault",
                    "status": None, "error": f"{type(error).__name__}: {error}"[:300]})
        shutil.rmtree(vault, ignore_errors=True)

        # The candidate listing is read-only and needs no identity at all. It is fetched to record
        # what a machine candidate looks like from outside, and in particular that nothing in it
        # attributes a decision to a person - the disposition path has no reviewer field.
        candidates_route = "workspace/api/runtime/candidates"
        try:
            request = urllib.request.Request(base + candidates_route, method="GET")
            with urllib.request.urlopen(request, timeout=30) as response:
                listing = json.loads(response.read().decode("utf-8"))
                receipt["candidates_status"] = response.status
                receipt["candidates_keys"] = (sorted(listing.keys())
                                              if isinstance(listing, dict) else None)
                receipt["candidates_payload"] = json.dumps(listing, ensure_ascii=False)[:400]
        except urllib.error.HTTPError as error:
            receipt["candidates_status"] = error.code
            try:
                receipt["candidates_error"] = error.read().decode("utf-8", "replace")[:240]
            except Exception as read_error:
                receipt["candidates_error"] = f"<unreadable: {type(read_error).__name__}>"
        except Exception as error:
            receipt["candidates_status"] = None
            receipt["candidates_error"] = f"{type(error).__name__}: {error}"[:240]

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
