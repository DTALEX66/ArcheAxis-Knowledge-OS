"""Pure-logic tests for the pre-registered local model quality suite.

No model, Core or network is used here: only the frozen entries, deterministic
scoring, refusal/conflict detection and the receipt schema are exercised.
"""

import importlib.util
import unittest
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts/probes/aaos_quality_suite.py"
)
SPEC = importlib.util.spec_from_file_location("quality_suite_under_test", SCRIPT)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


COMPLIANT_ANSWERS = {
    "Q01": "根据上下文，项目代号为 AURORA-7，发布状态为 FROZEN，冻结日期为 2026-03-14。",
    "Q02": "根据上下文，并发上限为 12，重试次数为 3，超时时间为 45 秒。",
    "Q03": "根据上下文，当班负责人是李明，升级联系人是王芳。",
    "Q04": "根据上下文，缓存容量为 256 GB，保留周期为 30 天。",
    "Q05": "材料中没有提供加密算法，无法回答。",
    "Q06": "材料中没有提供结束日期，无法确定。",
    "Q07": "材料给出两个不同的校验值 37 和 41，无法确定唯一值。",
    "Q08": "两份材料互相矛盾，无法确定当前版本。",
}


def entry(entry_id):
    return next(item for item in probe.ENTRIES if item["entry_id"] == entry_id)


def synthetic_result(item):
    text = COMPLIANT_ANSWERS[item["entry_id"]]
    return {
        "entry_id": item["entry_id"],
        "class": item["class"],
        "question": item["question"],
        "context": item["context"],
        "knowledge_id": "k_synthetic",
        "grant_document_id": "d_synthetic",
        "answer_id": "answer_synthetic",
        "status": "ANSWERED",
        "reason": None,
        "authority": "candidate",
        "answer_text": text,
        "answer": {"answer": text, "model": "synthetic-model"},
        "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
        "usage_status": "REPORTED",
        "model": {
            "requested_model": "synthetic-model",
            "reported_model": "synthetic-model",
            "observed_model": "synthetic-model",
            "endpoint": "http://127.0.0.1:1234/v1",
            "protocol": "openai",
            "engine": "synthetic",
            "engine_version": "0",
            "prompt_version": "synthetic",
            "answer_source": "content",
            "finish_reason": "stop",
            "truncated": False,
        },
        "judged": probe.judge(item, text),
    }


def synthetic_receipt():
    receipt = probe.receipt_template(
        run_id="synthetic-run",
        candidate=Path("candidate"),
        work=Path("work"),
        endpoint="http://127.0.0.1:1234/v1",
        model="synthetic-model",
    )
    receipt["results"] = [synthetic_result(item) for item in probe.ENTRIES]
    receipt["summary"] = probe.summarize(receipt["results"])
    receipt["evidence_level"] = "REAL_LOCAL_CORE_WORKER_MODEL"
    receipt["ok"] = True
    return receipt


class QualitySuiteProtocolTests(unittest.TestCase):
    def test_entries_are_unique_and_cover_three_classes(self):
        ids = [item["entry_id"] for item in probe.ENTRIES]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(6 <= len(probe.ENTRIES) <= 10)
        self.assertEqual({item["class"] for item in probe.ENTRIES}, set(probe.CLASSES))
        for item in probe.ENTRIES:
            self.assertTrue(item["context"].strip())
            self.assertTrue(item["question"].strip())
            self.assertIn(item["expected"], {"answer", "refuse", "refuse_or_flag_conflict"})

    def test_protocol_is_preregistered_and_digest_is_stable(self):
        first = probe.protocol()
        second = probe.protocol()
        self.assertEqual(first["sha256"], second["sha256"])
        self.assertTrue(first["held_out"])
        self.assertEqual(first["human_acceptance"], probe.HUMAN_ACCEPTANCE)
        self.assertEqual(first["entry_count"], len(probe.ENTRIES))
        self.assertEqual(first["scoring_rules"], probe.SCORING_RULES)


class QualitySuiteScoringTests(unittest.TestCase):
    def test_compliant_answers_pass_every_applicable_criterion(self):
        for item in probe.ENTRIES:
            with self.subTest(entry=item["entry_id"]):
                judged = probe.judge(item, COMPLIANT_ANSWERS[item["entry_id"]])
                self.assertTrue(judged["entry_pass"], judged)
                self.assertEqual(judged["criteria_passed"], judged["criteria_total"])

    def test_answerable_entry_rejects_refusal_and_wrong_fact(self):
        refused = probe.judge(entry("Q01"), "无法确定，材料里没有说。")
        self.assertFalse(refused["entry_pass"])
        self.assertEqual(refused["criteria"][0]["status"], "failed")

        wrong = probe.judge(entry("Q02"), "并发上限是 99。")
        self.assertFalse(wrong["entry_pass"])
        self.assertEqual(wrong["criteria"][1]["status"], "failed")
        self.assertEqual(wrong["criteria"][2]["status"], "failed")
        self.assertIn("99", wrong["criteria"][2]["detail"]["tokens"])

    def test_insufficient_context_requires_refusal_and_rejects_invention(self):
        refusal = probe.judge(entry("Q05"), "材料中没有提供加密算法，无法回答。")
        self.assertTrue(refusal["entry_pass"])
        invented = probe.judge(entry("Q05"), "系统使用 AES-256 加密。")
        self.assertFalse(invented["entry_pass"])
        self.assertEqual(invented["criteria"][0]["status"], "failed")
        self.assertEqual(invented["criteria"][2]["status"], "failed")

    def test_conflict_entry_accepts_refusal_or_explicit_conflict_flag(self):
        refused = probe.judge(entry("Q07"), "两份记录不一致，无法确定唯一校验值。")
        flagged = probe.judge(entry("Q08"), "两份材料互相矛盾（v2.4 与 v2.6）。")
        answered = probe.judge(entry("Q07"), "校验值是 37。")
        self.assertTrue(refused["entry_pass"])
        self.assertTrue(flagged["entry_pass"])
        self.assertFalse(answered["entry_pass"])

    def test_citation_is_required_for_answerable_entries(self):
        no_citation = probe.judge(entry("Q02"), "并发上限为 12，重试次数为 3，超时时间为 45 秒。")
        self.assertFalse(no_citation["entry_pass"])
        citation = next(
            item for item in no_citation["criteria"]
            if item["criterion"] == "timestamp_source_citation"
        )
        self.assertEqual(citation["status"], "failed")

    def test_unsupported_numeric_claim_blocks_pass(self):
        fabricated = probe.judge(
            entry("Q01"),
            "根据上下文，项目代号为 AURORA-7，状态为 FROZEN，冻结日期为 2026-03-14，"
            "预算为 500 万元。",
        )
        self.assertFalse(fabricated["entry_pass"])
        self.assertIn("500", fabricated["criteria"][2]["detail"]["tokens"])

    def test_refusal_detection_is_not_triggered_by_a_complete_answer(self):
        self.assertFalse(probe.detect_refusal(COMPLIANT_ANSWERS["Q01"]))
        self.assertTrue(probe.detect_refusal("信息不足，无法回答。"))
        self.assertFalse(probe.detect_conflict(COMPLIANT_ANSWERS["Q01"]))
        self.assertTrue(probe.detect_conflict("两份材料相互矛盾。"))


class QualitySuiteReceiptTests(unittest.TestCase):
    def test_complete_synthetic_receipt_validates(self):
        receipt = synthetic_receipt()
        self.assertTrue(probe.validate_receipt(receipt))
        self.assertTrue(receipt["summary"]["quality_pass"])
        self.assertEqual(receipt["summary"]["pass_rate"], 1.0)
        self.assertEqual(receipt["human_acceptance"], "NOT_EXECUTED")

    def test_receipt_refuses_fabricated_or_non_executed_answers(self):
        fabricated = synthetic_receipt()
        fabricated["results"][0]["status"] = "NOT_EXECUTED"
        with self.assertRaises(ValueError):
            probe.validate_receipt(fabricated)

        claimed_acceptance = synthetic_receipt()
        claimed_acceptance["human_acceptance"] = "PASSED"
        with self.assertRaises(ValueError):
            probe.validate_receipt(claimed_acceptance)

        missing_field = synthetic_receipt()
        del missing_field["results"][0]["usage"]
        with self.assertRaises(ValueError):
            probe.validate_receipt(missing_field)

        wrong_protocol = synthetic_receipt()
        wrong_protocol["suite"]["protocol_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            probe.validate_receipt(wrong_protocol)

    def test_missing_endpoint_is_named_not_executed(self):
        def failing_fetch(url, timeout):
            raise OSError("connection refused")

        inventory = probe.read_inventory("http://127.0.0.1:9/v1", fetch=failing_fetch)
        self.assertFalse(inventory["ok"])
        gate = probe.model_gate(inventory, "qwen3.5-4b")
        self.assertFalse(gate["executable"])
        self.assertEqual(gate["evidence_level"], "NOT_EXECUTED_MODEL")
        self.assertEqual(gate["reason"], "MODEL_ENDPOINT_UNAVAILABLE")
        results = probe.not_executed_results(gate["reason"])
        self.assertEqual(len(results), len(probe.ENTRIES))
        for row in results:
            self.assertEqual(row["status"], "NOT_EXECUTED")
            self.assertIsNone(row["answer_text"])
            self.assertIsNone(row["answer"])
            self.assertIsNone(row["judged"])

    def test_unlisted_model_is_named_not_executed(self):
        inventory = {"ok": True, "models": ["another-model"], "endpoint": "local"}
        gate = probe.model_gate(inventory, "qwen3.5-4b")
        self.assertFalse(gate["executable"])
        self.assertEqual(gate["reason"], "MODEL_NOT_LISTED")
        listed = probe.model_gate({"ok": True, "models": ["qwen3.5-4b"]}, "qwen3.5-4b")
        self.assertTrue(listed["executable"])


if __name__ == "__main__":
    unittest.main()
