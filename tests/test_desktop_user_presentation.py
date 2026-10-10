"""Ordinary users keep content and errors; protocol records require expansion."""
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET
import pytest

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "apps/ArcheAxis.Desktop"

@pytest.mark.parametrize("file,names", [
    ("MainWindow.axaml", ["JobLookupIdBox", "MemoryMapKnowledgeIdBox", "JobOutputText",
                          "LibrarySelectedDetailText", "LibraryDetailKnowledgeText", "LibraryDetailTransformText", "LibraryDetailEngineText"]),
    ("Views/SourceReaderView.axaml", ["SourceReaderIdBox", "SourceReaderResultsText", "SourceReaderCoreNoteText",
                                    "SourceReaderJobFieldText", "SourceReaderShaFieldText", "SourceReaderChainSourceText",
                                    "SourceReaderChainJobText", "SourceReaderChainShaText", "SourceReaderCandidateReceiptText"]),
    ("Views/EvidenceCenterView.axaml", ["EvidenceAnchorDetailText", "EvidenceDetailLocatorText", "EvidenceDetailChainText", "EvidenceBundlesText"]),
])
def test_internal_records_require_expansion(file, names):
    root = ET.parse(DESKTOP / file).getroot()
    parents = {child: parent for parent in root.iter() for child in parent}
    controls = {node.get("{http://schemas.microsoft.com/winfx/2006/xaml}Name"): node for node in root.iter()}
    for name in names:
        node = controls[name]
        while node in parents:
            node = parents[node]
            if node.tag.endswith("Expander") and node.get("IsExpanded") == "False":
                break
        else:
            pytest.fail(f"{file}: {name} is visible without expansion")

def test_errors_and_content_keep_visible_surfaces():
    for file, names in [
        ("MainWindow.axaml", ["JobUserStatusText", "LibrarySelectedSummaryText"]),
        ("Views/SourceReaderView.axaml", ["SourceReaderStatusText", "SourceReaderTransformText", "SourceReaderCandidateStatusText"]),
        ("Views/EvidenceCenterView.axaml", ["EvidenceStatusText", "EvidenceDetailBodyText", "EvidenceDetailSourceText"]),
    ]:
        root = ET.parse(DESKTOP / file).getroot()
        parents = {child: parent for parent in root.iter() for child in parent}
        controls = {node.get("{http://schemas.microsoft.com/winfx/2006/xaml}Name"): node for node in root.iter()}
        for name in names:
            node = controls[name]
            while node in parents:
                node = parents[node]
                assert not (node.tag.endswith("Expander") and node.get("IsExpanded") == "False"), name

def test_display_preserves_failure_meaning_and_unknowns():
    powershell = shutil.which("pwsh")
    if powershell is None:
        pytest.skip("PowerShell 7 is required for C# presentation behaviour")
    result = subprocess.run([powershell, "-NoProfile", "-File", str(ROOT / "tests/desktop/UserDisplay.Tests.ps1")],
                            cwd=ROOT, text=True, encoding="utf-8", capture_output=True, timeout=45)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "USER DISPLAY PASS" in result.stdout

def test_raw_evidence_bindings_require_expansion_in_home_and_evidence_rows():
    for file in ("MainWindow.axaml", "Views/EvidenceCenterView.axaml"):
        root = ET.parse(DESKTOP / file).getroot()
        parents = {child: parent for parent in root.iter() for child in parent}
        for node in root.iter():
            binding = node.get("Text", "")
            if not any(f"Binding {key}" in binding for key in ("AnchorId", "SourceId", "RawSha256Display", "SourceRevisionDisplay", "LocatorDisplay")):
                continue
            cursor = node
            while cursor in parents:
                cursor = parents[cursor]
                if cursor.tag.endswith("Expander") and cursor.get("IsExpanded") == "False":
                    break
            else:
                pytest.fail(f"{file}: raw binding visible by default: {binding}")
