"""Post-native maintenance candidate; SIMULATED actual XPath/DOM semantics."""
import importlib.util
import unittest
from pathlib import Path

from lxml import etree

spec = importlib.util.spec_from_file_location("label_candidate", Path(__file__).resolve().parents[1] / "scripts/probes/aaos01_grouped_owner_loop.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class LabelAssociationTests(unittest.TestCase):
    def test_current_aaos_field_sibling_uses_exact_for_id_not_position(self):
        root = etree.HTML('<div><input id="decoy"/><label for=":r3:">查找能力</label><span>help</span><input id=":r3:"/><input id="other"/></div>')
        found = root.xpath(probe.label_selector("查找能力"))
        self.assertEqual([n.get("id") for n in found], [":r3:"])

    def test_scope_and_hidden_boundaries_are_preserved_for_both_forms(self):
        root = etree.HTML('<section id="owned"><label for="actual">Same</label><input id="actual"/><div hidden="hidden"><label for="hidden">Same</label><input id="hidden"/></div><label>Wrapped<input id="wrapped"/></label></section><section><label for="foreign">Same</label><input id="foreign"/></section>')
        scope = "//section[@id='owned']"
        self.assertEqual([n.get("id") for n in root.xpath(probe.label_selector("Same", scope=scope))], ["actual"])
        self.assertEqual([n.get("id") for n in root.xpath(probe.label_selector("Wrapped", scope=scope))], ["wrapped"])

    def test_for_must_match_actual_id_and_hidden_label_cannot_target_visible_control(self):
        root = etree.HTML('<div><label for="missing">Missing</label><input id="different"/><div hidden="hidden"><label for="visible">Hidden</label></div><input id="visible"/></div>')
        self.assertEqual(root.xpath(probe.label_selector("Missing")), [])
        self.assertEqual(root.xpath(probe.label_selector("Hidden")), [])

if __name__ == "__main__":
    unittest.main()
