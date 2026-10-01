from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN_VIEW = ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml"
MAIN_CODE = ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml.cs"


def test_workspace_split_tracks_b05_proportions_and_stacks_for_compact_content() -> None:
    root = ET.parse(MAIN_VIEW).getroot()
    xname = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"
    grid = next(element for element in root.iter() if element.get(xname) == "WorkspacePageGrid")
    assert grid.get("ColumnDefinitions") == "0.29*,0.71*"

    code = MAIN_CODE.read_text(encoding="utf-8")
    assert 'var workspaceStacked = contentWidth < GetAaosBreakpoint("AaosWorkspaceStackBreakpoint", 900);' in code
    responsive = code.split("var workspaceStacked =", 1)[1].split("TopbarBrandTagline", 1)[0]
    assert 'new ColumnDefinitions("0.29*,0.71*")' in responsive
    assert 'new ColumnDefinitions("*")' in responsive
    assert 'Grid.SetRow(WorkspaceFilesPanel, workspaceStacked ? 1 : 0);' in responsive
