"""SIMULATED regression checks; no host/model/network calls."""

import ast
import html
import importlib.util
import json
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
            # SIMULATED rendering primitives; the actual production observer
            # still evaluates open/visible/focus/blocker readiness itself.
            prefix = """const computed=getComputedStyle;
getComputedStyle=(node,pseudo)=>pseudo?{contentVisibility:'visible',opacity:'1'}:computed(node);
document.defaultView.HTMLElement.prototype.getBoundingClientRect=function(){return {x:10,y:10,width:100,height:30};};
document.defaultView.HTMLElement.prototype.checkVisibility=function(){return this.getClientRects().length>0;};
document.defaultView.HTMLElement.prototype.getAnimations=function(){return [];};
document.elementFromPoint=()=>document.querySelector('button[data-page-id="03"]');
"""
            if focus != "body":
                prefix += (
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

        def wait(script, seconds=30):
            if script.startswith("return location.hash"):
                self.assertEqual(state["hash"], "#page=03")
                self.assertEqual(state["page"], "03")
            else:
                self.assertTrue(js(script), "SIMULATED rendered readiness was not satisfied")

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
            lambda _: {"ready": True, "disabled": False, "hit": True, "point": {"x": 5, "y": 9}},
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


class OriginalContextReadinessTests(unittest.TestCase):
    """SIMULATED actual probe observers and dispatch order; not native acceptance."""

    @classmethod
    def setUpClass(cls):
        path = ROOT / "scripts/probes/aaos01_tauri_webdriver_loop.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = {"original_context_script", "original_content_xpath",
                 "ui_format_conversion_loop", "ui_original_text_citations"}
        definitions = [node for node in tree.body
                       if isinstance(node, ast.FunctionDef) and node.name in names]
        assert len(definitions) == len(names)
        cls.probe = {"json": json}
        exec(compile(ast.Module(body=definitions, type_ignores=[]), str(path), "exec"), cls.probe)

    @staticmethod
    def markup(selected="scanned.pdf", title="scanned.pdf", hidden="", target_hidden=""):
        return (f'<div class="canonical-library" {hidden}>'
                '<nav aria-label="保留原件">'
                f'<button aria-current="true">{html.escape(selected)}</button></nav>'
                f'<div class="canonical-content"><h4>{html.escape(title)}</h4>'
                '<div class="canonical-reading"><div>'
                f'<section aria-label="真实转换产物" {target_hidden}>'
                '<button>执行真实内容转换</button></section>'
                '<section aria-label="原件文本范围引用"><textarea>synthetic</textarea></section>'
                '</div></div></div></div>')

    def observation(self, name="scanned.pdf"):
        return self.probe["original_context_script"](
            name, ':scope > .canonical-reading > div > section[aria-label="真实转换产物"]')

    def test_stale_split_hidden_and_ambiguous_contexts_are_rejected(self):
        cases = {
            "old_source": self.markup("text.pdf", "text.pdf"),
            "new_nav_old_content": self.markup(title="text.pdf"),
            "new_content_old_nav": self.markup(selected="text.pdf"),
            "substring_is_not_identity": self.markup("scanned.pdf.old", "scanned.pdf.old"),
            "hidden_root": self.markup(hidden="hidden"),
            "hidden_target": self.markup(target_hidden='style="display:none"'),
            "duplicate_context": self.markup() + self.markup(),
            "duplicate_selection": self.markup().replace(
                '</nav>', '<button aria-current="true">scanned.pdf</button></nav>'),
        }
        for label, markup in cases.items():
            with self.subTest(label=label):
                self.assertIsNone(evaluate(self.observation(), markup))

    def test_one_committed_visible_context_ignores_parked_source(self):
        markup = self.markup("text.pdf", "text.pdf", hidden="hidden") + self.markup()
        self.assertIs(evaluate(self.observation(), markup), True)
        name = "Author's scanned.pdf"
        self.assertIs(evaluate(self.observation(name), self.markup(name, name)), True)

    def test_wrong_context_never_reaches_conversion_input(self):
        actions = []

        def wait(script, **kwargs):
            self.assertIsNone(evaluate(script, self.markup("text.pdf", "text.pdf")))
            raise TimeoutError("SIMULATED old source never committed")

        with self.assertRaises(TimeoutError):
            self.probe["ui_format_conversion_loop"](
                lambda *args: self.fail("Old context must not even query target jobs"),
                lambda *args: actions.append(args), wait,
                lambda *args: self.fail("Old context must not inspect conversion control"),
                [{"name": "scanned.pdf", "format": "pdf-scanned", "source_id": "new-source"}])
        self.assertEqual(actions, [("scanned.pdf", "//nav[@aria-label='保留原件']")])

    def test_dispatch_waits_through_actual_async_context_transition(self):
        actions, reads, observations = [], [], []
        state = {"markup": self.markup("text.pdf", "text.pdf")}
        frames = [state["markup"], self.markup(title="text.pdf"), self.markup()]

        class ReachedConversion(Exception):
            pass

        def wait(script, **kwargs):
            for markup in frames:
                state["markup"] = markup
                ready = evaluate(script, markup)
                observations.append(ready)
                if ready:
                    return
            self.fail("New original did not become ready")

        def click(label, scope):
            actions.append((label, scope))
            if label == "执行真实内容转换":
                raise ReachedConversion()

        def bridge(operation, payload):
            reads.append((operation, payload))
            return {"jobs": []}

        with self.assertRaises(ReachedConversion):
            self.probe["ui_format_conversion_loop"](
                bridge, click, wait, lambda script: evaluate(script, state["markup"]),
                [{"name": "scanned.pdf", "format": "pdf-scanned", "source_id": "new-source"}])
        self.assertEqual(observations, [None, None, True])
        self.assertEqual(reads, [("source_jobs", {"source_id": "new-source"})])
        self.assertEqual([x[0] for x in actions], ["scanned.pdf", "执行真实内容转换"])
        self.assertIn('h4[normalize-space(.)="scanned.pdf"]', actions[1][1])

    def test_original_text_citation_also_waits_before_read_or_input(self):
        actions = []

        def wait(script, **kwargs):
            self.assertIsNone(evaluate(script, self.markup("text.pdf", "text.pdf")))
            raise TimeoutError("SIMULATED wrong original text target")

        with self.assertRaises(TimeoutError):
            self.probe["ui_original_text_citations"](
                lambda *args: self.fail("Wrong source must not be read"),
                lambda *args: actions.append(args),
                lambda *args: self.fail("Wrong original must not receive selection input"),
                wait, [{"format": "txt", "name": "text.txt"}],
                lambda *args: self.fail("No citation inspection before readiness"),
                lambda: self.fail("No pointer selection before readiness"))
        self.assertEqual(actions, [("text.txt", "//nav[@aria-label='保留原件']")])


if __name__ == "__main__":
    unittest.main()
