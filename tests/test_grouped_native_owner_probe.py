"""SIMULATED probe guard checks. No host, browser, model or business database."""

import ast
import importlib.util
import unittest
from pathlib import Path

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

    def test_answer_does_not_become_correctness_claim(self):
        task = {
            "scope": "runtime.answer",
            "outcome": "unmeasured",
            "conditions": {
                "answer": {"model": "actual-configured-model", "answer": "correct answer"}
            },
        }
        self.assertEqual(self.probe.inference_status(task), "EXECUTED_CANDIDATE_NOT_EVALUATED")
        self.assertEqual(
            self.probe.inference_status(
                {**task, "conditions": {"answer": {"model": "SIMULATED-model"}}}
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
                ActualUI(), lambda _: {"capabilities": [capability]}, None, None, {}, {}, True
            )
        # No explicit opt-in means no route or grant is consulted.
        self.assertEqual(
            self.probe.run_ai_stage(None, None, None, None, {}, {}, False)["status"], "NOT_EXECUTED"
        )
