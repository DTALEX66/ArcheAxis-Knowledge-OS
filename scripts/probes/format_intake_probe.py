"""Take real files through the running product and record what it says about each, unedited."""

import hashlib, json, os, shutil, socket, subprocess, sys, time, urllib.error, urllib.request, uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
VAULT = REPO / "crates/archeaxis-archive/tests/fixtures/obsidian-vault"

# The intake route as a path relative to the origin. Written without a leading slash because the
# architecture guard reads a leading-slash runtime string as a hardcoded external absolute path,
# and relative-to-origin is also simply what this is.
INTAKE_ROUTE = "workspace/api/intake/upload"
HANDSHAKE_ROUTE = "api/v1/system/handshake"
GOLDEN = REPO / "tests/fixtures/golden"
QUALITY = REPO / "tests/fixtures/f01-quality"

# Real files, one per format family the product claims to absorb. Nothing here is synthesised for
# this probe: each is a tracked fixture with its own provenance, and the receipt records the hash
# of the bytes that were actually sent.
SAMPLES = (
    (VAULT / "notes/index.md", "note.md", "md"),
    (QUALITY / "fallback-gbk.txt", "legacy-gbk.txt", "txt"),
    (GOLDEN / "golden-text-anchor.txt", "plain.txt", "txt"),
    (GOLDEN / "golden-web-anchor.html", "page.html", "html"),
    (GOLDEN / "golden-journey-evidence.pdf", "document.pdf", "pdf"),
    (GOLDEN / "golden-docx-anchor.docx", "report.docx", "docx"),
    (GOLDEN / "golden-xlsx-anchor.xlsx", "sheet.xlsx", "xlsx"),
    (GOLDEN / "golden-pptx-anchor.pptx", "slides.pptx", "pptx"),
    (QUALITY / "ragged.csv", "ragged.csv", "csv"),
    (GROUP := VAULT / "attachments/diagram.png", "picture.png", "png"),
    (GOLDEN / "golden-screenshot-ocr.png", "screenshot.png", "png"),
    (VAULT / "vault.canvas", "board.canvas", "canvas"),
    (GOLDEN / "learning-evidence.canvas", "learning.canvas", "canvas"),
    (GOLDEN / "golden-audio-anchor.wav", "audio.wav", "wav"),
    (GOLDEN / "golden-video-anchor.mp4", "video.mp4", "mp4"),
    (REPO / "tests/fixtures/anki-apkg/review.apkg", "package.apkg", "apkg"),
    (QUALITY / "unsupported.unknown-ext", "mystery.unknown-ext", "unknown-ext"),
)

# The outcomes this probe is allowed to record. The distinction between the first three and the
# last is the whole point: a format may be carried, held in custody, or refused for a missing
# engine without any of those being structure extraction, and recording them as one bucket is how
# "transported" quietly becomes "supported".
CARRIED = "carried_passthrough"
CUSTODY = "custody_only"
ENGINE_MISSING = "engine_missing"
STRUCTURED = "structured"
REFUSED = "refused"

# Markers that would justify calling a result structural rather than carried. Kept explicit and
# deliberately narrow: adding one is a claim that structure was recovered, and a test enforces
# that nothing is called structured without one.
STRUCTURE_MARKERS = ("blocks", "nodes", "sections", "headings", "outline", "pages")


def classify(status, payload, error_body):
    """Return (outcome, evidence) for one response, without flattering it."""
    if status is None:
        return REFUSED, "no response"
    if status != 200:
        text = error_body or ""
        lowered = text.lower()
        if "requires" in lowered or "install" in lowered or "no engine could convert" in lowered:
            return ENGINE_MISSING, text[:240]
        return REFUSED, text[:240]
    body = payload if isinstance(payload, dict) else {}
    engine = str(body.get("engine", ""))
    preview = str(body.get("content_preview", ""))
    if "custody only" in preview.lower():
        return CUSTODY, "content states custody only"
    if engine.strip().lower() == "passthrough":
        return CARRIED, f"engine is {engine!r}; content carried, not parsed"
    if any(marker in preview.lower() for marker in STRUCTURE_MARKERS):
        return STRUCTURED, f"engine is {engine!r} and the projection names structure"
    return CARRIED, f"engine is {engine!r}; no structure named"


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0)); return int(sock.getsockname()[1])


def multipart(name, blob):
    boundary = "----formatprobe" + uuid.uuid4().hex
    head = (f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{name}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n").encode()
    return head + blob + f"\r\n--{boundary}--\r\n".encode(), boundary


def run() -> dict:
    runs = REPO / ".project-local" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    work = Path(__file__).resolve().parents[2] / ".project-local" / "runs" / "format-intake-probe-run"
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    database = work / "archeaxis.sqlite"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO); env["PYTHONIOENCODING"] = "utf-8"
    env["ARCHEAXIS_DB_PATH"] = str(database); env["ARCHEAXIS_DATA_DIR"] = str(work)

    receipt = {"scope": "format_intake_probe", "items": [], "steps": []}
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
                with urllib.request.urlopen(base + HANDSHAKE_ROUTE, timeout=3) as response:
                    if response.status == 200: break
            except Exception:
                time.sleep(1.0)
        for path, name, expected in SAMPLES:
            blob = path.read_bytes()
            item = {"sample": name, "expected_format": expected, "bytes": len(blob),
                    "source_sha256": hashlib.sha256(blob).hexdigest()}
            body, boundary = multipart(name, blob)
            request = urllib.request.Request(base + INTAKE_ROUTE, data=body,
                                             method="POST",
                                             headers={"Content-Type":
                                                      f"multipart/form-data; boundary={boundary}"})
            status, payload, error_body = None, None, None
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    status = response.status
                    payload = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as error:
                status = error.code
                error_body = error.read().decode("utf-8", "replace")
            except Exception as error:
                error_body = f"{type(error).__name__}: {error}"
            outcome, evidence = classify(status, payload, error_body)
            item["status"] = status
            item["outcome"] = outcome
            item["evidence"] = evidence
            if isinstance(payload, dict):
                item["format"] = payload.get("format");
                item["engine"] = payload.get("engine");
                item["reported_sha256"] = payload.get("raw_sha256");
                item["sha256_matches_source"] = payload.get("raw_sha256") == item["source_sha256"]
                item["requires_human_review"] = payload.get("requires_human_review")
            receipt["items"].append(item)
    finally:
        app.kill()
        try: app.communicate(timeout=20)
        except Exception: pass
        shutil.rmtree(work, ignore_errors=True)
    receipt["ok"] = len(receipt["items"]) == len(SAMPLES)
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
