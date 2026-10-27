"""SIMULATED DOM: trusted import/reader disclosure prerequisites, no Host/model."""
import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from tests.dom_harness import evaluate

ROOT = Path(os.environ.get("AAOS_PROBE_TEST_ROOT", str(Path(__file__).resolve().parents[1])))


def load_probe():
    spec = importlib.util.spec_from_file_location("grouped_import_disclosures", ROOT / "scripts/probes/aaos01_grouped_owner_loop.py")
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    return probe


class GroupedImportDisclosureTests(unittest.TestCase):
    def test_short_context_label_requires_full_ui_diagnostic_and_exact_core_identity(self):
        probe = load_probe()
        expected_id = "knowledge-" + "a" * 64
        for mode in ("correct", "wrong_ui_id", "wrong_core_id", "wrong_provenance", "duplicate_diagnostic"):
            with self.subTest(mode=mode):
                state, actions = {"diagnostic": False}, []
                grant = {"schema": "archeaxis.context-grant/v1", "knowledge_id": expected_id,
                         "state": "candidate", "consumer": "local-machine",
                         "provenance": [{"kind": "knowledge", "knowledge_id": expected_id}]}
                if mode == "wrong_ui_id": grant["knowledge_id"] = "another-knowledge"
                if mode == "wrong_provenance": grant["provenance"][0]["knowledge_id"] = "another-knowledge"
                def js(script):
                    markup = '<section aria-label="项目记忆与上下文内容"><p>固定知识：knowledge…aaaa</p><button data-diagnostic-label="完整上下文授权">状态与诊断</button></section>'
                    if state["diagnostic"]:
                        detail = '<details open><summary>完整上下文授权 · 操作与回执 · synthetic</summary><pre>' + json.dumps(grant) + '</pre></details>'
                        markup += '<section aria-label="诊断控制台">' + detail + (detail if mode == "duplicate_diagnostic" else '') + '</section>'
                    return evaluate(script, markup)
                class UI:
                    def __init__(self): self.js = js
                    def click_revealed_selector(self, selector):
                        assert "data-diagnostic-label='完整上下文授权'" in selector
                        actions.append("open-real-diagnostic")
                        state["diagnostic"] = True
                    def click_revealed(self, label, scope):
                        assert label == "关闭运行诊断" and scope == "//*[@role='dialog']"
                        actions.append("close-real-diagnostic")
                        state["diagnostic"] = False
                def read(operation, payload):
                    self.assertEqual((operation, payload), ("knowledge_get", {"id": expected_id}))
                    return {"knowledge_id": "another-knowledge" if mode == "wrong_core_id" else expected_id, "status": "accepted"}
                def wait(script): self.assertTrue(js(script), "Unique visible current diagnostic required")
                if mode == "correct":
                    probe.assert_ui_grant_knowledge(UI(), read, wait, expected_id)
                else:
                    with self.assertRaises(AssertionError): probe.assert_ui_grant_knowledge(UI(), read, wait, expected_id)
                self.assertEqual(actions, ["open-real-diagnostic", "close-real-diagnostic"])
                self.assertFalse(state["diagnostic"])

    def test_closed_import_opens_real_summary_before_trusted_file_input(self):
        probe = load_probe()
        for initially_open in (False, True):
            state, commands, clicks, evidence = {"open": initially_open}, [], [], []
            def js(script):
                markup = '<main data-current-page-id="16"></main><details class="exchange-folder-import"' + (' open' if state["open"] else '') + '><summary>批量导入文件夹</summary><input type="file" aria-label="选择文件夹"></details>'
                markup += '<section hidden><details class="exchange-folder-import"><summary>旧视图</summary><input type="file" aria-label="选择文件夹"></details></section>'
                return evaluate(script, markup)
            ui = probe.GroupedUI(js, lambda _: None, lambda *_: "file", lambda *args: commands.append(args), evidence)
            def click(selector):
                self.assertTrue(selector.endswith("/summary"))
                self.assertFalse(commands, "No file selection before the visible disclosure opens")
                clicks.append(selector)
                state["open"] = True
            with patch.object(ui, "click_revealed_selector", click):
                ui.upload_directory(ROOT / ".project-local" / "not-created-disclosure-fixture")
            self.assertEqual(len(clicks), 0 if initially_open else 1)
            self.assertEqual([row[1] for row in commands], ["value"])
            self.assertEqual(evidence[0]["action"], "folder_import_disclosure")
            self.assertFalse(evidence[0]["business_completion"])
            self.assertEqual(evidence[1]["action"], "trusted_directory_upload")

    def test_import_refuses_bad_scope_failed_open_and_hidden_or_disabled_input(self):
        probe = load_probe()
        base = '<details class="exchange-folder-import"><summary>批量导入文件夹</summary><input type="file" aria-label="选择文件夹"></details>'
        for mode in ("wrong_page", "missing", "ambiguous", "hidden", "disabled", "no_summary", "failed_open", "input_hidden"):
            with self.subTest(mode=mode):
                state, commands = {"open": False}, []
                def js(script):
                    markup = "" if mode == "missing" else base
                    if state["open"]: markup = markup.replace('<details ', '<details open ')
                    if mode == "ambiguous": markup += markup
                    if mode == "hidden": markup = '<section hidden>' + markup + '</section>'
                    if mode == "disabled": markup = markup.replace('type="file"', 'type="file" disabled')
                    if mode == "input_hidden": markup = markup.replace('type="file"', 'type="file" hidden')
                    if mode == "no_summary": markup = markup.replace('<summary>批量导入文件夹</summary>', '')
                    page = "03" if mode == "wrong_page" else "16"
                    return evaluate(script, '<main data-current-page-id="' + page + '"></main>' + markup)
                ui = probe.GroupedUI(js, lambda _: None, lambda *_: "file", lambda *args: commands.append(args), [])
                def click(_):
                    state["open"] = mode != "failed_open"
                with patch.object(ui, "click_revealed_selector", click), self.assertRaises(AssertionError):
                    ui.upload_directory(ROOT / ".project-local" / "not-created-disclosure-fixture")
                self.assertEqual(commands, [], "Invalid disclosure must not upload any file")

    def test_reader_attributes_open_same_associated_panel_or_fail_closed(self):
        probe = load_probe()
        for mode in ("closed", "open", "failed_open", "wrong_panel", "duplicate_control", "missing_toolbar"):
            state, clicks = {"open": mode == "open"}, []
            def js(script):
                control = '<button aria-controls="metadata" aria-expanded="' + ('true' if state["open"] else 'false') + '">属性与引用</button>'
                if mode == "duplicate_control": control += control
                toolbar_class = "missing-toolbar" if mode == "missing_toolbar" else "stitch-reader-toolbar"
                markup = '<section aria-label="阅读与编辑文档视图"><div class="' + toolbar_class + '">' + control + '</div>'
                panel = '<aside id="metadata"' + ('' if state["open"] else ' hidden') + '>内容详情</aside>'
                return evaluate(script, markup + (panel if mode != "wrong_panel" else '') + '</section>' + (panel if mode == "wrong_panel" else ''))
            class UI:
                def click_revealed_selector(self, selector):
                    clicks.append(selector)
                    state["open"] = mode != "failed_open"
            if mode in ("closed", "open"):
                probe.open_reader_attributes(UI(), js)
                self.assertEqual(len(clicks), 1 if mode == "closed" else 0)
            else:
                with self.assertRaises(AssertionError): probe.open_reader_attributes(UI(), js)
                self.assertEqual(len(clicks), 1 if mode == "failed_open" else 0)


if __name__ == "__main__":
    unittest.main()
