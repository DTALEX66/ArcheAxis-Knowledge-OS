"""SIMULATED DOM: exact reference rendering, identity and Core readback guards."""
import copy
import importlib.util
import os
from pathlib import Path
import unittest

from tests.dom_harness import evaluate, reader_dom

ROOT = Path(os.environ.get("AAOS_PROBE_TEST_ROOT", str(Path(__file__).resolve().parents[1])))


class RestoredReaderReferenceTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("reference_reader_probe", ROOT / "scripts/probes/aaos01_grouped_owner_loop.py")
        self.probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.probe)
        self.document = {
            "document_id": "owned", "source_id": "source", "source_revision": "a" * 64,
            "content_sha256": "b" * 64, "version": 3, "title": "Same title",
            "text_projection": "Alpha\nBeta", "editor_json": {"type": "doc", "content": [
                {"type": "paragraph", "content": [
                    {"type": "text", "text": "Alpha"},
                    {"type": "evidenceReference", "attrs": {"excerpt": "first", "anchor_id": "one"}},
                    {"type": "hardBreak"}, {"type": "text", "text": "Beta"},
                    {"type": "evidenceReference", "attrs": {"excerpt": "second", "anchor_id": "two"}},
                ]}
            ]},
        }

    def exercise(self, change=None, snapshot=False):
        document = self.document
        identity = {key: document[key] for key in ("document_id", "source_id", "source_revision", "content_sha256")}
        if change in identity:
            identity[change] = "wrong"
        state = {"diagnostic": False, "closed": False}
        visible = "Alpha引用：first\nBeta引用：second"
        wrong_text = {
            "lost-prose": "Alpha引用：first\n引用：second",
            "lost-reference": "Alpha\nBeta引用：second",
            "wrong-excerpt": "Alpha引用：WRONG\nBeta引用：second",
            "reference-order": "Alpha引用：second\nBeta引用：first",
            "reference-position": "引用：firstAlpha\nBeta引用：second",
            "duplicate-reference": visible + "引用：second",
            "raw-projection-only": document["text_projection"],
        }

        def js(script):
            text = wrong_text.get(change, visible)
            if change == "changed-after-close" and state["closed"]:
                text += "changed"
            markup = reader_dom(document, diagnostic=state["diagnostic"], identity=identity,
                text=text, title="wrong" if change == "title" else None,
                version=2 if change == "version" else None,
                page="02" if change == "page" else "03",
                hidden="hidden" if change == "hidden" else "")
            if snapshot:
                markup = markup.replace('<section aria-label="版本化草稿编辑器"><div class="ProseMirror">', '<section><pre aria-label="共享文档当前内容">').replace('</div></section>', '</pre></section>', 1)
            return evaluate(script, markup)

        def wait(script):
            assert js(script), "Business reader not visible"

        class UI:
            def click_revealed_selector(self, selector):
                assert "文档与来源详细信息" in selector
                state["diagnostic"] = True

            def click_revealed(self, label, scope):
                assert label == "关闭运行诊断"
                state.update(diagnostic=False, closed=True)

        def read(op, payload):
            assert op == "document_get" and payload == {"document_id": "owned"}
            value = copy.deepcopy(document)
            if change == "core-reference":
                value["editor_json"]["content"][0]["content"][1]["attrs"]["anchor_id"] = "different-anchor"
            return value

        return self.probe.restored_reader(UI(), read, js, wait, document)

    def test_exact_references_pass_in_editor_and_shared_snapshot(self):
        for snapshot in (False, True):
            with self.subTest(snapshot=snapshot):
                self.assertEqual(self.exercise(snapshot=snapshot)["status"], "PASS")

    def test_content_identity_visibility_and_readback_corruption_fail(self):
        for change in ("lost-prose", "lost-reference", "wrong-excerpt", "reference-order", "reference-position",
                       "duplicate-reference", "raw-projection-only", "title", "version", "page", "hidden",
                       "document_id", "source_id", "source_revision", "content_sha256", "core-reference", "changed-after-close"):
            with self.subTest(change=change), self.assertRaises(AssertionError):
                self.exercise(change)

    def test_reference_oracle_rejects_missing_editor_tree(self):
        document = copy.deepcopy(self.document)
        del document["editor_json"]
        with self.assertRaisesRegex(KeyError, "editor_json"):
            self.probe.restored_reader_expected_text(document)

    def test_reference_oracle_refuses_inconsistent_projection_and_unsupported_shape(self):
        for change in ("projection", "shape", "empty-excerpt", "strike"):
            document = copy.deepcopy(self.document)
            paragraph = document["editor_json"]["content"][0]
            if change == "projection": document["text_projection"] += "unaccounted"
            if change == "shape": paragraph["type"] = "unknown"
            if change == "empty-excerpt": paragraph["content"][1]["attrs"]["excerpt"] = ""
            if change == "strike": paragraph["content"][0]["marks"] = [{"type": "strike"}]
            with self.subTest(change=change), self.assertRaises(AssertionError):
                self.probe.restored_reader_expected_text(document)


if __name__ == "__main__":
    unittest.main()
