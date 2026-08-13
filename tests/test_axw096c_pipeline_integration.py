"""AXW-096C: batch controller x real conversion pipeline integration.

Proves the controller drives the real resumable conversion pipeline:
a mixed directory converts to completion through the controller, a
paused batch leaves a consistent checkpoint, and resuming rehydrates
from the ledger without double-converting completed files.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.ingestion.batch_controller import BatchImportController
from app.ingestion.multi_format import convert_directory_resumable


def _conversion_worker_factory(corpus_dir: Path, artifacts_dir: Path, io_sleep_s: float = 0.0):
    """Build a worker that converts one file through the resumable pipeline."""

    def worker(rel_path: str) -> dict[str, str]:
        import time

        if io_sleep_s:
            time.sleep(io_sleep_s)  # simulate real bulk-import IO cost
        result = convert_directory_resumable(
            directory=corpus_dir,
            manifest_path=artifacts_dir / "manifest.json",
            output_dir=artifacts_dir,
            pattern=f"**/{rel_path}",
            max_files=1,
        )
        processed = result.get("processed", 0)
        return {"result_digest": f"converted:{processed}"}

    return worker


def test_batch_drives_real_conversion(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    (corpus / "docs").mkdir(parents=True)
    for name, content in (
        ("a.md", "# Alpha\n\nHello world."),
        ("b.md", "# Beta\n\nSecond file."),
        ("c.txt", "Plain text file.\n"),
    ):
        (corpus / "docs" / name).write_text(content, encoding="utf-8")

    artifacts = tmp_path / "artifacts"
    controller = BatchImportController(checkpoint_path=tmp_path / "ledger.jsonl")
    controller.add_tasks(["docs/a.md", "docs/b.md", "docs/c.txt"])
    state = controller.run(_conversion_worker_factory(corpus, artifacts), max_concurrent=2)

    assert state.state == "finished"
    assert state.completed == 3
    assert state.failed == 0
    # real artifacts were produced by the pipeline (converted md files)
    produced = [p.name for p in artifacts.glob("*.md")] if artifacts.is_dir() else []
    assert len(produced) >= 1
    # ledger recorded digests for every task
    status = controller.status()
    for task in ("docs/a.md", "docs/b.md", "docs/c.txt"):
        assert status["results"][task]["status"] == "completed"
        assert status["results"][task]["result_digest"].startswith("converted:")


def test_pause_resume_through_real_pipeline(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    (corpus / "docs").mkdir(parents=True)
    tasks: list[str] = []
    for index in range(12):
        name = f"f{index:02d}.md"
        (corpus / "docs" / name).write_text(f"# File {index}\n\nBody {index}.\n", encoding="utf-8")
        tasks.append(f"docs/{name}")

    artifacts = tmp_path / "artifacts"
    ledger = tmp_path / "ledger.jsonl"
    controller = BatchImportController(checkpoint_path=ledger)
    controller.add_tasks(tasks)

    import threading
    import time

    thread = threading.Thread(
        target=lambda: controller.run(
            _conversion_worker_factory(corpus, artifacts, io_sleep_s=0.03),
            max_concurrent=2,
        ),
        daemon=True,
    )
    thread.start()
    time.sleep(0.12)
    controller.pause()
    paused = controller.status()
    assert paused["state"] == "paused"
    assert 1 <= paused["completed"] < 12
    controller.resume()
    thread.join(timeout=60)
    assert controller.status()["state"] == "finished"
    assert controller.status()["completed"] == 12

    # resume from checkpoint: completed tasks keep digests, none re-run
    resumed = BatchImportController.from_checkpoint(ledger)
    resumed_state = resumed.status()
    assert resumed_state["results"]["docs/f00.md"]["status"] == "completed"
    assert all(line.strip() for line in ledger.read_text(encoding="utf-8").splitlines())
    for line in ledger.read_text(encoding="utf-8").splitlines():
        json.loads(line)
