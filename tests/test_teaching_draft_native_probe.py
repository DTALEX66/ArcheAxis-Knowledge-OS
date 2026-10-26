"""SIMULATED harness contract checks only; never launches native host or model."""
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


def load(name):
    path = Path(__file__).resolve().parents[1] / 'scripts/probes' / (name + '.py')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TeachingDraftProbeTests(unittest.TestCase):
    def setUp(self):
        self.probe = load('aaos01_teaching_draft_recovery')
        self.expected = dict(purpose='  用途  ', content='  正文\n\n')
        self.entry = dict(page_id='11', context_item_key=None, pending_record=None, form=self.expected)
        self.state = dict(workspace_id='ws', restore_epoch='epoch', recovery_requires_confirmation=False,
                          state=dict(teaching_drafts={'11:': self.entry, '12:': {'other': True}}))

    def test_exact_raw_inputs_and_page_context_are_required(self):
        self.probe.assert_draft(self.state, '11:', self.expected)
        for field, value in [('page_id', '12'), ('context_item_key', 'different'), ('pending_record', {'id': 'frozen'})]:
            state = copy.deepcopy(self.state)
            state['state']['teaching_drafts']['11:'][field] = value
            with self.subTest(field=field), self.assertRaises(AssertionError):
                self.probe.assert_draft(state, '11:', self.expected)
        for field in self.expected:
            state = copy.deepcopy(self.state)
            state['state']['teaching_drafts']['11:']['form'][field] = self.expected[field].strip()
            with self.subTest(field=field), self.assertRaises(AssertionError):
                self.probe.assert_draft(state, '11:', self.expected)

    def test_cleanup_retains_other_page_and_workspace(self):
        after = copy.deepcopy(self.state)
        del after['state']['teaching_drafts']['11:']
        self.probe.assert_cleanup(self.state, after, '11:')
        for mutation in ('other', 'epoch'):
            bad = copy.deepcopy(after)
            if mutation == 'other':
                bad['state']['teaching_drafts'] = {}
            else:
                bad['restore_epoch'] = 'different'
            with self.subTest(mutation=mutation), self.assertRaises(AssertionError):
                self.probe.assert_cleanup(self.state, bad, '11:')

    def test_frozen_editor_and_lossless_paragraphs_required(self):
        editor = dict(type='doc', content=[dict(type='paragraph', attrs=dict(block_id=str(i)),
                       **({'content': [dict(type='text', text=line)]} if line else {}))
                       for i, line in enumerate(self.expected['content'].split('\n'))])
        frozen = dict(operation='document_create', payload=dict(body=dict(editor_json=editor)))
        doc = dict(version=1, title='用途', source_id=None, source_revision=None, editor_json=editor,
                   text_projection='  正文')
        self.probe.assert_document(doc, self.expected, frozen)
        changed = copy.deepcopy(doc)
        changed['editor_json']['content'].pop()
        with self.assertRaises(AssertionError):
            self.probe.assert_document(changed, self.expected, frozen)
        with self.assertRaises(AssertionError):
            self.probe.assert_document({**doc, 'version': 2}, self.expected, frozen)

    def test_visible_values_and_editability_required(self):
        observed = {**self.expected, 'editable': True, 'form_count': 1, 'page': '12'}
        self.probe.assert_visible(observed, self.expected, '12')
        for mutation in ({'editable': False}, {'content': '正文'}, {'form_count': 0}, {'form_count': 2}, {'page': '11'}):
            with self.assertRaises(AssertionError):
                self.probe.assert_visible({**observed, **mutation}, self.expected, '12')

    def test_input_and_keys_scope_pin_current_dock_page(self):
        grouped = load('aaos01_grouped_owner_loop')
        calls = []
        ui = grouped.GroupedUI(lambda script: {'ready': True, 'disabled': False, 'hit': True, 'point': {'x': 1, 'y': 1}},
                               lambda script: True,
                               lambda using, selector: calls.append(selector) or 'visible-current-page',
                               lambda *args: None, [])
        ui.type('用途', 'raw', scope=self.probe.form_scope('12'))
        ui.keys(self.probe.form_scope('12') + "//label[normalize-space(text())='反馈分类']/select", '\ue015\ue007')
        self.assertEqual(len(calls), 3)
        for selector in calls:
            self.assertIn("contains(@data-session-key,':12:workspace')", selector)
            self.assertIn("not(ancestor-or-self::*[@hidden or @aria-hidden='true'])", selector)
            self.assertNotIn(':11:workspace', selector)
        with self.assertRaises(ValueError):
            self.probe.form_scope('01')

    def test_modes_reject_models_and_mutually_exclude_before_setup(self):
        grouped = load('aaos01_grouped_owner_loop')
        arguments = dict(bridge=None, js=None, wait=None, element=None, command=None, work=None,
                         screenshot=None, restart=None)
        for option in ('run_ai', 'authored_intervention', 'require_actual_ai_loop', 'review_ack_loss',
                       'multi_review_ack_loss', 'machine_ack_loss', 'machine_cancel', 'closure_features'):
            with self.subTest(option=option), patch.dict('os.environ', {'AAOS01_TEACHING_DRAFT_ONLY': '1', 'AAOS01_LEARNING_DRAFT_ONLY': '0'}), self.assertRaises(ValueError):
                grouped.run_grouped_loop(**arguments, **{option: True})
        with patch.dict('os.environ', {'AAOS01_TEACHING_DRAFT_ONLY': '1', 'AAOS01_LEARNING_DRAFT_ONLY': '1'}), self.assertRaises(ValueError):
            grouped.run_grouped_loop(**arguments)


if __name__ == '__main__':
    unittest.main()
