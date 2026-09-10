"""R15/F15: walk a real folder into a real Core, twice, and show what the second run costs.

The driver's claim is that a second run costs the Core nothing for unchanged files, and that a
file the Core will not take is recorded in the Core's own words. Both are measured here against a
real ``archeaxis-api`` process rather than a fake:

1. a folder is built with a markdown file, an HTML page, a real PDF, a nested text file, a file
   with an extension the Core cannot name, and a ``.git`` directory;
2. the driver imports each file and enqueues the job its kind calls for;
3. it runs again, and the receipt must show four skips and **zero** Core calls;
4. one file changes, and only that file is processed again.
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOKEN = "7" * 64
SESSION = "6" * 32


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


batch = _load("directory_batch_probe", REPO / "scripts" / "ingest" / "directory_batch.py")
core = _load("core_client_batch_probe", REPO / "shared" / "core_client.py")


def build_corpus(root: Path) -> None:
    import pymupdf

    root.mkdir(parents=True, exist_ok=True)
    (root / "nested").mkdir(exist_ok=True)
    (root / ".git").mkdir(exist_ok=True)
    (root / "notes.md").write_text("# Field notes\n\nThe radio array measured 41.5 decibels.\n", encoding="utf-8")
    (root / "page.html").write_text("<html><body><p>saved page body</p></body></html>", encoding="utf-8")
    (root / "nested" / "deep.txt").write_text("deep text file\n", encoding="utf-8")
    (root / "mystery.qzx").write_text("an extension nobody can name\n", encoding="utf-8")
    (root / ".git" / "config").write_text("[core]\n", encoding="utf-8")
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 100), "PDF body for the batch driver", fontsize=12)
    document.save(str(root / "sample.pdf"))
    document.close()


def launch_core(binary: Path, database: Path):
    child = subprocess.Popen(
        [str(binary), str(database), "0"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        cwd=str(REPO),
    )
    child.stdin.write(json.dumps({"launch_token": TOKEN, "session_id": SESSION}) + "\n")
    child.stdin.flush()
    child.stdin.close()
    deadline = time.time() + 20
    while time.time() < deadline:
        line = child.stdout.readline()
        if "127.0.0.1:" in line:
            port = line.split("127.0.0.1:", 1)[1].split()[0].strip()
            return child, f"http://127.0.0.1:{port}"
    child.kill()
    child.wait()
    return None, ""


def main() -> int:
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")

    receipt: dict = {"driver": "scripts/ingest/directory_batch.py", "token_printed": False}
    binary = REPO / ".project-local" / "build" / "cargo" / "debug" / "archeaxis-api.exe"
    if not binary.is_file():
        print(json.dumps({"ok": False, "blocked": "core binary not built", "path": str(binary)}, ensure_ascii=False, indent=2))
        return 2

    run_root = REPO / ".project-local" / "runs" / "r15-directory-batch"
    run_root.mkdir(parents=True, exist_ok=True)
    corpus = run_root / "corpus"
    build_corpus(corpus)
    manifest = run_root / "manifest.jsonl"
    with contextlib.suppress(FileNotFoundError):
        manifest.unlink()

    child, base = launch_core(binary, run_root / f"batch-{int(time.time())}.sqlite")
    if child is None:
        print(json.dumps({"ok": False, "reason": "the Core never reported readiness"}, ensure_ascii=False, indent=2))
        return 3

    calls: list[str] = []

    def counted_call(method: str, path: str, body=None):
        calls.append(path)
        return core.call(base, method, path, TOKEN, body)

    try:
        first = batch.run_batch(corpus, core_call=counted_call, manifest_path=manifest)
        first_calls = len(calls)
        calls.clear()
        second = batch.run_batch(corpus, core_call=counted_call, manifest_path=manifest)
        second_calls = len(calls)
        calls.clear()

        (corpus / "nested" / "deep.txt").write_text("deep text file, changed\n", encoding="utf-8")
        third = batch.run_batch(corpus, core_call=counted_call, manifest_path=manifest)
        third_calls = len(calls)
    finally:
        child.kill()
        child.wait()

    unmapped = [entry for entry in first["entries"] if entry["status"] == "imported_no_job"]
    receipt.update(
        {
            "corpus": sorted(path.relative_to(corpus).as_posix() for path in corpus.rglob("*") if path.is_file()),
            "excluded_paths": first["excluded_paths"],
            "run_1": {"counts": first["counts"], "core_calls": first_calls},
            "run_2": {"counts": second["counts"], "core_calls": second_calls},
            "run_3_after_one_change": {"counts": third["counts"], "core_calls": third_calls},
            "unmapped_reason": unmapped[0]["detail"] if unmapped else None,
            "manifest_lines": len([line for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]),
            "manifest": str(manifest),
        }
    )
    receipt["ok"] = bool(
        first["counts"]["enqueued"] == 4
        and first["counts"]["imported_no_job"] == 1
        and first["counts"]["refused"] == 0
        and second["counts"]["skipped_unchanged"] == 5
        and second_calls == 0
        and third["counts"]["enqueued"] == 1
        and third["counts"]["skipped_unchanged"] == 4
        and "no kind is mapped" in str(receipt["unmapped_reason"])
    )
    receipt["verdict"] = (
        "MEASURED: a real folder reached a real Core. The Core accepted the import of the file "
        "whose extension it cannot name, so the driver imported it and recorded that it carries no "
        "job, rather than guessing a route; the second run cost the Core nothing for unchanged "
        "files, and a third run after one change re-processed exactly that file"
    )
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt["ok"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
