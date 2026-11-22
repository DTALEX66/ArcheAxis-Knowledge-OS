"""The packaged client must resolve its adapters when launched outside a checkout."""

import json
import subprocess
import sys
from pathlib import Path

from scripts.release import stage_backend_runtime as stage

ROOT = Path(__file__).resolve().parents[1]


def test_exchange_is_a_runnable_bundled_resource(tmp_path):
    product = tmp_path / "AAOS"
    sources = stage.exchange_sources(ROOT)
    stage.stage_exchange_client(product, sources, [], None)
    app = product / "shared/exchange"
    for name, donor in sources.items():
        assert (app / name).read_bytes() == donor.read_bytes()
    resources = json.loads((ROOT / "src-tauri/tauri.conf.json").read_text(encoding="utf-8"))["bundle"]["resources"]
    assert "shared" in resources.values()
    assert '"%~dp0shared\\exchange" %*' in stage.write_launcher(product).read_text(encoding="utf-8")
    command = [sys.executable, "-I", "-B", str(app)]
    check = subprocess.run([*command, "--check-runtime"], cwd=tmp_path, capture_output=True, text=True, check=True)
    assert check.stdout.split() == ["anki", "evernote", "git", "joplin", "logseq", "notion", "obsidian", "siyuan", "zotero"]
    help_result = subprocess.run([*command, "exchange", "notion", "export", "--help"], cwd=tmp_path,
                                 capture_output=True, text=True, check=True)
    assert "--document" in help_result.stdout and "--output" in help_result.stdout
