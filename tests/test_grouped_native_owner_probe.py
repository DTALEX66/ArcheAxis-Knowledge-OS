"""SIMULATED probe guard checks. No host, browser, model or business database."""

import ast
import copy
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_probe():
    path = ROOT / "scripts/probes/aaos01_grouped_owner_loop.py"
    spec = importlib.util.spec_from_file_location("grouped_native_probe_contract", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GroupedNativeProbeTests(unittest.TestCase):
    def setUp(self):
        self.probe = load_probe()

    def test_mutations_refused(self):
        operations = [
            "source_import",
            "document_create",
            "document_draft",
            "anchor_create",
            "knowledge_from_transform",
            "knowledge_review",
            "course_from_knowledge",
            "learning_reference",
            "assessment_create",
            "learning_review",
            "machine_answer",
            "machine_correction",
            "machine_retest",
            "job_execute",
            "job_enqueue",
            "workspace_backup",
            "ui_state_write",
            "ui_state_recover",
            "capability_set_enabled",
        ]
        for operation in operations:
            with self.subTest(operation=operation):
                calls = []
                read = self.probe.readonly_bridge(
                    lambda op, payload, calls=calls: calls.append((op, payload))
                )
                with self.assertRaisesRegex(ValueError, "forbids bridge mutation"):
                    read(operation, {"body": {}})
                self.assertEqual(calls, [])

    def test_read_identity_preserved(self):
        calls = []
        read = self.probe.readonly_bridge(
            lambda op, payload, calls=calls: (
                calls.append((op, payload)) or {"document_id": payload["document_id"]}
            )
        )
        self.assertEqual(read("document_get", {"document_id": "exact"}), {"document_id": "exact"})
        self.assertEqual(calls, [("document_get", {"document_id": "exact"})])

    def test_assessment_same_object(self):
        pin = {
            "item_key": "course:c:artifact:a",
            "assessment_id": "assessment",
            "knowledge_id": "knowledge",
            "knowledge_version": "knowledge",
            "source_id": "source",
            "anchor_id": "anchor",
        }
        self.probe.assert_assessment(dict(pin), pin)
        for field in pin:
            with self.subTest(field=field), self.assertRaisesRegex(AssertionError, field):
                self.probe.assert_assessment({**pin, field: "another"}, pin)

    def test_selectors_quote_and_hidden_boundary(self):
        self.assertTrue(self.probe.xpath_literal("one'quoted\"name").startswith("concat("))
        self.assertIn("ancestor-or-self::*[@hidden]", self.probe.button_selector("保存草稿"))
        self.assertTrue(
            self.probe.label_selector("学习项目键").endswith(
                "/input[not(ancestor-or-self::*[@hidden])]"
            )
        )
        with self.assertRaises(AssertionError):
            self.probe.one(
                [{"id": "same"}, {"id": "same"}], lambda row: row["id"] == "same", "duplicate"
            )

    def test_webdriver_only_interactions(self):
        commands, observations, actions = [], [], []
        ui = self.probe.GroupedUI(
            lambda script: observations.append(script) or "#page=13",
            lambda script, **_: observations.append(script),
            lambda using, selector: "actual-element",
            lambda element, action, body: commands.append((element, action, body)),
            actions,
        )
        ui.click("保存草稿")
        ui.type("知识候选正文", "authored fixture", "textarea")
        ui.keys(self.probe.label_selector("选择实际引文", "textarea"), "\ue009\ue008\ue010\ue000")
        folder = ROOT / ".project-local" / "artifacts" / "unittest-fixture-no-files-written"
        ui.upload_directory(folder)
        self.assertEqual(
            [row[1] for row in commands], ["click", "clear", "value", "click", "value", "value"]
        )
        self.assertTrue(all(row[0] == "actual-element" for row in commands))
        self.assertEqual(commands[-1][2]["text"], str(folder.resolve()))
        self.assertFalse(
            any(
                ".click(" in script or "dispatchEvent(" in script or ".value=" in script
                for script in observations
            )
        )
        self.assertEqual(
            {row["action"] for row in actions},
            {"trusted_click", "trusted_type", "trusted_keys", "trusted_directory_upload"},
        )

    def test_unconfirmed_route_never_grants_or_invokes(self):
        class ForbiddenUI:
            def __getattr__(self, _):
                raise AssertionError("No UI model/grant mutation allowed without confirmed route")

        for enabled, health in [(False, "healthy"), (True, "declared"), (True, "worker_missing")]:
            with self.subTest(enabled=enabled, health=health):
                calls = []

                def read(op, calls=calls, enabled=enabled, health=health):
                    calls.append(op)
                    return {
                        "capabilities": [
                            {"capability": "machine.answer", "enabled": enabled, "health": health}
                        ]
                    }

                stage = self.probe.run_ai_stage(ForbiddenUI(), read, None, None, {}, {}, True)
                self.assertEqual(
                    [stage["status"], stage["correction"], stage["retest"]], ["NOT_EXECUTED"] * 3
                )
                self.assertEqual(calls, ["capabilities_list"])

    def test_quote_selection_requires_native_range_and_react_display(self):
        text = "中文🌌\n尾行\n"
        proof = {
            "focused": True,
            "value": text,
            "start": 0,
            "end": len(text.encode("utf-16-le")) // 2,
            "displayed": "已选引文：" + text,
        }
        self.probe.assert_quote_selection(proof, text)
        for field, wrong in [
            ("focused", False),
            ("start", 1),
            ("end", proof["end"] - 1),
            ("value", text.rstrip()),
            ("displayed", "已选引文："),
        ]:
            with self.subTest(field=field), self.assertRaises(AssertionError):
                self.probe.assert_quote_selection({**proof, field: wrong}, text)
        commands, scripts, result = [], [], {}
        ui = self.probe.GroupedUI(
            lambda _: proof,
            lambda script: scripts.append(script),
            lambda *_: "quote",
            lambda element, action, body: commands.append((action, body)),
            [],
        )
        self.probe.select_full_quote(
            ui, lambda _: proof, lambda script: scripts.append(script), text, result
        )
        self.assertEqual(commands, [("click", {}), ("value", {"text": "\ue009a\ue000"})])
        self.assertEqual(result["quote_selection"]["status"], "PASS")
        self.assertFalse(
            any(
                token in script
                for script in scripts
                for token in ["setSelectionRange(", "dispatchEvent(", ".focus("]
            )
        )
        failed = {}

        def timeout(_):
            raise TimeoutError("native selection missing")

        with self.assertRaises(TimeoutError):
            self.probe.select_full_quote(ui, lambda _: {**proof, "end": 0}, timeout, text, failed)
        self.assertEqual(failed["quote_selection"]["status"], "FAIL")
        self.assertEqual(failed["quote_selection"]["selection"]["end"], 0)

    def test_answer_does_not_become_correctness_claim(self):
        task = {
            "scope": "runtime.answer",
            "outcome": "unmeasured",
            "conditions": json.dumps(
                {"answer": {"model": "actual-configured-model", "answer": "correct answer"}}
            ),
        }
        self.assertEqual(self.probe.inference_status(task), "EXECUTED_CANDIDATE_NOT_EVALUATED")
        self.assertEqual(
            self.probe.inference_status(
                {**task, "conditions": json.dumps({"answer": {"model": "SIMULATED-model"}})}
            ),
            "UNVERIFIED",
        )
        self.assertEqual(self.probe.inference_status({**task, "outcome": "failed"}), "NOT_EXECUTED")

    def test_harness_separate_branch_retains_finally(self):
        source = (ROOT / "scripts/probes/aaos01_tauri_webdriver_loop.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        main = next(
            node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main"
        )
        branch = next(
            node
            for node in ast.walk(main)
            if isinstance(node, ast.If)
            and ast.unparse(node.test) == "args.grouped_common_owner_loop"
            and any(isinstance(child, ast.Raise) for child in node.body)
        )
        code = ast.unparse(branch)
        self.assertIn("run_grouped_loop", code)
        for forbidden in [
            "navigate_compatibility_space",
            "synthetic_course_loop(",
            "native_command(",
        ]:
            self.assertNotIn(forbidden, code)
        self.assertIn("grouped_run_ai", code)
        self.assertIn("report=receipt['grouped_common_owner_loop']", code)
        self.assertIn("compatibility fixtures", source)
        enclosing = next(
            node for node in ast.walk(main) if isinstance(node, ast.Try) and branch in node.body
        )
        self.assertTrue(enclosing.finalbody)
        self.assertTrue(
            any(
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "close_session"
                for node in ast.walk(enclosing)
            )
        )

    def test_declared_route_with_explicit_optin_attempts_ui_without_claiming_model_health(self):
        class FirstUIActionError(Exception):
            pass

        class ActualUI:
            def page(self, page):
                if page != "13":
                    raise AssertionError("wrong page")
                raise FirstUIActionError

        capability = {
            "capability": "machine.answer",
            "enabled": True,
            "registered": True,
            "health": "declared",
            "provider": {"worker_present": True, "interpreter_present": True},
        }
        with self.assertRaises(FirstUIActionError):
            self.probe.run_ai_stage(
                ActualUI(),
                lambda op, *_: (
                    {"capabilities": [capability]}
                    if op == "capabilities_list"
                    else {"knowledge_id": "exact", "status": "accepted"}
                ),
                None,
                None,
                {"knowledge_id": "exact"},
                {},
                True,
            )
        # No explicit opt-in means no route or grant is consulted.
        self.assertEqual(
            self.probe.run_ai_stage(None, None, None, None, {}, {}, False)["status"], "NOT_EXECUTED"
        )

    def test_persisted_task_conditions_requires_exact_json_text(self):
        self.assertEqual(
            self.probe.task_conditions({"conditions": '{"answer_id":"exact"}'}),
            {"answer_id": "exact"},
        )
        for invalid in [{"answer_id": "exact"}, None, "[]", "null", "bad-json"]:
            with (
                self.subTest(invalid=invalid),
                self.assertRaises((AssertionError, json.JSONDecodeError)),
            ):
                self.probe.task_conditions({"conditions": invalid})

    def ai_fixture(self):
        grant = {
            "document_id": "original-grant",
            "version": 1,
            "content_sha256": "a" * 64,
            "purpose": "original",
        }
        original = {
            "schema": "archeaxis.machine-answer/v1",
            "answer_id": "answer",
            "knowledge_id": "original-knowledge",
            "question": "question",
            "answer": {
                "answer": "A correct actual-answer-shaped test value",
                "model": "configured-model",
            },
            "authority": "candidate",
            "request": {"context_grant": grant},
        }
        task = {
            "task_id": "answer",
            "scope": "runtime.answer",
            "outcome": "unmeasured",
            "knowledge_version": "original-knowledge@v1",
            "model_version": "configured-model",
            "retest_of": None,
            "conditions": json.dumps(original),
        }
        authored = {
            "actor": "ENGINEERING_AUTHORED_INTERVENTION_NOT_OWNER",
            "body": "Authored clarification",
            "note": "Not independent model-error evidence",
        }
        correction = {
            "answer_id": "answer",
            "failed_task_id": "evaluation_answer",
            "corrects_knowledge_id": "original-knowledge",
            "question": "question",
            "machine_answer": original["answer"]["answer"],
            "corrected_answer": authored["body"],
            "error_note": authored["note"],
            "reviewer": authored["actor"],
            "correction_candidate_id": "corrected-knowledge",
        }
        failed = {
            "task_id": "evaluation_answer",
            "scope": "runtime.evaluation.failed",
            "outcome": "failed",
            "conditions": json.dumps({**original, "correction": correction}),
        }
        candidate = {
            "knowledge_id": "corrected-knowledge",
            "body": authored["body"],
            "source_id": None,
            "anchor_id": None,
            "status": "candidate",
        }
        return grant, original, task, authored, failed, candidate

    def test_original_task_and_corrected_lineage_preserve_correct_answer(self):
        grant, original, task, authored, failed, candidate = self.ai_fixture()
        self.assertEqual(
            self.probe.assert_inference_task(task, "original-knowledge", "question", grant),
            original,
        )
        self.probe.assert_correction_lineage(original, failed, candidate, authored)
        self.assertIn("correct actual", original["answer"]["answer"])
        self.assertEqual(self.probe.inference_status(task), "EXECUTED_CANDIDATE_NOT_EVALUATED")
        for field in [
            "answer_id",
            "corrects_knowledge_id",
            "question",
            "machine_answer",
            "corrected_answer",
            "error_note",
            "reviewer",
            "correction_candidate_id",
        ]:
            changed = copy.deepcopy(failed)
            body = json.loads(changed["conditions"])
            body["correction"][field] = "another"
            changed["conditions"] = json.dumps(body)
            with self.subTest(field=field), self.assertRaises(AssertionError):
                self.probe.assert_correction_lineage(original, changed, candidate, authored)
        for field in ["source_id", "anchor_id"]:
            with self.subTest(field=field), self.assertRaises(AssertionError):
                self.probe.assert_correction_lineage(
                    original, failed, {**candidate, field: "invented-source"}, authored
                )

    def test_retest_requires_new_exact_grant_and_failed_ancestor(self):
        grant, original, task, _, _, _ = self.ai_fixture()
        new_grant = {**grant, "document_id": "independent-retest-grant", "purpose": "retest"}
        retest = {
            **original,
            "schema": "archeaxis.machine-retest/v1",
            "answer_id": "retest",
            "retest_task_id": "retest",
            "knowledge_id": "corrected-knowledge",
            "retest_of": "evaluation_answer",
            "request": {"context_grant": new_grant},
        }
        proof = {
            **task,
            "task_id": "retest",
            "scope": "runtime.retest",
            "knowledge_version": "corrected-knowledge@v1",
            "retest_of": "evaluation_answer",
            "conditions": json.dumps(retest),
        }
        self.probe.assert_inference_task(
            proof, "corrected-knowledge", "question", new_grant, "runtime.retest"
        )
        self.assertEqual(self.probe.inference_status(proof), "EXECUTED_CANDIDATE_NOT_EVALUATED")
        with self.assertRaises(AssertionError):
            self.probe.assert_inference_task(
                proof, "corrected-knowledge", "question", grant, "runtime.retest"
            )
        with self.assertRaises(AssertionError):
            self.probe.assert_inference_task(
                {**proof, "retest_of": "other-failure"},
                "corrected-knowledge",
                "question",
                new_grant,
                "runtime.retest",
            )

    def test_authored_intervention_requires_explicit_actual_model(self):
        with self.assertRaisesRegex(AssertionError, "actual-model"):
            self.probe.run_ai_stage(None, None, None, None, {}, {}, False, True)
        source = (ROOT / "scripts/probes/aaos01_tauri_webdriver_loop.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("args.grouped_authored_intervention and not args.grouped_run_ai", source)
        self.assertIn("authored_intervention=args.grouped_authored_intervention", source)

    def test_restored_old_grant_refusal_observed_only_through_ui_without_new_task(self):
        grant, original, task, _, _, _ = self.ai_fixture()
        document = {
            **grant,
            "title": "original",
            "editor_json": {"attrs": {"archeaxis_context_grant": {"purpose": "original"}}},
        }
        stage = {
            "original_grant": document,
            "original_answer": original,
            "status": "EXECUTED_CANDIDATE_NOT_EVALUATED",
            "knowledge_before": {"knowledge_id": "original-knowledge", "status": "accepted"},
        }
        actions, reads, waits = [], [], []

        normalized = {"operation": "answer", "request": {
            "knowledge_id": "original-knowledge", "question": "question", "max_tokens": 2048, "timeout_s": 120,
            "context_grant": self.probe.grant_snapshot(document), "asset_context_grant": None,
            "client_request_id": "machine_new_fixture", "retest_of": None,
        }}
        receipt = {"schema": "archeaxis.context-admission-refusal/v1", "reason_code": "RESTORED_GRANT_FENCED",
            "execution_state": "NOT_EXECUTED", "execution_scope": "CURRENT_INVOCATION", "prior_request_execution": "UNVERIFIED",
            "answer_published": False, "operation": "answer", "knowledge_id": "original-knowledge", "retest_of": None,
            "client_request_id": "machine_new_fixture", "grant": {k: document[k] for k in ("document_id", "version", "content_sha256")},
            "request_sha256": hashlib.sha256(json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()}

        class UI:
            def js(self, script):
                self_script = script
                assert "contextAdmissionRefusal" in self_script
                return copy.deepcopy(receipt)

            def page(self, page):
                actions.append(("page", page))

            def click(self, label):
                actions.append(("click", label))

            def type(self, label, text, tag):
                actions.append(("type", label, text, tag))

        def read(op, payload=None):
            reads.append((op, payload))
            if op == "machine_tasks_list":
                return {"items": [{"task_id": "answer"}], "next_cursor": None}
            if op == "machine_task_get":
                return copy.deepcopy(task)
            if op == "document_get":
                return copy.deepcopy(document)
            if op == "knowledge_get":
                return copy.deepcopy(stage["knowledge_before"])
            if op == "capabilities_list":
                return {
                    "capabilities": [
                        {"capability": "machine.answer", "enabled": True, "registered": True}
                    ]
                }
            raise AssertionError("Unexpected write or read " + op)

        observed = self.probe.restored_grant_refusal(
            UI(), read, lambda script, **_: waits.append(script), stage
        )
        self.assertEqual(observed["status"], "PASS")
        self.assertTrue(observed["tasks_unchanged"])
        self.assertEqual(observed["exact_core_reason"], "RESTORED_GRANT_FENCED")
        self.assertEqual(observed["execution_scope"], "CURRENT_INVOCATION")
        self.assertEqual(observed["prior_request_execution"], "UNVERIFIED")
        for field in ("reason_code", "execution_scope", "prior_request_execution", "knowledge_id", "request_sha256", "grant"):
            bad = {**receipt, field: "mismatch"}
            with self.assertRaises(AssertionError):
                self.probe.restored_admission_receipt(bad, document, "original-knowledge", "question")
        with self.assertRaises(AssertionError):
            self.probe.restored_admission_receipt(None, document, "original-knowledge", "question")
        self.assertIn(("type", "实际问题", "question", "textarea"), actions)
        self.assertIn(("click", "执行本地机器回答"), actions)
        self.assertTrue(any("Core 明确拒绝此回答请求" in script for script in waits))
        self.assertTrue(all(op in self.probe.READ_OPERATIONS for op, _ in reads))
        self.assertEqual(
            self.probe.restored_grant_refusal(None, None, None, {})["status"], "NOT_EXECUTED"
        )
        task_reads = [0]

        def changed_task_read(op, payload=None):
            value = read(op, payload)
            if op == "machine_task_get":
                task_reads[0] += 1
                if task_reads[0] > 1:
                    return {**value, "model_version": "changed-after-request"}
            return value

        with self.assertRaisesRegex(AssertionError, "created/changed"):
            self.probe.restored_grant_refusal(UI(), changed_task_read, lambda *_, **__: None, stage)

        with self.assertRaisesRegex(AssertionError, "partial page"):
            self.probe.machine_tasks(lambda *_: {"items": [], "next_cursor": "next-page"})

    def test_simulated_full_helper_actual_shaped_answer_adoption_new_grant_retest(self):
        self.exercise_simulated_ai(False)
        self.exercise_simulated_ai(True)

    def exercise_simulated_ai(self, intervention):
        docs, tasks, actions, reads, fields = {}, {}, [], [], {}
        knowledge = {
            "knowledge_id": "original-knowledge",
            "body": "Preserved original bytes differ from document revisions",
            "status": "accepted",
            "version": "original-knowledge",
        }
        candidate = {}
        bound = [knowledge["knowledge_id"]]
        probe = self.probe

        class UI:
            def page(self, page):
                actions.append(("page", page))

            def click_selector(self, selector):
                actions.append(("checkbox", selector))
                fields["operation"] = "retest" if "允许本地复测" in selector else "answer"

            def type(self, label, text, tag="input", scope=""):
                actions.append(("type", label, tag, scope))
                fields[label] = text

            def click(self, label, scope=""):
                actions.append(("click", label, scope))
                if label == "明确授权并保存":
                    ident = "grant-" + str(len(docs) + 1)
                    grant = {
                        "purpose": fields["用途"],
                        "consumer": "local-machine",
                        "operations": [fields["operation"]],
                        "state": "granted",
                        "knowledge_id": bound[0],
                    }
                    docs[ident] = {
                        "document_id": ident,
                        "title": fields["用途"],
                        "version": 1,
                        "content_sha256": "a" * 64,
                        "editor_json": {"attrs": {"archeaxis_context_grant": grant}},
                    }
                elif label == "执行本地机器回答":
                    body = {
                        "schema": "archeaxis.machine-answer/v1",
                        "answer_id": "actual-shaped-answer",
                        "question": fields["实际问题"],
                        "knowledge_id": knowledge["knowledge_id"],
                        "authority": "candidate",
                        "answer": {
                            "model": "configured-model",
                            "answer": "A correct explanation; no actual error claimed",
                        },
                        "request": {
                            "context_grant": probe.grant_snapshot(docs["grant-1"]),
                            "context_sha256": hashlib.sha256(
                                knowledge["body"].encode()
                            ).hexdigest(),
                        },
                    }
                    tasks[body["answer_id"]] = {
                        "task_id": body["answer_id"],
                        "scope": "runtime.answer",
                        "outcome": "unmeasured",
                        "knowledge_version": knowledge["knowledge_id"] + "@v1",
                        "model_version": "configured-model",
                        "retest_of": None,
                        "conditions": json.dumps(body),
                    }
                elif label == "记录使用者纠正候选":
                    original = json.loads(tasks["actual-shaped-answer"]["conditions"])
                    candidate.update(
                        knowledge_id="corrected-knowledge",
                        body=fields["正确答案"],
                        status="candidate",
                        version="corrected-knowledge",
                        source_id=None,
                        anchor_id=None,
                    )
                    correction = {
                        "answer_id": original["answer_id"],
                        "failed_task_id": "evaluation_" + original["answer_id"],
                        "corrects_knowledge_id": original["knowledge_id"],
                        "question": original["question"],
                        "machine_answer": original["answer"]["answer"],
                        "corrected_answer": fields["正确答案"],
                        "error_note": fields["具体错误依据"],
                        "reviewer": fields["纠正提交者"],
                        "correction_candidate_id": candidate["knowledge_id"],
                    }
                    tasks[correction["failed_task_id"]] = {
                        "task_id": correction["failed_task_id"],
                        "scope": "runtime.evaluation.failed",
                        "outcome": "failed",
                        "conditions": json.dumps({**original, "correction": correction}),
                    }
                elif label == "接受纠正知识":
                    candidate["status"] = "accepted"
                elif label == "为此纠正知识建立独立复测授权":
                    bound[0] = candidate["knowledge_id"]
                elif label == "以已接受纠正知识运行独立复测":
                    original = json.loads(tasks["actual-shaped-answer"]["conditions"])
                    failed_id = "evaluation_" + original["answer_id"]
                    body = {
                        **original,
                        "schema": "archeaxis.machine-retest/v1",
                        "answer_id": "actual-shaped-retest",
                        "retest_task_id": "actual-shaped-retest",
                        "knowledge_id": candidate["knowledge_id"],
                        "retest_of": failed_id,
                        "request": {"context_grant": probe.grant_snapshot(docs["grant-2"])},
                        "prior": {"conditions": json.loads(tasks[failed_id]["conditions"])},
                    }
                    tasks[body["answer_id"]] = {
                        "task_id": body["answer_id"],
                        "scope": "runtime.retest",
                        "outcome": "unmeasured",
                        "knowledge_version": candidate["knowledge_id"] + "@v1",
                        "model_version": "configured-model",
                        "retest_of": failed_id,
                        "conditions": json.dumps(body),
                    }

        def read(op, payload=None):
            self.assertIn(op, probe.READ_OPERATIONS)
            reads.append(op)
            payload = payload or {}
            if op == "capabilities_list":
                return {
                    "capabilities": [
                        {
                            "capability": "machine.answer",
                            "enabled": True,
                            "registered": True,
                            "health": "declared",
                            "provider": {
                                "worker_present": True,
                                "interpreter_present": True,
                            },
                        }
                    ]
                }
            if op == "knowledge_get":
                return copy.deepcopy(
                    knowledge if payload["id"] == knowledge["knowledge_id"] else candidate
                )
            if op == "machine_contexts_list":
                return {
                    "items": [
                        {k: d[k] for k in ["document_id", "title", "version", "content_sha256"]}
                        for d in docs.values()
                    ],
                    "next_cursor": None,
                }
            if op == "document_get":
                return copy.deepcopy(docs[payload["document_id"]])
            if op == "machine_tasks_list":
                return {"items": [{"task_id": key} for key in tasks], "next_cursor": None}
            if op == "machine_task_get":
                return copy.deepcopy(tasks[payload["task_id"]])
            raise AssertionError("Unexpected op " + op)

        result = {}
        stage = probe.run_ai_stage(
            UI(),
            read,
            lambda _: "",
            lambda *_, **__: None,
            {"knowledge_id": knowledge["knowledge_id"]},
            result,
            True,
            intervention,
        )
        self.assertEqual(stage["status"], "EXECUTED_CANDIDATE_NOT_EVALUATED")
        self.assertIn(("type", "实际问题", "textarea", ""), actions)
        self.assertEqual(
            json.loads(tasks["actual-shaped-answer"]["conditions"])["answer"]["answer"],
            "A correct explanation; no actual error claimed",
        )
        if intervention:
            self.assertEqual(
                stage["correction"], "EXECUTED_AUTHORED_INTERVENTION_NOT_INDEPENDENT_ERROR"
            )
            self.assertEqual(stage["retest"], "EXECUTED_CANDIDATE_NOT_EVALUATED")
            self.assertFalse(stage["authored_intervention"]["independent_error_adjudication"])
            self.assertIn("not independent model-failure evidence", stage["semantic_limitation"])
            self.assertNotEqual(
                stage["original_grant"]["document_id"], stage["retest_grant"]["document_id"]
            )
            self.assertEqual(len(result["actual_tasks"]), 3)
        else:
            self.assertEqual(stage["correction"], "NOT_EXECUTED")
            self.assertEqual(stage["retest"], "NOT_EXECUTED")
            self.assertEqual(len(tasks), 1)
            self.assertFalse(any(action[1] == "记录使用者纠正候选" for action in actions))

    def capability_fixture(self):
        frozen = {
            "job_id": "read_exact",
            "request_id": "read_run_exact",
            "body": {"deadline_ms": 60000, "split": False, "words": False},
        }
        refused = {
            "job_id": "read_exact",
            "input_ref": "source-exact",
            "kind": "text",
            "state": "queued",
            "attempt": None,
            "request_id": None,
            "attempts": [],
            "attempts_capped": False,
        }
        succeeded = {
            **refused,
            "state": "succeeded",
            "attempt": 1,
            "request_id": "read_run_exact",
            "attempts": [
                {
                    "attempt": 1,
                    "request_id": "read_run_exact",
                    "state": "succeeded",
                    "budget": {**frozen["body"], "capability": "text.extract"},
                    "steps": {
                        "durable_claim": "RECORDED",
                        "worker_response_commit": "RECORDED",
                        "terminal_write": "RECORDED",
                    },
                    "checkpoint": {"status": "CORE_COMMITTED"},
                }
            ],
        }
        return frozen, refused, succeeded

    def test_refusal_empty_attempts_and_retry_full_identity_negative_guards(self):
        frozen, refused, succeeded = self.capability_fixture()
        self.probe.assert_unadmitted(refused, frozen["job_id"], "source-exact")
        self.probe.assert_single_attempt(succeeded, frozen, "source-exact")
        for field, changed in [
            ("attempt", 1),
            ("request_id", "consumed"),
            ("state", "running"),
            ("attempts", [succeeded["attempts"][0]]),
            ("input_ref", "another-source"),
            ("attempts_capped", True),
        ]:
            with self.subTest(refusal=field), self.assertRaises(AssertionError):
                self.probe.assert_unadmitted(
                    {**refused, field: changed}, frozen["job_id"], "source-exact"
                )
        for field, changed in [
            ("request_id", "another-request"),
            ("attempt", 2),
            ("state", "failed"),
            ("input_ref", "another-source"),
            ("attempts_capped", True),
            ("attempts", succeeded["attempts"] * 2),
        ]:
            with self.subTest(retry=field), self.assertRaises(AssertionError):
                self.probe.assert_single_attempt(
                    {**succeeded, field: changed}, frozen, "source-exact"
                )
        changed = copy.deepcopy(succeeded)
        changed["attempts"][0]["budget"]["split"] = True
        with self.assertRaises(AssertionError):
            self.probe.assert_single_attempt(changed, frozen, "source-exact")
        text = "Authored source text\n"
        output = {
            "content": text,
            "metadata": {
                "kind": "text",
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
                "byte_length": len(text.encode()),
            },
        }
        self.probe.assert_text_output(output, text)
        with self.assertRaises(AssertionError):
            self.probe.assert_text_output({**output, "content": "other"}, text)
        with self.assertRaises(AssertionError):
            self.probe.assert_text_output(
                {**output, "metadata": {**output["metadata"], "sha256": "bad"}}, text
            )

    def test_simulated_native_capability_controls_recover_exact_frozen_request(self):
        result, actions, restarts = self.exercise_capability_probe()
        self.assertEqual(
            [
                result[key]
                for key in [
                    "status",
                    "execution_refusal",
                    "enable_without_execution",
                    "same_request_retry",
                    "host_restart_result",
                ]
            ],
            ["PASS"] * 5,
        )
        self.assertEqual(restarts, [False, True])
        enable_index = actions.index(
            ("click", "启用 text.extract", "//section[@aria-label='冻结请求的能力恢复']")
        )
        retry_index = actions.index(
            ("click", "同请求重试转换", "//section[@aria-label='真实转换产物']")
        )
        self.assertGreater(retry_index, enable_index)
        self.assertFalse(any(action[0] == "page" for action in actions[enable_index:retry_index]))

    def test_simulated_enable_must_not_autoexecute_and_retry_cannot_change_identity(self):
        with self.assertRaisesRegex(AssertionError, "automatically"):
            self.exercise_capability_probe(autoexecute=True)
        with self.assertRaises(AssertionError):
            self.exercise_capability_probe(wrong_retry=True)

    def exercise_capability_probe(self, autoexecute=False, wrong_retry=False):
        frozen, refused, succeeded = self.capability_fixture()
        # Match the native UUID-shaped request text; pure tests never execute a host or model.
        frozen["request_id"] = "read_run_1234-abcd"
        succeeded["request_id"] = frozen["request_id"]
        succeeded["attempts"][0]["request_id"] = frozen["request_id"]
        state = {
            "enabled": True,
            "new_job": False,
            "status": copy.deepcopy(refused),
            "page": "#page=06",
            "finished": False,
        }
        actions, restarts = [], []
        text = "Authored source text\n"
        output = {
            "content": text,
            "metadata": {
                "kind": "text",
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
                "byte_length": len(text.encode()),
            },
        }
        document = {
            "title": "source.txt",
            "document_id": "document-exact",
            "source_revision": "a" * 64,
        }
        transform = {
            "source_id": "source-exact",
            "job_id": frozen["job_id"],
            "raw_sha256": document["source_revision"],
            "content": text,
        }
        quality = {
            "job_id": frozen["job_id"],
            "state": "succeeded",
            "engine": "actual-shaped-test-engine",
        }

        class UI:
            def page(self, page):
                state["page"] = "#page=" + page
                actions.append(("page", page))

            def click_selector(self, selector):
                actions.append(("selector", selector))
                if "禁用 text.extract" in selector:
                    state["enabled"] = False
                elif "打开文档" in selector:
                    state["page"] = "#page=03"
                else:
                    raise AssertionError("unexpected selector")

            def click(self, label, scope=""):
                actions.append(("click", label, scope))
                if label == "执行真实内容转换":
                    state["new_job"] = True
                elif label == "启用 text.extract":
                    state["enabled"] = True
                    if autoexecute:
                        state["status"] = copy.deepcopy(succeeded)
                elif label == "同请求重试转换":
                    state["status"] = copy.deepcopy(succeeded)
                    if wrong_retry:
                        state["status"]["request_id"] = "another-request"
                    state["finished"] = True

        def read(op, payload=None):
            self.assertIn(op, self.probe.READ_OPERATIONS)
            if op == "capabilities_list":
                return {
                    "capabilities": [{"capability": "text.extract", "enabled": state["enabled"]}]
                }
            if op == "source_jobs":
                return {
                    "source_id": "source-exact",
                    "jobs_capped": False,
                    "jobs": [{"job_id": "folder-original"}]
                    + (
                        [{"job_id": frozen["job_id"], "state": state["status"]["state"]}]
                        if state["new_job"]
                        else []
                    ),
                }
            if op == "job_execution_status":
                return copy.deepcopy(state["status"])
            if op == "job_output":
                return copy.deepcopy(output)
            if op == "job_quality":
                return copy.deepcopy(quality)
            if op == "source_job_transform":
                return copy.deepcopy(transform)
            if op == "document_get":
                return copy.deepcopy(document)
            raise AssertionError("unexpected operation")

        def js(script):
            if "const root=" in script:
                return {
                    "page": state["page"],
                    "frozen": "执行请求已冻结："
                    + frozen["request_id"]
                    + "；单次预算 60s。未知结果不会产生新作业。",
                    "latest": "最新任务 " + frozen["job_id"],
                    "recovery": "Core 已证明原请求未受理",
                }
            return text

        def restart():
            restarts.append(state["enabled"])

        with patch.object(self.probe.time, "sleep", lambda _: None):
            result = self.probe.capability_refusal_recovery(
                UI(),
                read,
                js,
                lambda *_, **__: None,
                restart,
                {"source_id": "source-exact"},
                document,
                text,
            )
        return result, actions, restarts

    def test_full_dom_range_including_lf_not_rendered_selection_serialization(self):
        text = "Line one.\nLine two.\n"
        proof = {
            "region_count": 1,
            "focused": True,
            "node_type": 3,
            "child_nodes": 1,
            "range_count": 1,
            "start_same": True,
            "end_same": True,
            "start_offset": 0,
            "end_offset": len(text),
            "node_length": len(text),
            "source_text": text,
            "node_text": text,
            "range_text": text,
            "cloned_text": text,
            "rendered_selection": text[:-1],
        }
        self.probe.assert_full_text_selection(proof, text)
        # A missing final LF in the DOM range is still a real failure, not trimmed away.
        for field, value in [
            ("focused", False),
            ("region_count", 2),
            ("range_count", 2),
            ("start_same", False),
            ("end_same", False),
            ("start_offset", 1),
            ("end_offset", len(text) - 1),
            ("node_length", len(text) - 1),
            ("source_text", text[:-1]),
            ("node_text", text[:-1]),
            ("range_text", text[:-1]),
            ("cloned_text", text[:-1]),
        ]:
            with self.subTest(field=field), self.assertRaises(AssertionError):
                self.probe.assert_full_text_selection({**proof, field: value}, text)
        script = self.probe.full_text_selection_wait_script(text)
        self.assertIn("document.activeElement===region", script)
        self.assertIn("range?.startContainer===node", script)
        self.assertIn("range?.endContainer===node", script)
        self.assertIn("proof.end_offset===proof.node_length", script)
        self.assertIn("proof.range_text===", script)
        self.assertIn("proof.cloned_text===", script)
        self.assertNotIn(".trim(", script)
        self.assertNotIn("proof.rendered_selection===", script)
        self.assertNotIn(".focus(", script)
        self.assertNotIn("addRange(", script)
        self.assertNotIn("removeAllRanges(", script)
        astral = "Astral \U0001f30c\n"
        self.probe.assert_full_text_selection(
            {
                **proof,
                "source_text": astral,
                "node_text": astral,
                "range_text": astral,
                "cloned_text": astral,
                "node_length": len(astral.encode("utf-16-le")) // 2,
                "end_offset": len(astral.encode("utf-16-le")) // 2,
            },
            astral,
        )
