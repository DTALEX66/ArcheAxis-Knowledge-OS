"""The desktop runtime must have one documented, testable delivery chain."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_delivery_authority_index_separates_formal_shell_from_green_legacy_chain() -> None:
    index = ROOT / "docs" / "RUNTIME_DELIVERY_AUTHORITY_INDEX.md"
    assert index.is_file()
    content = index.read_text(encoding="utf-8")

    for required in (
        "src-tauri/tauri.conf.json",
        ".project-local/build/frontend-dist",
        ".project-local/build/tauri/release/ArcheAxis.exe",
        "ArcheAxis.Knowledge.Green-x64/ArcheAxis.exe",
        "启动星环知识.vbs",
        "Formal desktop UI source",
        "apps/ArcheAxis.Desktop/",
        "Legacy Green UI source",
        "not the formal vNext desktop",
        "Required evidence for an authorized legacy Green maintenance repair",
        "exact-path R6/A16 Owner Gate",
        "For the formal Tauri desktop",
        "SUP-022",
        "finite authenticated bridge",
        "credentials stay in Rust memory",
        "stage_backend_runtime.py",
        "not a second default product shell",
        "frozen v0.6.14 revision",
    ):
        assert required in content


def test_runtime_delivery_authority_index_local_links_resolve() -> None:
    index = ROOT / "docs" / "RUNTIME_DELIVERY_AUTHORITY_INDEX.md"
    content = index.read_text(encoding="utf-8")
    links = re.findall(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)", content)
    assert links
    unresolved = [link for link in links if not (index.parent / link).resolve().exists()]
    assert unresolved == []
