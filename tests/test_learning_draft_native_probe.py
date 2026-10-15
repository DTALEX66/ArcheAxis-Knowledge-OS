"""SIMULATED negative evidence checks; no native process or model is launched."""

import copy
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


def load_probe():
    path = Path(__file__).resolve().parents[1] / "scripts/probes/aaos01_learning_draft_recovery.py"
    spec = importlib.util.spec_from_file_location("learning_draft_native_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LearningDraftNativeProbeTests(unittest.TestCase):
    def test_delayed_navigation_prompt_retries_observation_only(self):
        calls = []
        class Alert(Exception):
            value = {"error": "unexpected alert open"}
        class UI:
            def accept_navigation_alert(self):
                calls.append("accept")
        def observe(script):
            calls.append("observe")
            if len(calls) == 1:
                raise Alert()
            return True
        self.assertTrue(self.probe.wait_with_navigation(UI(), observe, "observation"))
        self.assertEqual(calls, ["observe", "accept", "observe"])
        with self.assertRaises(RuntimeError):
            self.probe.wait_with_navigation(UI(), lambda script: (_ for _ in ()).throw(RuntimeError()), "observation")

    def test_isolated_mode_rejects_model_and_fault_modes_before_setup(self):
        path = Path(__file__).resolve().parents[1] / "scripts/probes/aaos01_grouped_owner_loop.py"
        spec = importlib.util.spec_from_file_location("grouped_draft_mode_guard", path)
        grouped = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(grouped)
        for option in ("run_ai", "authored_intervention", "require_actual_ai_loop", "review_ack_loss", "multi_review_ack_loss", "machine_ack_loss", "machine_cancel", "closure_features"):
            with self.subTest(option=option), patch.dict("os.environ", {"AAOS01_LEARNING_DRAFT_ONLY": "1"}), self.assertRaises(ValueError):
                grouped.run_grouped_loop(bridge=None, js=None, wait=None, element=None, command=None, work=None, screenshot=None, restart=None, **{option: True})

    def setUp(self):
        self.probe = load_probe()
        self.pin = dict(item_key="course:c1:artifact:a1", assessment_id="assessment_1", knowledge_version="knowledge_1", knowledge_id="knowledge_1", source_id="source_1", anchor_id="anchor_1")
        self.draft = self.probe.expected_draft(self.pin, "  原始答案\n\n", revealed=True, correct=True, rating=3)
        self.state = dict(workspace_id="workspace_1", restore_epoch="epoch_1", recovery_requires_confirmation=False, state=dict(learning_drafts={"assessment_1": self.draft}, pending_reviews={}))
        self.history = dict(item_key=self.pin["item_key"], count=0, events=[])

    def check(self, state=None, history=None, assessment=None):
        self.probe.assert_unsubmitted(state or self.state, self.draft, self.history, history or self.history, assessment or self.pin, self.pin)

    def test_accepts_exact_unsubmitted_fields_only(self):
        self.check()
        for field, value in (("answer", "原始答案"), ("rating", None), ("checked_correct", False), ("answer_revealed", False), ("knowledge_version", "new"), ("assessment_id", "other"), ("item_key", "other")):
            state = copy.deepcopy(self.state)
            state["state"]["learning_drafts"]["assessment_1"][field] = value
            with self.subTest(field=field), self.assertRaises(AssertionError):
                self.check(state=state)

    def test_rejects_submitted_or_wrong_source_as_recovery(self):
        state = copy.deepcopy(self.state)
        state["state"]["pending_reviews"] = {"event_1": {"body": {"answer": "原始答案"}}}
        with self.assertRaises(AssertionError):
            self.check(state=state)
        with self.assertRaises(AssertionError):
            self.check(history={**self.history, "count": 1, "events": [{"kind": "review"}]})
        for field in ("source_id", "anchor_id", "knowledge_id"):
            with self.subTest(field=field), self.assertRaises(AssertionError):
                self.check(assessment={**self.pin, field: "wrong"})

    def test_visible_fields_must_be_editable_and_bound_to_question(self):
        assessment = {**self.pin, "question": "原题"}
        observed = {**self.draft, "editable": True, "question": "原题", "knowledge": "知识修订：knowledge_1"}
        self.probe.assert_visible(observed, self.draft, assessment)
        for field, value in (("editable", False), ("question", "其他题"), ("knowledge", "其他来源"), ("rating", 1), ("answer", "原始答案")):
            with self.subTest(field=field), self.assertRaises(AssertionError):
                self.probe.assert_visible({**observed, field: value}, self.draft, assessment)

    def test_clear_requires_exact_target_and_preserves_other_draft(self):
        before = copy.deepcopy(self.state)
        before["state"]["learning_drafts"]["assessment_2"] = {**self.draft, "assessment_id": "assessment_2", "item_key": "other"}
        after = copy.deepcopy(before)
        del after["state"]["learning_drafts"]["assessment_1"]
        self.probe.assert_cleared(before, after, "assessment_1")
        after["state"]["learning_drafts"] = {}
        with self.assertRaises(AssertionError):
            self.probe.assert_cleared(before, after, "assessment_1")


if __name__ == "__main__":
    unittest.main()
