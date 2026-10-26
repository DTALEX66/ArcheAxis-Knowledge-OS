"""SIMULATED regression checks; no host/model/network calls."""

import ast
import importlib.util
import unittest
from pathlib import Path

from tests.dom_harness import evaluate

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "grouped_native_focus_contract", ROOT / "scripts/probes/aaos01_grouped_owner_loop.py"
)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class NativeProbeFocusTests(unittest.TestCase):
    def exercise(self, summary=True, land="03", same=False, alert=False, confirm=False, current=None):
        state = {
            "focus": "summary" if summary else "body",
            "hash": "#page=03" if same else "#page=01",
            "page": current or ("03" if same else "01"),
        }
        actions = []
        markup = '<main aria-label="当前页面" data-current-page-id="CURRENT"></main><nav class="stitch-workspace-menu" aria-label="应用菜单"><div class="stitch-menus"><details open><summary>Menu</summary><button data-page-id="02">Two</button><button data-page-id="03">Three</button></details></div><button aria-label="全部页面，打开产品导航">全部页面</button></nav><nav class="stitch-workspace-dock" aria-label="工作空间快捷导航"><button data-page-id="01">首页</button></nav>'

        class AlertError(Exception):
            value = {"error": "unexpected alert open"}

        def js(script):
            if script == "return location.hash":
                return state["hash"]
            focus = state["focus"]
            prefix = ""
            if focus != "body":
                prefix = (
                    "document.querySelector("
                    + repr(
                        "summary" if focus == "summary" else 'button[data-page-id="' + focus + '"]'
                    )
                    + ").focus();"
                )
            return evaluate(prefix + script, markup.replace("CURRENT", state["page"]))

        def command(node, op, body):
            actions.append(body["text"])
            if body["text"] == "\ue004" * 2:
                state["focus"] = land
            elif body["text"] == "\ue007":
                if alert:
                    raise AlertError()
                state["hash"] = "#page=03"
                state["page"] = "03"
            else:
                raise AssertionError("Unexpected navigation input")

        def wait(script):
            if script.startswith("return location.hash"):
                self.assertEqual(state["hash"], "#page=03")
                self.assertEqual(state["page"], "03")

        def accept():
            actions.append("confirm")
            state["hash"] = "#page=03"
            state["page"] = "03"

        ui = p.GroupedUI(js, wait, lambda *args: "element", command, [], accept)
        try:
            ui.page("03", confirm_navigation=confirm)
        except Exception as error:
            return actions, error
        return actions, None

    def test_exact_target_requires_tabs_before_enter(self):
        actions, error = self.exercise()
        self.assertIsNone(error)
        self.assertEqual(actions, ["\ue004" * 2, "\ue007"])

    def test_missing_summary_focus_fails_without_any_input(self):
        actions, error = self.exercise(summary=False)
        self.assertIsInstance(error, AssertionError)
        self.assertEqual(actions, [])

    def test_wrong_tab_landing_never_activates_sibling(self):
        actions, error = self.exercise(land="02")
        self.assertIsInstance(error, AssertionError)
        self.assertEqual(actions, ["\ue004" * 2])

    def test_same_page_does_not_touch_menu(self):
        self.assertEqual(self.exercise(same=True), ([], None))

    def test_hash_alone_cannot_skip_a_different_rendered_page(self):
        actions, error = self.exercise(same=True, current="01")
        self.assertIsNone(error)
        self.assertEqual(actions, ["\ue004" * 2, "\ue007"])

    def test_unapproved_alert_propagates_without_retry(self):
        actions, error = self.exercise(alert=True)
        self.assertIsNotNone(error)
        self.assertEqual(actions, ["\ue004" * 2, "\ue007"])

    def test_confirmation_is_once_without_replaying_enter(self):
        actions, error = self.exercise(alert=True, confirm=True)
        self.assertIsNone(error)
        self.assertEqual(actions, ["\ue004" * 2, "\ue007", "confirm"])

    def test_xpath_dispatch_uses_hit_tested_pointer_path(self):
        actions = []
        ui = p.GroupedUI(
            lambda _: {"ready": True, "point": {"x": 5, "y": 9}},
            lambda _: None,
            lambda *_: "element",
            lambda *args: actions.append(args),
            [],
        )
        ui.click_selector("//button")
        self.assertEqual(actions, [(None, "pointer_click", {"x": 5, "y": 9})])


class ReaderAndImageDriftTests(unittest.TestCase):
    def test_current_component_heading_and_version_and_body(self):
        markup = '<main data-current-page-id="03"></main><section aria-label="阅读与编辑文档视图"><header class="stitch-reader-heading"><div><h2>Exact title</h2></div><p><span class="stitch-document-version">v7 · 未保存</span></p></header><article aria-label="文档正文与编辑"><header><h3>文档正文</h3></header><section aria-label="版本化草稿编辑器"><div class="ProseMirror">Exact body</div></section></article></section>'
        self.assertEqual(
            evaluate(p.READER_RESTORE_OBSERVATION, markup),
            {
                "page": "03",
                "reader_count": 1,
                "title": "Exact title",
                "text": "Exact body",
                "console_height": None,
                "version": 7,
            },
        )
        self.assertEqual(
            evaluate(p.READER_RESTORE_OBSERVATION, markup.replace("v7 · 未保存", "v3"))["version"],
            3,
        )
        ambiguous = markup.replace("</div><p>", "<h2>Wrong duplicate</h2></div><p>")
        self.assertIsNone(evaluate(p.READER_RESTORE_OBSERVATION, ambiguous)["title"])
        malformed = markup.replace("v7 · 未保存", "version unknown")
        self.assertIsNone(evaluate(p.READER_RESTORE_OBSERVATION, malformed)["version"])

    def test_image_wait_excludes_separator_but_keeps_visible_broken_image(self):
        tree = ast.parse(
            (ROOT / "scripts/probes/aaos01_tauri_webdriver_loop.py").read_text(encoding="utf-8")
        )
        scripts = [
            n.value
            for n in ast.walk(tree)
            if isinstance(n, ast.Constant)
            and isinstance(n.value, str)
            and "const brand=document" in n.value
        ]
        self.assertEqual(len(scripts), 2)
        setup = """document.querySelector('.stitch-brand svg').getBoundingClientRect=()=>({width:20,height:20});
for(const n of document.images){n.getClientRects=()=>[{width:n.className==='ProseMirror-separator'?0:20,height:n.className==='ProseMirror-separator'?0:20}];}
"""
        markup = '<div class="stitch-brand"><svg></svg></div><img class="ProseMirror-separator">'
        self.assertTrue(evaluate(setup + scripts[0], markup))
        self.assertEqual(evaluate(setup + scripts[1], markup)["visibleImages"], [])
        broken = markup + '<img src="missing.png" class="real-content">'
        self.assertFalse(evaluate(setup + scripts[0], broken))
        self.assertEqual(len(evaluate(setup + scripts[1], broken)["visibleImages"]), 1)
        self.assertTrue(
            evaluate(
                setup + scripts[0],
                broken.replace(
                    'class="real-content"', 'class="real-content" style="visibility:hidden"'
                ),
            )
        )


if __name__ == "__main__":
    unittest.main()
