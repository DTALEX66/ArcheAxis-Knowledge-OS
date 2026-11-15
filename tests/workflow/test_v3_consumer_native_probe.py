"""New probe guard regressions; simulated receipts, no Host/Core or real model.

The loopback test uses only the probe's synthetic server. These tests do not
qualify the five native UI consumers; that requires the explicit native run.
"""
from __future__ import annotations

import base64
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from urllib.request import ProxyHandler, Request, build_opener

import pytest

ROOT = Path(__file__).resolve().parents[2]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts/probes" / (name + ".py"))
    loaded = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(loaded)
    return loaded


@pytest.fixture
def probe():
    return module("aaos_v3_consumer_native")


class EnvironmentReached(Exception):
    pass


def cli(monkeypatch, flags):
    # Load only the actual two sibling imports, without changing sys.path.
    for name in ("aaos01_office_runtime_loop", "native_tcp_listeners"):
        monkeypatch.setitem(sys.modules, name, module(name))
    native = module("aaos01_tauri_webdriver_loop")
    monkeypatch.setattr(sys, "argv", ["probe", "--host", "never-launched.exe", *flags])
    monkeypatch.setattr(native, "probe_environment", lambda: (_ for _ in ()).throw(EnvironmentReached()))
    native.main()


def test_v3_mode_reaches_environment_without_inherited_modes(monkeypatch):
    for key in ("AAOS01_TEACHING_DRAFT_ONLY", "AAOS01_LEARNING_DRAFT_ONLY"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(EnvironmentReached):
        cli(monkeypatch, ["--v3-consumer-loop", "--build-receipt", "candidate.json"])


@pytest.mark.parametrize("flags", [
    ["--v3-consumer-loop"],
    ["--v3-consumer-loop", "--build-receipt", "candidate.json", "--grouped-common-owner-loop"],
    ["--v3-consumer-loop", "--build-receipt", "candidate.json", "--ui-format-conversion"],
    ["--v3-consumer-loop", "--build-receipt", "candidate.json", "--material-companion-cancel-loop"],
    ["--v3-consumer-loop", "--build-receipt", "candidate.json", "--v3-seed-receipt", "seed.json"],
    ["--v3-seed-receipt", "seed.json", "--v3-seed-receipt-sha256", "a" * 64],
])
def test_cli_refuses_ambiguous_authority_before_process_or_workspace(monkeypatch, flags):
    with pytest.raises(SystemExit) as error:
        cli(monkeypatch, flags)
    assert error.value.code == 2


def seed_fixture(tmp_path, probe):
    repo = tmp_path / "repo"
    output = repo / ".project-local/runs/w/s/artifacts/n"
    output.mkdir(parents=True)
    runtime = repo / ".project-local/runs/w/c/artifacts/r"
    core = runtime / "core/archeaxis-api.exe"
    core.parent.mkdir(parents=True)
    core.write_bytes(b"not executable: simulated identity")
    files = {"runtime/python.exe": b"synthetic Python identity", "workers/machine/worker_machine_answer.py": b"synthetic worker identity",
             "start-backend.py": b"synthetic launcher identity", "worker-profile.json": json.dumps({
                 "python": "runtime/python.exe", "routes": [{"capability": "machine.answer", "script": "workers/machine/worker_machine_answer.py"}]}).encode()}
    members = {}
    for name, content in files.items():
        member = runtime / name
        member.parent.mkdir(parents=True, exist_ok=True)
        member.write_bytes(content)
        members[name] = {"bytes": len(content), "sha256": probe.digest(content)}
    manifest = runtime / "backend-runtime-manifest.json"
    manifest.write_text(json.dumps({"files": members}), encoding="utf-8")
    binding = {"schema": "archeaxis.probe-runtime-binding/v1", "mode": "FORMAL_STAGED_RUNTIME",
               "manifest": {"sha256": probe.digest(manifest.read_bytes())},
               **{key: members[name] for key, name in {"python": "runtime/python.exe", "profile": "worker-profile.json",
                  "worker": "workers/machine/worker_machine_answer.py", "launcher": "start-backend.py"}.items()}}
    backup = output / "backups" / ("a" * 32 + ".sqlite")
    backup.parent.mkdir(); backup.write_bytes(b"simulated backup, no sqlite access")
    ref = {"document_id": "doc_seed", "version": 1, "content_sha256": "b" * 64}
    source = {"commit": "c" * 40, "patch_sha256": "d" * 64}
    seed = {"schema": "archeaxis.v3-native-seed/v1", "synthetic": True, "owner_acceptance": False,
        "source_worktree": str(repo), "source_commit": source["commit"], "source_patch_sha256": source["patch_sha256"],
        "core_sha256": probe.digest(core.read_bytes()), "workspace_id": "e" * 32, "restore_epoch": "initial",
        "runtime_manifest_sha256": probe.digest(manifest.read_bytes()), "runtime_binding": binding,
        "backup": {"path": str(backup), "sha256": probe.digest(backup.read_bytes()), "receipt": {
            "filename": backup.name, "verified": True, "schema": "archeaxis-core-backup-1", "sha256": probe.digest(backup.read_bytes())}},
        "snapshots": {name: copy.deepcopy(ref) for name in ("material_v1", "material_v2", "asset_candidate_v1", "asset_adopted_v1", "asset_candidate_v2", "asset_adopted_v2")}}
    path = output / "native-seed.json"
    def publish():
        path.write_text(json.dumps(seed), encoding="utf-8")
        return probe.digest(path.read_bytes())
    return SimpleNamespace(repo=repo, path=path, core=core, source=source, seed=seed, backup=backup, publish=publish)


def test_exact_project_owned_seed_is_accepted(probe, tmp_path_factory):
    f = seed_fixture(tmp_path_factory.mktemp("n"), probe)
    assert probe.load_seed(f.path, f.publish(), f.repo, f.core, f.source) == f.seed


@pytest.mark.parametrize("fault", ["missing_pin", "changed_manifest", "changed_python"])
def test_seed_rejects_different_runtime_even_with_the_same_core(probe, tmp_path_factory, fault):
    f = seed_fixture(tmp_path_factory.mktemp("n"), probe)
    if fault == "missing_pin":
        del f.seed["runtime_manifest_sha256"]
    elif fault == "changed_manifest":
        (f.core.parent.parent / "backend-runtime-manifest.json").write_bytes(b"{}")
    else:
        (f.core.parent.parent / "runtime/python.exe").write_bytes(b"other Python with unchanged Core")
    with pytest.raises(ValueError, match="runtime"):
        probe.load_seed(f.path, f.publish(), f.repo, f.core, f.source)


@pytest.mark.parametrize("fault", ["receipt_hash", "backup_hash", "candidate_core", "source_patch", "unverified_backup", "foreign_backup", "owner_claim"])
def test_seed_rejects_mismatched_or_foreign_handoff(probe, tmp_path, fault):
    f = seed_fixture(tmp_path, probe)
    expected = f.publish()
    if fault == "receipt_hash":
        f.path.write_bytes(f.path.read_bytes() + b" ")
    elif fault == "backup_hash":
        f.backup.write_bytes(b"changed")
    elif fault == "candidate_core":
        f.core.write_bytes(b"different executable")
    elif fault == "source_patch":
        f.source["patch_sha256"] = "f" * 64
    elif fault == "foreign_backup":
        foreign = tmp_path / "foreign.sqlite"; foreign.write_bytes(f.backup.read_bytes())
        f.seed["backup"]["path"] = str(foreign); expected = f.publish()
    elif fault == "owner_claim":
        f.seed["owner_acceptance"] = True; expected = f.publish()
    else:
        f.seed["backup"]["receipt"]["verified"] = False; expected = f.publish()
    with pytest.raises(ValueError):
        probe.load_seed(f.path, expected, f.repo, f.core, f.source)


def test_readonly_bridge_and_seed_allowlists_refuse_undeclared_writes(probe, tmp_path):
    calls = []
    j = probe.Journey(ui=None, bridge=lambda *args: calls.append(args), js=None, wait=None,
        restart=None, screenshot=None, work=tmp_path, report={}, model=None)
    for operation in ("document_create", "machine_answer", "learning_deeptutor_question_turn"):
        with pytest.raises(ValueError):
            j.read(operation, {"body": {}})
    with pytest.raises(ValueError):
        j.seed("machine_answer", {"body": {}})
    assert calls == []


def test_restore_uses_observed_target_and_normal_close_before_maintenance(probe, tmp_path, monkeypatch):
    f = seed_fixture(tmp_path, probe)
    work = f.repo / ".project-local/runs/worktree/native/tmp/journey"
    data = work / "data"; data.mkdir(parents=True)
    database = data / "archeaxis.sqlite"; database.write_bytes(b"empty simulated target")
    verbatim = "\\\\?\\" + str(database)
    events = []
    def run(command, **kwargs):
        events.append("maintenance")
        assert command == [str(f.core), "--maintenance-restore", str(database), str(f.backup)]
        assert kwargs["cwd"] == work and kwargs["env"] == {"OWNED": "child-only"}
        return SimpleNamespace(returncode=0, stdout=json.dumps({"ok": True, "verified": True,
            "authorization_requires_new_grants": True, "database": verbatim}))
    monkeypatch.setattr(probe.subprocess, "run", run)
    def read(operation):
        if operation == "system_version":
            return {"workspace_db": verbatim}
        return {"workspace_id": f.seed["workspace_id"], "restore_epoch": "f" * 32, "recovery_requires_confirmation": True}
    report = {}
    probe.restore_seed(f.seed, read=read, close=lambda: events.append("close"), launch=lambda: events.append("launch"),
        core=f.core, work=work, env={"OWNED": "child-only"}, report=report)
    assert events == ["close", "maintenance", "launch"]
    assert report["restore"]["receipt"]["authorization_requires_new_grants"] is True
    assert database.read_bytes() == b"empty simulated target", "Helper must never copy/patch SQLite"


@pytest.mark.parametrize("fault", ["unc_version", "other_filename", "foreign_maintenance"])
def test_restore_refuses_inexact_workspace_reports_before_consumer_actions(probe, tmp_path, monkeypatch, fault):
    f = seed_fixture(tmp_path, probe)
    work = f.repo / ".project-local/runs/worktree/native/tmp/journey"
    data = work / "data"; data.mkdir(parents=True)
    database = data / "archeaxis.sqlite"; database.write_bytes(b"empty simulated target")
    verbatim = "\\\\?\\" + str(database)
    reported = {"unc_version": "\\\\server\\share\\data\\archeaxis.sqlite",
                "other_filename": "\\\\?\\" + str(data / "other.sqlite"),
                "foreign_maintenance": verbatim}[fault]
    events = []
    def run(command, **kwargs):
        events.append("maintenance")
        assert command == [str(f.core), "--maintenance-restore", str(database), str(f.backup)]
        return SimpleNamespace(returncode=0, stdout=json.dumps({"ok": True, "verified": True,
            "authorization_requires_new_grants": True,
            "database": str(data / "other.sqlite") if fault == "foreign_maintenance" else verbatim}))
    monkeypatch.setattr(probe.subprocess, "run", run)
    def read(operation):
        if operation == "system_version":
            return {"workspace_db": reported}
        return {"workspace_id": f.seed["workspace_id"], "restore_epoch": "f" * 32, "recovery_requires_confirmation": True}
    with pytest.raises(ValueError):
        probe.restore_seed(f.seed, read=read, close=lambda: events.append("close"), launch=lambda: events.append("launch"),
            core=f.core, work=work, env={}, report={})
    assert "launch" not in events
    assert events == (["close", "maintenance"] if fault == "foreign_maintenance" else [])


@pytest.mark.parametrize("field", ["exit_code", "verified", "authorization_requires_new_grants"])
def test_unverified_restore_never_relaunches_consumers(probe, tmp_path, monkeypatch, field):
    f = seed_fixture(tmp_path, probe)
    work = f.repo / ".project-local/runs/worktree/native/tmp/journey"
    database = work / "data/archeaxis.sqlite"; database.parent.mkdir(parents=True); database.write_bytes(b"target")
    value = {"ok": True, "verified": True, "authorization_requires_new_grants": True, "database": str(database)}
    if field != "exit_code":
        value[field] = False
    monkeypatch.setattr(probe.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=1 if field == "exit_code" else 0, stdout=json.dumps(value)))
    launches = []
    with pytest.raises(AssertionError):
        probe.restore_seed(f.seed, read=lambda _op: {"workspace_db": str(database)}, close=lambda: None,
            launch=lambda: launches.append(True), core=f.core, work=work, env={}, report={})
    assert launches == []


def test_controlled_model_uses_owned_loopback_without_changing_global_environment(probe):
    before = dict(os.environ)
    service = probe.ControlledModel()
    try:
        env = service.start()
        assert env["ARCHEAXIS_MACHINE_ENDPOINT"].startswith("http://127.0.0.1:")
        assert dict(os.environ) == before
        opener = build_opener(ProxyHandler({}))
        request = Request(env["ARCHEAXIS_MACHINE_ENDPOINT"] + "/chat/completions",
            data=json.dumps({"model": probe.MODEL, "messages": [{"role": "user", "content": "synthetic input"}]}).encode(),
            headers={"Content-Type": "application/json"})
        with opener.open(request, timeout=5) as response:
            content = json.load(response)
        question = json.loads(content["choices"][0]["message"]["content"])
        assert question["correct_answer"] == "B"
        assert len(service.calls) == 1 and "messages" not in service.calls[0]
    finally:
        service.close()
    assert dict(os.environ) == before and not service.thread.is_alive()


def test_cancel_probe_rejects_a_cancel_of_another_frozen_payload(probe):
    pending = {"kind": "generate", "payload": {"body": {"create_request_id": "original"}}}
    material = {"document_id": "material", "version": 1, "content_sha256": "a" * 64}
    model = SimpleNamespace(calls=[], arm_delay=lambda: None, entered=SimpleNamespace(wait=lambda _s: True))
    j = SimpleNamespace(model=model, material_panel=lambda _m: "scope", type=lambda *_a: None,
        check=lambda *_a: None, journey=lambda *_a: None, namespace=lambda *_a: [(material, {"pending": pending})])
    def click(label, _scope):
        if label == "生成一道题目候选":
            model.calls.append({"synthetic": True})
    j.click = click
    j.returned = lambda _op: [{"operation": "learning_deeptutor_question_turn_cancel", "payload": {"body": {"create_request_id": "other"}},
                               "response": {"body": {"provider_stop_state": "UNKNOWN"}}}]
    with pytest.raises(AssertionError, match="exact frozen request"):
        probe.cancellation(j, {"cancel_material": material})
    assert pending["payload"]["body"]["create_request_id"] == "original"


def test_x8_cold_readback_difference_refuses_pass(probe, monkeypatch):
    calls = []
    j = SimpleNamespace(tag="synthetic", seed=lambda *_a: {"knowledge_id": "new"},
        read=lambda *_a: {"active": False, "currentness": "superseded"}, cold=lambda: calls.append("cold"), report={"consumers": {}})
    def read(_j, _fixtures, stage):
        calls.append(stage)
        return {"fixed_course_id": "old" if stage == "before-cold" else "different"}
    monkeypatch.setattr(probe, "x8_read", read)
    with pytest.raises(AssertionError):
        probe.x8(j, {"knowledge": {"knowledge_id": "old", "body": "fixed text", "version": 1}})
    assert calls == ["before-cold", "cold", "after-cold"]
    assert "x8" not in j.report["consumers"]


def historical_fixture(probe):
    raw = b"source-v1"
    source = {"source_id": "source", "source_revision": probe.digest(raw), "sha256": probe.digest(raw),
              "job_id": "text_job", "transform_id": "transform", "anchor_id": "anchor"}
    knowledge, tasks, fixed, documents, answer_refs, evaluations = {}, {}, {}, {}, [], []
    refs = {"source": source, "knowledge_grants": [], "asset_grants": []}
    for i in (1, 2):
        kid, task_id, text = f"knowledge_{i}", f"answer_{i}", f"fixed answer {i}"
        body = f"knowledge body {i}"
        knowledge[kid] = {"knowledge_id": kid, "version": i, "body": body, "source_id": "source", "anchor_id": "anchor"}
        refs[f"knowledge_v{i}"] = {"knowledge_id": kid, "review_version": i, "body_sha256": probe.digest(body.encode()),
            "source_id": "source", "anchor_id": "anchor", "source_revision": source["sha256"]}
        tasks[task_id] = {"task_id": task_id, "knowledge_version": kid + "@v1",
                          "conditions": json.dumps({"answer": {"answer": text}, "knowledge_id": kid})}
        binding = {"task_id": task_id, "knowledge_id": kid, "answer_sha256": probe.digest(text.encode()), "task_receipt_sha256": str(i) * 64}
        answer_refs.append(binding)
        fixed[task_id] = {"task_id": task_id, "knowledge_id": kid, "original_answer": text,
            "original_answer_sha256": binding["answer_sha256"], "task_receipt_sha256": binding["task_receipt_sha256"]}
        reference = {"document_id": f"evaluation_{i}", "version": 1, "content_sha256": "e" * 64}
        evaluations.append(reference)
        documents[reference["document_id"]] = {**reference, "editor_json": {"attrs": {"archeaxis_machine_evaluation": {
            "task_id": task_id, "knowledge_id": kid, "original_answer_sha256": binding["answer_sha256"],
            "task_receipt_sha256": binding["task_receipt_sha256"]}}}}
    grant = {"document_id": "prior_grant", "version": 1, "content_sha256": "f" * 64}
    refs["knowledge_grants"].append(grant); documents[grant["document_id"]] = dict(grant)
    refs.update(answers=answer_refs, evaluations=evaluations)
    anchor = {"anchor_id": "anchor", "source_id": "source", "source_revision": source["sha256"]}
    def read(op, payload):
        if op == "source_get": return source
        if op == "source_original": return {"sha256": source["sha256"], "content_base64": base64.b64encode(raw).decode()}
        if op == "source_job_transform": return {"transform_id": "transform"}
        if op == "anchors_list": return {"anchors": [anchor]}
        if op == "knowledge_get": return knowledge[payload["id"]]
        if op == "machine_task_get": return tasks[payload["task_id"]]
        if op == "machine_answer_snapshot": return fixed[payload["task_id"]]
        if op == "document_version": return documents[payload["document_id"]]
        raise AssertionError("Unexpected operation " + op)
    return SimpleNamespace(seed={"snapshots": refs}, read=read, anchor=anchor, fixed=fixed,
                           documents=documents, knowledge=knowledge)


def test_restored_history_reads_both_real_answer_bindings_and_evaluations(probe):
    f = historical_fixture(probe)
    proof = probe.seed_history(f, f.seed)
    assert [row["binding"]["task_id"] for row in proof["answers"]] == ["answer_1", "answer_2"]
    assert proof["evaluations"] == f.seed["snapshots"]["evaluations"]
    assert proof["old_grant_readback"] == f.seed["snapshots"]["knowledge_grants"]
    assert "old_grant_consumption_refusal" not in proof, "Read-only history is not a negative authorization execution test"


@pytest.mark.parametrize("fault", ["answer_bytes", "task_receipt", "evaluation_rebound", "anchor_rebound",
                                     "knowledge_body", "grant_version", "knowledge_version_rebound", "conditions_rebound"])
def test_history_refuses_rebound_answers_evaluation_anchor_or_grant(probe, fault):
    f = historical_fixture(probe)
    if fault == "answer_bytes":
        f.fixed["answer_1"]["original_answer"] = "changed answer"
    elif fault == "task_receipt":
        f.fixed["answer_2"]["task_receipt_sha256"] = "0" * 64
    elif fault == "knowledge_version_rebound":
        f.seed["snapshots"]["answers"][0]["knowledge_id"] = "unrelated"
    elif fault == "conditions_rebound":
        f.fixed["answer_1"]["knowledge_id"] = "unrelated"
    elif fault == "evaluation_rebound":
        f.documents["evaluation_2"]["editor_json"]["attrs"]["archeaxis_machine_evaluation"]["knowledge_id"] = "knowledge_1"
    elif fault == "anchor_rebound":
        f.anchor["source_id"] = "other_source"
    elif fault == "knowledge_body":
        f.knowledge["knowledge_2"]["body"] = "unexpected current text"
    else:
        f.documents["prior_grant"]["version"] = 2
    with pytest.raises(AssertionError):
        probe.seed_history(f, f.seed)


def test_chinese_css_attribute_selectors_keep_literal_unicode(probe):
    scripts = []
    j = SimpleNamespace(wait=lambda script: scripts.append(script))
    probe.Journey.text(j, "历史机器回答", '{"loan_days": 7}')
    assert len(scripts) == 1
    inner = scripts[0].split("document.querySelectorAll(", 1)[1].split(")", 1)[0]
    selector = json.loads(inner)
    assert selector == '[aria-label="历史机器回答"]'
    assert "\\u5386" not in selector
    source = (ROOT / "scripts/probes/aaos_v3_consumer_native.py").read_text(encoding="utf-8")
    assert "json.dumps(scope, ensure_ascii=False)" in source
