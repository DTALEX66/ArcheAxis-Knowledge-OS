"""Continue one saved public-research sample into learning and local machine use.

The public receipt and backup are explicit inputs; they are restored to an
independent synthetic workspace. Human acceptance and learning responses are
fixtures. A local model is called only with the separate opt-in flag.
"""

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = ("AAOS_TEST_CORE_EXE", "AAOS_TEST_PUBLIC_RESEARCH_RECEIPT", "AAOS_TEST_PUBLIC_RESEARCH_RECEIPT_SHA256")


@pytest.mark.skipif(not all(os.environ.get(key) for key in REQUIRED), reason="explicit Core and public receipt required")
def test_public_knowledge_reaches_learning_and_machine_after_independent_restore(tmp_path):
    from scripts.ci.real_core_grading_journey import Core
    from scripts.probes import aaos01_office_runtime_loop as office
    from scripts.probes import aaos_public_research_runtime_loop as public_probe
    from scripts.probes.aaos_ai_reference_observation_smoke import BASE, MODEL, WORKER, request

    real_model = os.environ.get("AAOS_TEST_PUBLIC_BRIDGE_REAL_MODEL") == "1"
    input_path = Path(os.environ["AAOS_TEST_PUBLIC_RESEARCH_RECEIPT"]).resolve(strict=True)
    input_bytes = input_path.read_bytes()
    input_sha = hashlib.sha256(input_bytes).hexdigest()
    assert input_sha == os.environ["AAOS_TEST_PUBLIC_RESEARCH_RECEIPT_SHA256"]
    public = json.loads(input_bytes)
    assert public["ok"] is True and public["evidence_level"] == "REAL_CORE_PUBLIC_NETWORK"
    assert public["source_consistent"] is True and public["candidate_consistent"] is True
    assert public["knowledge_admission"]["reviewer_kind"] == "synthetic_fixture"
    assert {(c["family"], c["provider"], c["status"]) for c in public["channel_statuses"]} >= {
        ("community", "stackexchange", "complete"), ("encyclopedia", "wikipedia", "complete"),
        ("research", "openalex", "complete")}
    core_exe = Path(os.environ["AAOS_TEST_CORE_EXE"]).resolve(strict=True)
    core_sha = hashlib.sha256(core_exe.read_bytes()).hexdigest()
    recorded_core = next(row["sha256"] for row in public["candidate_files"]
                         if str(row["path"]).lower().endswith("archeaxis-api.exe"))
    assert core_sha == recorded_core
    worker_sha = hashlib.sha256(WORKER.read_bytes()).hexdigest()
    recorded_worker = next(row["sha256"] for row in public["candidate_files"]
                           if str(row["path"]).lower().endswith("worker_machine_answer.py"))
    assert worker_sha == recorded_worker
    steps = {row["label"]: row for row in public["steps"]}
    search, knowledge = steps["public_search"]["body"], steps["admission_read"]["body"]
    document = steps["research_read"]["body"]
    original = steps["research_selected_original"]["body"]
    assert knowledge["status"] == "accepted" and knowledge["knowledge_id"] == public["knowledge_admission"]["knowledge_id"]
    assert knowledge["source_id"] == original["source_id"] and knowledge["anchor_id"]
    backup = public["backup"]
    assert backup["verified"] is True and Path(backup["filename"]).name == backup["filename"]
    source_backup = Path(public["workspace"]) / "backups" / backup["filename"]
    object_dir = Path(str(source_backup) + ".objects")
    launcher = office.load("public_bridge_launcher", ROOT / "scripts/release/backend_launcher.py")

    def verify_input():
        assert hashlib.sha256(input_path.read_bytes()).hexdigest() == input_sha
        public_probe.verify_backup_objects(source_backup, object_dir, backup["source_sha_list"],
                                           backup["sha256"], launcher.filesystem_path)
        assert hashlib.sha256(core_exe.read_bytes()).hexdigest() == core_sha
        assert hashlib.sha256(WORKER.read_bytes()).hexdigest() == worker_sha

    verify_input()
    source_workspace = tmp_path / "restored-public"
    source_workspace.mkdir()
    restored = subprocess.run([str(core_exe), "--maintenance-restore", str(source_workspace / "workspace.sqlite"),
        str(source_backup)], capture_output=True, text=True, timeout=120, check=False)
    restore_receipt = json.loads(restored.stdout) if restored.stdout else {}
    assert restored.returncode == 0 and restore_receipt.get("ok") is True
    assert restore_receipt.get("authorization_requires_new_grants") is True

    worker = WORKER
    if real_model:
        assert not any(os.environ.get(key, "").strip() for key in
                       ("ARCHEAXIS_MACHINE_ENDPOINT", "ARCHEAXIS_MACHINE_MODEL", "ARCHEAXIS_MACHINE_PROTOCOL"))
        spec = importlib.util.spec_from_file_location("public_bridge_machine_worker", WORKER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        lanes = module._declared_lanes()
        assert len(lanes) == 1 and lanes[0]["base"] == BASE and lanes[0]["model"] == MODEL
        assert lanes[0]["protocol"] == "openai"
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(BASE + "/models", timeout=5) as response:
            inventory = json.load(response)
        assert MODEL in {row.get("id") for row in inventory.get("data", []) if isinstance(row, dict)}
    else:
        worker = tmp_path / "synthetic_machine_worker.py"
        worker.write_text("import json\nprint(json.dumps({'answer':'Synthetic local worker candidate',"
                          "'model':'synthetic-worker','loss_receipt':{'params':{'authority':'candidate'}}}))\n",
                          encoding="utf-8")

    class BridgeCore(Core):
        with_machine = True

        def _launch_document(self):
            launch = super()._launch_document()
            if self.with_machine:
                launch["text_worker"]["routes"].append({"capability": "machine.answer", "script": str(worker)})
            return launch

    core = BridgeCore(core_exe, source_workspace, Path(sys.executable))
    receipt = {"schema": "aaos.public-learning-machine-bridge/v1", "input_receipt_sha256": input_sha,
        "core_sha256": core_sha, "source": "REAL_PUBLIC_RESEARCH", "human_review": "SYNTHETIC_FIXTURE",
        "learning_review": "SYNTHETIC_SELF_REPORT_INCORRECT", "model_quality": "NOT_MEASURED",
        "independent_mastery": "NOT_ESTABLISHED", "model_mode": "real_local" if real_model else "synthetic_worker",
        "status": "NOT_COMPLETED"}

    def call(method, path, body=None, expected=200, timeout=20):
        status, value = request(core, method, path, body, timeout=timeout)
        assert status == expected, (method, path, status, value.get("code") or value.get("reason_code"))
        return value

    def snap(value):
        return {key: value[key] for key in ("document_id", "version", "content_sha256")}

    try:
        core.start()
        state = call("GET", "/api/v1/workspace/ui-state")
        old_target = {key: search[key] for key in ("workspace_id", "restore_epoch", "request_id")}
        assert state["workspace_id"] == old_target["workspace_id"] and state["restore_epoch"] != old_target["restore_epoch"]
        call("POST", "/api/v1/research/public/read", old_target, expected=409)
        new_target = {**old_target, "restore_epoch": state["restore_epoch"]}
        assert call("POST", "/api/v1/research/public/read", new_target) == search
        assert call("GET", steps["research_read"]["path"]) == document
        assert call("GET", steps["research_selected_original"]["path"]) == original
        assert call("GET", steps["research_resolve"]["path"]) == steps["research_resolve"]["body"]
        assert call("GET", steps["admission_read"]["path"]) == knowledge

        item = "public-source-synthetic-learning"
        base = f"/api/v1/learning/items/{item}"
        call("POST", base + "/references", {"knowledge_id": knowledge["knowledge_id"]}, expected=201)
        assessment = call("POST", base + "/assessment", {"knowledge_id": knowledge["knowledge_id"]}, expected=201)
        assert assessment["knowledge_id"] == knowledge["knowledge_id"]
        assert assessment["source_id"] == knowledge["source_id"] and assessment["anchor_id"] == knowledge["anchor_id"]
        review_body = {"item_key": item, "client_event_id": "public-synthetic-review", "correct": False,
            "rating": 1, "now": "2026-11-10T00:00:00+00:00", "answer": "Synthetic fixture: no independent answer.",
            "assessment_id": assessment["assessment_id"], "knowledge_version": assessment["knowledge_version"]}
        review = call("POST", "/api/v1/learning/reviews", review_body, expected=201)
        assert review["schedule_authority"] == "fsrs" and review["mastery_projection"]["closed"] is False
        assert call("POST", "/api/v1/learning/reviews", review_body)["event_id"] == review["event_id"]
        learning = call("GET", base + "/state")
        history = call("GET", f"/api/v1/learning/events/{item}")
        assert learning["learner"]["assessment_progress"]["event_count"] == 1
        assert history["count"] == 1

        purpose = "public research synthetic engineering bridge"
        grant_body = {"schema": "archeaxis.context-grant/v1", "purpose": purpose, "consumer": "local-machine",
            "operations": ["answer"], "knowledge_id": knowledge["knowledge_id"], "provenance": [],
            "authorization_basis": "synthetic fixture grant", "expires_at": None, "state": "granted"}
        grant = call("POST", "/api/v1/documents", {"title": "Synthetic local machine grant", "editor_json": {
            "type": "doc", "content": [], "attrs": {"archeaxis_context_grant": grant_body}}}, expected=201)
        answer_request = {"client_request_id": "public-bridge-machine-answer", "knowledge_id": knowledge["knowledge_id"],
            "question": "Briefly describe the supplied unverified research excerpt, without claiming it is established fact.",
            "context_grant": {**snap(grant), "purpose": purpose}, "max_tokens": 4096, "timeout_s": 120}
        status, answer = request(core, "POST", "/api/v1/machine/answers", answer_request, timeout=150)
        receipt["machine_http_status"] = status
        if status != 200:
            receipt["machine_failure_code"] = answer.get("reason_code") or answer.get("code")
        assert status == 200, f"machine request returned HTTP {status}"
        assert answer["request"]["context_sha256"] == hashlib.sha256(knowledge["body"].encode("utf-8")).hexdigest()
        if real_model:
            model = answer["answer"]
            assert model["requested_model"] == model["observed_model"] == MODEL and model["endpoint"] == BASE
            assert model["finish_reason"] == "stop" and model["truncated"] is False
            assert isinstance(model["answer"], str) and model["answer"].strip()
            receipt["requested_model"] = MODEL
            receipt["answer_sha256"] = hashlib.sha256(model["answer"].encode("utf-8")).hexdigest()
        else:
            assert answer["answer"]["model"] == "synthetic-worker"
        saved = call("GET", f"/api/v1/machine/tasks/{answer['answer_id']}")
        core.stop()
        core.with_machine = False
        core.start()
        assert core.request("GET", "/api/v1/capabilities/machine.answer")[0] == 404
        assert call("POST", "/api/v1/machine/answers", answer_request) == answer
        assert call("GET", base + "/state") == learning
        assert call("GET", f"/api/v1/learning/events/{item}") == history
        generated_backup = call("POST", "/api/v1/workspace/backups", {}, expected=201)
        assert generated_backup["verified"] is True
        core.stop()
        artifact = source_workspace / "backups" / generated_backup["filename"]
        assert Path(generated_backup["filename"]).name == generated_backup["filename"]
        generated_objects = Path(str(artifact) + ".objects")
        assert set(backup["source_sha_list"]) <= set(generated_backup["source_sha_list"])
        public_probe.verify_backup_objects(artifact, generated_objects, generated_backup["source_sha_list"],
                                           generated_backup["sha256"], launcher.filesystem_path)
        final_workspace = tmp_path / "bridge-restore"
        final_workspace.mkdir()
        result = subprocess.run([str(core_exe), "--maintenance-restore", str(final_workspace / "workspace.sqlite"),
            str(artifact)], capture_output=True, text=True, timeout=120, check=False)
        restored_again = json.loads(result.stdout) if result.stdout else {}
        assert result.returncode == 0 and restored_again.get("ok") is True
        assert restored_again.get("authorization_requires_new_grants") is True
        core = BridgeCore(core_exe, final_workspace, Path(sys.executable))
        core.with_machine = False
        core.start()
        second_state = call("GET", "/api/v1/workspace/ui-state")
        assert second_state["workspace_id"] == state["workspace_id"]
        assert second_state["restore_epoch"] != state["restore_epoch"]
        call("POST", "/api/v1/research/public/read", new_target, expected=409)
        second_target = {**new_target, "restore_epoch": second_state["restore_epoch"]}
        assert call("POST", "/api/v1/research/public/read", second_target) == search
        assert call("GET", steps["research_read"]["path"]) == document
        assert call("GET", steps["research_selected_original"]["path"]) == original
        assert call("GET", steps["research_resolve"]["path"]) == steps["research_resolve"]["body"]
        assert call("GET", steps["admission_read"]["path"]) == knowledge
        assert call("GET", base + "/state") == learning
        assert call("GET", f"/api/v1/learning/events/{item}") == history
        assert call("GET", f"/api/v1/machine/tasks/{answer['answer_id']}") == saved
        call("POST", "/api/v1/machine/answers", answer_request, expected=403)
        public_probe.verify_backup_objects(artifact, generated_objects, generated_backup["source_sha_list"],
                                           generated_backup["sha256"], launcher.filesystem_path)
        verify_input()
        receipt.update({"status": "LOCAL_ENGINEERING_SAMPLE", "old_epoch_refused": True,
            "source_and_anchor_preserved": True, "learning_review_recorded": True,
            "machine_context_sha256": answer["request"]["context_sha256"], "restart_without_worker": True,
            "second_backup_verified": True, "second_backup_objects_verified": len(generated_backup["source_sha_list"]),
            "second_independent_restore": True, "second_epoch_refused": True, "old_grant_refused": True,
            "input_bytes_unchanged": True, "installed_or_owner_acceptance": "NOT_ESTABLISHED"})
    finally:
        core.stop()
        if output := os.environ.get("AAOS_TEST_PUBLIC_BRIDGE_OUTPUT"):
            with Path(output).open("x", encoding="utf-8") as stream:
                json.dump(receipt, stream, ensure_ascii=False, indent=2)


RECHECK = REQUIRED + (
    "AAOS_TEST_PUBLIC_BRIDGE_RECEIPT", "AAOS_TEST_PUBLIC_BRIDGE_RECEIPT_SHA256",
    "AAOS_TEST_PUBLIC_BRIDGE_BACKUP", "AAOS_TEST_PUBLIC_BRIDGE_BACKUP_SHA256",
    "AAOS_TEST_PUBLIC_BRIDGE_TASK_ID",
)


@pytest.mark.skipif(not all(os.environ.get(key) for key in RECHECK), reason="explicit real-sample backup required")
def test_offline_recheck_of_public_bridge_backup(tmp_path):
    """Restore the named real-model sample without a public-network or model call."""
    from scripts.ci.real_core_grading_journey import Core
    from scripts.probes import aaos01_office_runtime_loop as office
    from scripts.probes import aaos_public_research_runtime_loop as public_probe

    launcher = office.load("public_bridge_recheck_launcher", ROOT / "scripts/release/backend_launcher.py")
    public_path = Path(os.environ["AAOS_TEST_PUBLIC_RESEARCH_RECEIPT"]).resolve(strict=True)
    sample_path = Path(os.environ["AAOS_TEST_PUBLIC_BRIDGE_RECEIPT"]).resolve(strict=True)
    backup_path = Path(os.environ["AAOS_TEST_PUBLIC_BRIDGE_BACKUP"]).resolve(strict=True)
    core_exe = Path(os.environ["AAOS_TEST_CORE_EXE"]).resolve(strict=True)

    def checked_json(path, sha):
        data = launcher.filesystem_path(path).read_bytes()
        assert hashlib.sha256(data).hexdigest() == sha
        return json.loads(data)

    public_sha = os.environ["AAOS_TEST_PUBLIC_RESEARCH_RECEIPT_SHA256"]
    sample_sha = os.environ["AAOS_TEST_PUBLIC_BRIDGE_RECEIPT_SHA256"]
    backup_sha = os.environ["AAOS_TEST_PUBLIC_BRIDGE_BACKUP_SHA256"]
    public = checked_json(public_path, public_sha)
    sample = checked_json(sample_path, sample_sha)
    manifest_path = Path(str(backup_path) + ".manifest.json")
    manifest_bytes = launcher.filesystem_path(manifest_path).read_bytes()
    manifest = json.loads(manifest_bytes)
    assert manifest["filename"] == backup_path.name and manifest["sha256"] == backup_sha
    assert manifest["verified"] is True and set(public["backup"]["source_sha_list"]) <= set(manifest["source_sha_list"])
    assert sample["status"] == "LOCAL_ENGINEERING_SAMPLE" and sample["model_mode"] == "real_local"
    assert sample["input_receipt_sha256"] == public_sha and sample["second_backup_verified"] is True
    core_sha = hashlib.sha256(core_exe.read_bytes()).hexdigest()
    assert core_sha == sample["core_sha256"]
    assert core_sha == next(row["sha256"] for row in public["candidate_files"]
                            if str(row["path"]).lower().endswith("archeaxis-api.exe"))
    object_dir = Path(str(backup_path) + ".objects")

    def verify_inputs():
        checked_json(public_path, public_sha)
        checked_json(sample_path, sample_sha)
        assert launcher.filesystem_path(manifest_path).read_bytes() == manifest_bytes
        assert hashlib.sha256(core_exe.read_bytes()).hexdigest() == core_sha
        public_probe.verify_backup_objects(backup_path, object_dir, manifest["source_sha_list"], backup_sha,
                                           launcher.filesystem_path)

    verify_inputs()
    workspace = tmp_path / "offline-restore"
    workspace.mkdir()
    result = subprocess.run([str(core_exe), "--maintenance-restore", str(workspace / "workspace.sqlite"),
                             str(backup_path)], capture_output=True, text=True, timeout=120, check=False)
    restored = json.loads(result.stdout) if result.stdout else {}
    assert result.returncode == 0 and restored.get("ok") is True
    assert restored.get("authorization_requires_new_grants") is True
    steps = {row["label"]: row for row in public["steps"]}
    search = steps["public_search"]["body"]
    knowledge = steps["admission_read"]["body"]
    core = Core(core_exe, workspace, Path(sys.executable))

    def call(method, path, body=None, expected=200):
        status, value = core.request(method, path, body)
        assert status == expected, (method, path, status)
        return value

    try:
        core.start()
        assert call("GET", "/api/v1/capabilities/machine.answer", expected=404)
        state = call("GET", "/api/v1/workspace/ui-state")
        old_target = {key: search[key] for key in ("workspace_id", "restore_epoch", "request_id")}
        assert state["workspace_id"] == old_target["workspace_id"]
        assert state["restore_epoch"] != old_target["restore_epoch"]
        call("POST", "/api/v1/research/public/read", old_target, expected=409)
        assert call("POST", "/api/v1/research/public/read", {
            **old_target, "restore_epoch": state["restore_epoch"]}) == search
        for label in ("research_read", "research_selected_original", "research_resolve", "admission_read"):
            assert call("GET", steps[label]["path"]) == steps[label]["body"]
        item = "public-source-synthetic-learning"
        learning = call("GET", f"/api/v1/learning/items/{item}/state")["learner"]
        history = call("GET", f"/api/v1/learning/events/{item}")
        assessment = learning["assessment"]
        assert assessment["knowledge_id"] == knowledge["knowledge_id"]
        assert assessment["source_id"] == knowledge["source_id"] and assessment["anchor_id"] == knowledge["anchor_id"]
        assert learning["assessment_progress"]["event_count"] == history["count"] == 1
        outcome = json.loads(history["events"][0]["outcome"])
        assert outcome["assessment_id"] == assessment["assessment_id"]
        assert outcome["mastery_projection"]["closed"] is False
        task_id = os.environ["AAOS_TEST_PUBLIC_BRIDGE_TASK_ID"]
        saved = call("GET", f"/api/v1/machine/tasks/{task_id}")
        conditions = saved["conditions"]
        if isinstance(conditions, str):
            conditions = json.loads(conditions)
        assert conditions["request"]["context_sha256"] == sample["machine_context_sha256"]
        assert conditions["answer"]["requested_model"] == conditions["answer"]["observed_model"] == sample["requested_model"]
        assert conditions["answer"]["finish_reason"] == "stop" and conditions["answer"]["truncated"] is False
        assert hashlib.sha256(conditions["answer"]["answer"].encode("utf-8")).hexdigest() == sample["answer_sha256"]
        verify_inputs()
        if output := os.environ.get("AAOS_TEST_PUBLIC_BRIDGE_RECHECK_OUTPUT"):
            receipt = {"status": "OFFLINE_RECHECK_OF_REAL_SAMPLE_BACKUP", "sample_receipt_sha256": sample_sha,
                "backup_sha256": backup_sha, "core_sha256": core_sha, "source_objects_verified": len(manifest["source_sha_list"]),
                "old_public_epoch_refused": True, "source_and_anchor_preserved": True,
                "synthetic_learning_binding_preserved": True, "real_model_answer_hash_preserved": True,
                "new_public_network_or_model_request": False, "input_bytes_unchanged": True}
            with Path(output).open("x", encoding="utf-8") as stream:
                json.dump(receipt, stream, ensure_ascii=False, indent=2)
    finally:
        core.stop()
