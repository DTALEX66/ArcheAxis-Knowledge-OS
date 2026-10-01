"""Desktop navigation keeps current routes, honest future status and a compact path."""

import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
XAML = ROOT / "apps/ArcheAxis.Desktop/MainWindow.axaml"
CODE = ROOT / "apps/ArcheAxis.Desktop/MainWindow.axaml.cs"
XNAME = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"


class NavigationHierarchyContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ET.parse(XAML).getroot()
        cls.code = CODE.read_text(encoding="utf-8")
        cls.named = {node.get(XNAME): node for node in cls.root.iter() if node.get(XNAME)}

    def test_daily_rail_and_system_are_separate(self):
        primary = self.named["PrimaryRailScrollViewer"]
        daily = [node.get(XNAME) for node in primary.iter() if node.get(XNAME, "").startswith("Rail")
                 and "master-nav-button" in node.get("Classes", "")]
        self.assertEqual(daily, ["RailWorkspaceButton", "RailCaptureButton", "RailEvidenceButton",
                                 "RailOriginalsButton", "RailLearningButton", "RailMachineButton",
                                 "RailWorkspaceTreeButton", "RailMemoryMapButton", "RailSearchButton",
                                 "RailReviewButton"])
        self.assertNotIn("RailSystemButton", daily)
        self.assertIn("RailSystemButton", self.named)

    def test_context_and_compact_navigation_have_real_route_targets(self):
        for name in ("ContextKnowledgeSubnav", "ContextOriginalSubnav", "ContextProjectSubnav",
                     "ContextMemorySubnav", "ContextSearchSubnav", "ContextSystemSubnav",
                     "CompactContextNavigation", "BreadcrumbDomainButton"):
            self.assertIn(name, self.named)
        self.assertIn("var showContextSidebar = !mobile && frameSize.Width >= 1120;", self.code)
        self.assertIn("CompactContextNavigation.IsVisible = !showContextSidebar;", self.code)
        self.assertIn('section is "evidence" or "library" or "source-reader" or "knowledge"', self.code)
        self.assertIn("OnBreadcrumbDomainClick", self.code)

    def test_blueprint_is_read_only_and_no_sample_person(self):
        text = XAML.read_text(encoding="utf-8")
        self.assertIn('Header="未来能力 · 待开发"', text)
        self.assertIn("Capability Atlas V2", text)
        self.assertNotIn('Text="Alex"', text)
        self.assertNotIn('Text="Personal Workspace"', text)


if __name__ == "__main__":
    unittest.main()
