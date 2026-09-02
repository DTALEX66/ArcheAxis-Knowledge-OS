"""The desktop runtime must have one documented, testable delivery chain."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_delivery_authority_index_names_the_primary_shell_chain() -> None:
    index = ROOT / "docs" / "RUNTIME_DELIVERY_AUTHORITY_INDEX.md"
    assert index.is_file()
    content = index.read_text(encoding="utf-8")

    for required in (
        "src-tauri/tauri.conf.json",
        "frontend/dist",
        "src-tauri/target/release/ArcheAxis.exe",
        "ArcheAxis.Knowledge.Green-x64/ArcheAxis.exe",
        "启动星环知识.vbs",
    ):
        assert required in content


def test_runtime_delivery_authority_index_local_links_resolve() -> None:
    index = ROOT / "docs" / "RUNTIME_DELIVERY_AUTHORITY_INDEX.md"
    content = index.read_text(encoding="utf-8")
    links = re.findall(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)", content)
    assert links
    unresolved = [link for link in links if not (index.parent / link).resolve().exists()]
    assert unresolved == []
