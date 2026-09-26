from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.release.capture_source_snapshot import main


def _git_repo(root: Path) -> Path:
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
    (root / ".gitignore").write_text(".project-local/\n", encoding="utf-8")
    (root / "source.txt").write_text("source\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", ".gitignore", "source.txt"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "fixture"], check=True)
    return root


def test_capture_writes_only_a_new_project_local_snapshot(tmp_path: Path, monkeypatch, capsys) -> None:
    root = _git_repo(tmp_path / "repo")
    monkeypatch.delenv("ARCHEAXIS_DEV_ROOT", raising=False)
    output = root / ".project-local/runs/capture/artifacts/source-snapshot.json"
    monkeypatch.setattr(
        "sys.argv",
        ["capture_source_snapshot.py", "--root", str(root), "--out", str(output)],
    )

    assert main() == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema"] == "aaos.source-snapshot-receipt/v1"
    assert payload["snapshot"]["algorithm"] == "aaos-source-snapshot/v1"
    assert payload["snapshot"]["sha256"]
    assert "captured" in capsys.readouterr().out


def test_capture_refuses_existing_or_out_of_root_output(tmp_path: Path, monkeypatch) -> None:
    root = _git_repo(tmp_path / "repo")
    monkeypatch.delenv("ARCHEAXIS_DEV_ROOT", raising=False)
    existing = root / ".project-local/runs/capture/artifacts/existing.json"
    existing.parent.mkdir(parents=True)
    existing.write_text("preserve", encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        ["capture_source_snapshot.py", "--root", str(root), "--out", str(existing)],
    )
    assert main() != 0
    assert existing.read_text(encoding="utf-8") == "preserve"

    outside = tmp_path / "outside.json"
    monkeypatch.setattr(
        "sys.argv",
        ["capture_source_snapshot.py", "--root", str(root), "--out", str(outside)],
    )
    assert main() != 0
    assert not outside.exists()
