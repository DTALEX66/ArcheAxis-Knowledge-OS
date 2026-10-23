"""SIMULATED current-component presentation checks; no native/model execution."""
import importlib.util
import unittest
from pathlib import Path

from tests.dom_harness import evaluate

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("closure_probe", ROOT / "scripts/probes/aaos01_closure_features.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ClosureFeaturesProbeTests(unittest.TestCase):
    def roles_markup(self):
        # Static JSX section from the real current component, including all role
        # headings and the Owner decision boundary; dynamic paragraphs may remain
        # inert text in this bounded DOM test.
        source = (ROOT / "frontend/src/components/ModelTaskRoles.tsx").read_text(encoding="utf-8")
        return source[source.index('<section aria-label="模型与工具职责">'):source.index('</section>') + len('</section>')]

    def test_catalog_selection_opens_current_details_before_reading_roles(self):
        actions = []
        state = {"details": False}
        markup = self.roles_markup()

        class UI:
            def page(self, page, confirm_navigation=False):
                actions.append(("page", page, confirm_navigation))

            def click(self, label, scope):
                actions.append(("click", label, scope))

            def type(self, label, value):
                actions.append(("type", label, value))

            def click_selector(self, selector):
                actions.append(("selector", selector))
                state["details"] = True

        def js(script):
            return evaluate(script, '<div ' + ('' if state["details"] else 'hidden') + '>' + markup + '</div>')

        def wait(script):
            self.assertTrue(js(script), "Roles must actually be displayed")

        probe.qualify_task_roles(UI(), js, wait)
        self.assertEqual(actions[0], ("page", "17", True))
        self.assertIn(("type", "查找能力", ""), actions)
        self.assertIn("@data-entry-id", actions[-1][1])
        self.assertEqual(actions[-1][0], "selector")

    def test_roles_reject_hidden_duplicate_and_missing_decision_boundary(self):
        markup = self.roles_markup()
        for wrapper in ('<div hidden>', '<div style="display:none">', '<div aria-hidden="true">'):
            with self.subTest(wrapper=wrapper):
                self.assertIsNone(evaluate(probe.ROLE_OBSERVATION, wrapper + markup + '</div>'))
        self.assertIsNone(evaluate(probe.ROLE_OBSERVATION, markup + markup))
        self.assertIsNotNone(evaluate(probe.ROLE_OBSERVATION, markup + '<div hidden>' + markup + '</div>'))
        class UI:
            def __getattr__(self, name):
                return lambda *args, **kwargs: None
        wrong = markup.replace('最终采用由用户决定', '自动采用')
        with self.assertRaisesRegex(AssertionError, 'task-role'):
            probe.qualify_task_roles(UI(), lambda script: evaluate(script, wrong), lambda script: None)

    def test_import_wait_requires_actual_saved_status_not_pending_or_error(self):
        def panel(message):
            return '<section aria-label="有界文档便携包"><p role="status">' + message + '</p></section>'
        self.assertTrue(evaluate(probe.IMPORT_SAVED_OBSERVATION, panel('已保存为新文档；尚未加入知识库，旧引用位置需要重新核对。')))
        for text in ('待保存：合成文件', '已读取所选包；尚未保存。', '保存结果尚未确认；请重试同一次导入，不会另建文档。'):
            with self.subTest(text=text):
                self.assertFalse(evaluate(probe.IMPORT_SAVED_OBSERVATION, panel(text)))
