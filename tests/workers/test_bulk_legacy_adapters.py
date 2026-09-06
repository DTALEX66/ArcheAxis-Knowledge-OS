"""BULK-0907 P18: legacy adapter pure-function difference cases.

Imports the real app.adapters modules (no legacy DB, no workspace writes). Each
assertion is an independent expected value derived from the adapter contract, not
copied from output: Anki/Zotero file bridges, pure mastery derivation, sleep-loop
taskpack fail-closed projections and DeepTutor inbound authority firewall.
"""

import os
import tempfile
import unittest

from app.adapters.anki_zotero import AdapterError, parse_zotero_json, to_anki_csv
from app.adapters.deeptutor.authority import AuthorityBoundaryError, DeepTutorAuthorityAdapter
from app.adapters.mastery_signal import from_learning_snapshots
from app.adapters.sleep_taskpack import (
    ContractMappingError,
    from_sleep_ledger_task,
    project_sleep_ledger_task_for_execution,
)


class AnkiZoteroBulkTests(unittest.TestCase):
    def test_to_anki_csv_quotes_and_joins_tags(self):
        csv = to_anki_csv([{"front": "问题", "back": "答案", "tags": ["alpha", "beta"]}])
        self.assertEqual(csv, '"问题","答案","alpha beta"\n')

    def test_to_anki_csv_rejects_empty_and_incomplete_cards(self):
        with self.assertRaises(AdapterError):
            to_anki_csv([])
        with self.assertRaises(AdapterError):
            to_anki_csv([{"front": "f"}])

    def test_parse_zotero_skips_untitled_and_combines_creators(self):
        items = [
            {"title": "", "creators": [{"firstName": "A", "lastName": "B"}]},
            {"itemType": "journalArticle", "title": "聚变研究", "date": "2025-03-01",
             "creators": [{"firstName": "张三", "lastName": "李"}, {"firstName": "", "lastName": ""}],
             "DOI": "10.1000/xyz", "url": "https://example.org/x"},
        ]
        units = parse_zotero_json(items)
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0]["title"], "聚变研究")
        self.assertEqual(units[0]["creators"], ["张三 李"])
        self.assertEqual(units[0]["year"], "2025")
        self.assertEqual(units[0]["doi"], "10.1000/xyz")


class MasterySignalBulkTests(unittest.TestCase):
    def _reviews(self, qualities, *, card_id="c1"):
        return [
            {"id": f"r{i}", "card_id": card_id, "quality": q, "ease_factor": 2.5,
             "created_at": f"2026-01-0{i + 1}T00:00:00Z"}
            for i, q in enumerate(qualities)
        ]

    def test_three_quality_four_reviews_without_mistakes_is_mastered(self):
        signal = from_learning_snapshots({"card_id": "c1"},
                                         self._reviews([4, 5, 4]), [])
        self.assertTrue(signal.is_mastered)
        self.assertEqual(signal.review_count, 3)
        self.assertEqual(signal.latest_review_quality, 4)

    def test_unresolved_mistake_blocks_mastery(self):
        mistakes = [{"id": "m1", "card_id": "c1", "resolved": False}]
        signal = from_learning_snapshots({"card_id": "c1"}, self._reviews([5, 5, 5]), mistakes)
        self.assertFalse(signal.is_mastered)
        self.assertEqual(signal.unresolved_mistake_ids, ["m1"])

    def test_no_reviews_is_not_mastered(self):
        signal = from_learning_snapshots({"card_id": "c1"}, [], [])
        self.assertFalse(signal.is_mastered)
        self.assertIsNone(signal.latest_review_quality)


class SleepTaskpackBulkTests(unittest.TestCase):
    def test_fail_closed_on_noop_executor_and_dry_run(self):
        task = {"id": "t1", "executor": "noop", "payload": {}, "dependencies": [],
                "requires_review": False, "content": "x", "risk_level": "low"}
        with self.assertRaises(ContractMappingError):
            project_sleep_ledger_task_for_execution(task, declared_allowed_tools=["noop"])
        task2 = {**task, "executor": "safe_write", "payload": {"dry_run": True}}
        with self.assertRaises(ContractMappingError):
            project_sleep_ledger_task_for_execution(
                task2, declared_allowed_tools=["safe_write"])
        task3 = {**task, "executor": "safe_write", "payload": {"dry_run": False},
                 "requires_review": 0}
        projected = project_sleep_ledger_task_for_execution(
            task3, declared_allowed_tools=["safe_write"], satisfied_dependency_ids=[])
        self.assertEqual(projected.requested_tools, ["safe_write"])

    def test_dependencies_become_constraints_not_success_criteria(self):
        task = {"id": "t2", "executor": "echo", "payload": {}, "dependencies": ["d1", "d2"],
                "requires_review": 0, "content": "目标", "risk_level": "low"}
        canonical = from_sleep_ledger_task(task, declared_allowed_tools=["echo"])
        self.assertEqual(canonical.success_criteria, [])
        self.assertTrue(any(constraint.startswith("sleep_dependency_ids_json=")
                            for constraint in canonical.constraints))


class DeepTutorAuthorityBulkTests(unittest.TestCase):
    def test_truth_fields_are_never_accepted_inbound(self):
        adapter = DeepTutorAuthorityAdapter(tempfile.mkdtemp(dir=os.environ["ARCHEAXIS_RUN_ROOT"]))
        with self.assertRaises(AuthorityBoundaryError):
            adapter.accept_learning_result({"event_id": "e", "learner_id": "u",
                                            "source_ref": "s", "kind": "k",
                                            "outcome": {}, "verified": True})


if __name__ == "__main__":
    unittest.main()
