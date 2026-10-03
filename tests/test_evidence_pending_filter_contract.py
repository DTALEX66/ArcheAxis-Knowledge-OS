"""The Evidence Center can show only the rows whose knowledge still awaits a person.

The filter is a view over data the Core already returns (`knowledge_status` on each anchor), so it
cannot invent a pending item. These assertions pin that the control exists, that the predicate
tests the Core's own status, and that a filtered-empty list says so instead of looking like an
evidence centre that found nothing.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XAML = ROOT / "apps" / "ArcheAxis.Desktop" / "Views" / "EvidenceCenterView.axaml"
CODE = ROOT / "apps" / "ArcheAxis.Desktop" / "Views" / "EvidenceCenterView.axaml.cs"
XNAME = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"


def _named():
    root = ET.parse(XAML).getroot()
    return {node.get(XNAME): node for node in root.iter() if node.get(XNAME)}


def test_the_pending_review_filter_exists_in_the_toolbar():
    named = _named()
    check = named["EvidencePendingOnlyCheck"]
    assert check.tag.endswith("CheckBox")
    assert check.get("Content") == "仅看待复核"
    # Off by default: the whole projection stays the default reading.
    assert check.get("IsChecked") == "False"
    # It belongs to the toolbar, never among the category tabs whose labels are pinned elsewhere.
    assert check in list(named["EvidenceToolbarActions"].iter())
    assert check not in list(named["EvidenceCategoryTabs"].iter())


def test_the_filter_reads_the_cores_knowledge_status_rather_than_guessing():
    code = CODE.read_text(encoding="utf-8")
    assert (
        'public bool IsPendingReview => string.Equals(KnowledgeStatus, "candidate", StringComparison.Ordinal);'
        in code
    )
    assert "row.IsPendingReview" in code
    assert "_allRows = rows;" in code


def test_a_filtered_empty_list_says_so_instead_of_looking_like_no_evidence():
    code = CODE.read_text(encoding="utf-8")
    assert "没有待复核的引用记录" in code
    assert "取消“仅看待复核”可看到全部引用。" in code
